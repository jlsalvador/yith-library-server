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

import datetime

from freezegun import freeze_time

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

import transaction

from yithlibraryserver.compat import text_type
from yithlibraryserver.testing import TestCase
from yithlibraryserver.oauth2.models import AccessCode
from yithlibraryserver.oauth2.tests import create_client, create_user
from yithlibraryserver.password.models import Password


class ViewTests(TestCase):

    def setUp(self):
        super(ViewTests, self).setUp()

        self.owner_id, self.app_id, _ = create_client()
        self.user, self.user_id = create_user()
        self.access_code = '1234'
        self.auth_header = {'Authorization': 'Bearer %s' % self.access_code}

        expiration = datetime.datetime(2014, 2, 23, 9, 0)

        access_code = AccessCode(code=self.access_code,
                                 code_type='Bearer',
                                 expiration=expiration,
                                 scope=['read-passwords', 'write-passwords'],
                                 application_id=self.app_id,
                                 user_id=self.user_id)
        with transaction.manager:
            Session.add(access_code)
            Session.flush()

    def test_password_collection_options(self):
        res = self.testapp.options('/passwords')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, b'')
        self.assertEqual(res.headers['Access-Control-Allow-Methods'],
                         'GET, POST')
        self.assertEqual(res.headers['Access-Control-Allow-Headers'],
                         'Origin, Content-Type, Accept, Authorization')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_collection_get_empty(self):
        res = self.testapp.get('/passwords', headers=self.auth_header)
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, b'{"passwords": []}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_collection_get_non_empty(self):
        password = Password(service='testing',
                            secret='s3cr3t',
                            user_id=self.user_id)

        with transaction.manager:
            Session.add(password)
            Session.flush()
            password_id = password.id

        res = self.testapp.get('/passwords', headers=self.auth_header)
        self.assertEqual(res.status, '200 OK')

        self.assertEqual(res.json, {
            "passwords": [{
                'account': '',
                'creation': '2014-02-23T08:00:00',
                'modification': '2014-02-23T08:00:00',
                'expiration': None,
                'id': password_id,
                'notes': u'',
                'owner': self.user_id,
                'user': self.user_id,
                'secret': 's3cr3t',
                'service': 'testing',
                'tags': [],
            }],
        })

    @freeze_time('2014-02-23 08:00:00')
    def test_password_collection_post_bad_request(self):
        res = self.testapp.post('/passwords', '', headers=self.auth_header,
                                status=400)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.body,
                         b'{"message": "No JSON object could be decoded"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_collection_post_good_request(self):
        res = self.testapp.post('/passwords',
                                '{"password": {"secret": "s3cr3t", "service": "myservice"}}',
                                headers=self.auth_header)

        self.assertEqual(res.status, '200 OK')

    def test_password_options(self):
        res = self.testapp.options('/passwords/123456')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, b'')
        self.assertEqual(res.headers['Access-Control-Allow-Methods'],
                         'GET, PUT, DELETE')
        self.assertEqual(res.headers['Access-Control-Allow-Headers'],
                         'Origin, Content-Type, Accept, Authorization')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_get_password_invalid_id(self):
        res = self.testapp.get('/passwords/000000000000000000000000',
                               headers=self.auth_header,
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.body,
                         b'{"message": "Invalid password id"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_get_password_not_found(self):
        res = self.testapp.get('/passwords/00000000-0000-0000-0000-000000000000',
                               headers=self.auth_header,
                               status=404)
        self.assertEqual(res.status, '404 Not Found')
        self.assertEqual(res.body,
                         b'{"message": "Password not found"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_get_password_found(self):
        password = Password(service='testing',
                            secret='s3cr3t',
                            user_id=self.user_id)

        with transaction.manager:
            Session.add(password)
            Session.flush()
            password_id = password.id

        res = self.testapp.get('/passwords/%s' % str(password_id),
                               headers=self.auth_header)
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.json, {
            "password": {
                'account': '',
                'creation': '2014-02-23T08:00:00',
                'modification': '2014-02-23T08:00:00',
                'expiration': None,
                'id': password_id,
                'notes': u'',
                'owner': self.user_id,
                'user': self.user_id,
                'secret': 's3cr3t',
                'service': 'testing',
                'tags': [],
            },
        })

    @freeze_time('2014-02-23 08:00:00')
    def test_password_put_invalid_id(self):
        res = self.testapp.put('/passwords/000000000000000000000000',
                               headers=self.auth_header,
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.body,
                         b'{"message": "Invalid password id"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_put_not_found(self):
        res = self.testapp.put('/passwords/00000000-0000-0000-0000-000000000000',
                               headers=self.auth_header, status=404)
        self.assertEqual(res.status, '404 Not Found')
        self.assertEqual(res.body,
                         b'{"message": "Password not found"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_put_bad_request(self):
        password = Password(service='testing',
                            secret='s3cr3t',
                            user_id=self.user_id)

        with transaction.manager:
            Session.add(password)
            Session.flush()
            password_id = password.id

        res = self.testapp.put('/passwords/%s' % str(password_id),
                               '', headers=self.auth_header,
                               status=400)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.body,
                         b'{"message": "No JSON object could be decoded"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_put_found(self):
        password = Password(service='testing',
                            secret='s3cr3t',
                            user_id=self.user_id)

        with transaction.manager:
            Session.add(password)
            Session.flush()
            password_id = password.id

        data = """{
        "password": {
            "service": "testing2",
            "secret": "sup3rs3cr3t",
            "owner": "%s",
            "id": "%s"
            }
        }""" % (str(self.user_id), str(password_id))
        res = self.testapp.put('/passwords/%s' % str(password_id),
                               data, headers=self.auth_header)
        self.assertEqual(res.status, '200 OK')
        self.maxDiff = None
        self.assertEqual(res.json, {
            "password": {
                'account': '',
                'creation': '2014-02-23T08:00:00',
                'modification': '2014-02-23T08:00:00',
                'expiration': None,
                'id': password_id,
                'notes': u'',
                'owner': self.user_id,
                'user': self.user_id,
                'secret': 'sup3rs3cr3t',
                'service': 'testing2',
                'tags': [],
            },
        })
        password = Session.query(Password).filter(
            Password.id == password_id
        ).one()
        self.assertEqual(password.service, 'testing2')
        self.assertEqual(password.secret, 'sup3rs3cr3t')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_delete_invalid_id(self):
        res = self.testapp.delete('/passwords/000000000000000000000000',
                                  headers=self.auth_header,
                                  status=400)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.body,
                         b'{"message": "Invalid password id"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_delete_not_found(self):
        res = self.testapp.delete('/passwords/00000000-0000-0000-0000-000000000000',
                                  headers=self.auth_header, status=404)
        self.assertEqual(res.status, '404 Not Found')
        self.assertEqual(res.body,
                         b'{"message": "Password not found"}')

    @freeze_time('2014-02-23 08:00:00')
    def test_password_delete_found(self):
        password = Password(service='myservice',
                            secret='s3cr3t',
                            user_id=self.user_id)

        with transaction.manager:
            Session.add(password)
            Session.flush()
            password_id = password.id

        count_before = Session.query(Password).count()
        self.assertEqual(count_before, 1)

        res = self.testapp.delete('/passwords/%s' % str(password_id),
                                  headers=self.auth_header)
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, (b'{"password": {"id": "'
                                    + text_type(password_id).encode('ascii')
                                    + b'"}}'))
        count_after = Session.query(Password).count()
        self.assertEqual(count_after, 0)
        try:
            password = Session.query(Password).filter(
                Password.id == password_id
            ).one()
        except NoResultFound:
            password = None

        self.assertEqual(password, None)
