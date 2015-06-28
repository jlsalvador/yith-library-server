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

from pyramid_mailer import get_mailer

from yithlibraryserver import testing
from yithlibraryserver.user.tests.test_views import create_and_login_user


class ViewTests(testing.TestCase):

    def test_home_anonymous_user(self):
        res = self.testapp.get('/')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Start using it today', no='Get your passwords')

    def test_home_login_user(self):
        create_and_login_user(self.testapp)
        res = self.testapp.get('/')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Get your passwords', no='Start using it today')

    def test_contact_required_fields(self):
        res = self.testapp.get('/contact')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Name')
        res.mustcontain('Email')
        res.mustcontain('Message')

        # The three fields are required
        res = self.testapp.post('/contact', {
            'submit': 'Send message',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('class="error" id="error-deformField1">Required')
        res.mustcontain('class="error" id="error-deformField2">Required')
        res.mustcontain('class="error" id="error-deformField3">Required')

    def test_contact_valid_submission(self):
        res = self.testapp.post('/contact', {
            'name': 'John',
            'email': 'john@example.com',
            'message': 'Testing message',
            'submit': 'Send message',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/')
        # check that the email was sent
        res.request.registry = self.testapp.app.registry
        mailer = get_mailer(res.request)
        self.assertEqual(len(mailer.outbox), 1)
        self.assertEqual(mailer.outbox[0].subject,
                         "John sent a message from Yith's contact form")
        self.assertEqual(mailer.outbox[0].recipients,
                         ['admin1@example.com', 'admin2@example.com'])
        self.assertEqual(mailer.outbox[0].extra_headers,
                         {'Reply-To': 'john@example.com'})

    def test_contact_prefil_fields_with_logged_user(self):
        create_and_login_user(self.testapp,
                              email='john@example.com', email_verified=True)
        res = self.testapp.get('/contact')
        self.assertEqual(res.status, '200 OK')

        res.mustcontain('John')
        res.mustcontain('john@example.com')

    def test_contact_cancel_submission(self):
        res = self.testapp.post('/contact', {
            'cancel': 'Cancel',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/')

    def test_contact_no_admin_emails(self):
        # remove the admin emails configuration
        self.testapp.app.registry.settings['admin_emails'] = []

        res = self.testapp.post('/contact', {
            'name': 'John',
            'email': 'john@example.com',
            'message': 'Testing message',
            'submit': 'Send message',
        })
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/')
        # check that the email was *not* sent
        res.request.registry = self.testapp.app.registry
        mailer = get_mailer(res.request)
        self.assertEqual(len(mailer.outbox), 0)

    def test_tos(self):
        res = self.testapp.get('/tos')
        self.assertEqual(res.status, '200 OK')

    def test_faq(self):
        res = self.testapp.get('/faq?_LOCALE_=en')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Frequently Asked Questions')

        res = self.testapp.get('/faq', headers={
            'Accept-Language': 'en',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Frequently Asked Questions')

        res = self.testapp.get('/faq', headers={
            'Accept-Language': 'es',
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Preguntas Frecuentes')

        res = self.testapp.get('/faq', headers={
            'Accept-Language': 'de',  # German is not supported
        })
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('Frequently Asked Questions')

    def test_credits(self):
        res = self.testapp.get('/credits')
        self.assertEqual(res.status, '200 OK')
