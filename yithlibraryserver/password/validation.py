# Yith Library Server is a password storage server.
# Copyright (C) 2012-2013 Yaco Sistemas
# Copyright (C) 2012-2013 Alejandro Blanco Escudero <alejandro.b.e@gmail.com>
# Copyright (C) 2012-2013 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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


def validate_password(rawdata, encoding='utf-8'):
    errors = []

    try:
        json_data = json.loads(rawdata.decode(encoding))
        data = json_data['password']
    except ValueError:
        errors.append('No JSON object could be decoded')
    except KeyError:
        errors.append('There must be only one toplevel element called "password"')

    # if we have errors here, we can't proceed
    if errors:
        return {}, errors

    password = {}

    # white list submission attributes ignoring anything else
    # first required attributes
    try:
        password['secret'] = data['secret']
    except KeyError:
        errors.append('Secret is required')

    try:
        password['service'] = data['service']
    except KeyError:
        errors.append('Service is required')

    # then optional attributes
    password['account'] = data.get('account', '')
    password['expiration'] = data.get('expiration')
    password['notes'] = data.get('notes', '')
    password['tags'] = data.get('tags', [])

    return password, errors
