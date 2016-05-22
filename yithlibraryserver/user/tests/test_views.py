# Yith Library Server is a password storage server.
# Copyright (C) 2012-2014 Yaco Sistemas
# Copyright (C) 2012-2014 Alejandro Blanco Escudero <alejandro.b.e@gmail.com>
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

import datetime

from freezegun import freeze_time

from deform import ValidationFailure

from pyramid_mailer import get_mailer

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

import transaction

from yithlibraryserver.compat import mock, url_quote
from yithlibraryserver.testing import TestCase
from yithlibraryserver.oauth2.models import (
    AccessCode,
    Application,
    AuthorizedApplication,
)
from yithlibraryserver.password.models import Password
from yithlibraryserver.user.analytics import USER_ATTR
from yithlibraryserver.user.models import ExternalIdentity, User


class DummyValidationFailure(ValidationFailure):

    def render(self):
        return 'dummy error'


def create_user(email='', email_verified=False,
                provider='twitter', external_id='twitter1', **kwargs):
    date = datetime.datetime(2012, 12, 12, 12, 12)
    user = User(screen_name='John Doe',
                first_name='John',
                last_name='Doe',
                email=email,
                email_verified=email_verified,
                creation=date,
                last_login=date,
                **kwargs)
    identity = ExternalIdentity(provider=provider,
                                external_id=external_id,
                                user=user)

    with transaction.manager:
        Session.add(user)
        Session.add(identity)
        Session.flush()
        user_id = user.id

    return user_id


def create_and_login_user(testapp, **kwargs):
    user_id = create_user(**kwargs)
    testapp.get('/__login/' + str(user_id))
    return user_id


