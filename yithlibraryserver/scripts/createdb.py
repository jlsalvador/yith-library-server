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

from pyramid_sqlalchemy import BaseObject

from yithlibraryserver.scripts.utils import setup_simple_command


def createdb():
    result = setup_simple_command(
        "createdb",
        "Initialize the DB with DDL statements.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        BaseObject.metadata.create_all()

    finally:
        closer()


if __name__ == '__main__':  # pragma: no cover
    createdb()
