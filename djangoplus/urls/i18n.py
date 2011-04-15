from django.conf.urls.defaults import *

urlpatterns = patterns('djangoplus.views.i18n',
    url(r'^set-field-trans/$', 'set_field_translation', name='i18n_set_field_translation'),
)

