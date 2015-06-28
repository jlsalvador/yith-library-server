# Yith Library Server is a password storage server.
# Copyright (C) 2013 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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
import gzip
import json
import numbers

from yithlibraryserver.compat import BytesIO
from yithlibraryserver.jsonrenderer import datetime_parser, json_renderer
from yithlibraryserver.utils import remove_attrs


def get_user_passwords(user):
    return [remove_attrs(password.as_dict(), 'user', 'owner', 'id')
            for password in user.passwords]


def get_backup_filename(date):
    return 'yith-library-backup-%d-%02d-%02d.yith' % (
        date.year, date.month, date.day)


def compress(passwords):
    buf = BytesIO()
    gzip_data = gzip.GzipFile(fileobj=buf, mode='wb')
    renderer = json_renderer(None)
    data = renderer(passwords, {})
    gzip_data.write(data.encode('utf-8'))
    gzip_data.close()
    return buf.getvalue()


def uncompress(compressed_data):
    buf = BytesIO(compressed_data)
    gzip_data = gzip.GzipFile(fileobj=buf, mode='rb')
    raw_data = gzip_data.read()
    json_data = json.loads(raw_data.decode('utf-8'))

    def parse_date(item, dt_attr):
        if dt_attr in item:
            value = item[dt_attr]
            if isinstance(value, numbers.Integral):
                datetime_value = datetime.datetime.utcfromtimestamp(value / 1000.0)
            else:
                datetime_value = datetime_parser(item[dt_attr])
            item[dt_attr] = datetime_value

    def load_item(item):
        if 'last_modification' in item:
            last_modification = item.pop('last_modification')
            if last_modification is None:
                item['modification'] = item['creation']
            else:
                item['modification'] = last_modification

        parse_date(item, 'creation')
        parse_date(item, 'modification')

        return item

    return [load_item(item) for item in json_data]
