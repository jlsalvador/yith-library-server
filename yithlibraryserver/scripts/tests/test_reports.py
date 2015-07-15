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
import datetime
import sys

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.compat import StringIO
from yithlibraryserver.scripts.reports import users, applications, statistics
from yithlibraryserver.scripts.testing import ScriptTests
from yithlibraryserver.user.models import ExternalIdentity, User
from yithlibraryserver.oauth2.models import Application


class BaseReportTests(ScriptTests):

    def setUp(self):
        super(BaseReportTests, self).setUp()

        # Save sys values
        self.old_args = sys.argv[:]
        self.old_stdout = sys.stdout

    def tearDown(self):
        # Restore sys.values
        sys.argv = self.old_args
        sys.stdout = self.old_stdout

        super(BaseReportTests, self).tearDown()


class UserReportTests(BaseReportTests):

    def test_no_arguments(self):
        # Replace sys argv and stdout
        sys.argv = []
        sys.stdout = StringIO()

        # Call users with no arguments
        result = users()
        self.assertEqual(result, 2)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, 'You must provide at least one argument\n')

    def test_empty_database(self):
        # Call users with a config file but an empty database
        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = users()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, '')

    def test_non_empty_database(self):
        d = datetime.datetime
        with transaction.manager:
            user1 = User(first_name='John',
                         last_name='Doe',
                         creation=d(2012, 12, 12, 12, 12, 12),
                         last_login=d(2012, 12, 12, 12, 12, 12),
                         email='john@example.com')
            Session.add(user1)
            user2 = User(first_name='John2',
                         last_name='Doe2',
                         creation=d(2012, 12, 12, 12, 12, 12),
                         last_login=d(2012, 12, 12, 12, 12, 12),
                         email='john2@example.com',
                         email_verified=True)
            identity2 = ExternalIdentity(user=user2, provider='twitter',
                                         external_id='1234')
            Session.add(user2)
            Session.add(identity2)
            self.add_passwords(user2, 1)
            user3 = User(first_name='John3',
                         last_name='Doe3',
                         creation=d(2012, 12, 12, 12, 12, 12),
                         last_login=d(2012, 12, 12, 12, 12, 12),
                         email='john3@example.com',
                         email_verified=True)
            identity3_1 = ExternalIdentity(user=user3, provider='twitter',
                                           external_id='1234')
            identity3_2 = ExternalIdentity(user=user3, provider='facebook',
                                           external_id='5678')
            identity3_3 = ExternalIdentity(user=user3, provider='google',
                                           external_id='abcd')
            Session.add(user3)
            Session.add(identity3_1)
            Session.add(identity3_2)
            Session.add(identity3_3)
            self.add_passwords(user3, 2)

            Session.flush()
            u1_id = user1.id
            u2_id = user2.id
            u3_id = user3.id
        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = users()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        context = {
            'u1': u1_id,
            'u2': u2_id,
            'u3': u3_id,
            'tab': '\t',
        }
        expected_output = """John Doe <john@example.com> (%(u1)s)
%(tab)sPasswords: 0
%(tab)sProviders:
%(tab)sVerified: False
%(tab)sDate joined: 2012-12-12 12:12:12
%(tab)sLast login: 2012-12-12 12:12:12

John2 Doe2 <john2@example.com> (%(u2)s)
%(tab)sPasswords: 1
%(tab)sProviders: twitter
%(tab)sVerified: True
%(tab)sDate joined: 2012-12-12 12:12:12
%(tab)sLast login: 2012-12-12 12:12:12

John3 Doe3 <john3@example.com> (%(u3)s)
%(tab)sPasswords: 2
%(tab)sProviders: facebook, google, twitter
%(tab)sVerified: True
%(tab)sDate joined: 2012-12-12 12:12:12
%(tab)sLast login: 2012-12-12 12:12:12

""" % context
        self.assertEqual(stdout, expected_output)


class ApplicationsReportTests(BaseReportTests):

    def test_no_arguments(self):
        # Replace sys argv and stdout
        sys.argv = []
        sys.stdout = StringIO()

        result = applications()
        self.assertEqual(result, 2)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, 'You must provide at least one argument\n')

    def test_empty_database(self):
        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = applications()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, '')

    def test_non_empty_database(self):
        with transaction.manager:
            user = User(first_name='John',
                        last_name='Doe',
                        email='john@example.com')
            Session.add(user)

            app1 = Application(user=user,
                               name='Test application 1',
                               main_url='http://example.com',
                               callback_url='http://example.com/callback')
            Session.add(app1)

            app2 = Application(user=user,
                               name='Test application 2',
                               main_url='http://2.example.com',
                               callback_url='http://2.example.com/callback')
            Session.add(app2)

        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = applications()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        expected_output = """Test application 1
%(tab)sOwner: John Doe <john@example.com>
%(tab)sMain URL: http://example.com
%(tab)sCallback URL: http://example.com/callback
%(tab)sUsers: 0

Test application 2
%(tab)sOwner: John Doe <john@example.com>
%(tab)sMain URL: http://2.example.com
%(tab)sCallback URL: http://2.example.com/callback
%(tab)sUsers: 0

""" % {'tab': '\t'}
        self.assertEqual(stdout, expected_output)


