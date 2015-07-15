# Yith Library Server is a password storage server.
# Copyright (C) 2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from sqlalchemy.orm.exc import NoResultFound

import transaction

from yithlibraryserver.compat import StringIO
from yithlibraryserver.scripts.clean_access_codes import clean_access_codes
from yithlibraryserver.oauth2.models import AccessCode, Application
from yithlibraryserver.scripts.testing import ScriptTests
from yithlibraryserver.user.models import User


class CleanAccessCodesTests(ScriptTests):

    def setUp(self):
        super(CleanAccessCodesTests, self).setUp()

        # Save sys values
        self.old_args = sys.argv[:]
        self.old_stdout = sys.stdout

    def tearDown(self):
        # Restore sys.values
        sys.argv = self.old_args
        sys.stdout = self.old_stdout

        super(CleanAccessCodesTests, self).tearDown()

    def test_no_arguments(self):
        # Replace sys argv and stdout
        sys.argv = []
        sys.stdout = StringIO()

        # Call clean access codes with no arguments
        result = clean_access_codes()
        self.assertEqual(result, 2)
        stdout = sys.stdout.getvalue()
        self.assertEqual(stdout, 'You must provide at least one argument\n')

    @freeze_time('2015-07-14 20:00:00')
    def test_clean_expired_access_codes(self):
        # add some access codes
        with transaction.manager:
            user1 = User(first_name='John1', last_name='Doe')
            user2 = User(first_name='John2', last_name='Doe')
            user3 = User(first_name='John3', last_name='Doe')
            app = Application(name='Test Application')
            user1.applications.append(app)

            # access code that expires yesterday
            ac1 = AccessCode(
                code='123',
                expiration=datetime.datetime(2015, 7, 13, 10, 0, 0),
                application=app,
                user=user1,
            )

            # access code that expires one second ago
            ac2 = AccessCode(
                code='456',
                expiration=datetime.datetime(2015, 7, 14, 19, 59, 59),
                application=app,
                user=user2,
            )

            # access code that expires in 2 hours
            ac3 = AccessCode(
                code='789',
                expiration=datetime.datetime(2015, 7, 14, 22, 0, 0),
                application=app,
                user=user3,
            )

            Session.add(user1)
            Session.add(user2)
            Session.add(user3)
            Session.add(app)
            Session.add(ac1)
            Session.add(ac2)
            Session.add(ac3)

        self.assertEqual(Session.query(AccessCode).count(), 3)

        sys.argv = ['notused', self.conf_file_path]
        sys.stdout = StringIO()
        result = clean_access_codes()
        self.assertEqual(result, None)
        stdout = sys.stdout.getvalue()
        expected_output = """2 access codes were cleaned
"""
        self.assertEqual(stdout, expected_output)

        self.assertEqual(Session.query(AccessCode).count(), 1)
        try:
            access_code = Session.query(AccessCode).filter(
                AccessCode.code == '789').one()
        except NoResultFound:
            access_code = None

        self.assertNotEqual(access_code, None)
