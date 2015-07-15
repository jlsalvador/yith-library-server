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

import unittest

from freezegun import freeze_time

from pyramid import testing
from pyramid.testing import DummyRequest

from pyramid_mailer import get_mailer

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.backups.email import send_passwords
from yithlibraryserver.password.models import Password
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.models import User


class SendPasswordsTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)
        self.config = testing.setUp()
        self.config.include('pyramid_mailer.testing')
        self.config.include('pyramid_chameleon')
        self.config.include('yithlibraryserver.password')
        self.config.include('yithlibraryserver.user')
        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_send_passwords_user_has_no_passwords(self):
        preferences_link = 'http://localhost/preferences'
        backups_link = 'http://localhost/backups'

        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        with transaction.manager:
            Session.add(user)
            Session.flush()
            user_id = user.id

        user = Session.query(User).filter(User.id == user_id).one()

        request = DummyRequest()
        mailer = get_mailer(request)

        self.assertFalse(send_passwords(request, user,
                                        preferences_link, backups_link))
        self.assertEqual(len(mailer.outbox), 0)

    def test_send_passwords_user_has_some_passwords(self):
        preferences_link = 'http://localhost/preferences'
        backups_link = 'http://localhost/backups'

        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com')

        # add some passwords
        password1 = Password(service='testing1',
                             secret='s3cr3t1',
                             user=user)
        password2 = Password(service='testing2',
                             secret='s3cr3t2',
                             user=user)

        with transaction.manager:
            Session.add(user)
            Session.add(password1)
            Session.add(password2)
            Session.flush()
            user_id = user.id

        user = Session.query(User).filter(User.id == user_id).one()

        request = DummyRequest()
        mailer = get_mailer(request)

        with freeze_time('2012-01-10'):
            self.assertTrue(send_passwords(request, user,
                                           preferences_link, backups_link))
            self.assertEqual(len(mailer.outbox), 1)
            message = mailer.outbox[0]
            self.assertEqual(message.subject, "Your Yith Library's passwords")
            self.assertEqual(message.recipients, ['john@example.com'])
            self.assertTrue(preferences_link in message.body)
            self.assertTrue(backups_link in message.body)
            self.assertEqual(len(message.attachments), 1)
            attachment = message.attachments[0]
            self.assertEqual(attachment.content_type, 'application/yith')
            self.assertEqual(attachment.filename,
                             'yith-library-backup-2012-01-10.yith')
