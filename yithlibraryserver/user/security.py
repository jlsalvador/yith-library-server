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

from pyramid.httpexceptions import HTTPFound

from pyramid_sqlalchemy import Session

from sqlalchemy.orm.exc import NoResultFound

from yithlibraryserver.user.models import User


def get_user(request):
    user_id = request.unauthenticated_userid
    if user_id is None:
        return user_id

    try:
        user = Session.query(User).filter(User.id == user_id).one()
    except NoResultFound:
        user = None

    return user


def assert_authenticated_user_is_registered(request):
    user_id = request.authenticated_userid

    try:
        user = Session.query(User).filter(User.id == user_id).one()
    except NoResultFound:
        raise HTTPFound(location=request.route_path('register_new_user'))
    else:
        return user
