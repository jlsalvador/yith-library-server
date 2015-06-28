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

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.oauth2.models import Application
from yithlibraryserver.user.models import User


def create_client():
    user = User(screen_name='Administrator',
                first_name='Alice',
                last_name='Doe',
                email='alice@example.com')

    app = Application(user=user,
                      name='Example',
                      main_url='https://example.com',
                      callback_url='https://example.com/callback',
                      image_url='https://example.com/logo.png',
                      description='Example description')

    with transaction.manager:
        Session.add(user)
        Session.add(app)
        Session.flush()
        owner_id = user.id
        app_id = app.id
        app_secret = app.secret

    return owner_id, app_id, app_secret


def create_user():

    user = User(screen_name='John Doe',
                first_name='John',
                last_name='Doe',
                email='john@example.com')

    with transaction.manager:
        Session.add(user)
        Session.flush()
        user_id = user.id

    return user, user_id
