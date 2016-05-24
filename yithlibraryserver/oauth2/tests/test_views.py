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

from freezegun import freeze_time

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

import transaction

from yithlibraryserver.compat import encodebytes, encode_header, urlparse
from yithlibraryserver.oauth2.models import (
    AccessCode,
    Application,
    AuthorizationCode,
    AuthorizedApplication,
)
from yithlibraryserver.oauth2.tests import create_client, create_user
from yithlibraryserver.testing import TestCase
from yithlibraryserver.user.models import User


def auth_basic_encode(user, password):
    value = '%s:%s' % (user, password)
    value = 'Basic ' + encodebytes(value.encode('utf-8')).decode('utf-8')
    return encode_header(value)


def create_and_login_user(testapp):
    user, user_id = create_user()
    testapp.get('/__login/' + str(user_id))
    return user, user_id


class AuthorizationEndpointTests(TestCase):

    def test_anonymous_user(self):
        res = self.testapp.get('/oauth2/endpoints/authorization')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_no_client_id(self):
        create_and_login_user(self.testapp)
        res = self.testapp.get('/oauth2/endpoints/authorization',
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Error is: invalid_request')

    def test_invalid_client_id(self):
        create_and_login_user(self.testapp)
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'client_id': '1234',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Error is: invalid_request')

    def _assert_error(self, url, error, description=None):
        query = urlparse.parse_qs(urlparse.urlparse(url).query)
        expected = {'error': [error]}
        if description:
            expected['error_description'] = [description]

        self.assertEqual(query, expected)

    def test_no_response_type(self):
        create_and_login_user(self.testapp)
        _, app_id, _ = create_client()
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'client_id': app_id,
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self._assert_error(res.location, 'invalid_request',
                           'Missing response_type parameter.')

    def test_invalid_redirect_callback(self):
        create_and_login_user(self.testapp)
        _, app_id, _ = create_client()
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'client_id': app_id,
            'response_type': 'code',
            'redirect_uri': 'https://example.com/bad-callback',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Error is: invalid_request')

    def test_user_cancel(self):
        create_and_login_user(self.testapp)
        _, app_id, _ = create_client()
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'client_id': app_id,
            'response_type': 'code',
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'cancel': 'No thanks',
            'response_type': 'code',
            'client_id': app_id,
            'redirect_uri': 'https://example.com/callback',
            'scope': 'read-passwords',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location,
                         'https://example.com/callback?error=access_denied')

    @freeze_time('2012-01-10 15:31:11')
    def test_non_authorized_app_yet(self):
        _, user_id = create_and_login_user(self.testapp)
        _, application_id, _ = create_client()

        count = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id,
        ).count()
        self.assertEqual(count, 0)

        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Authorize Application')
        res.mustcontain('Permissions:')
        res.mustcontain('Access your passwords')
        res.mustcontain('Allow access')
        res.mustcontain('No, thanks')
        res.mustcontain('You can revoke this authorization in the future.')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'submit': 'Authorize',
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
            'scope': 'read-passwords',
        })
        self.assertEqual(res.status, '302 Found')

        # Check that the app is authorized now
        query = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id,
        )

        self.assertEqual(query.count(), 1)
        auth = query[0]
        self.assertEqual(auth.redirect_uri, 'https://example.com/callback')
        self.assertEqual(auth.response_type, 'code')
        self.assertEqual(auth.application.id, application_id)
        self.assertEqual(auth.scope, ['read-passwords'])
        self.assertEqual(auth.user_id, user_id)
        self.assertEqual(auth.application_id, application_id)

        # Check the right redirect url
        grant = Session.query(AuthorizationCode).filter(
            AuthorizationCode.application_id == application_id,
            AuthorizationCode.user_id == user_id,
        ).one()
        self.assertEqual(grant.application.id, application_id)
        location = 'https://example.com/callback?code=%s' % grant.code
        self.assertEqual(res.location, location)

    @freeze_time('2012-01-10 15:31:11')
    def test_already_authorized_app(self):
        _, user_id = create_and_login_user(self.testapp)
        _, application_id, _ = create_client()

        count = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id,
        ).count()
        self.assertEqual(count, 0)

        # do an initial authorization
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'submit': 'Authorize',
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
            'scope': 'read-passwords',
        })
        self.assertEqual(res.status, '302 Found')

        count = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id,
        ).count()
        self.assertEqual(count, 1)

        # Now do a second authorization
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '302 Found')

        count = Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user_id == user_id,
        ).count()
        self.assertEqual(count, 1)

        grants = Session.query(AuthorizationCode).filter(
            AuthorizationCode.application_id == application_id,
            AuthorizationCode.user_id == user_id,
        )

        # There are two grants now
        self.assertEqual(grants.count(), 2)
        code = grants.all()[1].code
        location = 'https://example.com/callback?code=%s' % code
        self.assertEqual(res.location, location)

    @freeze_time('2012-01-10 15:31:11')
    def test_invalid_redirect_callback_in_post(self):
        create_and_login_user(self.testapp)
        _, app_id, _ = create_client()

        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': app_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'submit': 'Authorize',
            'response_type': 'code',
            'client_id': app_id,
            'redirect_uri': 'https://example.malicious.com/callback',
            'scope': 'read-passwords',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Error is: invalid_request')

    @freeze_time('2012-01-10 15:31:11')
    def test_no_response_type_in_post(self):
        create_and_login_user(self.testapp)
        _, app_id, _ = create_client()

        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': app_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'submit': 'Authorize',
            # missing response_type
            'client_id': app_id,
            'redirect_uri': 'https://example.com/callback',
            'scope': 'read-passwords',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self._assert_error(res.location, 'invalid_request',
                           'Missing response_type parameter.')


