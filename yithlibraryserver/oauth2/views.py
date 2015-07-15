# Yith Library Server is a password storage server.
# Copyright (C) 2012-2013 Yaco Sistemas
# Copyright (C) 2012-2013 Alejandro Blanco Escudero <alejandro.b.e@gmail.com>
# Copyright (C) 2012-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# This file is part of Yith Library Server.
#
# Yith Library Server is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Yith Library Server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Yith Library Server.  If not, see <http://www.gnu.org/licenses/>.

import uuid

from deform import Button, Form, ValidationFailure

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPFound,
    HTTPNotFound,
)
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.view import view_config

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import true

from oauthlib.oauth2 import (
    AccessDeniedError,
    FatalClientError,
    OAuth2Error,
    Server,
)

from yithlibraryserver.i18n import TranslationString as _
from yithlibraryserver.oauth2.models import (
    Application,
    AuthorizedApplication,
)
from yithlibraryserver.oauth2.schemas import ApplicationSchema
from yithlibraryserver.oauth2.schemas import FullApplicationSchema
from yithlibraryserver.oauth2.utils import (
    create_response,
    extract_params,
    response_from_error,
)
from yithlibraryserver.oauth2.validator import RequestValidator
from yithlibraryserver.user.security import assert_authenticated_user_is_registered


@view_config(route_name='oauth2_developer_applications',
             renderer='templates/developer_applications.pt',
             permission='view-applications')
def developer_applications(request):
    assert_authenticated_user_is_registered(request)
    return {
        'applications': request.user.applications,
    }


@view_config(route_name='oauth2_developer_application_new',
             renderer='templates/developer_application_new.pt',
             permission='add-application')
def developer_application_new(request):
    assert_authenticated_user_is_registered(request)
    schema = ApplicationSchema()
    button1 = Button('submit', _('Save application'))
    button1.css_class = 'btn-primary'
    button2 = Button('cancel', _('Cancel'))
    button2.css_class = 'btn-default'
    form = Form(schema, buttons=(button1, button2))

    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {'form': e.render()}

        # the data is fine, save into the db
        application = Application(
            name=appstruct['name'],
            main_url=appstruct['main_url'],
            callback_url=appstruct['callback_url'],
            authorized_origins=appstruct['authorized_origins'],
            production_ready=appstruct['production_ready'],
            image_url=appstruct['image_url'],
            description=appstruct['description'],
        )
        request.user.applications.append(application)

        request.session.flash(
            _('The application ${app} was created successfully',
              mapping={'app': appstruct['name']}),
            'success')

        Session.add(request.user)

        return HTTPFound(
            location=request.route_path('oauth2_developer_applications'))
    elif 'cancel' in request.POST:
        return HTTPFound(
            location=request.route_path('oauth2_developer_applications'))

    # this is a GET
    return {'form': form.render()}


@view_config(route_name='oauth2_developer_application_edit',
             renderer='templates/developer_application_edit.pt',
             permission='edit-application')
def developer_application_edit(request):
    app_id = request.matchdict['app']

    try:
        uuid.UUID(app_id)
    except ValueError:
        return HTTPBadRequest()

    try:
        app = Session.query(Application).filter(Application.id == app_id).one()
    except NoResultFound:
        return HTTPNotFound()

    assert_authenticated_user_is_registered(request)

    if app.user != request.user:
        return HTTPUnauthorized()

    schema = FullApplicationSchema()
    button1 = Button('submit', _('Save application'))
    button1.css_class = 'btn-primary'
    button2 = Button('delete', _('Delete application'))
    button2.css_class = 'btn-danger'
    button3 = Button('cancel', _('Cancel'))
    button3.css_class = 'btn-default'
    form = Form(schema, buttons=(button1, button2, button3))

    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {'form': e.render(), 'app': app}

        # the data is fine, save into the db
        app.name = appstruct['name']
        app.main_url = appstruct['main_url']
        app.callback_url = appstruct['callback_url']
        app.authorized_origins = appstruct['authorized_origins']
        app.production_ready = appstruct['production_ready']
        app.image_url = appstruct['image_url']
        app.description = appstruct['description']

        Session.add(app)

        request.session.flash(_('The changes were saved successfully'),
                              'success')

        return HTTPFound(
            location=request.route_path('oauth2_developer_applications'))
    elif 'delete' in request.POST:
        return HTTPFound(
            location=request.route_path('oauth2_developer_application_delete',
                                        app=app.id))
    elif 'cancel' in request.POST:
        return HTTPFound(
            location=request.route_path('oauth2_developer_applications'))

    # this is a GET
    return {
        'form': form.render({
            'name': app.name,
            'main_url': app.main_url,
            'callback_url': app.callback_url,
            'authorized_origins': app.authorized_origins,
            'production_ready': app.production_ready,
            'image_url': app.image_url,
            'description': app.description,
            'client_id': app.id,
            'client_secret': app.secret,
        }),
        'app': app,
    }


@view_config(route_name='oauth2_developer_application_delete',
             renderer='templates/developer_application_delete.pt',
             permission='delete-application')
