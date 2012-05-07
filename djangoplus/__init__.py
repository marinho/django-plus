VERSION = (1, 2, 14)

def get_version():
    return '%d.%d.%d'%VERSION

__author__ = 'Marinho Brandao'
#__date__ = '$Date: 2008-07-26 14:04:51 -0300 (Ter, 26 Fev 2008) $'[7:-2]
__license__ = 'GNU Lesser General Public License (LGPL)'
__url__ = 'http://django-plus.googlecode.com'
__version__ = get_version()

def get_dynamic_template(slug, context=None):
    from models import DynamicTemplate

    return DynamicTemplate.objects.get(slug=slug).render(context or {})

