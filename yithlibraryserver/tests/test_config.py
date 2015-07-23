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

import os
import unittest

from pyramid.exceptions import ConfigurationError

from yithlibraryserver import main
from yithlibraryserver.config import read_setting_from_env


class ConfigTests(unittest.TestCase):

    def test_read_setting_from_env(self):
        settings = {
            'foo_bar': '1',
        }

        self.assertEqual('1', read_setting_from_env(settings, 'foo_bar'))

        self.assertEqual('default',
                         read_setting_from_env(settings, 'new_option', 'default'))
        self.assertEqual(None,
                         read_setting_from_env(settings, 'new_option'))

        os.environ['FOO_BAR'] = '2'
        self.assertEqual('2', read_setting_from_env(settings, 'foo_bar'))
        del os.environ['FOO_BAR']

    def test_required_settings(self):
        settings = {}
        # Unfortunately Python 2.6 does not support self.assertRaises
        # as a context manager to inspect the msg of the exception

        # The auth_tk_secret configuration option is required
        self.assertRaises(ConfigurationError, main, {}, **settings)

        settings = {
            'auth_tk_secret': '1234',
        }
        # The database_url configuration option is required
        self.assertRaises(ConfigurationError, main, {}, **settings)

        settings = {
            'auth_tk_secret': '1234',
            'database_url': 'postgresql://foo:bar@localhost:5432/test',
        }
        # The redis.sessions.secret configuration option is required
        self.assertRaises(ConfigurationError, main, {}, **settings)

        settings = {
            'auth_tk_secret': '1234',
            'database_url': 'postgresql://foo:bar@localhost:5432/test',
            'redis.sessions.secret': '1234',
        }
        # The redis.sessions.url configuration option is required
        self.assertRaises(ConfigurationError, main, {}, **settings)

        settings = {
            'auth_tk_secret': '1234',
            'database_url': 'postgresql://foo:bar@localhost:5432/test',
            'redis.sessions.secret': '1234',
            'redis.sessions.url': 'redis://127.0.0.1:6379/0',
        }
        app = main({}, **settings)
        self.assertEqual(settings['auth_tk_secret'],
                         app.registry.settings['auth_tk_secret'])
        self.assertEqual(settings['database_url'],
                         app.registry.settings['database_url'])
        self.assertEqual(settings['redis.sessions.secret'],
                         app.registry.settings['redis.sessions.secret'])
        self.assertEqual(settings['redis.sessions.url'],
                         app.registry.settings['redis.sessions.url'])

    def test_setting_with_dots(self):
        settings = {
            'foo.bar': '1'
        }
        self.assertEqual('1', read_setting_from_env(settings, 'foo.bar'))
        os.environ['FOO_BAR'] = '2'
        self.assertEqual('2', read_setting_from_env(settings, 'foo.bar'))
        del os.environ['FOO_BAR']
