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

import unittest

from pyramid import testing
from pyramid.testing import DummyRequest

from pyramid_mailer import get_mailer

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

import transaction

from yithlibraryserver.password.models import Password
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.accounts import merge_accounts, merge_users
from yithlibraryserver.user.accounts import notify_admins_of_account_removal
from yithlibraryserver.user.models import ExternalIdentity, User


class BaseMergeTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('yithlibraryserver.oauth2')
        self.config.include('yithlibraryserver.password')
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)


class MergeAccountsTests(BaseMergeTests):

    def test_merge_empty_user(self):
        self.assertEqual(0, merge_accounts(None, []))

    def test_merge_with_itself(self):
        user = User()
        Session.add(user)
        Session.flush()

        self.assertEqual(1, Session.query(User).count())
        self.assertEqual(0, merge_accounts(user, [user.id]))
        self.assertEqual(1, Session.query(User).count())

    def test_merge_with_invented_users(self):
        user = User()
        Session.add(user)
        Session.flush()

        fake_id = '00000000-0000-0000-0000-000000000000'
        self.assertEqual(1, Session.query(User).count())
        self.assertEqual(0, merge_accounts(user, [fake_id]))
        self.assertEqual(1, Session.query(User).count())

    def test_merge_valid_users(self):
        master_user = User()
        Session.add(master_user)

        other_user = User()
        Session.add(other_user)

        Session.flush()

        self.assertEqual(2, Session.query(User).count())
        self.assertEqual(1, merge_accounts(master_user, [other_user.id]))
        self.assertEqual(1, Session.query(User).count())


class MergeUsersTests(BaseMergeTests):

    def test_merge_users(self):
        with transaction.manager:
            user1 = User(email='john@example.com')
            identity1 = ExternalIdentity(provider='twitter', external_id='1234',
                                         user=user1)
            password1 = Password(secret='s3cr3t1', user=user1)
            password2 = Password(secret='s3cr3t2', user=user1)

            user2 = User(email='john@example.com')
            identity2 = ExternalIdentity(provider='google', external_id='4321',
                                         user=user2)
            password3 = Password(secret='s3cr3t3', user=user2)
            password4 = Password(secret='s3cr3t4', user=user2)

            Session.add(user1)
            Session.add(identity1)
            Session.add(password1)
            Session.add(password2)
            Session.add(user2)
            Session.add(identity2)
            Session.add(password3)
            Session.add(password4)
            Session.flush()
            user1_id = user1.id
            user2_id = user2.id

        user1 = Session.query(User).filter(User.id == user1_id).one()
        user2 = Session.query(User).filter(User.id == user2_id).one()
        self.assertEqual(1, len(user1.identities))
        self.assertEqual(4, Session.query(Password).count())

        with transaction.manager:
            merge_users(user1, user2)

        self.assertEqual(4, Session.query(Password).count())
        self.assertEqual(0, Session.query(Password).filter(
            Password.user_id == user2_id).count())
        try:
            user2_refreshed = Session.query(User).filter(User.id == user2_id).one()
        except NoResultFound:
            user2_refreshed = None
        self.assertEqual(user2_refreshed, None)

        user1 = Session.query(User).filter(User.id == user1_id).one()
        self.assertEqual(2, len(user1.identities))


class AccountRemovalNotificationTests(unittest.TestCase):

    def setUp(self):
        self.admin_emails = ['admin1@example.com', 'admin2@example.com']
        self.config = testing.setUp(settings={
            'admin_emails': self.admin_emails,
        })
        self.config.include('pyramid_mailer.testing')
        self.config.include('pyramid_chameleon')
        self.config.add_route('home', '/')

    def tearDown(self):
        testing.tearDown()

    def test_notify_admins_of_account_removal(self):
        request = DummyRequest()
        mailer = get_mailer(request)
        self.assertEqual(len(mailer.outbox), 0)

        user = {'first_name': 'John', 'last_name': 'Doe',
                'email': 'john@example.com'}
        reason = 'I do not trust free services'
        notify_admins_of_account_removal(request, user, reason)

        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         'A user has destroyed his Yith Library account')
        self.assertEqual(mailer.outbox[0].recipients, self.admin_emails)
        self.assertTrue('John Doe <john@example.com' in mailer.outbox[0].body)
        self.assertTrue('I do not trust free services' in mailer.outbox[0].body)
