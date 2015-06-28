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

from pyramid.testing import DummyRequest

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver import testing
from yithlibraryserver.cors import CORSManager
from yithlibraryserver.oauth2.models import Application
from yithlibraryserver.user.models import User


class CORSManagerTests(testing.TestCase):

    def test_cors_headers_global_origins_access_denied(self):
        cm = CORSManager('')

        request = DummyRequest(headers={'Origin': 'foo'})
        response = request.response

        cm.add_cors_header(request, response)

        self.assertEqual(response.headers, {
            'Content-Type': 'text/html; charset=UTF-8',
            'Content-Length': '0',
        })

    def test_cors_headers_global_origins(self):
        cm = CORSManager('http://localhost')

        request = DummyRequest(headers={'Origin': 'http://localhost'})
        response = request.response

        cm.add_cors_header(request, response)

        self.assertEqual(response.headers, {
            'Content-Type': 'text/html; charset=UTF-8',
            'Content-Length': '0',
            'Access-Control-Allow-Origin': 'http://localhost',
        })

    def test_cors_headers_app_origins_access_denied(self):
        cm = CORSManager('')

        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          authorized_origins=['http://localhost'])
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.add(app)
            Session.flush()

        bad_app_id = '00000000-0000-0000-0000-000000000000'
        request = DummyRequest(headers={'Origin': 'http://localhost'},
                               params={'client_id': bad_app_id})
        response = request.response

        cm.add_cors_header(request, response)

        self.assertEqual(response.headers, {
            'Content-Type': 'text/html; charset=UTF-8',
            'Content-Length': '0',
        })

    def test_cors_headers_app_origins(self):
        cm = CORSManager('')

        user = User(screen_name='John Doe',
                    first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        app = Application(name='Test Application',
                          authorized_origins=['http://localhost'])
        user.applications.append(app)

        with transaction.manager:
            Session.add(user)
            Session.add(app)
            Session.flush()
            app_id = app.id

        request = DummyRequest(headers={'Origin': 'http://localhost'},
                               params={'client_id': app_id})
        response = request.response

        cm.add_cors_header(request, response)

        self.assertEqual(response.headers, {
            'Content-Type': 'text/html; charset=UTF-8',
            'Content-Length': '0',
            'Access-Control-Allow-Origin': 'http://localhost',
        })
