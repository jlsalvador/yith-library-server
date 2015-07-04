# Yith Library Server is a password storage server.
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

from pyramid.testing import DummyRequest

from yithlibraryserver.user.analytics import GoogleAnalytics
from yithlibraryserver.user.analytics import get_google_analytics
from yithlibraryserver.user.analytics import USER_ATTR
from yithlibraryserver.user.models import User


class DummyRegistry(object):

    def __init__(self, **kwargs):
        self.settings = kwargs


class GoogleAnalyticsTests(unittest.TestCase):

    def test_enabled(self):
        request = DummyRequest()
        request.session = {}
        request.registry = DummyRegistry(google_analytics_code='1234')
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.enabled)

    def test_disabled(self):
        request = DummyRequest()
        request.session = {}
        request.registry = DummyRegistry(google_analytics_code=None)
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.enabled)

    def test_first_time_empty_session_no_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = None
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.first_time)

    def test_first_time_true_session_no_user(self):
        request = DummyRequest()
        request.session = {USER_ATTR: True}
        request.user = None
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.first_time)

    def test_first_time_false_session_no_user(self):
        request = DummyRequest()
        request.session = {USER_ATTR: False}
        request.user = None
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.first_time)

    def test_first_time_empty_session_default_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = User()
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.first_time)

    def test_first_time_empty_session_true_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = User(allow_google_analytics=True)
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.first_time)

    def test_first_time_empty_session_false_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = User(allow_google_analytics=False)
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.first_time)

    def test_show_in_session(self):
        request = DummyRequest()
        request.session = {}
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.show_in_session())

        request = DummyRequest()
        request.session = {USER_ATTR: False}
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.show_in_session())

        request = DummyRequest()
        request.session = {USER_ATTR: True}
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.show_in_session())

    def test_show_in_user(self):
        request = DummyRequest()
        ga = GoogleAnalytics(request)

        self.assertFalse(ga.show_in_user(User(allow_google_analytics=False)))

        self.assertTrue(ga.show_in_user(User(allow_google_analytics=True)))

    def test_is_in_session_empty_session(self):
        request = DummyRequest()
        request.session = {}
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.is_in_session())

    def test_is_in_session_true_session(self):
        request = DummyRequest()
        request.session = {USER_ATTR: True}
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.is_in_session())

    def test_is_in_session_false_session(self):
        request = DummyRequest()
        request.session = {USER_ATTR: False}
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.is_in_session())

    def test_show_empty_session_no_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = None
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.show)

    def test_show_true_session_no_user(self):
        request = DummyRequest()
        request.session = {USER_ATTR: True}
        request.user = None
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.show)

    def test_show_empty_session_true_user(self):
        request = DummyRequest()
        request.session = {}
        request.user = User(allow_google_analytics=True)
        ga = GoogleAnalytics(request)
        self.assertTrue(ga.show)

    def test_show_true_session_false_user(self):
        request = DummyRequest()
        request.session = {USER_ATTR: True}
        request.user = User(allow_google_analytics=False)
        ga = GoogleAnalytics(request)
        self.assertFalse(ga.show)

    def test_clean_session_empty_session(self):
        request = DummyRequest()
        request.session = {}
        request.user = None
        ga = GoogleAnalytics(request)
        ga.clean_session()
        self.assertEqual(request.session, {})

    def test_clean_session_true_session(self):
        request = DummyRequest()
        request.session = {USER_ATTR: True}
        request.user = None
        ga = GoogleAnalytics(request)
        ga.clean_session()
        self.assertEqual(request.session, {})

    def test_get_google_analytics(self):
        request = DummyRequest()
        ga = get_google_analytics(request)

        self.assertTrue(isinstance(ga, GoogleAnalytics))
        self.assertEqual(ga.request, request)
