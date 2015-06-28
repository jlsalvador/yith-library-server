# Yith Library Server is a password storage server.
# Copyright (C) 2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

import pymongo

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.compat import urlparse
from yithlibraryserver.contributions.models import Donation
from yithlibraryserver.oauth2.models import (
    Application,
    AuthorizedApplication,
)
from yithlibraryserver.password.models import Password
from yithlibraryserver.scripts.utils import setup_simple_command
from yithlibraryserver.user.models import ExternalIdentity, User


def get_naive_date_or_now(date, now):
    if date is None:
        return now
    else:
        return date.replace(tzinfo=None)


def get_date_from_js_timestamp(timestamp, now):
    if timestamp is None:
        return now
    else:
        return datetime.datetime.utcfromtimestamp(timestamp / 1000.0)


def migrate_authorized_applications(mongodb, user_mapping, app_mapping, now):

    orphan_auth_apps = []
    seen = set()

    for mongo_auth_app in mongodb.authorized_apps.find():
        try:
            user_id = user_mapping[mongo_auth_app['user']]
        except KeyError:
            orphan_auth_apps.append(mongo_auth_app)
        else:
            try:
                app_id = app_mapping[mongo_auth_app['client_id']]
            except KeyError:
                orphan_auth_apps.append(mongo_auth_app)
            else:
                if (user_id, app_id) in seen:
                    print('Duplicated authorized app %d %d:' % (user_id, app_id))
                    print(mongo_auth_app)
                else:
                    scope = mongo_auth_app.get('scope', '').split(' ')
                    postgres_auth_app = AuthorizedApplication(
                        scope=[s for s in scope if s],
                        response_type=mongo_auth_app.get('response_type', ''),
                        redirect_uri=mongo_auth_app.get('redirect_uri', ''),
                        application_id=app_id,
                        user_id=user_id,
                    )
                    Session.add(postgres_auth_app)
                    seen.add((user_id, app_id))

    return orphan_auth_apps


def migrate_applications(mongodb, user_mapping, now):

    orphan_apps = []
    mapping = {}

    for mongo_application in mongodb.applications.find():
        try:
            user_id = user_mapping[mongo_application['owner']]
        except KeyError:
            orphan_apps.append(mongo_application)
        else:
            client_id = mongo_application.get('client_id', '')
            postgres_application = Application(
                name=mongo_application.get('name', ''),
                creation=now,
                modification=now,
                main_url=mongo_application.get('main_url', ''),
                callback_url=mongo_application.get('callback_url', ''),
                authorized_origins=mongo_application.get('authorized_origins', []),
                secret=mongo_application.get('client_secret', ''),
                image_url=mongo_application.get('image_url', ''),
                description=mongo_application.get('description', ''),
                production_ready=mongo_application.get('production_ready', False),
                user_id=user_id,
            )
            Session.add(postgres_application)
            if client_id:
                mapping[client_id] = postgres_application

    Session.flush()
    for client_id in mapping.iterkeys():
        mapping[client_id] = mapping[client_id].id

    return mapping, orphan_apps


def migrate_donations(mongodb, user_mapping, now):

    orphan_donations = []

    for mongo_donation in mongodb.donations.find():
        creation = mongo_donation.get('date_joined', None)
        mongo_user = mongo_donation.get('user', None)
        if mongo_user is not None:
            try:
                user_id = user_mapping[mongo_user]
            except KeyError:
                orphan_donations.append(mongo_donation)
                continue
        else:
            user_id = None

        postgres_donation = Donation(
            creation=get_naive_date_or_now(creation, now),
            first_name=mongo_donation.get('firstname', ''),
            last_name=mongo_donation.get('lastname', ''),
            email=mongo_donation.get('email', ''),
            street=mongo_donation.get('street', ''),
            city=mongo_donation.get('city', ''),
            zipcode=mongo_donation.get('zip', ''),
            state=mongo_donation.get('state', ''),
            country=mongo_donation.get('country', ''),
            amount=mongo_donation['amount'],
            send_sticker=mongo_donation.get('send_sticker', True),
            user_id=user_id,
        )
        Session.add(postgres_donation)

    return orphan_donations