class StatisticsReportTests(BaseReportTests):

    def test_statistics_no_arguments(self):
        # Replace sys argv and stdout
        sys.argv = []
        sys.stdout = StringIO()

        # Call statistics with no arguments
        result = statistics()
        self.assertEqual(result, 2)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, 'You must provide at least one argument\n')

    def test_statistics_empty_database(self):
        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = statistics()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, '')

    def test_statistics_non_empty_database(self):
        with transaction.manager:
            user1 = User(first_name='John',
                         last_name='Doe',
                         email='john@example.com',
                         email_verified=True,
                         allow_google_analytics=True)
            identity1 = ExternalIdentity(user=user1, provider='google',
                                         external_id='1')
            Session.add(user1)
            Session.add(identity1)
            self.add_passwords(user1, 10)

            user2 = User(first_name='Peter',
                         last_name='Doe',
                         email='peter@example.com',
                         email_verified=True,
                         allow_google_analytics=False)
            identity2 = ExternalIdentity(user=user1, provider='twitter',
                                         external_id='1')
            Session.add(user2)
            Session.add(identity2)
            self.add_passwords(user2, 20)

            user3 = User(first_name='Susan',
                         last_name='Doe',
                         email='susan@example2.com',
                         email_verified=True,
                         allow_google_analytics=False)
            identity3 = ExternalIdentity(user=user1, provider='facebook',
                                         external_id='1')
            Session.add(user3)
            Session.add(identity3)
            self.add_passwords(user3, 15)

            user4 = User(first_name='Alice',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity4 = ExternalIdentity(user=user1, provider='persona',
                                         external_id='1')
            Session.add(user4)
            Session.add(identity4)

            user5 = User(first_name='Bob',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity5 = ExternalIdentity(user=user1, provider='google',
                                         external_id='2')
            Session.add(user5)
            Session.add(identity5)

            user6 = User(first_name='Kevin',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity6 = ExternalIdentity(user=user1, provider='google',
                                         external_id='3')
            Session.add(user6)
            Session.add(identity6)

            user7 = User(first_name='Maria',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity7 = ExternalIdentity(user=user1, provider='google',
                                         external_id='4')
            Session.add(user7)
            Session.add(identity7)

            user8 = User(first_name='Bran',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity8 = ExternalIdentity(user=user1, provider='twitter',
                                         external_id='2')
            Session.add(user8)
            Session.add(identity8)

            user9 = User(first_name='George',
                         last_name='Doe',
                         email='',
                         email_verified=False,
                         allow_google_analytics=False)
            identity9 = ExternalIdentity(user=user1, provider='twitter',
                                         external_id='3')
            Session.add(user9)
            Session.add(identity9)

            user10 = User(first_name='Travis',
                          last_name='Doe',
                          email='',
                          email_verified=False,
                          allow_google_analytics=False)
            identity10 = ExternalIdentity(user=user1, provider='persona',
                                          external_id='2')
            Session.add(user10)
            Session.add(identity10)
            Session.flush()

        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = statistics()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()

        expected_output = """Number of users: 10
Number of passwords: 45
Verified users: 30.00%% (3)
Users that allow Google Analytics cookie: 10.00%% (1)
Identity providers:
%(tab)sgoogle: 40.00%% (4)
%(tab)stwitter: 30.00%% (3)
%(tab)spersona: 20.00%% (2)
%(tab)sfacebook: 10.00%% (1)
Email providers:
%(tab)sexample.com: 66.67%% (2)
%(tab)sOthers: 33.33%% (1)
Users without email: 70.00%% (7)
Most active users:
%(tab)sPeter Doe <peter@example.com>: 20
%(tab)sSusan Doe <susan@example2.com>: 15
%(tab)sJohn Doe <john@example.com>: 10
Users without passwords: 70.00%% (7)
""" % {'tab': '\t'}
        self.assertEqual(stdout, expected_output)
