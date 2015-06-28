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

from yithlibraryserver.password.validation import validate_password


class ValidatePasswordsTests(unittest.TestCase):

    def test_empty_json(self):
        password, errors = validate_password(b'')
        self.assertEqual(password, {})
        self.assertEqual(errors, ['No JSON object could be decoded'])

    def test_bad_json(self):
        password, errors = validate_password(b'[1')
        self.assertEqual(password, {})
        self.assertEqual(errors, ['No JSON object could be decoded'])

    def test_no_password(self):
        password, errors = validate_password(b'{"foo": "bar"}')
        self.assertEqual(password, {})
        self.assertEqual(errors, ['There must be only one toplevel element called "password"'])

    def test_secret_missing(self):
        password, errors = validate_password(b'{"password": {}}')
        self.assertEqual(errors, ['Secret is required',
                                  'Service is required'])

    def test_service_missing(self):
        password, errors = validate_password(b'{"password": {"secret": "s3cr3t"}}')
        self.assertEqual(errors, ['Service is required'])

    def test_everything_fine(self):
        password, errors = validate_password(b'{"password": {"secret": "s3cr3t", "service": "myservice"}}')
        self.assertEqual(errors, [])
        self.assertEqual(password, {
            'secret': 's3cr3t',
            'service': 'myservice',
            'account': '',
            'expiration': None,
            'notes': '',
            'tags': [],
        })
