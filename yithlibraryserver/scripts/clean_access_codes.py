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

from pyramid_sqlalchemy import Session

import transaction

from yithlibraryserver.oauth2.models import AccessCode
from yithlibraryserver.scripts.utils import safe_print, setup_simple_command


def clean_access_codes():
    result = setup_simple_command(
        "clean_access_codes",
        "Deletes expired access codes"
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        now = datetime.datetime.utcnow()

        with transaction.manager:
            counter = 0
            for access_code in Session.query(AccessCode).filter(
                AccessCode.expiration < now
            ):
                Session.delete(access_code)
                counter += 1

            if counter > 0:
                safe_print('%d access codes were cleaned' % counter)

    finally:
        closer()


if __name__ == '__main__':  # pragma: no cover
    clean_access_codes()
