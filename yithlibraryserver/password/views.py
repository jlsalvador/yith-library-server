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

import json
import uuid

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import view_config, view_defaults

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

from yithlibraryserver.errors import invalid_password_id, password_not_found
from yithlibraryserver.oauth2.decorators import protected_method
from yithlibraryserver.password.models import Password
from yithlibraryserver.password.validation import validate_password


@view_defaults(route_name='password_collection_view', renderer='json')
class PasswordCollectionRESTView(object):

    def __init__(self, request):
        self.request = request

    @view_config(request_method='OPTIONS', renderer='string')
    def options(self):
        headers = self.request.response.headers
        headers['Access-Control-Allow-Methods'] = 'GET, POST'
        headers['Access-Control-Allow-Headers'] = ('Origin, Content-Type, '
                                                   'Accept, Authorization')
        return ''

    @view_config(request_method='GET')
    @protected_method(['read-passwords'])
    def get(self):
        return {
            "passwords": [p.as_dict() for p in self.request.user.passwords],
        }

    @view_config(request_method='POST')
    @protected_method(['write-passwords'])
    def post(self):
        cleaned_data, errors = validate_password(self.request.body,
                                                 self.request.charset)

        if errors:
            result = {'message': ','.join(errors)}
            return HTTPBadRequest(body=json.dumps(result),
                                  content_type='application/json')

        password = Password(**cleaned_data)
        self.request.user.passwords.append(password)
        Session.add(password)
        Session.flush()

        return {'password': password.as_dict()}


@view_defaults(route_name='password_view', renderer='json')
class PasswordRESTView(object):

    def __init__(self, request):
        self.request = request
        self.password_id = self.request.matchdict['password']

    @view_config(request_method='OPTIONS', renderer='string')
    def options(self):
        headers = self.request.response.headers
        headers['Access-Control-Allow-Methods'] = 'GET, PUT, DELETE'
        headers['Access-Control-Allow-Headers'] = ('Origin, Content-Type, '
                                                   'Accept, Authorization')
        return ''

    def _get_password(self):
        try:
            return Session.query(Password).filter(
                Password.id == self.password_id,
                Password.user == self.request.user,
            ).one()
        except NoResultFound:
            return None

    @view_config(request_method='GET')
    @protected_method(['read-passwords'])
    def get(self):
        try:
            uuid.UUID(self.password_id)
        except ValueError:
            return invalid_password_id()

        password = self._get_password()
        if password is None:
            return password_not_found()
        else:
            return {'password': password.as_dict()}

    @view_config(request_method='PUT')
    @protected_method(['write-passwords'])
    def put(self):
        try:
            uuid.UUID(self.password_id)
        except ValueError:
            return invalid_password_id()

        password = self._get_password()
        if password is None:
            return password_not_found()

        else:
            cleaned_data, errors = validate_password(self.request.body,
                                                     self.request.charset)

            if errors:
                result = {'message': ','.join(errors)}
                return HTTPBadRequest(body=json.dumps(result),
                                      content_type='application/json')

            password.secret = cleaned_data['secret']
            password.service = cleaned_data['service']
            password.account = cleaned_data['account']
            password.expiration = cleaned_data['expiration']
            password.notes = cleaned_data['notes']
            password.tags = cleaned_data['tags']

            Session.add(password)

            return {'password': password.as_dict()}

    @view_config(request_method='DELETE')
    @protected_method(['write-passwords'])
    def delete(self):
        try:
            uuid.UUID(self.password_id)
        except ValueError:
            return invalid_password_id()

        password = self._get_password()

        if password is None:
            return password_not_found()
        else:
            Session.delete(password)
            return {'password': {'id': self.password_id}}
