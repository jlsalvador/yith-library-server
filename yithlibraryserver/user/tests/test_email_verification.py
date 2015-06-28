# Yith Library Server is a password storage server.
# Copyright (C) 2012-2013 Yaco Sistemas
# Copyright (C) 2012-2013 Alejandro Blanco Escudero <alejandro.b.e@gmail.com>
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

from pyramid_mailer import get_mailer

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)
from yithlibraryserver.user.email_verification import EmailVerificationCode
from yithlibraryserver.user.models import User


class EmailVerificationCodeTests(unittest.TestCase):

    def setUp(self):
        self.db_uri = get_test_db_uri()
        self.db_context = sqlalchemy_setup(self.db_uri)

        self.config = testing.setUp()
        self.config.include('pyramid_mailer.testing')
        self.config.include('pyramid_chameleon')
        self.config.include('yithlibraryserver.user')

        metadata.create_all()

    def tearDown(self):
        testing.tearDown()
        sqlalchemy_teardown(self.db_context)

    def test_email_verification_code_verify_negative(self):
        evc = EmailVerificationCode()

        self.assertNotEqual(evc.code, None)

        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com')
        Session.add(user)
        Session.flush()

        evc2 = EmailVerificationCode(evc.code)
        result = evc2.verify('john@example.com')
        self.assertEqual(result, None)

    def test_email_verification_code_verify_positive(self):
        evc = EmailVerificationCode()

        self.assertNotEqual(evc.code, None)

        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com',
                    email_verification_code=evc.code)
        Session.add(user)
        Session.flush()

        evc2 = EmailVerificationCode(evc.code)
        result = evc2.verify('john@example.com')
        self.assertNotEqual(result, None)
        self.assertEqual(user.id, result.id)

    def test_email_verification_code_send(self):
        evc = EmailVerificationCode()
        user = User(first_name='John',
                    last_name='Doe',
                    email='john@example.com',
                    email_verification_code=evc.code)
        Session.add(user)
        Session.flush()

        request = testing.DummyRequest()
        mailer = get_mailer(request)
        self.assertEqual(len(mailer.outbox), 0)

        evc2 = EmailVerificationCode(evc.code)
        evc2.send(request, user, 'http://example.com/verify')

        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         'Please verify your email address')
        self.assertEqual(mailer.outbox[0].recipients,
                         ['john@example.com'])
