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

import os
import unittest
import tempfile

from pyramid_sqlalchemy import metadata
from pyramid_sqlalchemy import Session

from yithlibraryserver.password.models import Password
from yithlibraryserver.testing import (
    get_test_db_uri,
    sqlalchemy_setup,
    sqlalchemy_teardown,
)

CONFIG = """[app:main]
use = egg:yith-library-server
database_url = %s
auth_tk_secret = 123456
redis.sessions.secret = 123456
redis.sessions.url = redis://127.0.0.1:6379/0
testing = True
pyramid_mailer.prefix = mail_
mail_default_sender = no-reply@yithlibrary.com
admin_emails = admin1@example.com admin2@example.com

[server:main]
use = egg:waitress#main
host = 0.0.0.0
port = 65432
""" % get_test_db_uri()


class ScriptTests(unittest.TestCase):

    use_db = True

    def setUp(self):
        fd, self.conf_file_path = tempfile.mkstemp()
        os.write(fd, CONFIG.encode('ascii'))
        if self.use_db:
            self.db_uri = get_test_db_uri()
            self.db_context = sqlalchemy_setup(self.db_uri)

            metadata.create_all()

    def tearDown(self):
        os.unlink(self.conf_file_path)
        if self.use_db:
            sqlalchemy_teardown(self.db_context)

    def add_passwords(self, user, n):
        for i in range(n):
            p = Password(service='service-%d' % (i + 1),
                         secret='s3cr3t',
                         user=user)
            Session.add(p)
