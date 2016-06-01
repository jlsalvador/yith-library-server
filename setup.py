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
import platform
import sys

from setuptools import setup, find_packages
join = os.path.join

here = os.path.abspath(os.path.dirname(__file__))
README = open(join(here, 'README.rst')).read()
CHANGES = open(join(here, 'CHANGES.rst')).read()


def parse_requirements(requirements_file):
    """Parses requirements.txt file into a list."""
    requirements = []

    with open(join(here, requirements_file), 'r') as requirements_file:
        for line in requirements_file:
            line = line.strip()

            # remove inline comments
            if '#' in line:
                line = line[:line.index('#')]
                line = line.strip()

            if line:
                requirements.append(line)

    return requirements

base_requirements = parse_requirements('requirements.txt')

if sys.version_info[0] < 3:
    # packages that only work in Python 2.x
    base_requirements += parse_requirements(join('requirements', 'python2.txt'))

if platform.python_implementation() == 'PyPy':
    base_requirements += parse_requirements(join('requirements', 'pypy.txt'))
    base_requirements.remove('psycopg2==2.6.1')


docs_requirements = parse_requirements(join('requirements', 'docs.txt'))
test_support_requirements = parse_requirements(join('requirements', 'test_support.txt'))
testing_requirements = parse_requirements(join('requirements', 'testing.txt'))


setup(
    name='yith-library-server',
    version='0.4',
    description='yith-library-server',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pyramid",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=base_requirements,
    tests_require=base_requirements + test_support_requirements,
    extras_require={
        'testing': testing_requirements + test_support_requirements,
        'docs': docs_requirements,
    },
    test_suite="yithlibraryserver",
    entry_points="""\
    [paste.app_factory]
    main = yithlibraryserver:main
    [console_scripts]
    yith_users_report = yithlibraryserver.scripts.reports:users
    yith_apps_report = yithlibraryserver.scripts.reports:applications
    yith_stats_report = yithlibraryserver.scripts.reports:statistics
    yith_migrate = yithlibraryserver.scripts.migrations:migrate
    yith_send_backups_via_email = yithlibraryserver.scripts.backups:send_backups_via_email
    yith_announce = yithlibraryserver.scripts.announce:announce
    yith_build_assets = yithlibraryserver.scripts.buildassets:buildassets
    yith_create_db = yithlibraryserver.scripts.createdb:createdb
    yith_clean_access_codes = yithlibraryserver.scripts.clean_access_codes:clean_access_codes""",
)
