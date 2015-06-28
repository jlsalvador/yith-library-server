# Yith Library Server is a password storage server.
# Copyright (C) 2013-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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
import sys

from freezegun import freeze_time

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.compat import StringIO
from yithlibraryserver.scripts.backups import get_all_users
from yithlibraryserver.scripts.backups import send_backups_via_email
from yithlibraryserver.scripts.testing import ScriptTests
from yithlibraryserver.user.models import User


class GetAllUsersTests(ScriptTests):

    def test_get_all_users(self):
        d = datetime.datetime
        with transaction.manager:
            user1 = User(first_name='John1',
                         last_name='Doe',
                         creation=d(2012, 12, 12, 9, 10, 0),
                         email='john1@example.com',
                         email_verified=False,
                         send_passwords_periodically=False)
            Session.add(user1)
            self.add_passwords(user1, 10)

            user2 = User(first_name='John2',
                         last_name='Doe',
                         creation=d(2013, 1, 2, 13, 10, 0),
                         email='john2@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user2)
            self.add_passwords(user2, 10)

            user3 = User(first_name='John3',
                         last_name='Doe',
                         creation=d(2014, 6, 20, 10, 58, 10),
                         email='john2@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user3)
            self.add_passwords(user3, 10)

        when = datetime.datetime(2012, 10, 12, 10, 0, 0)
        users = tuple(get_all_users(when))
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].first_name, 'John3')


class BackupsTests(ScriptTests):

    def setUp(self):
        super(BackupsTests, self).setUp()

        # Save sys values
        self.old_args = sys.argv[:]
        self.old_stdout = sys.stdout

    def tearDown(self):
        # Restore sys.values
        sys.argv = self.old_args
        sys.stdout = self.old_stdout

        super(BackupsTests, self).tearDown()

    def test_no_arguments(self):
        # Replace sys argv and stdout
        sys.argv = []
        sys.stdout = StringIO()

        # Call send backups with no arguments
        result = send_backups_via_email()
        self.assertEqual(result, 2)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, 'You must provide at least one argument\n')

    def test_empty_database(self):
        # Call send backups with a config file but an empty database
        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = send_backups_via_email()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, '')

    def test_send_specific_user(self):
        with transaction.manager:
            user1 = User(first_name='John1',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         send_passwords_periodically=False)
            Session.add(user1)
            self.add_passwords(user1, 10)

            user2 = User(first_name='John2',
                         last_name='Doe',
                         email='john2@exaple.com',
                         email_verified=True,
                         send_passwords_periodically=False)
            Session.add(user2)
            self.add_passwords(user2, 10)

            user3 = User(first_name='John3',
                         last_name='Doe',
                         email='john3@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user3)
            self.add_passwords(user3, 10)

            user4 = User(first_name='John4',
                         last_name='Doe',
                         email='john4@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user4)
            self.add_passwords(user4, 10)

        sys.argv = ['notused', self.conf_file_path, 'john3@example.com']
        sys.stdout = StringIO()
        result = send_backups_via_email()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        expected_output = """Passwords sent to John3 Doe <john3@example.com>
"""
        self.assertEqual(stdout, expected_output)

    @freeze_time('2012-01-01 10:00:00')
    def test_several_users_first_of_month(self):
        d = datetime.datetime
        # Add some users
        with transaction.manager:
            user1 = User(first_name='John1',
                         last_name='Doe',
                         creation=d(2012, 12, 12, 9, 10, 0),
                         email='john1@example.com',
                         email_verified=False,
                         send_passwords_periodically=False)
            Session.add(user1)
            self.add_passwords(user1, 10)

            user2 = User(first_name='John2',
                         last_name='Doe',
                         creation=d(2013, 1, 2, 13, 10, 0),
                         email='john2@exaple.com',
                         email_verified=True,
                         send_passwords_periodically=False)
            Session.add(user2)
            self.add_passwords(user2, 10)

            user3 = User(first_name='John3',
                         last_name='Doe',
                         creation=d(2014, 6, 20, 10, 58, 10),
                         email='john3@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user3)
            self.add_passwords(user3, 10)

        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = send_backups_via_email()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        expected_output = """Passwords sent to John3 Doe <john3@example.com>
"""
        self.assertEqual(stdout, expected_output)

    @freeze_time('2012-01-03 10:00:00')
    def test_several_users_not_first_of_month(self):
        d = datetime.datetime
        # Add some users
        with transaction.manager:
            user1 = User(first_name='John1',
                         last_name='Doe',
                         creation=d(2012, 12, 12, 9, 10, 0),
                         email='john1@example.com',
                         email_verified=False,
                         send_passwords_periodically=False)
            Session.add(user1)
            self.add_passwords(user1, 10)

            user2 = User(first_name='John2',
                         last_name='Doe',
                         creation=d(2013, 1, 2, 13, 10, 0),
                         email='john2@exaple.com',
                         email_verified=True,
                         send_passwords_periodically=False)
            Session.add(user2)
            self.add_passwords(user2, 10)

            user3 = User(first_name='John3',
                         last_name='Doe',
                         creation=d(2014, 6, 20, 10, 58, 10),
                         email='john3@example.com',
                         email_verified=True,
                         send_passwords_periodically=True)
            Session.add(user3)
            self.add_passwords(user3, 10)

        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = send_backups_via_email()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        expected_output = ""
        self.assertEqual(stdout, expected_output)