class TokenEndpointTests(TestCase):

    def test_no_grant_type(self):
        res = self.testapp.post('/oauth2/endpoints/token', {}, status=400)

        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.json, {
            'error': 'unsupported_grant_type'
        })

    def test_no_client(self):
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'password',
        }, status=401)
        self.assertEqual(res.status, '401 Unauthorized')
        self.assertEqual(res.json, {
            'error': 'invalid_client'
        })

    def test_invalid_client(self):
        headers = {
            'Authorization': auth_basic_encode('123456', 'secret'),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'password',
        }, headers=headers, status=401)
        self.assertEqual(res.json, {
            'error': 'invalid_client'
        })

    def test_bad_client_secret(self):
        _, app_id, _ = create_client()
        headers = {
            'Authorization': auth_basic_encode(app_id, 'secret'),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'password',
        }, headers=headers, status=401)
        self.assertEqual(res.json, {
            'error': 'invalid_client'
        })

    def test_usupported_grant_type(self):
        _, app_id, app_secret = create_client()
        headers = {
            'Authorization': auth_basic_encode(app_id, app_secret),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'foo',
        }, headers=headers, status=400)
        self.assertEqual(res.json, {
            'error': 'unsupported_grant_type'
        })

    def test_missing_code(self):
        _, app_id, app_secret = create_client()
        headers = {
            'Authorization': auth_basic_encode(app_id, app_secret),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'authorization_code',
        }, headers=headers, status=400)

        self.assertEqual(res.json, {
            'error': 'invalid_request',
            'error_description': 'Missing code parameter.',
        })

    def test_invalid_code(self):
        _, app_id, app_secret = create_client()
        headers = {
            'Authorization': auth_basic_encode(app_id, app_secret),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'authorization_code',
            'code': 'this-code-does-not-exist',
        }, headers=headers, status=401)

        self.assertEqual(res.json, {
            'error': 'invalid_grant',
        })

    @freeze_time('2012-01-10 15:31:11')
    def test_valid_request(self):
        _, user_id = create_and_login_user(self.testapp)
        _, application_id, application_secret = create_client()

        # First authorize the app
        res = self.testapp.get('/oauth2/endpoints/authorization', {
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
        })
        self.assertEqual(res.status, '200 OK')

        res = self.testapp.post('/oauth2/endpoints/authorization', {
            'submit': 'Authorize',
            'response_type': 'code',
            'client_id': application_id,
            'redirect_uri': 'https://example.com/callback',
            'scope': 'read-passwords',
        })
        self.assertEqual(res.status, '302 Found')
        grant = Session.query(AuthorizationCode).filter(
            AuthorizationCode.application_id == application_id,
            AuthorizationCode.user_id == user_id,
        ).one()
        code = grant.code

        # now send the token request
        headers = {
            'Authorization': auth_basic_encode(application_id,
                                               application_secret),
        }
        res = self.testapp.post('/oauth2/endpoints/token', {
            'grant_type': 'authorization_code',
            'code': code,
        }, headers=headers)
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.headers['Cache-Control'], 'no-store')
        self.assertEqual(res.headers['Pragma'], 'no-cache')

        # the grant code should be removed
        try:
            grant = Session.query(AuthorizationCode).filter(
                AuthorizationCode.application_id == application_id,
                AuthorizationCode.user_id == user_id,
            ).one()
        except NoResultFound:
            grant = None
        self.assertEqual(grant, None)

        # and an access token should be created
        self.assertEqual(res.json['token_type'], 'Bearer')
        self.assertEqual(res.json['expires_in'], 3600)

        access_code = Session.query(AccessCode).filter(
            AccessCode.code == res.json['access_token'],
        ).one()
        self.assertNotEqual(access_code, None)


