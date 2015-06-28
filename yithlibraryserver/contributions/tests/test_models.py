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

import unittest

from yithlibraryserver.contributions.models import Donation, include_sticker
from yithlibraryserver.testing import TestCase


class IncludeStickerTests(unittest.TestCase):

    def test_include_sticker(self):
        self.assertFalse(include_sticker(1))
        self.assertTrue(include_sticker(5))
        self.assertTrue(include_sticker(10))


class ModelTests(TestCase):

    def test_should_include_sticker(self):
        self.assertFalse(Donation(amount=1).should_include_sticker())
        self.assertTrue(Donation(amount=5).should_include_sticker())
        self.assertTrue(Donation(amount=10).should_include_sticker())
