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

from datetime import datetime

from pyramid_sqlalchemy import BaseObject

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship, backref


class Application(BaseObject):
    __tablename__ = 'applications'

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    secret = Column(UUID, nullable=False, default=func.uuid_generate_v4())

    name = Column(String, nullable=False, default='')

    creation = Column(DateTime, nullable=False, default=datetime.utcnow)
    modification = Column(DateTime, nullable=False,
                          default=datetime.utcnow, onupdate=datetime.utcnow)

    main_url = Column(String, nullable=False, default='')
    callback_url = Column(String, nullable=False, default='')
    authorized_origins = Column(ARRAY(Text, dimensions=1), nullable=True)

    image_url = Column(String, nullable=False, default='')
    description = Column(Text, nullable=False, default='')

    production_ready = Column(Boolean, nullable=False, default=False)

    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    user = relationship('User', backref=backref('applications'))


class AuthorizedApplication(BaseObject):
    __tablename__ = 'authorized_applications'

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    scope = Column(ARRAY(Text, dimensions=1), nullable=True)
    response_type = Column(String, nullable=False, default='')
    redirect_uri = Column(String, nullable=False, default='')

    application_id = Column(
        UUID,
        ForeignKey('applications.id'),
        nullable=False,
    )
    application = relationship(
        'Application',
        backref=backref('authorized_applications',
                        cascade='all, delete-orphan'),
    )

    user_id = Column(
        UUID,
        ForeignKey('users.id'),
        nullable=False,
    )
    user = relationship(
        'User',
        backref=backref('authorized_applications',
                        cascade='all, delete-orphan'),
    )

    __table_args__ = (
        UniqueConstraint(application_id, user_id),
    )


class AuthorizationCode(BaseObject):
    __tablename__ = 'authorization_codes'

    code = Column(String, primary_key=True)
    creation = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiration = Column(DateTime, nullable=False)

    scope = Column(ARRAY(Text, dimensions=1), nullable=True)
    redirect_uri = Column(String, nullable=False, default='')

    application_id = Column(
        UUID,
        ForeignKey('applications.id'),
        nullable=False,
    )
    application = relationship(
        'Application',
        backref=backref('authorization_codes'),
    )

    user_id = Column(
        UUID,
        ForeignKey('users.id'),
        nullable=False,
    )
    user = relationship(
        'User',
        backref=backref('authorization_codes',
                        cascade='all, delete-orphan'),
    )


class AccessCode(BaseObject):
    __tablename__ = 'access_codes'

    code = Column(String, primary_key=True)
    code_type = Column(String, nullable=False, default='')

    creation = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiration = Column(DateTime, nullable=False)

    refresh_code = Column(String, nullable=False, default='')

    scope = Column(ARRAY(Text, dimensions=1), nullable=True)

    application_id = Column(
        UUID,
        ForeignKey('applications.id'),
        nullable=False,
    )
    application = relationship(
        'Application',
        backref=backref('access_codes'),
    )

    user_id = Column(
        UUID,
        ForeignKey('users.id'),
        nullable=False,
    )
    user = relationship(
        'User',
        backref=backref('access_codes',
                        cascade='all, delete-orphan'),
    )
