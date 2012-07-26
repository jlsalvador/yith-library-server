import bson
from deform import Button, Form, ValidationFailure

from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.httpexceptions import HTTPNotImplemented, HTTPUnauthorized
from pyramid.view import view_config

from yithlibraryserver.oauth2.application import create_client_id_and_secret
from yithlibraryserver.oauth2.authentication import authenticate_client
from yithlibraryserver.oauth2.authorization import Authorizator
from yithlibraryserver.oauth2.schemas import ApplicationSchema
from yithlibraryserver.user.security import assert_authenticated_user_is_registered


DEFAULT_SCOPE = 'passwords'


@view_config(route_name='oauth2_applications',
             renderer='templates/applications.pt',
             permission='view-applications')
def applications(request):
    assert_authenticated_user_is_registered(request)
    authorized_apps_filter = {'_id': {'$in': request.user['authorized_apps']}}
    owned_apps_filter = {'owner': request.user['_id']}
    return {
        'screen_name': request.user['screen_name'],
        'authorized_apps': request.db.applications.find(authorized_apps_filter),
        'applications': request.db.applications.find(owned_apps_filter)
        }


@view_config(route_name='oauth2_application_new',
             renderer='templates/application_new.pt',
             permission='add-application')
def application_new(request):
    assert_authenticated_user_is_registered(request)
    schema = ApplicationSchema()
    form = Form(schema, buttons=(Button('submit', 'Create application'),
                                 Button('cancel', 'Cancel')))
    form['main_url'].widget.css_class = 'input-xlarge'
    form['callback_url'].widget.css_class = 'input-xlarge'

    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {'form': e.render()}

        # the data is fine, save into the db
        application = {
            'owner': request.user['_id'],
            'name': appstruct['name'],
            'main_url': appstruct['main_url'],
            'callback_url': appstruct['callback_url'],
            }
        create_client_id_and_secret(application)

        request.db.applications.insert(application, safe=True)
        return HTTPFound(location=request.route_url('oauth2_applications'))
    elif 'cancel' in request.POST:
        return HTTPFound(location=request.route_url('oauth2_applications'))

    # this is a GET
    return {'form': form.render()}


@view_config(route_name='oauth2_application_view',
             renderer='templates/application_view.pt',
             permission='view-application')
def application_view(request):
    try:
        app_id = bson.ObjectId(request.matchdict['app'])
    except bson.errors.InvalidId:
        return HTTPBadRequest(body='Invalid application id')

    assert_authenticated_user_is_registered(request)

    app = request.db.applications.find_one(app_id)
    if app is None:
        return HTTPNotFound()

    if app['owner'] != request.user['_id']:
        return HTTPUnauthorized()

    return {'app': app}


@view_config(route_name='oauth2_application_delete',
             renderer='templates/application_delete.pt',
             permission='delete-application')
def application_delete(request):
    try:
        app_id = bson.ObjectId(request.matchdict['app'])
    except bson.errors.InvalidId:
        return HTTPBadRequest(body='Invalid application id')

    app = request.db.applications.find_one(app_id)
    if app is None:
        return HTTPNotFound()

    assert_authenticated_user_is_registered(request)
    if app['owner'] != request.user['_id']:
        return HTTPUnauthorized()

    if 'submit' in request.POST:
        request.db.applications.remove(app_id, safe=True)
        return HTTPFound(location=request.route_url('oauth2_applications'))

    return {'app': app}


@view_config(route_name='oauth2_authorization_endpoint',
             renderer='string')
def authorization_endpoint(request):
    response_type = request.params.get('response_type')
    if response_type is None:
        return HTTPBadRequest('Missing required response_type')

    if response_type != 'code':
        return HTTPNotImplemented('Only code is supported')

    # code grant
    client_id = request.params.get('client_id')
    if client_id is None:
        return HTTPBadRequest('Missing required client_type')

    app = request.db.applications.find_one({'client_id': client_id})
    if app is None:
        return HTTPNotFound()

    redirect_uri = request.params.get('redirect_uri')
    if redirect_uri is None:
        redirect_uri = app['callback_url']
    else:
        if redirect_uri != app['callback_url']:
            return HTTPBadRequest('Redirect URI does not match registered callback URL')

    scope = request.params.get('scope', DEFAULT_SCOPE)

    state = request.params.get('state')

    user = assert_authenticated_user_is_registered(request)

    authorizator = Authorizator(request.db, app)

    if user and authorizator.is_app_authorized(user):
        if 'authorization_info' in request.session:
            del request.session['authorization_info']

        code = authorizator.auth_codes.create(
            user['_id'], app['client_id'], scope)
        url = authorizator.auth_codes.get_redirect_url(
            code, redirect_uri, state)
        return HTTPFound(location=url)
    elif user:
        request.session['authorization_info'] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state
            }
        return HTTPFound(request.route_url('oauth2_authorize_application', app=str(app['_id'])))
    else:
        request.session['authorization_info'] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state
            }
        return HTTPFound(request.route_url('oauth2_authenticate_anonymous', app=str(app['_id'])))