def developer_application_delete(request):
    app_id = request.matchdict['app']

    try:
        uuid.UUID(app_id)
    except ValueError:
        return HTTPBadRequest()

    try:
        app = Session.query(Application).filter(Application.id == app_id).one()
    except NoResultFound:
        return HTTPNotFound()

    assert_authenticated_user_is_registered(request)
    if app.user != request.user:
        return HTTPUnauthorized()

    if 'submit' in request.POST:
        Session.delete(app)
        request.session.flash(
            _('The application ${app} was deleted successfully',
              mapping={'app': app.name}),
            'success',
        )
        return HTTPFound(
            location=request.route_path('oauth2_developer_applications'))

    return {'app': app}


class AuthorizationEndpoint(object):

    def __init__(self, request):
        self.request = request
        self.validator = RequestValidator()
        self.server = Server(self.validator)

    @view_config(route_name='oauth2_authorization_endpoint',
                 renderer='templates/application_authorization.pt',
                 permission='add-authorized-app',
                 request_method='GET')
    def get(self):
        uri, http_method, body, headers = extract_params(self.request)

        try:
            scopes, credentials = self.server.validate_authorization_request(
                uri, http_method, body, headers,
            )

            app = self.validator.get_client(credentials['client_id'])

            try:
                auth_app = Session.query(AuthorizedApplication).filter(
                    AuthorizedApplication.user == self.request.user,
                    AuthorizedApplication.scope == scopes,
                    AuthorizedApplication.redirect_uri == credentials['redirect_uri'],
                    AuthorizedApplication.response_type == credentials['response_type'],
                    AuthorizedApplication.application == app,
                ).one()
            except NoResultFound:
                auth_app = None

            if auth_app is not None:
                credentials['user'] = self.request.user
                server_response = self.server.create_authorization_response(
                    uri, http_method, body, headers, scopes, credentials,
                )
                return create_response(*server_response)
            else:
                authorship_information = app.user.email

                pretty_scopes = self.validator.get_pretty_scopes(scopes)
                return {
                    'response_type': credentials['response_type'],
                    'client_id': credentials['client_id'],
                    'redirect_uri': credentials['redirect_uri'],
                    'state': credentials['state'],
                    'scope': ' '.join(scopes),
                    'app': app,
                    'scopes': pretty_scopes,
                    'authorship_information': authorship_information,
                }
        except FatalClientError as e:
            return response_from_error(e)

        except OAuth2Error as e:
            return HTTPFound(e.in_uri(e.redirect_uri))

    @view_config(route_name='oauth2_authorization_endpoint',
                 permission='add-authorized-app',
                 request_method='POST')
    def post(self):
        uri, http_method, body, headers = extract_params(self.request)

        redirect_uri = self.request.POST.get('redirect_uri')
        if 'submit' in self.request.POST:
            scope = self.request.POST.get('scope', '')
            scopes = scope.split()
            credentials = {
                'client_id': self.request.POST.get('client_id'),
                'redirect_uri': redirect_uri,
                'response_type': self.request.POST.get('response_type'),
                'state': self.request.POST.get('state'),
                'user': self.request.user,
            }
            try:
                server_response = self.server.create_authorization_response(
                    uri, http_method, body, headers, scopes, credentials,
                )

                app = Session.query(Application).filter(
                    Application.id == credentials['client_id'],
                ).one()

                try:
                    auth_app = Session.query(AuthorizedApplication).filter(
                        AuthorizedApplication.user == self.request.user,
                        AuthorizedApplication.application == app,
                    ).one()
                except NoResultFound:
                    auth_app = AuthorizedApplication(
                        user=self.request.user,
                        application=app,
                    )

                auth_app.redirect_uri = credentials['redirect_uri']
                auth_app.response_type = credentials['response_type']
                auth_app.scope = scopes

                Session.add(auth_app)

                return create_response(*server_response)
            except FatalClientError as e:
                return response_from_error(e)

        elif 'cancel' in self.request.POST:
            e = AccessDeniedError()
            return HTTPFound(e.in_uri(redirect_uri))


@view_config(route_name='oauth2_token_endpoint',
             renderer='json')
def token_endpoint(request):
    validator = RequestValidator()
    server = Server(validator)

    uri, http_method, body, headers = extract_params(request)
    server_response = server.create_token_response(
        uri, http_method, body, headers, {},
    )
    return create_response(*server_response)


@view_config(route_name='oauth2_authorized_applications',
             renderer='templates/authorized_applications.pt',
             permission='view-applications')
def authorized_applications(request):
    assert_authenticated_user_is_registered(request)
    return {'authorized_apps': request.user.authorized_applications}


@view_config(route_name='oauth2_revoke_application',
             renderer='templates/application_revoke_authorization.pt',
             permission='revoke-authorized-app')
def revoke_application(request):
    app_id = request.matchdict['app']

    try:
        uuid.UUID(app_id)
    except ValueError:
        return HTTPBadRequest()

    try:
        app = Session.query(Application).filter(Application.id == app_id).one()
    except NoResultFound:
        return HTTPNotFound()

    assert_authenticated_user_is_registered(request)

    if 'submit' in request.POST:

        authorized_apps = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.application == app,
            AuthorizedApplication.user == request.user
        ).all()
        for authorized_app in authorized_apps:
            Session.delete(authorized_app)

        request.session.flash(
            _('The access to application ${app} has been revoked',
              mapping={'app': app.name}),
            'success',
        )
        return HTTPFound(
            location=request.route_path('oauth2_authorized_applications'))

    return {'app': app}


@view_config(route_name='oauth2_clients',
             renderer='templates/clients.pt')
def clients(request):
    apps = Session.query(Application).filter(Application.production_ready == true())
    return {'apps': apps}
