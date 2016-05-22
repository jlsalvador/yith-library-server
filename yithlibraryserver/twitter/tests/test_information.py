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

import unittest

from pyramid.httpexceptions import HTTPUnauthorized

from yithlibraryserver.compat import mock
from yithlibraryserver.twitter.information import get_user_info


class InformationTests(unittest.TestCase):

    def setUp(self):
        super(InformationTests, self).setUp()
        self.settings = {
            'twitter_consumer_key': 'key',
            'twitter_consumer_secret': 'secret',
            'twitter_bearer_token_url': 'https://api.twitter.com/oauth2/token',
            'twitter_user_info_url': 'https://api.twitter.com/1.1/users/show.json'
        }

    def test_get_user_info(self):
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.ok = True
            response.json = lambda: {
                'token_type': 'bearer',
                'access_token': '1234567890',
            }
            with mock.patch('requests.get') as fake2:
                response2 = fake2.return_value
                response2.ok = True
                response2.json = lambda: {
                    'screen_name': 'John Doe',
                }
                info = get_user_info(self.settings, '1234')
                self.assertEqual(info, {'screen_name': 'John Doe'})

    def test_get_user_info_non_authorized(self):
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.ok = False

            self.assertRaises(HTTPUnauthorized,
                              get_user_info, self.settings, '1234')

    def test_get_user_info_non_authorized2(self):
        with mock.patch('requests.post') as fake:
            response = fake.return_value
            response.ok = True
            response.json = lambda: {
                'token_type': 'bearer',
                'access_token': '1234567890',
            }
            with mock.patch('requests.get') as fake2:
                response2 = fake2.return_value
                response2.ok = False

                self.assertRaises(HTTPUnauthorized,
                                  get_user_info, self.settings, '1234')
