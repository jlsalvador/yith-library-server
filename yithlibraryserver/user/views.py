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

from deform import Button, Form, ValidationFailure

from pyramid.httpexceptions import HTTPBadRequest, HTTPFound
from pyramid.i18n import get_localizer
from pyramid.security import remember, forget
from pyramid.view import view_config, view_defaults, forbidden_view_config

from pyramid_sqlalchemy import Session

from yithlibraryserver.compat import url_quote
from yithlibraryserver.i18n import translation_domain
from yithlibraryserver.i18n import TranslationString as _
from yithlibraryserver.oauth2.decorators import protected_method
from yithlibraryserver.user import analytics
from yithlibraryserver.user.accounts import merge_accounts
from yithlibraryserver.user.accounts import notify_admins_of_account_removal
from yithlibraryserver.user.email_verification import EmailVerificationCode
from yithlibraryserver.user.models import User
from yithlibraryserver.user.schemas import UserSchema, NewUserSchema
from yithlibraryserver.user.schemas import AccountDestroySchema
from yithlibraryserver.user.schemas import UserPreferencesSchema


@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    login_url = request.route_path('login')
    referrer = request.path
    if request.query_string:
        referrer += '?' + request.query_string
    if referrer == login_url:
        referrer = request.route_path('oauth2_clients')
    came_from = request.params.get('came_from', referrer)
    return {
        'identity_providers': request.registry.identity_providers,
        'next_url': url_quote(came_from),
    }


@view_config(route_name='register_new_user',
             renderer='templates/register.pt')
def register_new_user(request):
    try:
        user_info = request.session['user_info']
    except KeyError:
        return HTTPBadRequest('Missing user info in the session')

    try:
        next_url = request.session['next_url']
    except KeyError:
        next_url = request.route_url('oauth2_clients')

    schema = NewUserSchema()
    button1 = Button('submit', _('Register into Yith Library'))
    button1.css_class = 'btn-primary'
    button2 = Button('cancel', _('Cancel'))
    button2.css_class = 'btn-default logout'

    form = Form(schema, buttons=(button1, button2))

    if 'submit' in request.POST:

        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {
                'form': e.render(),
                'provider': user_info.get('provider', ''),
                'email': user_info.get('email', ''),
                'next_url': next_url,
            }

        email = appstruct['email']
        if email != '' and email == user_info['email']:
            email_verified = True
        else:
            email_verified = False

        user_attrs = {
            'screen_name': appstruct['screen_name'],
            'first_name': appstruct['first_name'],
            'last_name': appstruct['last_name'],
            'email': email,
            'email_verified': email_verified,
        }

        if request.google_analytics.is_in_session():
            allow_analytics = request.google_analytics.show_in_session()
            user_attrs[analytics.USER_ATTR] = allow_analytics
            request.google_analytics.clean_session()

        user = User(**user_attrs)
        provider = user_info['provider']
        external_id = user_info['external_id']
        user.add_identity(provider, external_id)
        Session.add(user)

        if not email_verified and email != '':
            evc = EmailVerificationCode()
            user.email_verification_code = evc.code
            link = request.route_url('user_verify_email')
            evc.send(request, user, link)

        del request.session['user_info']
        if 'next_url' in request.session:
            del request.session['next_url']

        Session.flush()

        request.session['current_provider'] = provider
        return HTTPFound(location=next_url,
                         headers=remember(request, str(user.id)))
    elif 'cancel' in request.POST:
        del request.session['user_info']
        if 'next_url' in request.session:
            del request.session['next_url']

        return HTTPFound(location=next_url)

    return {
        'form': form.render({
            'first_name': user_info.get('first_name', ''),
            'last_name': user_info.get('last_name', ''),
            'screen_name': user_info.get('screen_name', ''),
            'email': user_info.get('email', ''),
        }),
        'provider': user_info.get('provider', ''),
        'email': user_info.get('email', ''),
        'next_url': next_url,
    }


@view_config(route_name='logout', renderer='string')
def logout(request):
    location = request.route_path('home')

    if 'current_provider' in request.session:
        current_provider = request.session['current_provider']
        del request.session['current_provider']

        if current_provider == 'persona':
            location += '?force-persona-logout=true'

    return HTTPFound(location=location,
                     headers=forget(request))


@view_config(route_name='user_destroy',
             renderer='templates/destroy.pt',
             permission='destroy-account')
def destroy(request):
    schema = AccountDestroySchema()
    button1 = Button('submit', _('Yes, I am sure. Destroy my account'))
    button1.css_class = 'btn-danger'
    button2 = Button('cancel', _('Cancel'))
    button2.css_class = 'btn-default'

    form = Form(schema, buttons=(button1, button2))

    user = request.user

    can_destroy = len(user.applications) == 0

    context = {
        'passwords': len(user.passwords),
        'can_destroy': can_destroy,
    }

    if 'submit' in request.POST:

        if not can_destroy:
            request.session.flash(
                _('You must remove your applications before destroying your account'),
                'error',
            )
            return HTTPFound(location=request.route_path('oauth2_developer_applications'))

        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            context['form'] = e.render()
            return context

        reason = appstruct['reason']
        notify_admins_of_account_removal(request, user, reason)

        Session.delete(user)

        request.session.flash(
            _('Your account has been removed. Have a nice day!'),
            'success',
        )
        return logout(request)

    elif 'cancel' in request.POST:
        request.session.flash(
            _('Thanks for reconsidering removing your account!'),
            'info',
        )
        return HTTPFound(location=request.route_path('user_information'))

    context['form'] = form.render()
    return context


