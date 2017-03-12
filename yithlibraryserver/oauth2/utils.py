# Yith Library Server is a password storage server.
# Copyright (C) 2014 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from webob.compat import native_

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import Response

from oauthlib.common import to_unicode, bytes_type


def extract_params(request):
    """Extract uri, http_method, body and headers from the request"""
    uri = request.url
    http_method = request.method
    headers = dict(request.headers)
    for header_to_remove in ('wsgi.input', 'wsgi.errors'):
        if header_to_remove in headers:
            del headers[header_to_remove]
    body = request.body
    return uri, http_method, body, headers


def create_response(headers, body, status):
    headerlist = [(native_(k), native_(v))
                  for k, v in headers.items()]
    return Response(body=body, status=status, headerlist=headerlist,
                    charset='utf8')


def response_from_error(error):
    response = HTTPBadRequest()
    msg = 'Evil client is unable to send a proper request. Error is: '
    response.text = to_unicode(msg + error.error, 'utf-8')
    return response


def decode_base64(text, encoding='utf-8'):
    """Decode base64 string."""
    if text and not isinstance(text, bytes_type):
        text = text.encode(encoding)
    return to_unicode(base64.b64decode(text), encoding)
