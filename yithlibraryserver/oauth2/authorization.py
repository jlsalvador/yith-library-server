# Yith Library Server is a password storage server.
# Copyright (C) 2012-2014 Yaco Sistemas
# Copyright (C) 2012-2014 Alejandro Blanco Escudero <alejandro.b.e@gmail.com>
# Copyright (C) 2012-2014 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from oauthlib.oauth2 import Server

from pyramid.httpexceptions import HTTPUnauthorized

from yithlibraryserver.oauth2.utils import extract_params
from yithlibraryserver.oauth2.validator import RequestValidator


def verify_request(request, scopes):
    validator = RequestValidator()
    server = Server(validator)

    uri, http_method, body, headers = extract_params(request)

    valid, r = server.verify_request(
        uri, http_method, body, headers, scopes,
    )

    if not valid:
        raise HTTPUnauthorized()

    return r.user
