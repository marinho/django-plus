from django.conf import settings
from django.contrib.sites.models import Site

MONETARY_LOCALE = getattr(settings, 'MONETARY_LOCALE', '')
THOUSANDS_SEPARATOR = getattr(settings, 'THOUSANDS_SEPARATOR', '')
STATIC_FILES_PATH = getattr(settings, 'STATIC_FILES_PATH', 'uploads')

ROBOT_PROTECTION_DOMAIN = getattr(settings, 'ROBOT_PROTECTION_DOMAIN', None)

RESULT_OK = getattr(settings, 'RESULT_OK', 'ok')
RESULT_ERROR = getattr(settings, 'RESULT_ERROR', 'error')

AJAX_FK_USE_MEDIA = getattr(settings, 'AJAX_FK_USE_MEDIA', True)