class ApplicationViewTests(TestCase):

    def test_applications_requires_authentication(self):
        res = self.testapp.get('/oauth2/applications')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_applications_list_apps_empty(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get('/oauth2/applications')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('John')
        res.mustcontain('Log out')
        res.mustcontain('Developer Applications')
        res.mustcontain('Register new application')

    def test_applications_list_apps_one_app(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='https://example.com',
                          callback_url='https://example.com/callback',
                          production_ready=False)
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.flush()
            app_id = app.id
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.get('/oauth2/applications')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('John')
        res.mustcontain('Log out')
        res.mustcontain('Developer Applications')
        res.mustcontain('Register new application')
        res.mustcontain(app_id)
        res.mustcontain('Test Application')
        res.mustcontain('https://example.com')

    def test_application_new_requires_authentication(self):
        res = self.testapp.get('/oauth2/applications/new')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_application_new_success(self):
        _, user_id = create_and_login_user(self.testapp)

        res = self.testapp.get('/oauth2/applications/new')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('New Application')
        res.mustcontain('Name')
        res.mustcontain('Main URL')
        res.mustcontain('Callback URL')
        res.mustcontain('Authorized Origins')
        res.mustcontain('Production ready')
        res.mustcontain('Image URL')
        res.mustcontain('Description')

        res = self.testapp.post('/oauth2/applications/new', {
            'name': 'Test Application',
            'main_url': 'http://example.com',
            'callback_url': 'http://example.com/callback',
            'authorized_origins': '''http://example.com
https://example.com''',
            'submit': 'submit',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')

        app = Session.query(Application).filter(
            Application.name == 'Test Application',
            Application.main_url == 'http://example.com',
            Application.callback_url == 'http://example.com/callback',
            Application.authorized_origins == ['http://example.com',
                                               'https://example.com']
        ).one()
        self.assertNotEqual(app.id, '')
        self.assertNotEqual(app.secret, '')
        self.assertEqual(app.user.id, user_id)
        self.assertEqual(app.name, 'Test Application')
        self.assertEqual(app.main_url, 'http://example.com')
        self.assertEqual(app.callback_url, 'http://example.com/callback')
        self.assertEqual(app.authorized_origins,
                         ['http://example.com', 'https://example.com'])
        self.assertEqual(app.production_ready, False)
        self.assertEqual(app.image_url, '')
        self.assertEqual(app.description, '')

    def test_application_new_validation_error(self):
        create_and_login_user(self.testapp)

        res = self.testapp.post('/oauth2/applications/new', {
            'name': 'Test Application',
            'callback_url': 'http://example.com/callback',
            'submit': 'submit',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('There was a problem with your submission')

    def test_application_new_user_cancel(self):
        create_and_login_user(self.testapp)

        res = self.testapp.post('/oauth2/applications/new', {
            'cancel': 'Cancel',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')

    def test_application_delete_requires_authentication(self):
        res = self.testapp.get('/oauth2/applications/new')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_application_delete_invalid_app_id(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get('/oauth2/applications/000000000000000000000000/delete',
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_application_delete_app_id_doesnt_exist(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get(
            '/oauth2/applications/00000000-0000-0000-0000-000000000000/delete',
            status=404
        )
        self.assertEqual(res.status, '404 Not Found')

    def test_application_delete_unauthorized(self):
        create_and_login_user(self.testapp)

        app = Application(name='Test Application',
                          callback_url='https://example.com/callback',
                          production_ready=False)

        other_user = User(screen_name='Alice doe',
                          first_name='Alice',
                          last_name='Doe',
                          email='alice@example.com')

        other_user.applications.append(app)

        with transaction.manager:
            Session.add(other_user)
            Session.flush()
            app_id = app.id

        res = self.testapp.get('/oauth2/applications/%s/delete' % str(app_id),
                               status=401)
        self.assertEqual(res.status, '401 Unauthorized')

    def test_application_delete(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          callback_url='https://example.com/callback',
                          production_ready=False)
        user.applications.append(app)
        auth_app = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/callback',
            application=app,
            user=user,
        )

        with transaction.manager:
            Session.add(user)
            Session.add(auth_app)
            Session.flush()
            app_id = app.id
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        self.assertEqual(Session.query(Application).count(), 1)
        self.assertEqual(Session.query(AuthorizedApplication).count(), 1)

        res = self.testapp.get('/oauth2/applications/%s/delete' % str(app_id))
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Delete Application <span>Test Application</span>')
        res.mustcontain('Are you sure you want to remove the application')
        res.mustcontain('Yes, I am sure')
        res.mustcontain('No, take me back to the application list')

        # now delete it
        res = self.testapp.post('/oauth2/applications/%s/delete' % str(app_id),
                                {'submit': 'Yes, I am sure'})
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')

        try:
            app = Session.query(Application).filter(Application.id == app_id).one()
        except NoResultFound:
            app = None

        self.assertEqual(app, None)

        self.assertEqual(Session.query(User).count(), 1)
        self.assertEqual(Session.query(Application).count(), 0)
        # Related authorizations should be deleted on cascade
        self.assertEqual(Session.query(AuthorizedApplication).count(), 0)

    def test_application_edit_requires_authentication(self):
        res = self.testapp.get('/oauth2/applications/xxx/edit')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_application_edit_invalid_app_id(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get(
            '/oauth2/applications/000000000000000000000000/edit',
            status=400,
        )
        self.assertEqual(res.status, '400 Bad Request')

    def test_application_edit_app_id_doesnt_exist(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get(
            '/oauth2/applications/00000000-0000-0000-0000-000000000000/edit',
            status=404,
        )
        self.assertEqual(res.status, '404 Not Found')

    def test_application_edit_unauthorized(self):
        create_and_login_user(self.testapp)

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          authorized_origins=['http://example.com',
                                              'https://example.com'],
                          production_ready=False,
                          image_url='http://example.com/image.png',
                          description='example description')

        other_user = User(screen_name='Alice doe',
                          first_name='Alice',
                          last_name='Doe',
                          email='alice@example.com')

        other_user.applications.append(app)

        with transaction.manager:
            Session.add(other_user)
            Session.flush()
            app_id = app.id

        res = self.testapp.get('/oauth2/applications/%s/edit' % str(app_id),
                               status=401)
        self.assertEqual(res.status, '401 Unauthorized')

    def test_application_edit(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          authorized_origins=['http://example.com',
                                              'https://example.com'],
                          production_ready=False,
                          image_url='http://example.com/image.png',
                          description='example description')
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.flush()
            app_id = app.id
            app_secret = app.secret
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.get('/oauth2/applications/%s/edit' % str(app_id))
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Edit application <span>Test Application</span>')
        res.mustcontain('Name')
        res.mustcontain('Test Application')
        res.mustcontain('Main URL')
        res.mustcontain('http://example.com')
        res.mustcontain('Callback URL')
        res.mustcontain('http://example.com/callback')
        res.mustcontain('Authorized Origins')
        res.mustcontain("""http://example.com
https://example.com""")
        res.mustcontain('Production ready')
        res.mustcontain('Image URL')
        res.mustcontain('http://example.com/image.png')
        res.mustcontain('Description')
        res.mustcontain('example description')
        res.mustcontain('Client Id')
        res.mustcontain(app_id)
        res.mustcontain('Client secret')
        res.mustcontain(app_secret)
        res.mustcontain('Save application')
        res.mustcontain('Delete application')
        res.mustcontain('Cancel')

        # Let's make some changes
        old_count = Session.query(Application).count()
        res = self.testapp.post('/oauth2/applications/%s/edit' % str(app_id), {
            'name': 'Test Application 2',
            'main_url': 'http://example.com/new',
            'callback_url': 'http://example.com/new/callback',
            'authorized_origins': 'http://client.example.com',
            'production_ready': 'true',
            'image_url': 'http://example.com/image2.png',
            'description': 'example description 2',
            'client_id': '123456-2',
            'client_secret': 'secret2',
            'submit': 'Save changes',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')
        new_app = Session.query(Application).filter(Application.id == app_id).one()
        self.assertEqual(new_app.name, 'Test Application 2')
        self.assertEqual(new_app.main_url, 'http://example.com/new')
        self.assertEqual(new_app.callback_url, 'http://example.com/new/callback')
        self.assertEqual(new_app.authorized_origins, ['http://client.example.com'])
        self.assertEqual(new_app.production_ready, True)
        self.assertEqual(new_app.image_url, 'http://example.com/image2.png')
        self.assertEqual(new_app.description, 'example description 2')
        # the Id and Secret shouldn't change
        self.assertEqual(new_app.id, app_id)
        self.assertEqual(new_app.secret, app_secret)
        new_count = Session.query(Application).count()
        self.assertEqual(old_count, new_count)

    def test_application_edit_invalid_change(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          authorized_origins=['http://example.com',
                                              'https://example.com'],
                          production_ready=False,
                          image_url='http://example.com/image.png',
                          description='example description')
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.flush()
            app_id = app.id
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.post('/oauth2/applications/%s/edit' % str(app_id), {
            'submit': 'Save changes',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('There was a problem with your submission')
        res.mustcontain('Required')

    def test_application_edit_delete(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          authorized_origins=['http://example.com',
                                              'https://example.com'],
                          production_ready=False,
                          image_url='http://example.com/image.png',
                          description='example description')
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.flush()
            app_id = app.id
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.post('/oauth2/applications/%s/edit' % str(app_id), {
            'delete': 'Delete',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location,
                         'http://localhost/oauth2/applications/%s/delete'
                         % str(app_id))

    def test_application_edit_cancel(self):
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          authorized_origins=['http://example.com',
                                              'https://example.com'],
                          production_ready=False,
                          image_url='http://example.com/image.png',
                          description='example description')
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.flush()
            app_id = app.id
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.post('/oauth2/applications/%s/edit' % str(app_id), {
            'cancel': 'Cancel',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/applications')

    def test_authorized_applications_requires_authentication(self):
        res = self.testapp.get('/oauth2/authorized-applications')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_authorized_applications(self):
        administrator = User(screen_name='Alice doe',
                             first_name='Alice',
                             last_name='Doe',
                             email='alice@example.com')
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app1 = Application(name='Test Application 1',
                           main_url='http://example.com/1',
                           callback_url='http://example.com/1/callback',
                           image_url='http://example.com/1/image.png',
                           description='Test description 1',
                           user=administrator)

        auth_app1 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/1/callback',
            application=app1,
            user=user,
        )

        app2 = Application(name='Test Application 2',
                           main_url='http://example.com/2',
                           callback_url='http://example.com/2/callback',
                           image_url='http://example.com/2/image.png',
                           description='Test description 2',
                           user=administrator)

        auth_app2 = AuthorizedApplication(
            scope=['scope1'],
            response_type='code',
            redirect_uri='http://example.com/2/callback',
            application=app2,
            user=user,
        )

        with transaction.manager:
            Session.add(user)
            Session.add(app1)
            Session.add(auth_app1)
            Session.add(app2)
            Session.add(auth_app2)
            Session.flush()
            user_id = user.id

        self.testapp.get('/__login/' + str(user_id))

        res = self.testapp.get('/oauth2/authorized-applications')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Authorized Applications')
        res.mustcontain('Test Application 1')
        res.mustcontain('Test Application 2')

    def test_revoke_application_requires_authentication(self):
        res = self.testapp.get('/oauth2/applications/xxx/revoke')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

    def test_revoke_application_invalid_app_id(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get(
            '/oauth2/applications/000000000000000000000000/revoke',
            status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_revoke_application_app_id_doesnt_exist(self):
        create_and_login_user(self.testapp)

        res = self.testapp.get(
            '/oauth2/applications/00000000-0000-0000-0000-000000000000/revoke',
            status=404)
        self.assertEqual(res.status, '404 Not Found')

    def test_revoke_application_app(self):
        administrator = User(screen_name='Alice doe',
                             first_name='Alice',
                             last_name='Doe',
                             email='alice@example.com')
        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          main_url='http://example.com',
                          callback_url='http://example.com/callback',
                          user=administrator)

        auth_app = AuthorizedApplication(
            scope=['read-passwords'],
            response_type='code',
            redirect_uri='http://example.com/callback',
            application=app,
            user=user,
        )

        with transaction.manager:
            Session.add(user)
            Session.add(app)
            Session.add(auth_app)
            Session.flush()
            user_id = user.id
            app_id = app.id

        self.testapp.get('/__login/' + str(user_id))

        self.assertEqual(Session.query(Application).count(), 1)
        self.assertEqual(Session.query(AuthorizedApplication).count(), 1)

        res = self.testapp.get('/oauth2/applications/%s/revoke' % str(app_id))
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Revoke authorization to application <span>Test Application</span>')

        res = self.testapp.post('/oauth2/applications/%s/revoke' % str(app_id), {
            'submit': 'Yes, I am sure',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/oauth2/authorized-applications')
        try:
            auth_app = Session.query(AuthorizedApplication).filter(
                AuthorizedApplication.application_id == app_id,
                AuthorizedApplication.user_id == user_id,
            ).one()
        except NoResultFound:
            auth_app = None

        self.assertEqual(auth_app, None)

        # the application should not be removed on cascade
        self.assertEqual(Session.query(Application).count(), 1)

    def test_clients_empty(self):
        res = self.testapp.get('/oauth2/clients')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Available Clients')

    def test_clients_two_apps(self):
        administrator = User(screen_name='Alice doe',
                             first_name='Alice',
                             last_name='Doe',
                             email='alice@example.com')

        app1 = Application(name='Example app 1',
                           main_url='https://example.com',
                           callback_url='https://example.com/callback',
                           image_url='https://example.com/image.png',
                           description='example description',
                           production_ready=True,
                           user=administrator)

        app2 = Application(name='Example app 2',
                           main_url='https://2.example.com',
                           callback_url='https://2.example.com/callback',
                           production_ready=False,
                           user=administrator)

        with transaction.manager:
            Session.add(app1)
            Session.add(app2)
            Session.flush()

        res = self.testapp.get('/oauth2/clients')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain(
            'Available Clients', 'Example app 1', 'https://example.com',
            'https://example.com/image.png', 'example description',
            no=('Example app 2', 'https://2.example.com'),
        )
