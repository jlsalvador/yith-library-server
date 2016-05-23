# Yith Library Server is a password storage server.
# Copyright (C) 2012-2013 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
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

from yithlibraryserver.locale import DatesFormatter


class DatesFormatterTests(unittest.TestCase):

    def test_date(self):
        df_en = DatesFormatter('en')
        df_es = DatesFormatter('es')

        date = datetime.date(2012, 12, 12)

        self.assertEqual(df_en.date(date), 'Dec 12, 2012')
        self.assertEqual(df_es.date(date), '12 dic. 2012')

    def test_datetime(self):
        df_en = DatesFormatter('en')
        df_es = DatesFormatter('es')

        date = datetime.datetime(2012, 12, 12, 12, 12, 12)

        self.assertEqual(df_en.datetime(date), 'Dec 12, 2012, 12:12:12 PM')
        self.assertEqual(df_es.datetime(date), '12 dic. 2012 12:12:12')
