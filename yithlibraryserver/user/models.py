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

from datetime import datetime

from pyramid_sqlalchemy import BaseObject, Session

from sqlalchemy import Boolean, Column, Enum, DateTime, String
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from yithlibraryserver.compat import text_type


class User(BaseObject):
    __tablename__ = 'users'

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    first_name = Column(String, nullable=False, default='')
    last_name = Column(String, nullable=False, default='')
    screen_name = Column(String, nullable=False, default='')

    email = Column(String, nullable=False, default='')
    email_verified = Column(Boolean, nullable=False, default=False)
    email_verification_code = Column(String, nullable=False, default='')

    creation = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=False, default=datetime.utcnow)

    allow_google_analytics = Column(Boolean, nullable=True, default=None)
    send_passwords_periodically = Column(Boolean, nullable=False, default=False)

    @hybrid_property
    def full_name(self):
        result = ' '.join([self.first_name, self.last_name])
        result = result.strip()
        return result

    def __unicode__(self):
        result = self.screen_name
        if result:
            return result

        result = self.full_name
        if result:
            return result

        result = self.email
        if result:
            return result

        return text_type(self.id)

    # py3 compatibility
    def __str__(self):
        return self.__unicode__()

    def as_dict(self):
        return dict(
            id=self.id,
            creation=self.creation,
            last_login=self.last_login,
            first_name=self.first_name,
            last_name=self.last_name,
            screen_name=self.screen_name,
            email=self.email,
            email_verified=self.email_verified,
            allow_google_analytics=self.allow_google_analytics,
            send_passwords_periodically=self.send_passwords_periodically,
        )

    def update_preferences(self, preferences):
        for preference in ('allow_google_analytics', 'send_passwords_periodically'):
            if preference in preferences:
                setattr(self, preference, preferences[preference])

    def update_user_info(self, user_info):
        for attribute in ('screen_name', 'first_name', 'last_name'):
            if attribute in user_info and user_info[attribute]:
                setattr(self, attribute, user_info[attribute])

        # email is special
        if 'email' in user_info and self.email != user_info['email']:
            self.email = user_info['email']
            self.email_verified = False

    def get_accounts(self, current_provider):
        other_users = Session.query(
            User
        ).filter(User.email == self.email).filter(User.id != self.id)

        users = [self] + list(other_users)
        accounts = []
        for user in users:
            providers = user.get_providers(current_provider)
            is_current = any([p['is_current'] for p in providers])

            accounts.append({
                'providers': providers,
                'is_current': is_current,
                'passwords': len(user.passwords),
                'id': user.id,
                'is_verified': user.email_verified,
            })

        return accounts

    def get_providers(self, current_provider):
        result = []
        for identity in self.identities:
            result.append({
                'name': identity.provider,
                'is_current': identity.provider == current_provider,
            })
        return result

    def add_identity(self, provider, external_id):
        identity = ExternalIdentity(provider=provider, external_id=external_id)
        self.identities.append(identity)

    def verify_email(self):
        self.email_verified = True
        self.email_verification_code = ''


class ExternalIdentity(BaseObject):
    __tablename__ = 'external_identities'

    PROVIDERS = ('facebook', 'google', 'twitter', 'persona', 'liveconnect')

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    provider = Column(Enum(*PROVIDERS, name='providers'), nullable=False)
    external_id = Column(String, nullable=False)

    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    user = relationship(
        'User',
        backref=backref('identities', cascade='all, delete-orphan'),
    )
