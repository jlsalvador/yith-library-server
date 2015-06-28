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

from pyramid import testing

from pyramid_mailer import get_mailer

from yithlibraryserver.contributions.email import send_thankyou_email
from yithlibraryserver.contributions.email import send_notification_to_admins
from yithlibraryserver.contributions.models import Donation
from yithlibraryserver.testing import (
    FakeRequest,
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)


class SendEmailTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)
        self.admin_emails = ['admin1@example.com', 'admin2@example.com']
        self.config = testing.setUp(settings={
            'admin_emails': self.admin_emails,
            'database_url': get_test_db_uri(),
        })
        self.config.include('pyramid_mailer.testing')
        self.config.include('pyramid_chameleon')

        self.config.include('yithlibraryserver.contributions')
        self.config.include('yithlibraryserver.user')
        self.config.add_route('home', '/')

        self.donation = Donation(
            amount=10,
            first_name='John',
            last_name='Doe',
            city='Springfield',
            country='Exampleland',
            state='Example',
            street='Main Street 10',
            zipcode='12345678',
            email='john@example.com',
            send_sticker=True,
        )

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_send_thankyou_email(self):
        request = FakeRequest()
        mailer = get_mailer(request)

        self.assertEqual(len(mailer.outbox), 0)

        send_thankyou_email(request, self.donation)

        self.assertEqual(len(mailer.outbox), 1)
        message = mailer.outbox[0]
        self.assertEqual(message.subject, 'Thanks for your contribution!')
        self.assertEqual(message.recipients, ['john@example.com'])

    def test_send_notification_to_admins(self):
        request = testing.DummyRequest()
        mailer = get_mailer(request)

        self.assertEqual(len(mailer.outbox), 0)

        send_notification_to_admins(request, self.donation)

        self.assertEqual(len(mailer.outbox), 1)
        message = mailer.outbox[0]
        self.assertEqual(message.subject, 'A new donation was received!')
        self.assertEqual(message.recipients, self.admin_emails)
