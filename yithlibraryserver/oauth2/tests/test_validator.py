# Yith Library Server is a password storage server.
# Copyright (C) 2014-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

import base64
import datetime

from freezegun import freeze_time

from oauthlib.common import Request, to_unicode

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

from yithlibraryserver.testing import TestCase
from yithlibraryserver.oauth2.models import (
    AccessCode,
    AuthorizationCode,
)
from yithlibraryserver.oauth2.tests import create_client, create_user
from yithlibraryserver.oauth2.validator import RequestValidator
from yithlibraryserver.user.models import User


class RequestValidatorTests(TestCase):

    def setUp(self):
        super(RequestValidatorTests, self).setUp()
        self.owner_id, self.app_id, self.app_secret = create_client()
        _, self.user_id = create_user()

    def _create_request_validator(self, scopes=None):
        rv = RequestValidator(default_scopes=scopes)
        request = Request('https://server.example.com/')
        return rv, request

    def test_init(self):
        rv, _ = self._create_request_validator()
        self.assertEqual(rv.default_scopes, ['read-passwords'])

    def test_init_custom_default_scopes(self):
        rv, _ = self._create_request_validator(['scope1', 'scope2'])
        self.assertEqual(rv.default_scopes, ['scope1', 'scope2'])

    def test_get_client(self):
        rv, _ = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertEqual(client.user_id, self.owner_id)
        self.assertEqual(client.id, self.app_id)
        self.assertEqual(client.name, 'Example')
        self.assertEqual(client.callback_url, 'https://example.com/callback')

    def test_get_client_invalid_client_id_bad_format(self):
        rv, _ = self._create_request_validator()
        client = rv.get_client('123456')
        self.assertEqual(client, None)

    def test_get_client_invalid_client_id_does_not_exist(self):
        rv, _ = self._create_request_validator()
        client = rv.get_client('00000000-0000-0000-0000-000000000000')
        self.assertEqual(client, None)

    def test_get_pretty_scopes(self):
        rv, _ = self._create_request_validator()
        self.assertEqual(rv.get_pretty_scopes([
            'read-passwords',
            'write-passwords',
            'read-userinfo',
        ]), [
            'Access your passwords',
            'Modify your passwords',
            'Access your user information',
        ])

    def test_validate_client_id_true(self):
        rv, request = self._create_request_validator()
        self.assertTrue(rv.validate_client_id(self.app_id, request))
        self.assertEqual(request.client.id, self.app_id)

    def test_validate_client_id_false(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.validate_client_id('invalid-client-id', request))
        self.assertEqual(request.client, None)

    def test_validate_redirect_uri_true(self):
        rv, request = self._create_request_validator()
        self.assertTrue(rv.validate_redirect_uri(
            self.app_id, 'https://example.com/callback', request))

    def test_validate_redirect_uri_false(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.validate_redirect_uri(
            self.app_id, 'https://phising.example.com/callback', request))

    def test_get_default_redirect_uri(self):
        rv, request = self._create_request_validator()
        self.assertEquals(rv.get_default_redirect_uri(self.app_id, request),
                          'https://example.com/callback')

    def test_validate_scopes_true(self):
        rv, request = self._create_request_validator()
        self.assertTrue(rv.validate_scopes(
            self.app_id,
            ['read-passwords'],
            None, request,
        ))
        self.assertTrue(rv.validate_scopes(
            self.app_id,
            ['read-passwords', 'write-passwords'],
            None, request,
        ))
        self.assertTrue(rv.validate_scopes(
            self.app_id,
            ['read-passwords', 'write-passwords', 'read-userinfo'],
            None, request,
        ))

    def test_validate_scopes_false(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.validate_scopes(
            self.app_id,
            ['read-userinfo', 'write-userinfo'],
            None, request,
        ))

    def test_get_default_scopes(self):
        rv, request = self._create_request_validator()
        self.assertEquals(rv.get_default_scopes(self.app_id, request),
                          ['read-passwords'])

    def test_validate_response_type_code(self):
        rv, request = self._create_request_validator()
        self.assertTrue(rv.validate_response_type(self.app_id, 'code',
                                                  None, request))

    def test_validate_response_type_token(self):
        rv, request = self._create_request_validator()
        self.assertTrue(rv.validate_response_type(self.app_id, 'token',
                                                  None, request))

    def test_validate_response_type_invalid(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.validate_response_type(self.app_id, 'invalid',
                                                   None, request))

    @freeze_time('2012-01-10 15:31:11')
    def test_save_authorization_code(self):
        rv, request = self._create_request_validator()
        request.user = Session.query(User).filter(User.id == self.user_id).one()
        request.client = rv.get_client(self.app_id)
        request.scopes = ['read-passwords', 'write-passwords']
        request.redirect_uri = 'https://example.com/callback'
        rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        auth_code = Session.query(AuthorizationCode).filter(
            AuthorizationCode.code == 'abcdef',
        ).one()
        self.assertEquals(auth_code.user_id, self.user_id)
        self.assertEquals(auth_code.application_id, self.app_id)
        self.assertEquals(auth_code.scope, ['read-passwords', 'write-passwords'])
        self.assertEquals(auth_code.redirect_uri, 'https://example.com/callback')
        expected_expiration = datetime.datetime(2012, 1, 10, 15, 41, 11)
        self.assertEquals(auth_code.expiration, expected_expiration)

    def test_authenticate_client_no_headers_no_request_attrs(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_no_headers_bad_request_attrs(self):
        rv, request = self._create_request_validator()
        request.client_id = 'bad client id'
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_no_headers_bad_client_secret(self):
        rv, request = self._create_request_validator()
        request.client_id = self.app_id
        request.client_secret = 'secret'
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_no_headers_good_request_attrs(self):
        rv, request = self._create_request_validator()
        request.client_id = self.app_id
        request.client_secret = self.app_secret
        self.assertTrue(rv.authenticate_client(request))

    def test_authenticate_client_headers_bad_type(self):
        rv, request = self._create_request_validator()
        request.headers['Authorization'] = 'Bearer 123456789'
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_headers_bad_client_id(self):
        rv, request = self._create_request_validator()
        data = 'bad-client-id:bad-password'.encode('utf-8')
        auth = to_unicode(base64.b64encode(data), 'utf-8')
        request.headers['Authorization'] = 'Basic ' + auth
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_headers_bad_password(self):
        rv, request = self._create_request_validator()
        auth = to_unicode(base64.b64encode('123456:secret'.encode('utf-8')),
                          'utf-8')
        request.headers['Authorization'] = 'Basic ' + auth
        self.assertFalse(rv.authenticate_client(request))

    def test_authenticate_client_headers_good(self):
        rv, request = self._create_request_validator()
        credentials = "%s:%s" % (self.app_id, self.app_secret)
        auth = to_unicode(base64.b64encode(credentials.encode('utf-8')),
                          'utf-8')
        request.headers['Authorization'] = 'Basic ' + auth
        self.assertTrue(rv.authenticate_client(request))

    def test_authenticate_client_id_non_implemented(self):
        rv, request = self._create_request_validator()
        self.assertRaises(NotImplementedError, rv.authenticate_client_id,
                          self.app_id, request)

    def test_validate_code_bad_code(self):
        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertFalse(rv.validate_code(self.app_id, 'abcdef', client, request))

    def test_validate_code_expired_code(self):
        with freeze_time('2012-01-10 15:31:11'):
            rv, request = self._create_request_validator()
            client = rv.get_client(self.app_id)

            request.user = Session.query(User).filter(User.id == self.user_id).one()
            request.client = client
            request.scopes = ['read-passwords', 'write-passwords']
            request.redirect_uri = 'https://example.com/callback'
            rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        # move time forward 11 minutes
        with freeze_time('2012-01-10 15:42:11'):
            self.assertFalse(rv.validate_code(self.app_id, 'abcdef', client, request))

    def test_validate_code_good(self):
        with freeze_time('2012-01-10 15:31:11'):
            rv, request = self._create_request_validator()
            request.user = Session.query(User).filter(User.id == self.user_id).one()
            request.client = rv.get_client(self.app_id)
            request.scopes = ['read-passwords', 'write-passwords']
            request.redirect_uri = 'https://example.com/callback'
            rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        # move time forward 5 minutes
        with freeze_time('2012-01-10 15:36:11'):
            rv2, request2 = self._create_request_validator()
            client2 = rv2.get_client(self.app_id)
            request2.client = client2
            self.assertTrue(rv2.validate_code(self.app_id, 'abcdef', client2, request2))
            self.assertEquals(request2.user.id, self.user_id)
            self.assertEquals(request2.scopes, ['read-passwords', 'write-passwords'])

    def test_confirm_redirect_uri_no_redirect_uri(self):
        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertTrue(rv.confirm_redirect_uri(self.app_id, 'abcdef',
                                                None, client))

    def test_confirm_redirect_uri_bad_code(self):
        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertFalse(rv.confirm_redirect_uri(self.app_id, 'abcdef',
                                                 'https://example.com/callback',
                                                 client))

    @freeze_time('2012-01-10 15:31:11')
    def test_confirm_redirect_uri_bad_redirect_uri(self):
        rv, request = self._create_request_validator()
        request.user = Session.query(User).filter(User.id == self.user_id).one()
        request.client = rv.get_client(self.app_id)
        request.scopes = ['read-passwords', 'write-passwords']
        request.redirect_uri = 'https://example.com/callback'
        rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertFalse(rv.confirm_redirect_uri(self.app_id, 'abcdef',
                                                 'http://example.com/callback',
                                                 client))

    @freeze_time('2012-01-10 15:31:11')
    def test_confirm_redirect_uri_good_redirect_uri(self):
        rv, request = self._create_request_validator()
        request.user = Session.query(User).filter(User.id == self.user_id).one()
        request.client = rv.get_client(self.app_id)
        request.scopes = ['read-passwords', 'write-passwords']
        request.redirect_uri = 'https://example.com/callback'
        rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertTrue(rv.confirm_redirect_uri(self.app_id, 'abcdef',
                                                'https://example.com/callback',
                                                client))

    def test_validate_grant_type_bad(self):
        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertFalse(rv.validate_grant_type(self.app_id, 'bad-code',
                                                client, request))

    def test_validate_grant_type_good(self):
        rv, request = self._create_request_validator()
        client = rv.get_client(self.app_id)
        self.assertTrue(rv.validate_grant_type(self.app_id, 'authorization_code',
                                               client, request))

    @freeze_time('2012-01-10 15:31:11')
    def test_save_bearer_token(self):
        rv, request = self._create_request_validator()
        token = {
            'expires_in': 3600,  # seconds
            'access_token': 'fghijk',
            'token_type': 'Bearer',
            'refresh_token': 'lmnopq',
        }
        request.user = Session.query(User).filter(User.id == self.user_id).one()
        request.scopes = ['read-passwords', 'write-passwords']
        request.client = rv.get_client(self.app_id)
        rv.save_bearer_token(token, request)

        access_code = Session.query(AccessCode).filter(
            AccessCode.code == 'fghijk'
        ).one()
        self.assertEquals(access_code.code, 'fghijk')
        self.assertEquals(access_code.code_type, 'Bearer')
        self.assertEquals(access_code.scope, ['read-passwords', 'write-passwords'])
        self.assertEquals(access_code.refresh_code, 'lmnopq')
        expected_expiration = datetime.datetime(2012, 1, 10, 16, 31, 11)
        self.assertEquals(access_code.expiration, expected_expiration)
        self.assertEquals(access_code.user_id, self.user_id)
        self.assertEquals(access_code.application_id, self.app_id)

    @freeze_time('2012-01-10 15:31:11')
    def test_invalidate_authorization_code(self):
        rv, request = self._create_request_validator()
        request.user = Session.query(User).filter(User.id == self.user_id).one()
        request.client = rv.get_client(self.app_id)
        request.scopes = ['read-passwords', 'write-passwords']
        request.redirect_uri = 'https://example.com/callback'
        rv.save_authorization_code(self.app_id, {'code': 'abcdef'}, request)

        rv, request = self._create_request_validator()
        request.client = rv.get_client(self.app_id)
        rv.invalidate_authorization_code(self.app_id, 'abcdef', request)
        try:
            auth_code = Session.query(AuthorizationCode).filter(
                AuthorizationCode.code == 'abcdef',
            ).one()
        except NoResultFound:
            auth_code = None
        self.assertEqual(auth_code, None)

    def test_validate_bearer_token_no_token(self):
        rv, request = self._create_request_validator()
        self.assertFalse(rv.validate_bearer_token(
            'fghijk',
            ['read-passwords', 'write-passwords'],
            request,
        ))

    def test_validate_bearer_token_expired_token(self):
        with freeze_time('2012-01-10 15:31:11'):
            rv, request = self._create_request_validator()
            token = {
                'expires_in': 3600,  # seconds
                'access_token': 'fghijk',
                'token_type': 'Bearer',
                'refresh_token': 'lmnopq',
            }
            request.user = Session.query(User).filter(User.id == self.user_id).one()
            request.scopes = ['read-passwords', 'write-passwords']
            request.client = rv.get_client(self.app_id)
            rv.save_bearer_token(token, request)

        # move time forward 2 hours
        with freeze_time('2012-01-10 17:42:11'):
            rv, request = self._create_request_validator()
            self.assertFalse(rv.validate_bearer_token(
                'fghijk',
                ['read-passwords', 'write-passwords'],
                request,
            ))

    def test_validate_bearer_token_bad_scopes(self):
        with freeze_time('2012-01-10 15:31:11'):
            rv, request = self._create_request_validator()
            token = {
                'expires_in': 3600,  # seconds
                'access_token': 'fghijk',
                'token_type': 'Bearer',
                'refresh_token': 'lmnopq',
            }
            request.user = Session.query(User).filter(User.id == self.user_id).one()
            request.scopes = ['read-passwords', 'write-passwords']
            request.client = rv.get_client(self.app_id)
            rv.save_bearer_token(token, request)

        # move time forward 1/2 hour
        with freeze_time('2012-01-10 16:01:11'):
            rv, request = self._create_request_validator()
            self.assertFalse(rv.validate_bearer_token(
                'fghijk',
                ['read-passwords', 'write-passwords', 'read-userinfo'],
                request,
            ))

    def test_validate_bearer_token_good(self):
        with freeze_time('2012-01-10 15:31:11'):
            rv, request = self._create_request_validator()
            token = {
                'expires_in': 3600,  # seconds
                'access_token': 'fghijk',
                'token_type': 'Bearer',
                'refresh_token': 'lmnopq',
            }
            request.user = Session.query(User).filter(User.id == self.user_id).one()
            request.scopes = ['read-passwords', 'write-passwords']
            request.client = rv.get_client(self.app_id)
            rv.save_bearer_token(token, request)

        # move time forward 1/2 hour
        with freeze_time('2012-01-10 16:01:11'):
            rv, request = self._create_request_validator()
            self.assertTrue(rv.validate_bearer_token(
                'fghijk',
                ['read-passwords', 'write-passwords'],
                request,
            ))

    def test_get_original_scopes_non_implemented(self):
        rv, request = self._create_request_validator()
        self.assertRaises(NotImplementedError, rv.get_original_scopes,
                          'refresh-token', request)
