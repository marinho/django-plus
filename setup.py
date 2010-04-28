# django-djangoplus setup
# First version of this file done by Guilherme Semente
# Some things was copied from Django's setup.py
from distutils.command.install import INSTALL_SCHEMES
import os, sys

# Downloads setuptools if not find it before try to import
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup
from djangoplus import get_version

# Tell distutils to put the data_files in platform-specific installation
# locations. See here for an explanation:
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

data_files = []

for dirpath, dirnames, filenames in os.walk('djangoplus'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if filenames:
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])

# Small hack for working with bdist_wininst.
# See http://mail.python.org/pipermail/distutils-sig/2004-August/004134.html
if len(sys.argv) > 1 and sys.argv[1] == 'bdist_wininst':
    for file_info in data_files:
        file_info[0] = '\\PURELIB\\%s' % file_info[0]

setup(
    name = 'django-plus',
    version = get_version(),
    description = 'Django utilities library',
    long_description = 'django-plus is a library containing a coupple of utilities for Django developers.',
    author = 'Marinho Brandao',
    author_email = 'marinho@gmail.com',
    url = 'http://django-plus.googlecode.com',
    license = 'GNU Lesser General Public License (LGPL)',
    packages = ['djangoplus', 'djangoplus.templatetags',
        'djangoplus.fieldtypes','djangoplus.forms','djangoplus.middleware',
        'djangoplus.shortcuts','djangoplus.templates',
        'djangoplus.templates.admin','djangoplus.templates.admin.djangoplus',
        'djangoplus.templates.admin.djangoplus.dynamictemplate',
        'djangoplus.templates.djangoplus','djangoplus.tests',
        'djangoplus.utils','djangoplus.views','djangoplus.widgets',],
    data_files = data_files,
)

