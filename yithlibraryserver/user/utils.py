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

import datetime

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

from yithlibraryserver.user.models import ExternalIdentity


def split_name(name):
    parts = name.split(' ')
    if len(parts) > 1:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
    else:
        first_name = parts[0]
        last_name = ''

    return first_name, last_name


def user_from_provider_id(provider, external_id):
    try:
        identity = Session.query(ExternalIdentity).filter(
            ExternalIdentity.provider == provider,
            ExternalIdentity.external_id == external_id,
        ).one()
        return identity.user
    except NoResultFound:
        return None


def register_or_update(request, provider, external_id, info, default_url='/'):
    user = user_from_provider_id(provider, external_id)
    if user is None:

        new_info = {'provider': provider, 'external_id': external_id}
        for attribute in ('screen_name', 'first_name', 'last_name', 'email'):
            if attribute in info:
                new_info[attribute] = info[attribute]
            else:
                new_info[attribute] = ''

        request.session['user_info'] = new_info
        if 'next_url' not in request.session:
            request.session['next_url'] = default_url
        return HTTPFound(location=request.route_path('register_new_user'))
    else:
        user.last_login = datetime.datetime.utcnow()

        ga = request.google_analytics
        if ga.is_in_session():
            if user.allow_google_analytics is None:
                user.allow_google_analytics = ga.show_in_session()
            ga.clean_session()

        user.update_user_info(info)
        Session.add(user)

        if 'next_url' in request.session:
            next_url = request.session['next_url']
            del request.session['next_url']
        else:
            next_url = default_url

        request.session['current_provider'] = provider
        remember_headers = remember(request, str(user.id))
        return HTTPFound(location=next_url, headers=remember_headers)