def migrate_passwords(mongodb, user_mapping, now):

    orphan_passwords = []

    for mongo_password in mongodb.passwords.find():
        creation = mongo_password.get('creation', None)
        modification = mongo_password.get('last_modification', None)
        try:
            user_id = user_mapping[mongo_password['owner']]
        except KeyError:
            orphan_passwords.append(mongo_password)
        else:
            postgres_password = Password(
                account=mongo_password.get('account', ''),
                service=mongo_password.get('service', ''),
                tags=mongo_password.get('tags', []),
                notes=mongo_password.get('notes', ''),
                creation=get_date_from_js_timestamp(creation, now),
                modification=get_date_from_js_timestamp(modification, now),
                secret=mongo_password.get('secret', ''),
                expiration=mongo_password.get('expiration', None),
                user_id=user_id,
            )
            Session.add(postgres_password)

    return orphan_passwords


def migrate_users(mongodb, now):

    mapping = {}

    for mongo_user in mongodb.users.find():
        postgres_user = User(
            first_name=mongo_user.get('first_name', ''),
            last_name=mongo_user.get('last_name', ''),
            screen_name=mongo_user.get('screen_name', ''),
            email=mongo_user.get('email', ''),
            email_verified=mongo_user.get('email_verified', False),
            allow_google_analytics=mongo_user.get('allow_google_analytics', None),
            send_passwords_periodically=mongo_user.get('send_passwords_periodically', False),
            creation=get_naive_date_or_now(mongo_user.get('date_joined', None), now),
            last_login=get_naive_date_or_now(mongo_user.get('last_login', None), now),
        )

        Session.add(postgres_user)

        for provider in ('facebook', 'google', 'twitter', 'persona', 'liveconnect'):
            provider_key = '%s_id' % provider
            if provider_key in mongo_user:
                external_identity = ExternalIdentity(
                    provider=provider,
                    external_id=mongo_user[provider_key],
                    user=postgres_user,
                )
                Session.add(external_identity)

        mapping[mongo_user['_id']] = postgres_user

    Session.flush()

    for mongo_id in mapping.iterkeys():
        mapping[mongo_id] = mapping[mongo_id].id

    return mapping


def mongo2postgres():
    result = setup_simple_command(
        "mongo2postgres",
        "Migrate the DB from MongoDB to Postgresql.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result


    try:
        uri_info = urlparse.urlparse(settings['mongo_uri'])
        connection = pymongo.MongoClient(host=uri_info.hostname,
                                         port=uri_info.port,
                                         tz_aware=True)
        database_name = uri_info.path[1:]
        database = connection[database_name]
        database.authenticate(uri_info.username, uri_info.password)

        now = datetime.datetime.utcnow()

        with transaction.manager:
            print('Migrating users')
            user_mapping = migrate_users(database, now)

            print('Migrating passwords')
            orphan_passwords = migrate_passwords(database, user_mapping, now)
            if orphan_passwords:
                print("There are orphan passwords:")
                print(orphan_passwords)

            print('Migrating donations')
            orphan_donations = migrate_donations(database, user_mapping, now)
            if orphan_donations:
                print("There are orphan donations:")
                print(orphan_donations)

            print('Migratig applications')
            app_mapping, orphan_apps = migrate_applications(database, user_mapping, now)
            if orphan_apps:
                print("There are orphan applications:")
                print(orphan_apps)

            print('Migratig authorized applications')
            orphan_auth_apps = migrate_authorized_applications(database, user_mapping, app_mapping, now)
            if orphan_auth_apps:
                print("There are orphan authorized applications:")
                print(orphan_auth_apps)

    finally:
        closer()


if __name__ == '__main__':  # pragma: no cover
    mongo2postgres()