class ViewTests(TestCase):

    def assertClearAuthCookie(self, headers):
        self.assertTrue('Set-Cookie' in headers)

        def parse_cookie(raw_string):
            pieces = [p.split('=') for p in raw_string.split(';')]
            return dict([(key.strip(), value) for key, value in pieces])

        cookies = [parse_cookie(value) for value in headers.getall('Set-Cookie')]

        for cookie in cookies:
            if 'auth_tkt' in cookie:
                self.assertEqual(cookie['auth_tkt'], '')
                self.assertEqual(cookie['Path'], '/')
                if 'Domain' in cookie:
                    self.assertEqual(cookie['Domain'], 'localhost')
                self.assertEqual(cookie['Max-Age'], '0')

    def test_login(self):
        res = self.testapp.get('/login?param1=value1&param2=value2')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in with Twitter')
        res.mustcontain('/twitter/login')
        res.mustcontain(url_quote('param1=value1&param2=value2'))

        res = self.testapp.get('/login')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in with Twitter')
        res.mustcontain('/twitter/login')
        res.mustcontain('next_url=/')

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_empty_session(self):
        res = self.testapp.get('/register', status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing user info in the session')

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_email_verified(self):
        self.testapp.post('/__session', {
            'next_url': 'http://localhost/foo/bar',
            'user_info__provider': 'facebook',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': 'john@example.com',
        }, status=302)

        res = self.testapp.get('/register')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain("It looks like it's the first time you log into the Yith Library.")
        res.mustcontain("Register into Yith Library")
        res.mustcontain("John")
        res.mustcontain("Doe")
        res.mustcontain("john@example.com")

        self.assertEqual(Session.query(User).count(), 0)
        res = self.testapp.post('/register', {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'submit': 'Register into Yith Library',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')
        self.assertEqual(Session.query(User).count(), 1)
        user = Session.query(User).filter(User.first_name == 'John').one()
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'john@example.com')
        self.assertEqual(user.email_verified, True)
        self.assertEqual(user.send_passwords_periodically, False)
        identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.external_id == '1234',
            ExternalIdentity.provider == 'facebook',
        ).one()
        self.assertEqual(identity.user, user)

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_email_not_verified(self):
        self.testapp.post('/__session', {
            'next_url': 'http://localhost/foo/bar',
            'user_info__provider': 'twitter',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': 'john@example.com',
        }, status=302)

        # if no email is provided at registration, the email is
        # not verified
        res = self.testapp.post('/register', {
            'first_name': 'John2',
            'last_name': 'Doe2',
            'email': '',
            'submit': 'Register into Yith Library',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')
        self.assertEqual(Session.query(User).count(), 1)
        user = Session.query(User).filter(User.first_name == 'John2').one()
        self.assertEqual(user.first_name, 'John2')
        self.assertEqual(user.last_name, 'Doe2')
        self.assertEqual(user.email, '')
        self.assertEqual(user.email_verified, False)
        self.assertEqual(user.send_passwords_periodically, False)
        identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.external_id == '1234',
            ExternalIdentity.provider == 'twitter',
        ).one()
        self.assertEqual(identity.user, user)

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_email_not_verified_neither_provided(self):
        self.testapp.post('/__session', {
            'next_url': 'http://localhost/foo/bar',
            'user_info__provider': 'google',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': '',
        }, status=302)

        # if an email is provided at registration, but
        # there is no email in the session (the provider
        # did not gave it to us) the email is not verified
        # and a verification email is sent
        res = self.testapp.post('/register', {
            'first_name': 'John2',
            'last_name': 'Doe2',
            'email': 'john@example.com',
            'submit': 'Register into Yith Library',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')
        self.assertEqual(Session.query(User).count(), 1)
        user = Session.query(User).filter(User.first_name == 'John2').one()
        self.assertEqual(user.first_name, 'John2')
        self.assertEqual(user.last_name, 'Doe2')
        self.assertEqual(user.email, 'john@example.com')
        self.assertEqual(user.email_verified, False)
        self.assertEqual(user.send_passwords_periodically, False)
        identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.external_id == '1234',
            ExternalIdentity.provider == 'google',
        ).one()
        self.assertEqual(identity.user, user)

        # check that the email was sent
        res.request.registry = self.testapp.app.registry
        mailer = get_mailer(res.request)
        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         'Please verify your email address')
        self.assertEqual(mailer.outbox[0].recipients,
                         ['john@example.com'])

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_wants_analytics_cookie(self):
        self.testapp.post('/__session', {
            'next_url': 'http://localhost/foo/bar',
            'user_info__provider': 'google',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': '',
            USER_ATTR: True,
        }, status=302)

        # The user want the Google Analytics cookie
        res = self.testapp.post('/register', {
            'first_name': 'John3',
            'last_name': 'Doe3',
            'email': 'john3@example.com',
            'submit': 'Register into Yith Library',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')
        self.assertEqual(Session.query(User).count(), 1)
        user = Session.query(User).filter(User.first_name == 'John3').one()
        self.assertFalse(user is None)
        self.assertEqual(user.first_name, 'John3')
        self.assertEqual(user.last_name, 'Doe3')
        self.assertEqual(user.email, 'john3@example.com')
        self.assertEqual(user.email_verified, False)
        self.assertEqual(user.allow_google_analytics, True)
        self.assertEqual(user.send_passwords_periodically, False)
        identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.external_id == '1234',
            ExternalIdentity.provider == 'google',
        ).one()
        self.assertEqual(identity.user, user)

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_canceled_with_next_url(self):
        self.testapp.post('/__session', {
            'next_url': 'http://localhost/foo/bar',
            'user_info__provider': 'twitter',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': 'john@example.com',
        }, status=302)

        # simulate a cancel
        res = self.testapp.post('/register', {
            'cancel': 'Cancel',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_canceled_without_next_url(self):
        self.testapp.post('/__session', {
            'user_info__provider': 'twitter',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': 'john@example.com',
        }, status=302)

        res = self.testapp.post('/register', {
            'cancel': 'Cancel',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/clients')

    @freeze_time('2013-01-02 10:11:02')
    def test_register_new_user_form_failed(self):
        self.testapp.post('/__session', {
            'user_info__provider': 'twitter',
            'user_info__external_id': '1234',
            'user_info__screen_name': 'John Doe',
            'user_info__first_name': 'John',
            'user_info__last_name': 'Doe',
            'user_info__email': 'john@example.com',
        }, status=302)

        with mock.patch('deform.Form.validate') as fake:
            fake.side_effect = DummyValidationFailure('f', 'c', 'e')
            res = self.testapp.post('/register', {
                'submit': 'Register into Yith Library',
            })
            self.assertEqual(res.status, '200 OK')

    def test_logout(self):
        # Log in
        self.testapp.get('/__login/twitter1')
        self.testapp.post('/__session', {
            'current_provider': 'twitter',
        }, status=302)

        res = self.testapp.get('/logout', status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/')

        self.assertClearAuthCookie(res.headers)
        self.assertFalse('current_provider' in self.get_session(res))

    def test_logout_from_persona(self):
        # Log in
        self.testapp.get('/__login/persona1')
        self.testapp.post('/__session', {
            'current_provider': 'persona',
        }, status=302)

        res = self.testapp.get('/logout', status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/?force-persona-logout=true')

        self.assertClearAuthCookie(res.headers)
        self.assertFalse('current_provider' in self.get_session(res))

    def test_user_information_requires_authentication(self):
        # this view required authentication
        res = self.testapp.get('/profile')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_user_information_make_changes(self):
        user_id = create_and_login_user(self.testapp)

        res = self.testapp.get('/profile')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Profile')
        res.mustcontain('John')
        res.mustcontain('Doe')
        res.mustcontain('Save changes')

        res = self.testapp.post('/profile', {
            'submit': 'Save changes',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/profile')
        # check that the user has changed
        new_user = Session.query(User).filter(User.id == user_id).one()

        self.assertEqual(new_user.first_name, 'John')
        self.assertEqual(new_user.last_name, 'Doe')
        self.assertEqual(new_user.email, 'john@example.com')

    def test_user_information_form_fail(self):
        create_and_login_user(self.testapp)

        # make the form fail
        with mock.patch('deform.Form.validate') as fake:
            fake.side_effect = DummyValidationFailure('f', 'c', 'e')
            res = self.testapp.post('/profile', {
                'submit': 'Save Changes',
            })
            self.assertEqual(res.status, '200 OK')

    def test_destroy_requires_authentication(self):
        # this view required authentication
        res = self.testapp.get('/destroy')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_destroy_cancel(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get('/destroy')
        res.mustcontain('Destroy account')
        res.mustcontain('Do you really really really want to destroy your account?')
        res.mustcontain('You will not be able to undo this operation')

        # simulate a cancel
        res = self.testapp.post('/destroy', {
            'cancel': 'Cancel',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/profile')

    def test_destroy_form_fail(self):
        create_and_login_user(self.testapp)

        # make the form fail
        with mock.patch('deform.Form.validate') as fake:
            fake.side_effect = DummyValidationFailure('f', 'c', 'e')
            res = self.testapp.post('/destroy', {
                'reason': '',
                'submit': 'Yes, I am sure. Destroy my account',
            })
            self.assertEqual(res.status, '200 OK')

    def test_destroy_user_who_owns_application_warning_message(self):
        user_id = create_and_login_user(self.testapp,
                                        email='john@example.com',
                                        email_verified=True)
        app = Application(name='Test Application',
                          callback_url='https://example.com/callback/',
                          user_id=user_id)
        with transaction.manager:
            Session.add(app)
            Session.flush()

        res = self.testapp.get('/destroy')
        res.mustcontain('This account can not be destroyed')
        res.mustcontain('You can not destroy this account because '
                        'you are the owner of an application')
        res.mustcontain('Please remove the application first')
        res.mustcontain('Go to my appplications')

    def test_destroy_user_who_owns_application_error_message(self):
        user_id = create_and_login_user(self.testapp,
                                        email='john@example.com',
                                        email_verified=True)
        app = Application(name='Test Application',
                          callback_url='https://example.com/callback/',
                          user_id=user_id)
        with transaction.manager:
            Session.add(app)
            Session.flush()

        res = self.testapp.post('/destroy', {
            'reason': 'I do not need a password manager',
            'submit': 'Yes, I am sure. Destroy my account',
        }, status=302)
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')

        res = self.testapp.get('/oauth2/applications')
        res.mustcontain('You must remove your applications before '
                        'destroying your account')

    def test_destroy_success(self):
        user_id = create_and_login_user(self.testapp)

        # this user has a password, an authorized app and an access code
        password = Password(secret='s3cr3t',
                            user_id=user_id)

        admin = User(screen_name='Alice doe',
                     first_name='Alice',
                     last_name='Doe',
                     email='alice@example.com')
        app = Application(name='Test Application',
                          callback_url='https://example.com/callback')
        admin.applications.append(app)
        auth_app = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback',
            application=app,
            user_id=user_id,
        )
        access_code = AccessCode(code='1234',
                                 code_type='Bearer',
                                 expiration=datetime.datetime(2014, 2, 23, 9, 0),
                                 scope=['read-userinfo'],
                                 user_id=user_id,
                                 application=app)

        with transaction.manager:
            Session.add(password)
            Session.add(admin)
            Session.add(app)
            Session.add(auth_app)
            Session.add(access_code)

        res = self.testapp.post('/destroy', {
            'reason': 'I do not need a password manager',
            'submit': 'Yes, I am sure. Destroy my account',
        }, status=302)
        self.assertEqual(res.location, 'http://localhost/')

        self.assertClearAuthCookie(res.headers)

        try:
            user = Session.query(User).filter(User.id == user_id).one()
        except NoResultFound:
            user = None
        self.assertEqual(user, None)

        identities = Session.query(ExternalIdentity).filter(
            ExternalIdentity.user_id == user_id
        ).count()
        self.assertEqual(identities, 0)

        authorized_apps = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id
        ).count()
        self.assertEqual(authorized_apps, 0)

        access_codes = Session.query(AccessCode).filter(
            AccessCode.user_id == user_id
        ).count()
        self.assertEqual(access_codes, 0)

        passwords = Session.query(Password).filter(
            Password.user_id == user_id
        ).count()
        self.assertEqual(passwords, 0)

        res.request.registry = self.testapp.app.registry
        mailer = get_mailer(res.request)
        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         'A user has destroyed his Yith Library account')
        self.assertEqual(mailer.outbox[0].recipients,
                         ['admin1@example.com', 'admin2@example.com'])
        self.assertTrue('I do not need a password manager' in mailer.outbox[0].body)

    def test_send_email_verification_code_requires_authentication(self):
        res = self.testapp.get('/send-email-verification-code')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_send_email_verification_code_user_has_no_email(self):
        create_and_login_user(self.testapp)

        # the user has no email so an error is expected
        res = self.testapp.get('/send-email-verification-code')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {
            'status': 'bad',
            'error': 'You have not an email in your profile',
        })

    def test_send_email_verification_code_wrong_method(self):
        create_and_login_user(self.testapp, email='john@example.com')

        # the request must be a post
        res = self.testapp.get('/send-email-verification-code')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {
            'status': 'bad',
            'error': 'Not a post',
        })

    def test_send_email_verification_code_good_request(self):
        create_and_login_user(self.testapp, email='john@example.com')

        res = self.testapp.post('/send-email-verification-code', {
            'submit': 'Send verification code'})
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {
            'status': 'ok',
            'error': None,
        })
        res.request.registry = self.testapp.app.registry
        mailer = get_mailer(res.request)
        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         'Please verify your email address')
        self.assertEqual(mailer.outbox[0].recipients,
                         ['john@example.com'])

    def test_verify_email_no_code_parameter(self):
        res = self.testapp.get('/verify-email', status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing code parameter')

    def test_verify_email_no_email_parameter(self):
        res = self.testapp.get('/verify-email?code=1234', status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing email parameter')

    def test_verify_email_bad_code(self):
        res = self.testapp.get('/verify-email?code=1234&email=john@example.com')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Sorry, your verification code is not correct or has expired')

    def test_verify_email_good_code(self):
        user_id = create_user(email='john@example.com',
                              email_verification_code='1234')

        res = self.testapp.get('/verify-email?code=1234&email=john@example.com')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Congratulations, your email has been successfully verified')

        user = Session.query(User).filter(User.id == user_id).one()
        self.assertEqual(user.email_verified, True)
        self.assertEqual(user.email_verification_code, '')


class IdentityProviderViewTests(TestCase):

    def test_identity_providers_requires_authentication(self):
        res = self.testapp.get('/identity-providers')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_identity_providers_only_one_account(self):
        user1_id = create_and_login_user(self.testapp,
                                         email='john@example.com',
                                         email_verified=True)
        app1 = Application(name='Test Application',
                           callback_url='https://example.com/callback/1')
        app2 = Application(name='Test Application',
                           callback_url='https://example.com/callback/2')
        admin = User(screen_name='Alice doe',
                     first_name='Alice',
                     last_name='Doe',
                     email='alice@example.com')
        admin.applications.append(app1)
        admin.applications.append(app2)

        auth_app1 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/1',
            application=app1,
            user_id=user1_id,
        )
        auth_app2 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/2',
            application=app2,
            user_id=user1_id,
        )
        password = Password(secret='s3cr3t',
                            user_id=user1_id)

        with transaction.manager:
            Session.add(admin)
            Session.add(app1)
            Session.add(app2)
            Session.add(auth_app1)
            Session.add(auth_app2)
            Session.add(password)
            Session.flush()

        # one account is not enough for merging
        res = self.testapp.post('/identity-providers', {
            'submit': 'Merge my accounts',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('You do not have enough accounts to merge')

    def test_identity_providers_two_accounts_only_one_selected(self):
        user1_id = create_and_login_user(self.testapp,
                                         email='john@example.com',
                                         email_verified=True)
        user2_id = create_user(email='john@example.com',
                               email_verified=True,
                               provider='google',
                               external_id='google1')
        app1 = Application(name='Test Application',
                           callback_url='https://example.com/callback/1')
        app2 = Application(name='Test Application',
                           callback_url='https://example.com/callback/2')
        app3 = Application(name='Test Application',
                           callback_url='https://example.com/callback/3')
        admin = User(screen_name='Alice doe',
                     first_name='Alice',
                     last_name='Doe',
                     email='alice@example.com')
        admin.applications.append(app1)
        admin.applications.append(app2)
        admin.applications.append(app3)

        auth_app1 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/1',
            application=app1,
            user_id=user1_id,
        )
        auth_app2 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/2',
            application=app2,
            user_id=user1_id,
        )
        auth_app3 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/2',
            application=app2,
            user_id=user2_id,
        )
        auth_app4 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/3',
            application=app3,
            user_id=user2_id,
        )
        password1 = Password(secret='s3cr3t',
                             user_id=user1_id)
        password2 = Password(secret='s3cr3t',
                             user_id=user2_id)

        with transaction.manager:
            Session.add(admin)
            Session.add(app1)
            Session.add(app2)
            Session.add(app3)
            Session.add(auth_app1)
            Session.add(auth_app2)
            Session.add(auth_app3)
            Session.add(auth_app4)
            Session.add(password1)
            Session.add(password2)
            Session.flush()

        # now the profile view should say I can merge my accounts
        res = self.testapp.get('/identity-providers')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('You are registered with the following accounts',
                        'Merge my accounts',
                        'If you merge your accounts')

        # if only one account is selected or fake accounts
        # are selected nothing is merged
        res = self.testapp.post('/identity-providers', {
            'account-%s' % str(user1_id): 'on',
            'account-000000000000000000000000': 'on',
            'submit': 'Merge my accounts',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/identity-providers')
        self.assertEqual(3, Session.query(User).count())
        self.assertEqual(1, Session.query(Password).filter(
            Password.user_id == user1_id).count())
        self.assertEqual(1, Session.query(Password).filter(
            Password.user_id == user2_id).count())

    def test_identity_providers_two_accounts_two_selected(self):
        user1_id = create_and_login_user(self.testapp,
                                         email='john@example.com',
                                         email_verified=True)
        user2_id = create_user(email='john@example.com',
                               email_verified=True,
                               provider='google',
                               external_id='google1')
        app1 = Application(name='Test Application',
                           callback_url='https://example.com/callback/1')
        app2 = Application(name='Test Application',
                           callback_url='https://example.com/callback/2')
        app3 = Application(name='Test Application',
                           callback_url='https://example.com/callback/3')
        admin = User(screen_name='Alice doe',
                     first_name='Alice',
                     last_name='Doe',
                     email='alice@example.com')
        admin.applications.append(app1)
        admin.applications.append(app2)
        admin.applications.append(app3)

        auth_app1 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/1',
            application=app1,
            user_id=user1_id,
        )
        auth_app2 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/2',
            application=app2,
            user_id=user1_id,
        )
        auth_app3 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/2',
            application=app2,
            user_id=user2_id,
        )
        auth_app4 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback/3',
            application=app3,
            user_id=user2_id,
        )
        password1 = Password(secret='s3cr3t',
                             user_id=user1_id)
        password2 = Password(secret='s3cr3t',
                             user_id=user2_id)

        with transaction.manager:
            Session.add(admin)
            Session.add(app1)
            Session.add(app2)
            Session.add(app3)
            Session.add(auth_app1)
            Session.add(auth_app2)
            Session.add(auth_app3)
            Session.add(auth_app4)
            Session.add(password1)
            Session.add(password2)
            Session.flush()
            app1_id = app1.id
            app2_id = app2.id
            app3_id = app3.id

        # let's merge them
        res = self.testapp.post('/identity-providers', {
            'account-%s' % str(user1_id): 'on',
            'account-%s' % str(user2_id): 'on',
            'submit': 'Merge my accounts',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/identity-providers')

        # the accounts have been merged
        self.assertEqual(2, Session.query(User).count())
        user1_refreshed = Session.query(User).filter(User.id == user1_id).one()
        google_identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.user == user1_refreshed,
            ExternalIdentity.provider == 'google',
        ).one()
        self.assertEqual(google_identity.external_id, 'google1')
        auths = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user == user1_refreshed,
        )
        client_ids = [auth_app.application.id for auth_app in auths]
        self.assertEqual(set(client_ids), set([app1_id, app2_id, app3_id]))

        try:
            user2_refreshed = Session.query(User).filter(User.id == user2_id).one()
        except NoResultFound:
            user2_refreshed = None
        self.assertEqual(user2_refreshed, None)

        self.assertEqual(2, Session.query(Password).filter(
            Password.user_id == user1_id).count())

    def test_google_analytics_preference_no_preference_parameter(self):
        res = self.testapp.post('/google-analytics-preference', status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing preference parameter')

    def test_google_analytics_preference_anonymous_users(self):
        # Anonymous users save the preference in the session
        res = self.testapp.post('/google-analytics-preference', {'yes': 'Yes'})
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {'allow': True})
        self.assertEqual(self.get_session(res)[USER_ATTR], True)

        res = self.testapp.post('/google-analytics-preference', {'no': 'No'})
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {'allow': False})
        self.assertEqual(self.get_session(res)[USER_ATTR], False)

    def test_google_analytics_preference_auth_users(self):
        # Authenticated users save the preference in the database
        user_id = create_and_login_user(self.testapp, email='john@example.com')

        res = self.testapp.post('/google-analytics-preference', {'yes': 'Yes'})
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {'allow': True})
        user_refreshed = Session.query(User).filter(User.id == user_id).one()
        self.assertEqual(user_refreshed.allow_google_analytics, True)

        res = self.testapp.post('/google-analytics-preference', {'no': 'No'})
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {'allow': False})
        user_refreshed = Session.query(User).filter(User.id == user_id).one()
        self.assertEqual(user_refreshed.allow_google_analytics, False)


