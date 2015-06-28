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

from pyramid import testing

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

from yithlibraryserver.compat import text_type
from yithlibraryserver.password.models import Password
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.models import ExternalIdentity, User


class FullNameTests(unittest.TestCase):

    def test_empty(self):
        user = User(first_name='', last_name='')
        self.assertEqual(user.full_name, '')

    def test_only_first_name(self):
        user = User(first_name='John', last_name='')
        self.assertEqual(user.full_name, 'John')

    def test_only_last_name(self):
        user = User(first_name='', last_name='Doe')
        self.assertEqual(user.full_name, 'Doe')

    def test_first_and_last_name(self):
        user = User(first_name='John', last_name='Doe')
        self.assertEqual(user.full_name, 'John Doe')


class UnicodeTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_unicode_only_id(self):
        user = User()
        Session.add(user)
        Session.flush()
        self.assertEqual(text_type(user), text_type(user.id))

    def test_unicode_only_email(self):
        user = User(email='john@example.com')
        Session.add(user)
        Session.flush()
        self.assertEqual(text_type(user), 'john@example.com')

    def test_unicode_only_last_name(self):
        user = User(last_name='Doe')
        Session.add(user)
        Session.flush()
        self.assertEqual(text_type(user), 'Doe')

    def test_unicode_first_name_and_last_name(self):
        user = User(first_name='John', last_name='Doe')
        Session.add(user)
        Session.flush()
        self.assertEqual(text_type(user), 'John Doe')

    def test_unicode_only_screen_name(self):
        user = User(screen_name='Johnny')
        Session.add(user)
        Session.flush()
        self.assertEqual(text_type(user), 'Johnny')

    def test_unicode_is_str(self):
        u = User()
        Session.add(u)
        Session.flush()
        self.assertEqual(u.__unicode__(), u.__str__())


class UpdatePreferencesTests(unittest.TestCase):

    def setUp(self):
        self.user = User(allow_google_analytics=False,
                         send_passwords_periodically=True)

    def test_empty_preferences(self):
        self.user.update_preferences({})
        self.assertEqual(self.user.allow_google_analytics, False)
        self.assertEqual(self.user.send_passwords_periodically, True)

    def test_fake_preferences(self):
        self.user.update_preferences({'foo': 'bar'})
        self.assertEqual(self.user.allow_google_analytics, False)
        self.assertEqual(self.user.send_passwords_periodically, True)

    def test_real_preferences(self):
        self.user.update_preferences({
            'allow_google_analytics': True,
            'send_passwords_periodically': False,
        })
        self.assertEqual(self.user.allow_google_analytics, True)
        self.assertEqual(self.user.send_passwords_periodically, False)


class UpdateUserInfo(unittest.TestCase):

    def setUp(self):
        self.user = User(screen_name='', first_name='', last_name='',
                         email='', email_verified=False)

    def test_update_user_info_empty(self):
        self.user.update_user_info({})
        self.assertEqual(self.user.screen_name, '')
        self.assertEqual(self.user.first_name, '')
        self.assertEqual(self.user.last_name, '')
        self.assertEqual(self.user.email, '')
        self.assertEqual(self.user.email_verified, False)

    def test_update_user_info_names(self):
        self.user.update_user_info({
            'screen_name': 'John Doe',
            'first_name': 'John',
            'last_name': 'Doe',
        })
        self.assertEqual(self.user.screen_name, 'John Doe')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, '')
        self.assertEqual(self.user.email_verified, False)

    def test_update_user_info_names_dont_update_empty_ones(self):
        self.user.screen_name = 'John Doe'
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.update_user_info({
            'screen_name': '',
            'first_name': '',
            'last_name': '',
        })
        self.assertEqual(self.user.screen_name, 'John Doe')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, '')
        self.assertEqual(self.user.email_verified, False)

    def test_update_user_info_email(self):
        self.user.update_user_info({'email': 'john@example.com'})
        self.assertEqual(self.user.email, 'john@example.com')
        self.assertEqual(self.user.email_verified, False)

    def test_update_user_info_email_force_verified(self):
        self.user.update_user_info({
            'email': 'john@example.com',
            'email_verified': True,
        })
        self.assertEqual(self.user.email, 'john@example.com')
        self.assertEqual(self.user.email_verified, False)

    def test_update_user_info_email_previously_verified(self):
        self.user.email = 'johndoe@example.com'
        self.user.email_verified = True
        self.user.update_user_info({'email': 'john@example.com'})
        self.assertEqual(self.user.email, 'john@example.com')
        self.assertEqual(self.user.email_verified, False)


class GetAccountsTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('yithlibraryserver.password')
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_get_accounts_no_provider(self):
        user = User(email='john@example.com')
        Session.add(user)
        Session.flush()
        self.assertEqual(user.get_accounts(''), [
            {'id': user.id,
             'is_current': False,
             'is_verified': False,
             'passwords': 0,
             'providers': []}
        ])

    def test_get_accounts_one_provider(self):
        user = User(email='john@example.com')
        identity = ExternalIdentity(user=user, provider='twitter',
                                    external_id='1234')
        Session.add(user)
        Session.add(identity)
        Session.flush()
        self.assertEqual(user.get_accounts(''), [
            {'id': user.id,
             'is_current': False,
             'is_verified': False,
             'passwords': 0,
             'providers': [{
                 'name': 'twitter',
                 'is_current': False,
             }]}
        ])

    def test_get_accounts_one_provider_email_verified(self):
        user = User(email='john@example.com', email_verified=True)
        identity = ExternalIdentity(user=user, provider='twitter',
                                    external_id='1234')
        Session.add(user)
        Session.add(identity)
        Session.flush()
        self.assertEqual(user.get_accounts(''), [
            {'id': user.id,
             'is_current': False,
             'is_verified': True,
             'passwords': 0,
             'providers': [{
                 'name': 'twitter',
                 'is_current': False,
             }]}
        ])

    def test_get_accounts_with_passwords(self):
        user = User(email='john@example.com', email_verified=True)
        identity = ExternalIdentity(user=user, provider='twitter',
                                    external_id='1234')
        password = Password(user=user, secret='secret')
        Session.add(user)
        Session.add(identity)
        Session.add(password)
        Session.flush()
        self.assertEqual(user.get_accounts(''), [
            {'id': user.id,
             'is_current': False,
             'is_verified': True,
             'passwords': 1,
             'providers': [{
                 'name': 'twitter',
                 'is_current': False,
             }]}
        ])

    def test_get_accounts_multiple_providers(self):
        user = User(email='john@example.com', email_verified=True)
        identity1 = ExternalIdentity(user=user, provider='twitter',
                                     external_id='1234')
        identity2 = ExternalIdentity(user=user, provider='google',
                                     external_id='4321')
        password = Password(user=user, secret='secret')
        Session.add(user)
        Session.add(identity1)
        Session.add(identity2)
        Session.add(password)
        Session.flush()
        self.assertEqual(user.get_accounts('google'), [
            {'id': user.id,
             'is_current': True,
             'is_verified': True,
             'passwords': 1,
             'providers': [{
                 'name': 'twitter',
                 'is_current': False,
             }, {
                 'name': 'google',
                 'is_current': True,
             }]}
        ])
