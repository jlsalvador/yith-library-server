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

from freezegun import freeze_time

from pyramid_mailer import get_mailer

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.compat import mock
from yithlibraryserver.contributions.models import Donation
from yithlibraryserver.testing import TestCase
from yithlibraryserver.user.models import User


def create_and_login_user(testapp):

    user = User(screen_name='John Doe',
                first_name='John',
                last_name='Doe',
                email='john@example.com')

    with transaction.manager:
        Session.add(user)
        Session.flush()
        user_id = user.id

    testapp.get('/__login/' + str(user_id))
    return user, user_id


class TestViews(TestCase):

    def test_contributions_index(self):
        res = self.testapp.get('/contribute')
        self.assertEqual(res.status, '200 OK')
        res.mustcontain('We need your help!', 'Spread the word',
                        'Translate', 'Write some code',
                        'Give us your money')

    def test_contributions_donate_bad_method(self):
        res = self.testapp.get('/contribute/donate', status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_contributions_donate_bad_amount(self):
        res = self.testapp.post('/contribute/donate', {
            'amount': 'five',
            'submit': 'submit',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_contributions_donate(self):
        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success&TOKEN=123'
            res = self.testapp.post('/contribute/donate', {
                'amount': '5',
                'submit': 'submit',
            }, status=302)

            self.assertEqual(res.status, '302 Found')
            self.assertEqual(res.location, 'https://www.sandbox.paypal.com/webscr?cmd=_express-checkout&token=123')

            # USER, PWD, and SIGNATURE are Paypal testing values
            # They are set in yithlibrary.testing.TestCase.setUp
            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'SetExpressCheckout',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'LOCALECODE': 'EN',
                'PAYMENTREQUEST_0_ITEMAMT': 5,
                'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
                'PAYMENTREQUEST_0_CURRENCYCODE': 'USD',
                'PAYMENTREQUEST_0_AMT': 5,
                'PAYMENTREQUEST_0_DESC': 'Donation',
                'L_PAYMENTREQUEST_0_NAME0': 'Donation of $5',
                'L_PAYMENTREQUEST_0_AMT0': 5,
                'BRANDNAME': 'Yith Library',
                'RETURNURL': 'http://localhost/contribute/paypal-success-callback',
                'CANCELURL': 'http://localhost/contribute/paypal-cancel-callback',
            })

    def test_contributions_confirm_error(self):
        res = self.testapp.get('/contribute/paypal-success-callback',
                               status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/contribute')
        session = self.get_session(res)
        self.assertEqual(session['_f_error'], ['There was a problem in the confirmation process. Please start the checkout again'])

    def test_contributions_confirm_details(self):
        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success&AMT=5.00&FIRSTNAME=John&LASTNAME=Doe&SHIPTOCITY=ExampleCity&SHIPTOCOUNTRYNAME=ExampleCountry&SHIPTOSTATE=ExampleState&SHIPTOSTREET=ExampleStreet&SHIPTOZIP=123456&EMAIL=john@example.com'
            res = self.testapp.get('/contribute/paypal-success-callback?token=123&PayerID=456')
            self.assertEqual(res.status, '200 OK')
            res.mustcontain('John', 'Doe', 'ExampleCity', 'ExampleCountry',
                            'ExampleState', 'ExampleStreet', '123456')
            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'GetExpressCheckoutDetails',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'TOKEN': '123',
                'PAYERID': '456',
            })

    def test_contributions_confirm_bad_action(self):
        res = self.testapp.post('/contribute/paypal-success-callback',
                                status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_contributions_confirm_bad_amount(self):
        res = self.testapp.post('/contribute/paypal-success-callback', {
            'submit': 'Submit',
            'token': '123',
            'payerid': '456',
            'amount': 'five',
        }, status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_contributions_confirm_cancel(self):
        res = self.testapp.post('/contribute/paypal-success-callback', {
            'cancel': 'Cancel',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/contribute/paypal-cancel-callback')

    def test_contributions_confirm_error2(self):
        res = self.testapp.post('/contribute/paypal-success-callback', {
            'submit': 'Submit',
        }, status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/contribute')

        session = self.get_session(res)
        self.assertEqual(session['_f_error'], ['There was a problem in the confirmation process. Please start the checkout again'])

    @freeze_time('2013-01-02 10:11:02')
    def test_contributions_confirm_success_with_sticker(self):
        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success'

            self.assertEqual(Session.query(Donation).count(), 0)

            res = self.testapp.post('/contribute/paypal-success-callback', {
                'submit': 'Submit',
                'token': '123',
                'payerid': '456',
                'amount': '5',
                'firstname': 'John',
                'lastname': 'Doe',
                'city': 'ExampleCity',
                'country': 'ExampleCountry',
                'state': 'ExampleState',
                'street': 'ExampleStreet',
                'zip': '123456',
                'email': 'john@example.com',
            }, status=302)
            self.assertEqual(res.status, '302 Found')
            self.assertEqual(res.location, 'http://localhost/contribute')

            session = self.get_session(res)
            self.assertEqual(session['_f_success'], ['Thank you very much for your great contribution'])

            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'DoExpressCheckoutPayment',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'TOKEN': '123',
                'PAYERID': '456',
                'LOCALECODE': 'EN',
                'PAYMENTREQUEST_0_ITEMAMT': 5,
                'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
                'PAYMENTREQUEST_0_CURRENCYCODE': 'USD',
                'PAYMENTREQUEST_0_AMT': 5,
                'PAYMENTREQUEST_0_DESC': 'Donation',
                'L_PAYMENTREQUEST_0_NAME0': 'Donation of $5',
                'L_PAYMENTREQUEST_0_AMT0': 5,
                'BRANDNAME': 'Yith Library',
            })

            res.request.registry = self.testapp.app.registry
            mailer = get_mailer(res.request)

            # a couple of emails are sent
            self.assertEqual(len(mailer.outbox), 2)
            self.assertEqual(mailer.outbox[0].subject,
                             'Thanks for your contribution!')
            self.assertEqual(mailer.outbox[0].recipients,
                             ['john@example.com'])
            self.assertEqual(mailer.outbox[1].subject,
                             'A new donation was received!')
            self.assertEqual(mailer.outbox[1].recipients,
                             ['admin1@example.com', 'admin2@example.com'])

            # a new object in the database stores this donation
            self.assertEqual(Session.query(Donation).count(), 1)
            donation = Session.query(Donation).one()
            self.assertEqual(donation.amount, 5)
            self.assertEqual(donation.first_name, 'John')
            self.assertEqual(donation.last_name, 'Doe')
            self.assertEqual(donation.city, 'ExampleCity')
            self.assertEqual(donation.country, 'ExampleCountry')
            self.assertEqual(donation.state, 'ExampleState')
            self.assertEqual(donation.street, 'ExampleStreet')
            self.assertEqual(donation.zipcode, '123456')
            self.assertEqual(donation.email, 'john@example.com')
            self.assertEqual(donation.creation,
                             datetime.datetime(2013, 1, 2, 10, 11, 2))
            self.assertTrue(donation.send_sticker)
            self.assertEqual(donation.user, None)

    @freeze_time('2013-01-02 10:11:02')
    def test_contributions_confirm_success_with_no_sticker_small_contribution(self):
        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success'

            self.assertEqual(Session.query(Donation).count(), 0)

            res = self.testapp.post('/contribute/paypal-success-callback', {
                'submit': 'Submit',
                'token': '123',
                'payerid': '456',
                'amount': '1',
                'firstname': 'John',
                'lastname': 'Doe',
                'city': 'ExampleCity',
                'country': 'ExampleCountry',
                'state': 'ExampleState',
                'street': 'ExampleStreet',
                'zip': '123456',
                'email': 'john@example.com',
            }, status=302)
            self.assertEqual(res.status, '302 Found')
            self.assertEqual(res.location, 'http://localhost/contribute')

            session = self.get_session(res)
            self.assertEqual(session['_f_success'], ['Thank you very much for your great contribution'])

            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'DoExpressCheckoutPayment',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'TOKEN': '123',
                'PAYERID': '456',
                'LOCALECODE': 'EN',
                'PAYMENTREQUEST_0_ITEMAMT': 1,
                'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
                'PAYMENTREQUEST_0_CURRENCYCODE': 'USD',
                'PAYMENTREQUEST_0_AMT': 1,
                'PAYMENTREQUEST_0_DESC': 'Donation',
                'L_PAYMENTREQUEST_0_NAME0': 'Donation of $1',
                'L_PAYMENTREQUEST_0_AMT0': 1,
                'BRANDNAME': 'Yith Library',
            })

            res.request.registry = self.testapp.app.registry
            mailer = get_mailer(res.request)

            # a couple of emails are sent
            self.assertEqual(len(mailer.outbox), 2)
            self.assertEqual(mailer.outbox[0].subject,
                             'Thanks for your contribution!')
            self.assertEqual(mailer.outbox[0].recipients,
                             ['john@example.com'])
            self.assertEqual(mailer.outbox[1].subject,
                             'A new donation was received!')
            self.assertEqual(mailer.outbox[1].recipients,
                             ['admin1@example.com', 'admin2@example.com'])

            # a new object in the database stores this donation
            self.assertEqual(Session.query(Donation).count(), 1)
            donation = Session.query(Donation).one()
            self.assertEqual(donation.amount, 1)
            self.assertEqual(donation.first_name, 'John')
            self.assertEqual(donation.last_name, 'Doe')
            self.assertEqual(donation.city, 'ExampleCity')
            self.assertEqual(donation.country, 'ExampleCountry')
            self.assertEqual(donation.state, 'ExampleState')
            self.assertEqual(donation.street, 'ExampleStreet')
            self.assertEqual(donation.zipcode, '123456')
            self.assertEqual(donation.email, 'john@example.com')
            self.assertEqual(donation.creation,
                             datetime.datetime(2013, 1, 2, 10, 11, 2))
            self.assertFalse(donation.send_sticker)
            self.assertEqual(donation.user, None)

    @freeze_time('2013-01-02 10:11:02')
    def test_contributions_confirm_success_with_no_sticker_user_donate_all_money(self):
        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success'

            self.assertEqual(Session.query(Donation).count(), 0)

            res = self.testapp.post('/contribute/paypal-success-callback', {
                'submit': 'Submit',
                'token': '123',
                'payerid': '456',
                'amount': '10',
                'firstname': 'John',
                'lastname': 'Doe',
                'city': 'ExampleCity',
                'country': 'ExampleCountry',
                'state': 'ExampleState',
                'street': 'ExampleStreet',
                'zip': '123456',
                'email': 'john@example.com',
                'no-sticker': '1',
            }, status=302)
            self.assertEqual(res.status, '302 Found')
            self.assertEqual(res.location, 'http://localhost/contribute')

            session = self.get_session(res)
            self.assertEqual(session['_f_success'], ['Thank you very much for your great contribution'])

            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'DoExpressCheckoutPayment',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'TOKEN': '123',
                'PAYERID': '456',
                'LOCALECODE': 'EN',
                'PAYMENTREQUEST_0_ITEMAMT': 10,
                'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
                'PAYMENTREQUEST_0_CURRENCYCODE': 'USD',
                'PAYMENTREQUEST_0_AMT': 10,
                'PAYMENTREQUEST_0_DESC': 'Donation',
                'L_PAYMENTREQUEST_0_NAME0': 'Donation of $10',
                'L_PAYMENTREQUEST_0_AMT0': 10,
                'BRANDNAME': 'Yith Library',
            })

            res.request.registry = self.testapp.app.registry
            mailer = get_mailer(res.request)

            # a couple of emails are sent
            self.assertEqual(len(mailer.outbox), 2)
            self.assertEqual(mailer.outbox[0].subject,
                             'Thanks for your contribution!')
            self.assertEqual(mailer.outbox[0].recipients,
                             ['john@example.com'])
            self.assertEqual(mailer.outbox[1].subject,
                             'A new donation was received!')
            self.assertEqual(mailer.outbox[1].recipients,
                             ['admin1@example.com', 'admin2@example.com'])

            # a new object in the database stores this donation
            self.assertEqual(Session.query(Donation).count(), 1)
            donation = Session.query(Donation).one()
            self.assertEqual(donation.amount, 10)
            self.assertEqual(donation.first_name, 'John')
            self.assertEqual(donation.last_name, 'Doe')
            self.assertEqual(donation.city, 'ExampleCity')
            self.assertEqual(donation.country, 'ExampleCountry')
            self.assertEqual(donation.state, 'ExampleState')
            self.assertEqual(donation.street, 'ExampleStreet')
            self.assertEqual(donation.zipcode, '123456')
            self.assertEqual(donation.email, 'john@example.com')
            self.assertEqual(donation.creation,
                             datetime.datetime(2013, 1, 2, 10, 11, 2))
            self.assertFalse(donation.send_sticker)
            self.assertEqual(donation.user, None)

    @freeze_time('2013-01-02 10:11:02')
    def test_contributions_confirm_success_with_user(self):
        user, user_id = create_and_login_user(self.testapp)

        with mock.patch('requests.post') as fake:
            fake.return_value.ok = True
            fake.return_value.text = 'ACK=Success'

            self.assertEqual(Session.query(Donation).count(), 0)

            res = self.testapp.post('/contribute/paypal-success-callback', {
                'submit': 'Submit',
                'token': '123',
                'payerid': '456',
                'amount': '10',
                'firstname': 'John',
                'lastname': 'Doe',
                'city': 'ExampleCity',
                'country': 'ExampleCountry',
                'state': 'ExampleState',
                'street': 'ExampleStreet',
                'zip': '123456',
                'email': 'john@example.com',
            }, status=302)
            self.assertEqual(res.status, '302 Found')
            self.assertEqual(res.location, 'http://localhost/contribute')

            session = self.get_session(res)
            self.assertEqual(session['_f_success'], ['Thank you very much for your great contribution'])

            fake.assert_called_with('https://api-3t.sandbox.paypal.com/nvp', data={
                'METHOD': 'DoExpressCheckoutPayment',
                'VERSION': '72.0',
                'USER': 'sdk-three_api1.sdk.com',
                'PWD': 'QFZCWN5HZM8VBG7Q',
                'SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
                'TOKEN': '123',
                'PAYERID': '456',
                'LOCALECODE': 'EN',
                'PAYMENTREQUEST_0_ITEMAMT': 10,
                'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
                'PAYMENTREQUEST_0_CURRENCYCODE': 'USD',
                'PAYMENTREQUEST_0_AMT': 10,
                'PAYMENTREQUEST_0_DESC': 'Donation',
                'L_PAYMENTREQUEST_0_NAME0': 'Donation of $10',
                'L_PAYMENTREQUEST_0_AMT0': 10,
                'BRANDNAME': 'Yith Library',
            })

            res.request.registry = self.testapp.app.registry
            mailer = get_mailer(res.request)

            # a couple of emails are sent
            self.assertEqual(len(mailer.outbox), 2)
            self.assertEqual(mailer.outbox[0].subject,
                             'Thanks for your contribution!')
            self.assertEqual(mailer.outbox[0].recipients,
                             ['john@example.com'])
            self.assertEqual(mailer.outbox[1].subject,
                             'A new donation was received!')
            self.assertEqual(mailer.outbox[1].recipients,
                             ['admin1@example.com', 'admin2@example.com'])

            # a new object in the database stores this donation
            self.assertEqual(Session.query(Donation).count(), 1)
            donation = Session.query(Donation).one()
            self.assertEqual(donation.amount, 10)
            self.assertEqual(donation.first_name, 'John')
            self.assertEqual(donation.last_name, 'Doe')
            self.assertEqual(donation.city, 'ExampleCity')
            self.assertEqual(donation.country, 'ExampleCountry')
            self.assertEqual(donation.state, 'ExampleState')
            self.assertEqual(donation.street, 'ExampleStreet')
            self.assertEqual(donation.zipcode, '123456')
            self.assertEqual(donation.email, 'john@example.com')
            self.assertEqual(donation.creation,
                             datetime.datetime(2013, 1, 2, 10, 11, 2))
            self.assertTrue(donation.send_sticker)
            self.assertEqual(donation.user_id, user_id)

    def test_contributions_cancel(self):
        res = self.testapp.get('/contribute/paypal-cancel-callback',
                               status=302)
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.location, 'http://localhost/contribute')
        session = self.get_session(res)
        self.assertEqual(session['_f_info'], ['Thanks for considering donating to Yith Library. We will be ready if you change your mind'])