@view_config(route_name='user_information',
             renderer='templates/user_information.pt',
             permission='edit-profile')
def user_information(request):
    schema = UserSchema()
    button1 = Button('submit', _('Save changes'))
    button1.css_class = 'btn-primary'

    form = Form(schema, buttons=(button1, ))

    user = request.user

    if 'submit' in request.POST:

        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {'form': e.render()}

        changes = {
            'first_name': appstruct['first_name'],
            'last_name': appstruct['last_name'],
            'screen_name': appstruct['screen_name'],
            'email': appstruct['email']['email'],
        }
        user.update_user_info(changes)

        Session.add(user)

        request.session.flash(
            _('The changes were saved successfully'),
            'success',
        )
        return HTTPFound(location=request.route_path('user_information'))

    return {
        'form': form.render({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'screen_name': user.screen_name,
            'email': {
                'email': user.email,
                'email_verified': user.email_verified,
            },
        }),
    }


@view_config(route_name='user_preferences',
             renderer='templates/preferences.pt',
             permission='edit-profile')
def preferences(request):
    schema = UserPreferencesSchema()
    button1 = Button('submit', _('Save changes'))
    button1.css_class = 'btn-primary'

    form = Form(schema, buttons=(button1, ))

    user = request.user

    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {'form': e.render()}

        user.update_preferences(appstruct)
        Session.add(user)

        request.session.flash(
            _('The changes were saved successfully'),
            'success',
        )
        return HTTPFound(location=request.route_path('user_preferences'))

    return {
        'form': form.render({
            'allow_google_analytics': user.allow_google_analytics,
            'send_passwords_periodically': user.send_passwords_periodically,
        })
    }


@view_config(route_name='user_identity_providers',
             renderer='templates/identity_providers.pt',
             permission='edit-profile')
def identity_providers(request):
    current_provider = request.session.get('current_provider', None)
    accounts = request.user.get_accounts(current_provider)
    context = {
        'accounts': accounts
    }
    verified = [ac for ac in accounts if ac['is_verified']]
    context['can_merge'] = len(verified) > 1

    if 'submit' in request.POST:
        if not context['can_merge']:
            return HTTPBadRequest('You do not have enough accounts to merge')

        def is_verified(ac):
            for a in accounts:
                if a['id'] == ac:
                    return a['is_verified']
            return False

        accounts_to_merge = [account.replace('account-', '')
                             for account in request.POST.keys()
                             if account != 'submit']
        accounts_to_merge = [account
                             for account in accounts_to_merge
                             if is_verified(account)]

        if len(accounts_to_merge) > 1:
            merged = merge_accounts(request.user, accounts_to_merge)
            localizer = get_localizer(request)
            msg = localizer.pluralize(
                _('Congratulations, ${n_merged} of your accounts has been merged into the current one'),
                _('Congratulations, ${n_merged} of your accounts have been merged into the current one'),
                merged,
                domain=translation_domain,
                mapping={'n_merged': merged},
            )
            request.session.flash(msg, 'success')
        else:
            request.session.flash(
                _('Not enough accounts for merging'),
                'error',
            )

        return HTTPFound(
            location=request.route_path('user_identity_providers'))

    return context


@view_config(route_name='user_send_email_verification_code',
             renderer='json',
             permission='edit-profile')
def send_email_verification_code(request):
    user = request.user
    if not user.email:
        return {
            'status': 'bad',
            'error': 'You have not an email in your profile',
        }

    if 'submit' in request.POST:
        evc = EmailVerificationCode()
        user.email_verification_code = evc.code
        link = request.route_url('user_verify_email')
        evc.send(request, request.user, link)
        return {'status': 'ok', 'error': None}
    else:
        return {'status': 'bad', 'error': 'Not a post'}


@view_config(route_name='user_verify_email',
             renderer='templates/verify_email.pt')
def verify_email(request):
    try:
        code = request.params['code']
    except KeyError:
        return HTTPBadRequest('Missing code parameter')

    try:
        email = request.params['email']
    except KeyError:
        return HTTPBadRequest('Missing email parameter')

    evc = EmailVerificationCode(code)
    user = evc.verify(email)
    if user is not None:
        request.session.flash(
            _('Congratulations, your email has been successfully verified'),
            'success',
        )
        user.verify_email()
        Session.add(user)
        return {
            'verified': True,
        }
    else:
        request.session.flash(
            _('Sorry, your verification code is not correct or has expired'),
            'error',
        )
        return {
            'verified': False,
        }


@view_config(route_name='user_google_analytics_preference', renderer='json')
def google_analytics_preference(request):
    if 'yes' in request.POST:
        allow = True
    elif 'no' in request.POST:
        allow = False
    else:
        return HTTPBadRequest('Missing preference parameter')

    if request.user is None:
        request.session[analytics.USER_ATTR] = allow
    else:
        request.user.allow_google_analytics = allow
        Session.add(request.user)

    return {'allow': allow}


@view_defaults(route_name='user_view', renderer='json')
class UserRESTView(object):

    def __init__(self, request):
        self.request = request

    @view_config(request_method='OPTIONS', renderer='string')
    def options(self):
        headers = self.request.response.headers
        headers['Access-Control-Allow-Methods'] = 'GET'
        headers['Access-Control-Allow-Headers'] = ('Origin, Content-Type, '
                                                   'Accept, Authorization')
        return ''

    @view_config(request_method='GET')
    @protected_method(['read-userinfo'])
    def get(self):
        return self.request.user.as_dict()
