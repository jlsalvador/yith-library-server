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
import unittest

from freezegun import freeze_time

from pyramid import testing

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.backups.utils import get_user_passwords
from yithlibraryserver.backups.utils import get_backup_filename
from yithlibraryserver.backups.utils import compress, uncompress
from yithlibraryserver.password.models import Password
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.models import User


class UtilsTests(unittest.TestCase):

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

    def test_get_user_passwords_no_passwords(self):
        user = User(first_name='John',
                    last_name='Doe')

        with transaction.manager:
            Session.add(user)
            Session.flush()
            user_id = user.id

        user = Session.query(User).filter(User.id == user_id).one()

        self.assertEqual(get_user_passwords(user), [])

    @freeze_time('2014-02-23 08:00:00')
    def test_get_user_passwords_some_passwords(self):
        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        # add some passwords
        password1 = Password(secret='s3cr3t1', user=user)
        password2 = Password(secret='s3cr3t2', user=user)

        with transaction.manager:
            Session.add(user)
            Session.add(password1)
            Session.add(password2)
            Session.flush()
            user_id = user.id

        user = Session.query(User).filter(User.id == user_id).one()

        self.assertEqual(get_user_passwords(user), [{
            'account': '',
            'creation': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'expiration': None,
            'modification': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'notes': '',
            'secret': 's3cr3t1',
            'service': '',
            'tags': [],
        }, {
            'account': '',
            'creation': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'expiration': None,
            'modification': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'notes': '',
            'secret': 's3cr3t2',
            'service': '',
            'tags': [],
        }])

    def test_get_backup_filename(self):
        self.assertEqual(get_backup_filename(datetime.date(2012, 10, 28)),
                         'yith-library-backup-2012-10-28.yith')
        self.assertEqual(get_backup_filename(datetime.date(2013, 1, 8)),
                         'yith-library-backup-2013-01-08.yith')

    def test_compress_and_uncompress(self):
        passwords = [{
            'account': '',
            'creation': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'expiration': None,
            'modification': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'notes': '',
            'secret': 's3cr3t2',
            'service': '',
            'tags': [],
        }, {
            'account': '',
            'creation': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'expiration': None,
            'modification': datetime.datetime(2014, 2, 23, 8, 0, 0),
            'notes': '',
            'secret': 's3cr3t2',
            'service': '',
            'tags': [],
        }]

        self.assertEqual(uncompress(compress(passwords)), passwords)