class RESTViewTests(TestCase):

    def setUp(self):
        super(RESTViewTests, self).setUp()

        self.access_code = '1234'
        self.user_id = create_user(email='john@example.com',
                                   email_verified=True,
                                   allow_google_analytics=True)
        app = Application(name='test-app')
        admin = User(screen_name='Alice doe',
                     first_name='Alice',
                     last_name='Doe',
                     email='alice@example.com')
        admin.applications.append(app)
        with transaction.manager:
            Session.add(app)
            Session.add(admin)
            Session.flush()
            self.application_id = app.id

    def test_user_options(self):
        res = self.testapp.options('/user')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, b'')
        self.assertEqual(res.headers['Access-Control-Allow-Methods'],
                         'GET')
        self.assertEqual(res.headers['Access-Control-Allow-Headers'],
                         'Origin, Content-Type, Accept, Authorization')

    @freeze_time('2014-02-23 08:00:00')
    def test_user_get(self):
        expiration = datetime.datetime(2014, 2, 23, 9, 0)

        access_code = AccessCode(code=self.access_code,
                                 code_type='Bearer',
                                 expiration=expiration,
                                 scope=['read-userinfo'],
                                 user_id=self.user_id,
                                 application_id=self.application_id)
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

        auth_header = {'Authorization': 'Bearer %s' % self.access_code}

        res = self.testapp.get('/user', headers=auth_header)
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {
            'id': self.user_id,
            'screen_name': 'John Doe',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'email_verified': True,
            'allow_google_analytics': True,
            'send_passwords_periodically': False,
            'creation': '2012-12-12T12:12:00',
            'last_login': '2012-12-12T12:12:00',
        })


