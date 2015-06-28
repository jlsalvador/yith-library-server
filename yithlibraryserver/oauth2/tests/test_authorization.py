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

import transaction

from pyramid.httpexceptions import HTTPUnauthorized

from pyramid_sqlalchemy import Session

from yithlibraryserver.testing import FakeRequest, TestCase
from yithlibraryserver.oauth2.authorization import verify_request
from yithlibraryserver.oauth2.models import AccessCode
from yithlibraryserver.oauth2.tests import create_client


class VerifyRequestTests(TestCase):

    def test_no_auth_header(self):
        request = FakeRequest(headers={})
        self.assertRaises(HTTPUnauthorized, verify_request, request, ['scope1'])

    def test_basic_auth_header(self):
        request = FakeRequest(headers={'Authorization': 'Basic foobar'})
        self.assertRaises(HTTPUnauthorized, verify_request, request, ['scope1'])

    def test_bad_bearer_header(self):
        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        self.assertRaises(HTTPUnauthorized, verify_request, request, ['scope1'])

    @freeze_time('2014-02-23 08:00:00')
    def test_invalid_scope(self):
        user_id, app_id, _ = create_client()
        expiration = datetime.datetime(2014, 2, 23, 9, 0)
        access_code = AccessCode(
            code='1234',
            code_type='Bearer',
            expiration=expiration,
            scope=['scope1'],
            user_id=user_id,
            application_id=app_id,
        )
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        self.assertRaises(HTTPUnauthorized, verify_request, request, ['scope2'])

    @freeze_time('2014-02-23 08:00:00')
    def test_expired_token(self):
        user_id, app_id, _ = create_client()
        expiration = datetime.datetime(2014, 2, 23, 7, 0)
        access_code = AccessCode(
            code='1234',
            code_type='Bearer',
            expiration=expiration,
            scope=['scope1'],
            user_id=user_id,
            application_id=app_id,
        )
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        self.assertRaises(HTTPUnauthorized, verify_request, request, ['scope1'])

    @freeze_time('2014-02-23 08:00:00')
    def test_valid_user(self):
        user_id, app_id, _ = create_client()
        expiration = datetime.datetime(2014, 2, 23, 9, 0)
        access_code = AccessCode(
            code='1234',
            code_type='Bearer',
            expiration=expiration,
            scope=['scope1'],
            user_id=user_id,
            application_id=app_id,
        )
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})

        user = verify_request(request, ['scope1'])
        self.assertEqual(user.id, user_id)