@view_config(route_name='oauth2_authorize_application',
             renderer='templates/application_authorization.pt',
             permission='add-authorized-app')
def authorize_application(request):
    try:
        authorization_info = request.session['authorization_info']
    except KeyError:
        return HTTPBadRequest()

    assert_authenticated_user_is_registered(request)

    try:
        app_id = bson.ObjectId(request.matchdict['app'])
    except bson.errors.InvalidId:
        return HTTPBadRequest(body='Invalid application id')

    app = request.db.applications.find_one(app_id)
    if app is None:
        return HTTPNotFound()

    scope = authorization_info['scope']

    if 'submit' in request.POST:
        authorizator = Authorizator(request.db, app)
        if not authorizator.is_app_authorized(request.user):
            authorizator.store_user_authorization(request.user)

        redirect_uri = authorization_info['redirect_uri']
        state = authorization_info['state']
        del request.session['authorization_info']

        code = authorizator.auth_codes.create(
            request.user['_id'], app['client_id'], scope)
        url = authorizator.auth_codes.get_redirect_url(
            code, redirect_uri, state)
        return HTTPFound(location=url)

    return {'app': app, 'scopes': scope.split(' ')}


@view_config(route_name='oauth2_authenticate_anonymous',
             renderer='templates/authenticate_anonymous.pt')
def authenticate_anonymous(request):
    try:
        authorization_info = request.session['authorization_info']
    except KeyError:
        return HTTPBadRequest()

    try:
        app_id = bson.ObjectId(request.matchdict['app'])
    except bson.errors.InvalidId:
        return HTTPBadRequest(body='Invalid application id')

    app = request.db.applications.find_one(app_id)
    if app is None:
        return HTTPNotFound()

    scope = authorization_info['scope']

    return {'app': app, 'scopes': scope.split(' ')}


@view_config(route_name='oauth2_token_endpoint',
             renderer='json')
def token_endpoint(request):
    app = authenticate_client(request)

    grant_type = request.POST.get('grant_type')
    if grant_type is None:
        return HTTPBadRequest('Missing required grant_type')

    if grant_type != 'authorization_code':
        return HTTPNotImplemented('Only authorization_code is supported')

    code = request.POST.get('code')
    if code is None:
        return HTTPBadRequest('Missing required code')

    authorizator = Authorizator(request.db, app)

    grant = authorizator.auth_codes.find(code)
    if grant is None:
        return HTTPUnauthorized()

    # TODO: check if the grant is rotten

    if app['client_id'] != grant['client_id']:
        return HTTPUnauthorized()

    authorizator.auth_codes.remove(grant)

    request.response.headers['Cache-Control'] = 'no-store'
    request.response.headers['Pragma'] = 'no-cache'

    access_code = authorizator.access_codes.create(grant['user'], grant)

    return {
        'access_code': access_code,
        'token_type': 'bearer',
        'expires_in': 3600,
        'scope': grant['scope'],
        }


@view_config(route_name='oauth2_revoke_application',
             renderer='templates/application_revoke_authorization.pt',
             permission='revoke-authorized-app')
def revoke_application(request):
    assert_authenticated_user_is_registered(request)

    try:
        app_id = bson.ObjectId(request.matchdict['app'])
    except bson.errors.InvalidId:
        return HTTPBadRequest(body='Invalid application id')

    app = request.db.applications.find_one(app_id)
    if app is None:
        return HTTPNotFound()

    if 'submit' in request.POST:
        authorizator = Authorizator(request.db, app)
        authorizator.remove_user_authorization(request.user)

        return HTTPFound(location=request.route_url('oauth2_applications'))

    return {'app': app}