class PreferencesTests(TestCase):

    def test_authentication_required(self):
        # this view required authentication
        res = self.testapp.get('/preferences')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_backup_form_messages(self):
        create_and_login_user(self.testapp, allow_google_analytics=False)
        res = self.testapp.get('/preferences')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain(
            'Preferences',
            'Allow statistics cookie',
            'You will receive your passwords backup on the first day of the month',
            'Save changes',
        )

    def test_save_changes(self):
        user_id = create_and_login_user(self.testapp, allow_google_analytics=False)
        res = self.testapp.post('/preferences', {
            'submit': 'Save changes',
            'allow_google_analytics': 'true',
            'send_passwords_periodically': 'false',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/preferences')
        # check that the user has changed
        new_user = Session.query(User).filter(User.id == user_id).one()
        self.assertEqual(new_user.allow_google_analytics, True)
        self.assertEqual(new_user.send_passwords_periodically, False)

    def test_form_fail(self):
        create_and_login_user(self.testapp, allow_google_analytics=False)
        # make the form fail
        with mock.patch('deform.Form.validate') as fake:
            fake.side_effect = DummyValidationFailure('f', 'c', 'e')
            res = self.testapp.post('/preferences', {
                'submit': 'Save Changes',
            })
            self.assertEqual(res.status, '200 OK')
