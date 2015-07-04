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

import json

USER_ATTR = 'allow_google_analytics'


class GoogleAnalytics(object):

    def __init__(self, request):
        self.request = request

    @property
    def enabled(self):
        code = self.request.registry.settings['google_analytics_code']
        return code is not None

    @property
    def first_time(self):
        if self.request.user is None:
            return USER_ATTR not in self.request.session
        else:
            return self.request.user.allow_google_analytics is None

    def show_in_session(self):
        return self.request.session.get(USER_ATTR, False)

    def show_in_user(self, user):
        return user.allow_google_analytics

    def is_in_session(self):
        return USER_ATTR in self.request.session

    @property
    def show(self):
        user = self.request.user
        if user is None:
            return self.show_in_session()
        else:
            return self.show_in_user(user)

    def clean_session(self):
        if USER_ATTR in self.request.session:
            del self.request.session[USER_ATTR]

    @property
    def json(self):
        data = {
            'code': self.request.registry.settings['google_analytics_code'],
            'show': self.show,
        }
        return json.dumps(data)


def get_google_analytics(request):
    return GoogleAnalytics(request)
