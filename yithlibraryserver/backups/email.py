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

import datetime

from pyramid_mailer.message import Attachment

from yithlibraryserver.backups.utils import get_backup_filename
from yithlibraryserver.backups.utils import get_user_passwords, compress
from yithlibraryserver.email import send_email


def send_passwords(request, user, preferences_link, backups_link):
    passwords = get_user_passwords(user)
    if not passwords:
        return False

    context = {
        'user': user,
        'preferences_link': preferences_link,
        'backups_link': backups_link,
    }

    today = datetime.date.today()
    attachment = Attachment(get_backup_filename(today),
                            "application/yith",
                            compress(passwords))

    send_email(
        request,
        'yithlibraryserver.backups:templates/email_passwords',
        context,
        "Your Yith Library's passwords",
        [user.email],
        attachments=[attachment],
    )

    return True
