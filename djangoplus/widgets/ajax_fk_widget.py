# -*- coding: utf-8 -*-
import operator

from django.forms.widgets import TextInput
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.db import models
from django.http import HttpResponse
from django.contrib import admin
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist

from djangoplus.utils import path_to_object, get_admin_url
from djangoplus import app_settings

registered_models = {}

if hasattr(settings, 'AJAX_FK_MEDIA_URL'):
    MEDIA_URL = settings.AJAX_FK_MEDIA_URL
elif hasattr(settings, 'STATIC_URL'):
    MEDIA_URL = settings.STATIC_URL
else:
    MEDIA_URL = settings.MEDIA_URL

class AjaxFKWidget(TextInput):
    if app_settings.AJAX_FK_USE_MEDIA:
        class Media:
            js = (MEDIA_URL+'js/ajax_fk_widget.js',)
            css = {'all': (MEDIA_URL+'css/ajax_fk_widget.css',)}

    fill_left_zeros = 0
    rel = None
    model = None
    driver = None
    related_field = None
    filter_dict = {}
    hide_input = False

    window_url = None
    load_url = None
    add_url = None

    def __init__(self, *args, **kwargs):
        if 'rel' in kwargs:
            self.rel = kwargs.pop('rel')
            self.get_from_rel()
        elif 'driver' in kwargs:
            self.driver = kwargs.pop('driver')
            self._driver = registered_models[self.driver]

            self.model = kwargs.pop('model', self._driver.model)
            self.related_field = kwargs.pop('related_field', 'pk')
        else:
            self.model = kwargs.pop('model', None)
            self.related_field = kwargs.pop('related_field', 'pk')
            self._driver = registered_models[self.model]

        if 'fill_left_zeros' in kwargs:
            self.fill_left_zeros = kwargs.pop('fill_left_zeros')

        url_app = self.driver and 'driverbyname' or self.model._meta.app_label
        url_model = self.driver and self.driver or self.model.__name__

        self.window_url = kwargs.pop('window_url', self.window_url)
        if self.window_url is None:
            self.window_url = reverse('ajax-fk-window-url', kwargs={'app': url_app, 'model': url_model})

        self.load_url = kwargs.pop('load_url', self.load_url)
        if self.load_url is None:
            self.load_url = reverse('ajax-fk-load-url', kwargs={'app': url_app, 'model': url_model})

        self.add_url = kwargs.pop('add_url', self.add_url)
        if self.add_url is None:
            self.add_url = '%s%s/%s/add/'%(admin.site.root_path, url_app, url_model.lower())

        self.hide_input = kwargs.pop('hide_input', self.hide_input)

        super(AjaxFKWidget, self).__init__(*args, **kwargs)

    def get_from_rel(self):
        self.model = self.rel.to
        self.related_field = self.rel.get_related_field().name

    def value_from_datadict(self, data, files, name):
        ret = super(AjaxFKWidget, self).value_from_datadict(data, files, name)
        
        return ret or None

    def render(self, name, value, attrs=None):
        attrs = attrs or {}
        attrs['class'] = attrs.get('class', '') + ' ajax-fk'
        
        # Implement max length
        try:    
            attrs['maxlength'] = self.rel.get_related_field().max_length
        except AttributeError:
            pass

        # Renders using inherited class
        ret = super(AjaxFKWidget, self).render(name, value, attrs)

        # Buf, if is going to hide the input, then replace 'text' to 'hidden'
        if self.hide_input:
            ret = ret.replace(' type="text" ', ' type="hidden" ')

        #class_path = '.'.join([self.model.__module__, self.model.__name__])

        display = self.make_display(attrs, value)

        script = self.make_script(name)

        return mark_safe(' '.join([ret, display, script]))

    def make_display(self, attrs, value):
        url = self.get_display_url(value)

        return '<a id="%s_display" class="ajax-fk-display" %s>%s</a>'%(
                attrs['id'],
                url and 'href="%s"'%url or '',
                value and self.label_for_value(value) or '(nenhum selecionado)',
                )

    def make_script(self, name):
        if self.driver:
            param_model = 'driverbyname.' + self.driver
        else:
            param_model = '.'.join([self.model.__module__,self.model.__name__])

        sc_params = {
                "model": param_model,
                "filter": self.filter_dict or {},
                "window-url": self.window_url,
                "load-url": self.load_url,
                "add-url": self.add_url,
                "fill-left-zeros": self.fill_left_zeros,
                "callback-function-on-change": '', # JavaScript function name to call after
                                                   # change the widget value. This function
                                                   # must waits for a param to receive the
                                                   # JSON of changed values
                }

        # Loads extra parameters from its driver
        try:
            try:
                driver = self._driver
            except AttributeError:
                self._driver = registered_models[self.driver]

            sc_params.update(self._driver.get_extra_params(self, sc_params))
        except KeyError:
            pass

        script = """<script type="text/javascript">fk_widgets['%s'] = %s;%s</script>"""%(
                name,
                simplejson.dumps(sc_params),
                self.get_additional_script(name)
                )

        return script

    def get_additional_script(self, name):
        """To be used to extend script functions"""
        return ''

    def label_for_value(self, value):
        try:
            obj = self.model._default_manager.get(**{self.related_field: value})
            return unicode(obj)
        except ObjectDoesNotExist:
            return ''

    def get_display_url(self, value):
        global registered_models
        
        #try:
        #    driver = registered_models[self.model]
        #except KeyError:
        #    return ''

        if not self.model:
            return ''

        try:
            obj = self.model._default_manager.get(**{self.related_field: value})

            return get_admin_url(obj)
        except ObjectDoesNotExist:
            return ''

    @classmethod
    def register(cls, driver_class, name=None):
        """Register a model class with its driver class.

        Examples:
            AjaxFKWidget.register(AjaxFKMyModelClass)
            AjaxFKWidget.register(AjaxFKMyModelClass, 'MyDriver')
            """
        global registered_models

        registered_models[driver_class.model] = driver_class

        if name:
            registered_models[name] = driver_class

