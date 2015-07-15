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

from pyramid_sqlalchemy import Session
from sqlalchemy.orm.exc import NoResultFound

from yithlibraryserver.email import send_email_to_admins
from yithlibraryserver.oauth2.models import (
    AccessCode,
    Application,
    AuthorizedApplication,
    AuthorizationCode,
)
from yithlibraryserver.password.models import Password
from yithlibraryserver.user.models import ExternalIdentity, User


def merge_accounts(master_user, accounts):
    merged = 0

    for account in accounts:
        user_id = account
        if master_user.id == user_id:
            continue

        try:
            current_user = Session.query(User).filter(User.id == user_id).one()
        except NoResultFound:
            continue

        merge_users(master_user, current_user)

        merged += 1

    return merged


def merge_users(user1, user2):
    values = {'user_id': user1.id}
    for Model in (Password, Application, AuthorizationCode, AccessCode,
                  ExternalIdentity):
        Session.query(Model).filter(Model.user == user2).update(values, False)

    # Because the previous updates break the Unit of Work pattern we need
    # to refresh the current objects in the session
    Session.expire_all()

    for auth_app in Session.query(AuthorizedApplication).filter(
            AuthorizedApplication.user == user2):
        try:
            Session.query(AuthorizedApplication).filter(
                AuthorizedApplication.user == user1,
                AuthorizedApplication.application == auth_app.application,
            ).one()
        except NoResultFound:
            auth_app.user = user1
            Session.add(auth_app)

    Session.delete(user2)


def notify_admins_of_account_removal(request, user, reason):
    context = {
        'reason': reason or 'no reason was given',
        'user': user,
        'home_link': request.route_url('home'),
    }
    return send_email_to_admins(
        request,
        'yithlibraryserver.user:templates/account_removal_notification',
        context,
        'A user has destroyed his Yith Library account',
    )
