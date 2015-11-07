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

import datetime
import unittest

from yithlibraryserver.jsonrenderer import datetime_adapter, datetime_parser


class DatetimeParserTests(unittest.TestCase):

    def test_parse_date_with_no_milliseconds(self):
        self.assertEqual(datetime_parser('2015-04-30T22:10:30'),
                         datetime.datetime(2015, 4, 30, 22, 10, 30))

    def test_parse_date_with_milliseconds(self):
        self.assertEqual(datetime_parser('2015-04-30T22:10:30.123000'),
                         datetime.datetime(2015, 4, 30, 22, 10, 30, 123000))


class DatetimeAdapterTests(unittest.TestCase):

    def test_adapt_date(self):
        date = datetime.datetime(2015, 4, 30, 22, 10, 30)
        self.assertEqual(datetime_adapter(date, None), '2015-04-30T22:10:30')