class AjaxFKDriver(object):
    model = None
    list_display = None
    search_fields = None
    list_filter = None
    ordering = None
    template = 'djangoplus/ajaxfkwidget_window.html'
    verbose_name = None

    def __init__(self, request, cls=None):
        self.request = request
        self.cls = cls

        try:
            self.verbose_name = self.model._meta.verbose_name
        except AttributeError:
            pass

    def _get_field_display(self, field_name):
        if field_name == '__unicode__':
            return self.model._meta.verbose_name.capitalize()

        try:
            return getattr(self, 'get_%s_display'%field_name)()
        except AttributeError:
            try:
                return self.model._meta.get_field_by_name(field_name)[0].verbose_name.capitalize()
            except (models.fields.FieldDoesNotExist, AttributeError):
                return field_name.replace('_', ' ').capitalize()

    def _get_field_value(self, field_name, obj):
        # Unicode representation
        if field_name == '__unicode__':
            return unicode(obj)

        # Using a specific method
        try:
            return getattr(self, 'get_%s_value'%field_name)(obj)
        except AttributeError:
            pass

        # Getting from dictionary
        if isinstance(obj, dict):
            value = obj.get(field_name, None)

        # Getting by attribute
        else:
            value = getattr(obj, field_name, None)

        # If the attribute is callable
        if callable(value):
            value = value()

        return value

    def get_columns(self):
        return [self._get_field_display(f) for f in self.list_display]

    def get_results(self):
        qs = self.get_query_set()

        # Keyword search
        qs = self.search_by_fields(qs)

        return qs

    def search_by_fields(self, qs):
        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and self.request.GET.get('ajax_fk_search', ''):
            for bit in self.request.GET['ajax_fk_search'].split():
                or_queries = [models.Q(**{construct_search(str(field_name)): bit}) for field_name in self.search_fields]
                qs = qs.filter(reduce(operator.or_, or_queries))
            for field_name in self.search_fields:
                if '__' in field_name:
                    qs = qs.distinct()
                    break

        return qs

    def get_by_pk(self):
        try:
            obj = self.get_query_set().get(pk=self.request.GET['pk'])

            ret = {
                'res': app_settings.RESULT_OK,
                'pk': obj.pk,
                'display': unicode(obj),
                'url': self.get_display_url(obj),
            }
        except ObjectDoesNotExist:
            ret = {
                'res': app_settings.RESULT_ERROR,
                'msg': u'%s não encontrado!' % self.verbose_name,
            }

        return ret

    def get_query_set(self):
        qs = self.model.objects.all()

        # Ordering
        if self.ordering:
            qs = qs.order_by(*self.ordering)

        # Filters
        for k,v in self.request.GET.items():
            if not k.startswith('ajax-fk-filter-'):
                continue

            f_name = k[15:]

            qs = qs.filter(**{str(f_name): v})

        return qs

    def get_object_pk(self, obj):
        return obj.pk

    def get_object_display(self, obj):
        return unicode(obj)

    @classmethod
    def get_display_url(cls, obj):
        """Returns the url to show as a link on the object display when selected.
        
        The default value is the Admin URL for this object.
        
        You can also inform an empty string to set it as disabled."""
        if isinstance(obj, models.Model):
            return get_admin_url(obj)
        else:
            return ''

    @classmethod
    def get_extra_params(cls, widget=None, current_params=None):
        """Returns extra params to append to the parameters dictionary of widgets
        that use this model class."""
        return {}

def window_view(request, app, model):
    if app == 'driverbyname':
        driver = registered_models[model](request)
    else:
        cls = path_to_object('%s.models.%s'%(app, model))
        driver = registered_models[cls](request, cls)

    columns = driver.get_columns()
    results = driver.get_results()
    list_display = driver.list_display

    return render_to_response(
            driver.template,
            locals(),
            context_instance=RequestContext(request),
            )

def load_view(request, app, model):
    cls = path_to_object('%s.models.%s'%(app, model))
    driver = registered_models[cls](request, cls)

    ret = driver.get_by_pk()

    return HttpResponse(simplejson.dumps(ret), mimetype='text/javascript')
