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

import collections
import unittest

from webtest import TestApp

from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import ISessionFactory
from pyramid.security import remember
from pyramid.settings import asbool
from pyramid.testing import DummyRequest

from pyramid_sqlalchemy import init_sqlalchemy
from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

from sqlalchemy import create_engine

import transaction

from yithlibraryserver import main
from yithlibraryserver.compat import mock


class FakeRequest(DummyRequest):

    def __init__(self, *args, **kwargs):
        super(FakeRequest, self).__init__(*args, **kwargs)
        self.authorization = self.headers.get('Authorization', '').split(' ')


def enable_sql_two_phase_commit_test(config, enable=True):
    """Fake enable_sql_two_phase_commit function used in the tests."""


def includeme_test(config):
    """Fake includeme function that replaces the real one in the tests."""
    config.add_directive('enable_sql_two_phase_commit', enable_sql_two_phase_commit_test)


SQLAlchemyTestContext = collections.namedtuple('SQLAlchemyTestContext',
                                               ['engine', 'sqlalchemy_patcher'])


def sqlalchemy_setup(db_uri):
    engine = create_engine(db_uri)
    init_sqlalchemy(engine)

    sqlalchemy_patcher = mock.patch('pyramid_sqlalchemy.includeme', includeme_test)
    sqlalchemy_patcher.start()

    return SQLAlchemyTestContext(engine, sqlalchemy_patcher)


def sqlalchemy_teardown(context):
    transaction.abort()
    Session.remove()
    metadata.drop_all()
    Session.configure(bind=None)
    metadata.bind = None
    context.engine.dispose()
    context.sqlalchemy_patcher.stop()


def get_test_db_uri():
    return 'postgresql://postgres@/test_yithlibrary'


class TestCase(unittest.TestCase):

    db_uri = get_test_db_uri()

    def setUp(self):
        super(TestCase, self).setUp()

        self.db_context = sqlalchemy_setup(self.db_uri)

        settings = {
            'database_url': self.db_uri,
            'auth_tk_secret': '123456',
            'redis.sessions.secret': '123456',
            'redis.sessions.url': 'redis://127.0.0.1:6379/0',
            'twitter_consumer_key': 'key',
            'twitter_consumer_secret': 'secret',
            'facebook_app_id': 'id',
            'facebook_app_secret': 'secret',
            'google_client_id': 'id',
            'google_client_secret': 'secret',
            'liveconnect_client_id': 'id',
            'liveconnect_client_secret': 'secret',
            'paypal_user': 'sdk-three_api1.sdk.com',
            'paypal_password': 'QFZCWN5HZM8VBG7Q',
            'paypal_signature': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
            'testing': 'True',
            'pyramid_mailer.prefix': 'mail_',
            'mail_default_sender': 'no-reply@yithlibrary.com',
            'admin_emails': 'admin1@example.com admin2@example.com',
            'public_url_root': 'http://localhost:6543/',
            'webassets.debug': 'True',
        }
        app = main({}, **settings)
        self.testapp = TestApp(app)

        metadata.create_all()

    def tearDown(self):
        sqlalchemy_teardown(self.db_context)
        self.testapp.reset()
        super(TestCase, self).tearDown()

    def get_session(self, response):
        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)
        request = response.request

        if not hasattr(request, 'add_response_callback'):
            request.add_response_callback = lambda r: r

        if 'Set-Cookie' in response.headers:
            request.environ['HTTP_COOKIE'] = response.headers['Set-Cookie']

        return session_factory(request)


def view_test_login(request):
    """Log in a user.

    This view is only registered in testing mode
    """
    return HTTPFound(location='/',
                     headers=remember(request, request.matchdict['user']))


def view_test_add_to_session(request):
    """Add data to the user session via a POST

    If a key in the POST dict has a '__' substring, it will be
    handled as a nested dict.

    This view is only registered in testing mode
    """
    items = {}
    for key, value in request.POST.items():
        if '__' in key:
            subkey1, subkey2 = key.split('__')
            if subkey1 not in items:
                items[subkey1] = {}
            items[subkey1][subkey2] = value
        else:
            items[key] = value

    for key, value in items.items():
        if value in ('True', 'False'):
            value = asbool(value)
        request.session[key] = value

    return HTTPFound(location='/')
