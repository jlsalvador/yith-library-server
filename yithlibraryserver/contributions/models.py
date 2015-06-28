# Yith Library Server is a password storage server.
# Copyright (C) 2013-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref


def now():
    return datetime.utcnow()


class Donation(BaseObject):
    __tablename__ = 'donations'

    id = Column(UUID, primary_key=True, default=func.uuid_generate_v4())
    creation = Column(DateTime, nullable=False, default=now)
    modification = Column(DateTime, nullable=False, default=now, onupdate=now)

    first_name = Column(String, nullable=False, default='')
    last_name = Column(String, nullable=False, default='')

    email = Column(String, nullable=False, default='')

    street = Column(String, nullable=False, default='')
    city = Column(String, nullable=False, default='')
    zipcode = Column(String, nullable=False, default='')
    state = Column(String, nullable=False, default='')
    country = Column(String, nullable=False, default='')

    amount = Column(Integer, nullable=False)
    send_sticker = Column(Boolean, nullable=False, default=True)

    user_id = Column(UUID, ForeignKey('users.id'), nullable=True)
    user = relationship('User', backref=backref('donations'))

    def should_include_sticker(self):
        return include_sticker(self.amount)


def include_sticker(amount):
    return amount > 1
