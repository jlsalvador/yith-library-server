# Yith Library Server is a password storage server.
# Copyright (C) 2014-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from pyramid.httpexceptions import HTTPUnauthorized

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.testing import FakeRequest, TestCase
from yithlibraryserver.oauth2.decorators import (
    protected,
    protected_method,
)
from yithlibraryserver.oauth2.models import AccessCode
from yithlibraryserver.oauth2.tests import create_client, create_user


@protected(['scope1'])
def view_function(request):
    return 'response'


class ViewClass(object):

    def __init__(self, request):
        self.request = request

    @protected_method(['scope1'])
    def view_method(self):
        return 'response'


class DecoratorsTests(TestCase):

    def setUp(self):
        super(DecoratorsTests, self).setUp()
        self.owner_id, self.app_id, _ = create_client()
        _, self.user_id = create_user()

    def _create_access_code(self, scope):
        expiration = datetime.datetime(2014, 2, 23, 9, 0)
        access_code = AccessCode(code='1234',
                                 code_type='Bearer',
                                 expiration=expiration,
                                 scope=scope,
                                 user_id=self.user_id,
                                 application_id=self.app_id)
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

    @freeze_time('2014-02-23 08:00:00')
    def test_protected_bad_scope(self):
        self._create_access_code(['scope2'])
        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        self.assertRaises(HTTPUnauthorized, view_function, request)

    @freeze_time('2014-02-23 08:00:00')
    def test_protected(self):
        self._create_access_code(['scope1'])

        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        self.assertEqual(view_function(request), 'response')
        self.assertEqual(request.user.id, self.user_id)

    @freeze_time('2014-02-23 08:00:00')
    def test_protected_method_bad_scope(self):
        self._create_access_code(['scope2'])
        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        view_object = ViewClass(request)
        self.assertRaises(HTTPUnauthorized, view_object.view_method)

    @freeze_time('2014-02-23 08:00:00')
    def test_protected_method(self):
        self._create_access_code(['scope1'])
        request = FakeRequest(headers={'Authorization': 'Bearer 1234'})
        view_object = ViewClass(request)
        self.assertEqual(view_object.view_method(), 'response')
        self.assertEqual(request.user.id, self.user_id)
