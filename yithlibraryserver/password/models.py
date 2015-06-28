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

from datetime import datetime

from pyramid_sqlalchemy import BaseObject

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship, backref


def now():
    return datetime.utcnow()


class Password(BaseObject):
    __tablename__ = 'passwords'

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    creation = Column(DateTime, nullable=False, default=now)
    modification = Column(DateTime, nullable=False, default=now, onupdate=now)

    notes = Column(Text, nullable=False, default='')
    tags = Column(ARRAY(Text, dimensions=1), nullable=False, default=[])

    secret = Column(String, nullable=False, default='')
    account = Column(String, nullable=False, default='')
    service = Column(String, nullable=False, default='')
    expiration = Column(Integer, nullable=True)

    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    user = relationship(
        'User',
        backref=backref('passwords', cascade='all, delete-orphan'),
    )

    def as_dict(self):
        return dict(
            id=self.id,
            creation=self.creation,
            modification=self.modification,
            notes=self.notes,
            tags=self.tags,
            secret=self.secret,
            account=self.account,
            service=self.service,
            expiration=self.expiration,
            user=self.user_id,
            owner=self.user_id,  # backwards compatibility
        )
