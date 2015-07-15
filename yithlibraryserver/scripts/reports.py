# Yith Library Server is a password storage server.
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
from sqlalchemy import desc, func, select
from sqlalchemy.sql.expression import true

from yithlibraryserver.oauth2.models import Application
from yithlibraryserver.password.models import Password
from yithlibraryserver.scripts.utils import safe_print, setup_simple_command
from yithlibraryserver.scripts.utils import get_user_display_name
from yithlibraryserver.user.models import ExternalIdentity, User


def _get_user_info(user):
    providers = ', '.join(sorted([identity.provider for identity in user.identities]))
    return {
        'display_name': get_user_display_name(user),
        'passwords': len(user.passwords),
        'providers': providers,
        'verified': user.email_verified,
        'date_joined': user.creation,
        'last_login': user.last_login,
    }


def users():
    result = setup_simple_command(
        "users",
        "Report information about users and their passwords.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        for user in Session.query(User).order_by(User.creation):
            info = _get_user_info(user)
            providers = info['providers']
            text = (
                '%s (%s)\n'
                '\tPasswords: %d\n'
                '\tProviders:%s\n'
                '\tVerified: %s\n'
                '\tDate joined: %s\n'
                '\tLast login: %s\n' % (
                    info['display_name'],
                    user.id,
                    info['passwords'],
                    ' ' + providers if providers else '',
                    info['verified'],
                    info['date_joined'],
                    info['last_login'],
                )
            )
            safe_print(text)

    finally:
        closer()


def applications():
    result = setup_simple_command(
        "applications",
        "Report information about oauth2 client applications.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        for app in Session.query(Application).all():
            text = (
                '%s\n'
                '\tOwner: %s\n'
                '\tMain URL: %s\n'
                '\tCallback URL: %s\n'
                '\tUsers: %d\n' % (
                    app.name,
                    get_user_display_name(app.user),
                    app.main_url,
                    app.callback_url,
                    len(app.authorized_applications),
                )
            )
            safe_print(text)

    finally:
        closer()


def statistics():
    result = setup_simple_command(
        "statistics",
        "Report several different statistics.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        # Get the number of users and passwords
        n_users = Session.query(User).count()
        if n_users == 0:
            return

        n_passwords = Session.query(Password).count()

        # How many users are verified
        n_verified = Session.query(User).filter(
            User.email_verified == true()).count()
        # How many users allow the analytics cookie
        n_allow_cookie = Session.query(User).filter(
            User.allow_google_analytics == true()).count()

        # Identity providers
        by_identity = Session.query(
            ExternalIdentity.provider,
            func.count(ExternalIdentity.provider).label('provider_count')
        ).select_from(
            ExternalIdentity
        ).group_by(ExternalIdentity.provider).order_by(desc('provider_count'))

        # Email providers
        domains_with_counts = select([
            func.substring(User.email, r'.*@(.*)').label('domain'),
            func.count('*').label('count'),
        ]).where(User.email != '').group_by('domain').order_by(desc('count'))
        aliased = domains_with_counts.alias()
        by_email = Session.query(aliased).filter(aliased.c.count > 1)

        without_email = Session.query(User).filter(User.email == '').count()
        with_email = n_users - without_email

        # Top ten users
        most_active_users = Session.query(
            User, func.count(User.id).label('password_count'),
        ).join(
            Password
        ).group_by(User.id).order_by(desc('password_count'))

        users_with_passwords = most_active_users.count()
        most_active_users = most_active_users.limit(10)

        # print the statistics
        safe_print('Number of users: %d' % n_users)
        safe_print('Number of passwords: %d' % n_passwords)
        safe_print('Verified users: %.2f%% (%d)' % (
            (100.0 * n_verified) / n_users, n_verified))
        safe_print('Users that allow Google Analytics cookie: %.2f%% (%d)' % (
            (100.0 * n_allow_cookie) / n_users, n_allow_cookie))

        safe_print('Identity providers:')
        for provider, amount in by_identity:
            safe_print('\t%s: %.2f%% (%d)' % (
                provider, (100.0 * amount) / n_users, amount))

        safe_print('Email providers:')
        others = with_email
        for provider, amount in by_email:
            safe_print('\t%s: %.2f%% (%d)' % (
                provider, (100.0 * amount) / with_email, amount))
            others -= amount
        safe_print('\tOthers: %.2f%% (%d)' % (
            (100.0 * others) / with_email, others))
        safe_print('Users without email: %.2f%% (%d)' % (
            (100.0 * without_email) / n_users, without_email))

        safe_print('Most active users:')
        for user, n_passwords in most_active_users:
            safe_print('\t%s: %s' % (get_user_display_name(user), n_passwords))

        users_no_passwords = n_users - users_with_passwords
        safe_print('Users without passwords: %.2f%% (%d)' % (
            (100 * users_no_passwords) / n_users, users_no_passwords))

    finally:
        closer()
