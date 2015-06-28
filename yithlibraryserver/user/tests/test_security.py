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

from pyramid import testing
from pyramid.httpexceptions import HTTPFound

from pyramid_sqlalchemy import Session

from pyramid_sqlalchemy import metadata
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.security import (
    get_user,
    assert_authenticated_user_is_registered,
)
from yithlibraryserver.user.models import User


class GetUserTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_get_user_no_userid(self):
        request = testing.DummyRequest()
        self.assertEqual(None, get_user(request))

    def test_get_user_no_user(self):
        request = testing.DummyRequest()
        user_id = '00000000-0000-0000-0000-000000000000'
        self.config.testing_securitypolicy(userid=user_id)
        self.assertEqual(None, get_user(request))

    def test_get_user_existing_user(self):
        user = User(screen_name='John Doe')
        Session.add(user)
        Session.flush()
        user_id = user.id

        self.config.testing_securitypolicy(userid=user_id)
        request = testing.DummyRequest()
        new_user = get_user(request)
        self.assertEqual(new_user.id, user.id)
        self.assertEqual(new_user.screen_name, 'John Doe')


class AssertAuthenticatedUserIsRegisteredTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_assert_authenticated_user_is_registered_no_user(self):
        user_id = '00000000-0000-0000-0000-000000000000'
        self.config.testing_securitypolicy(userid=user_id)

        request = testing.DummyRequest()

        self.assertRaises(HTTPFound, assert_authenticated_user_is_registered, request)
        try:
            assert_authenticated_user_is_registered(request)
        except HTTPFound as exp:
            self.assertEqual(exp.location, '/register')

    def test_assert_authenticated_user_is_registered_existing_user(self):
        user = User(screen_name='John Doe')
        Session.add(user)
        Session.flush()
        user_id = user.id

        self.config.testing_securitypolicy(userid=user_id)
        request = testing.DummyRequest()
        res = assert_authenticated_user_is_registered(request)
        self.assertEqual(res.id, user_id)
        self.assertEqual(res.screen_name, 'John Doe')
