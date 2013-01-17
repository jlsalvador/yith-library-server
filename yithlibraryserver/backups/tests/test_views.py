# Yith Library Server is a password storage server.
# Copyright (C) 2013 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from yithlibraryserver.testing import TestCase


class ViewTests(TestCase):

    clean_collections = ('users', 'passwords', )

    def test_backups_index(self):
        res = self.testapp.get('/backup')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

        # Log in
        date = datetime.datetime(2012, 12, 12, 12, 12)
        user_id = self.db.users.insert({
                'twitter_id': 'twitter1',
                'screen_name': 'John Doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': '',
                'email_verified': False,
                'authorized_apps': [],
                'date_joined': date,
                'last_login': date,
                }, safe=True)
        self.set_user_cookie(str(user_id))

        res = self.testapp.get('/backup')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Backup', 'Export passwords', 'Import passwords')

    def test_backups_export(self):
        res = self.testapp.get('/backup/export')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

        # Log in
        date = datetime.datetime(2012, 12, 12, 12, 12)
        user_id = self.db.users.insert({
                'twitter_id': 'twitter1',
                'screen_name': 'John Doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': '',
                'email_verified': False,
                'authorized_apps': [],
                'date_joined': date,
                'last_login': date,
                }, safe=True)
        self.set_user_cookie(str(user_id))

        res = self.testapp.get('/backup/export')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.content_type, 'application/json')
        self.assertEqual(res.json, [])
        cd = 'attachment; filename=yith-library-backup-%d-%02d-%02d.json'
        today = datetime.date.today()
        self.assertEqual(res.content_disposition,
                         cd % (today.year, today.month, today.day))

        self.db.passwords.insert({
                'owner': user_id,
                'password': 'secret1',
                })
        self.db.passwords.insert({
                'owner': user_id,
                'password': 'secret2',
                })

        res = self.testapp.get('/backup/export')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.content_type, 'application/json')
        self.assertEqual(res.json, [{
                    'password': 'secret1',
                    }, {
                    'password': 'secret2',
                    }])
        cd = 'attachment; filename=yith-library-backup-%d-%02d-%02d.json'
        today = datetime.date.today()
        self.assertEqual(res.content_disposition,
                         cd % (today.year, today.month, today.day))

    def test_backups_import(self):
        res = self.testapp.post('/backup/import')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Log in')

        # Log in
        date = datetime.datetime(2012, 12, 12, 12, 12)
        user_id = self.db.users.insert({
                'twitter_id': 'twitter1',
                'screen_name': 'John Doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': '',
                'email_verified': False,
                'authorized_apps': [],
                'date_joined': date,
                'last_login': date,
                }, safe=True)
        self.set_user_cookie(str(user_id))

        # no file to upload
        res = self.testapp.post('/backup/import', status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(0, self.db.passwords.count())

        # not really a file
        res = self.testapp.post('/backup/import', {
                'passwords-file': '',
                }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(0, self.db.passwords.count())

        # bad file
        res = self.testapp.post(
            '/backup/import', {},
            upload_files=[('passwords-file', 'bad.json', '[{}')],
            status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(0, self.db.passwords.count())

        # file with good syntax but empty
        res = self.testapp.post(
            '/backup/import', {},
            upload_files=[('passwords-file', 'empty.json', '[]')],
            status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(0, self.db.passwords.count())

        # file with good syntax but empty
        res = self.testapp.post(
            '/backup/import', {},
            upload_files=[('passwords-file', 'empty.json', '[{}]')],
            status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(0, self.db.passwords.count())

        # file with good passwords
        content = '[{"secret": "password1"}, {"secret": "password2"}]'
        res = self.testapp.post(
            '/backup/import', {},
            upload_files=[('passwords-file', 'good.json', content)],
            status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/backup')

        self.assertEqual(2, self.db.passwords.count())
