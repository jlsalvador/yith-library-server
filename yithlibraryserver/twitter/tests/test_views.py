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

import transaction

from yithlibraryserver import testing
from yithlibraryserver.compat import mock
from yithlibraryserver.user.models import ExternalIdentity, User


class ViewTests(testing.TestCase):

    def setUp(self):
        super(ViewTests, self).setUp()
        settings = self.testapp.app.registry.settings
        # these are invalid Twitter tokens taken from the examples
        settings['twitter_consumer_key'] = 'cChZNFj6T5R0TigYB9yd1w'
        settings['twitter_consumer_secret'] = 'L8qq9PZyRg6ieKGEKhZolGC0vJWLw8iEJ88DRdyOg'
        settings['twitter_authenticate_url'] = 'https://api.twitter.com/oauth/authenticate'
        settings['twitter_request_token_url'] = 'https://api.twitter.com/oauth/request_token'
        settings['twitter_access_token_url'] = 'https://api.twitter.com/oauth/access_token'

    def test_twitter_login(self):
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.status_code = 200
            response.text = 'oauth_callback_confirmed=true&oauth_token=123456789'
            res = self.testapp.get('/twitter/login')
            self.assertEqual(res.status, '302 Found')
            loc = 'https://api.twitter.com/oauth/authenticate?oauth_token=123456789'
            self.assertEqual(res.location, loc)

        # simulate an authentication error from Twitter
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.status_code = 401
            res = self.testapp.get('/twitter/login', status=401)
            self.assertEqual(res.status, '401 Unauthorized')

        # simulate an oauth_callback_confirmed=false
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.status_code = 200
            response.text = 'oauth_callback_confirmed=false'
            res = self.testapp.get('/twitter/login', status=401)
            self.assertEqual(res.status, '401 Unauthorized')
            res.mustcontain('oauth_callback_confirmed is not true')

    def test_twitter_callback_failures(self):
        res = self.testapp.get('/twitter/callback', status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing required oauth_token')

        res = self.testapp.get('/twitter/callback?oauth_token=123456789',
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('Missing required oauth_verifier')

        good_url = '/twitter/callback?oauth_token=123456789&oauth_verifier=abc'
        res = self.testapp.get(good_url, status=400)
        self.assertEqual(res.status, '400 Bad Request')
        res.mustcontain('No oauth_token was found in the session')

        # bad request because oauth tokens are different
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.status_code = 200
            response.text = 'oauth_callback_confirmed=true&oauth_token=987654321'
            self.testapp.get('/twitter/login')

            res = self.testapp.get(good_url, status=401)
            self.assertEqual(res.status, '401 Unauthorized')
            res.mustcontain("OAuth tokens don't match")

        # good request, twitter is not happy with us
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.status_code = 200
            response.text = 'oauth_callback_confirmed=true&oauth_token=123456789'
            self.testapp.get('/twitter/login')

            response = fake.return_value
            response.status_code = 401
            response.text = 'Invalid token'

            res = self.testapp.get(good_url, status=401)
            self.assertEqual(res.status, '401 Unauthorized')
            res.mustcontain('Invalid token')

    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_twitter_callback_new_user(self, post_mock, get_mock):
        # good request, twitter is happy now. New user
        mock0 = mock.Mock()
        mock0.status_code = 200
        mock0.text = 'oauth_callback_confirmed=true&oauth_token=123456789'

        mock1 = mock.Mock()
        mock1.status_code = 200
        mock1.text = 'oauth_token=xyz&user_id=user1&screen_name=JohnDoe'

        mock2 = mock.Mock()
        mock2.ok = True
        mock2.json = lambda: {
            'token_type': 'bearer',
            'access_token': '1234567890',
        }

        post_mock.side_effect = [mock0, mock1, mock2]

        get_response = get_mock.return_value
        get_response.ok = True
        get_response.json = lambda: {
            'name': 'John Doe',
        }

        self.testapp.get('/twitter/login')

        good_url = '/twitter/callback?oauth_token=123456789&oauth_verifier=abc'
        res = self.testapp.get(good_url, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/register')

    @freeze_time('2012-01-10 15:31:11')
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_twitter_callback_existing_user(self, post_mock, get_mock):
        # good request, twitter is happy now. Existing user
        user = User(screen_name='Johnny')
        identity = ExternalIdentity(user=user, provider='twitter', external_id='user1')

        with transaction.manager:
            Session.add(user)
            Session.add(identity)
            Session.flush()
            user_id = user.id

        mock0 = mock.Mock()
        mock0.status_code = 200
        mock0.text = 'oauth_callback_confirmed=true&oauth_token=123456789'

        mock1 = mock.Mock()
        mock1.status_code = 200
        mock1.text = 'oauth_token=xyz&user_id=user1&screen_name=JohnDoe'

        mock2 = mock.Mock()
        mock2.ok = True
        mock2.json = lambda: {
            'token_type': 'bearer',
            'access_token': '1234567890',
        }

        post_mock.side_effect = [mock0, mock1, mock2]

        get_response = get_mock.return_value
        get_response.ok = True
        get_response.json = lambda: {
            'name': 'John Doe',
        }

        self.testapp.get('/twitter/login')

        good_url = '/twitter/callback?oauth_token=123456789&oauth_verifier=abc'
        res = self.testapp.get(good_url, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/')
        self.assertTrue('Set-Cookie' in res.headers)

        # even if the response from twitter included a different
        # screen_name, our user will not be updated
        new_user = Session.query(User).filter(User.id == user_id).one()
        self.assertEqual(new_user.screen_name, 'Johnny')

    @freeze_time('2012-01-10 15:31:11')
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_twitter_callback_existing_user_remember_url(self, post_mock, get_mock):
        # good request, existing user, remember next_url
        user = User(screen_name='Johnny')
        identity = ExternalIdentity(user=user, provider='twitter', external_id='user1')

        with transaction.manager:
            Session.add(user)
            Session.add(identity)

        mock0 = mock.Mock()
        mock0.status_code = 200
        mock0.text = 'oauth_callback_confirmed=true&oauth_token=123456789'

        mock1 = mock.Mock()
        mock1.status_code = 200
        mock1.text = 'oauth_token=xyz&user_id=user1&screen_name=JohnDoe'

        mock2 = mock.Mock()
        mock2.ok = True
        mock2.json = lambda: {
            'token_type': 'bearer',
            'access_token': '1234567890',
        }

        post_mock.side_effect = [mock0, mock1, mock2]

        get_response = get_mock.return_value
        get_response.ok = True
        get_response.json = lambda: {
            'name': 'John Doe',
        }

        self.testapp.get('/twitter/login?next_url=http://localhost/foo/bar')

        good_url = '/twitter/callback?oauth_token=123456789&oauth_verifier=abc'
        res = self.testapp.get(good_url, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/foo/bar')
        self.assertTrue('Set-Cookie' in res.headers)
