from django.utils.translation import ugettext as _
from django.utils.encoding import smart_unicode
#from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.filterspecs import FilterSpec
from django.contrib.admin.util import unquote

from model_info import ModelInfo

class CustomFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(CustomFilterSpec, self).__init__(
                f, request, params, model, model_admin,
                )

        # Forces GET QueryDict to modify it
        request.GET._mutable = True

        self.lookup_val = request.GET.pop(self.field, [None])[0]
        self.params = params
        self.model = model
        self.model_admin = model_admin

    # Attribute 'field' must be a string with field name. It will be
    # used to find method to filter on model_admin instance.
    def title(self):
        try:
            func = getattr(self.model_admin, 'get_%s_title'%self.field)
            return func()
        except AttributeError:
            return self.field.replace('_', ' ')

    def choices(self, cl):
        try:
            func = getattr(self.model_admin, 'get_%s_choices'%self.field)
            choices = func()
        except AttributeError, e:
            choices = ()

        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.field]),
               'display': _('All')}
        for k, v in choices:
            yield {'selected': smart_unicode(k) == self.lookup_val,
                   'query_string': cl.get_query_string({self.field: k}),
                   'display': v}
    

class CustomChangeList(ChangeList):
    """Works on Django 1.2 rev 12103 or higher"""

    def __init__(self, request, *args, **kwargs):
        super(CustomChangeList, self).__init__(request, *args, **kwargs)

        # Adds filterspecs of customized filters
        self.list_filter_custom = getattr(self.model_admin, 'list_filter_custom', [])
        self.filter_specs_custom, self.has_filters_custom = \
                self.get_filters_custom(request)

    def get_filters_custom(self, request):
        filter_specs = []

        if self.list_filter_custom:
            for f in self.list_filter_custom:
                spec = CustomFilterSpec(f, request, self.params, self.model, self.model_admin)
                if spec and spec.has_output():
                    filter_specs.append(spec)

        return filter_specs, bool(filter_specs)

class CustomModelAdmin(ModelAdmin):
    info_form_template = None

    def get_changelist(self, request, **kwargs):
        """Works on Django 1.2 rev 12103 or higher"""
        return CustomChangeList

    def get_model_perms(self, request):
        perms = super(CustomModelAdmin, self).get_model_perms(request)

        perms['view'] = self.has_view_permission(request)
        perms['change'] = perms['change'] or perms['view']

        return perms

    #@csrf_protect
    @transaction.commit_on_success
    def change_view(self, request, object_id, extra_context=None):
        """Redirects to 'info' view if user has not change permission or if this is forced
        by attribute 'show_info_instead_form'"""

        #obj = self.get_object(request, unquote(object_id)) # Django 1.2
        obj = get_object_or_404(self.model, pk=unquote(object_id))

        # You can force with attribute 'show_info_instead_form'
        # You can choose it by GET param
        # It is show if user has no permission to change
        if getattr(self, 'show_info_instead_form', False) or\
           request.GET.get('view', None) == 'view' or\
           (not self.has_change_permission(request, obj) and self.has_view_permission(request, obj)):
            return self.info_view(request, object_id, extra_context, obj=obj)

        return super(CustomModelAdmin, self).change_view(request, object_id, extra_context)

    def has_view_permission(self, request, obj=None):
        """Returns boolean value about user has 'view' permission on this model or not."""
        return request.user.has_perm('%s.view_%s'%(self.opts.app_label, self.model.__name__.lower()))

    def has_change_permission(self, request, obj=None):
        """Returns True if user has permission to change or view on this model."""
        if obj:
            return super(CustomModelAdmin, self).has_change_permission(request, obj)
        else:
            return super(CustomModelAdmin, self).has_change_permission(request, obj) or\
                    self.has_view_permission(request, obj)

    def info_view(self, request, object_id, extra_context=None, obj=None):
        """Shows fields with no form, just for viewing"""

        obj = obj or self.get_object(request, unquote(object_id))

        if not self.has_view_permission(request, obj):
            raise PermissionDenied

        context = {
                'original': obj,
                'title': unicode(obj),
                'model_info': self.get_model_info(request, obj),
                'app_label': self.opts.app_label,
                'opts': self.opts,
                }

        return render_to_response(
            self.info_form_template or [
                "admin/%s/%s/view_info.html" %( self.opts.app_label, self.opts.object_name.lower()),
                "admin/%s/view_info.html" % self.opts.app_label,
                "admin/view_info.html"
            ], context, context_instance=RequestContext(request),
        )

    def get_model_info_class(self, request, obj):
        """Returns an instance of model info for the given object"""

        def make_fieldsets(fieldsets):
            return [(fs[0], fs[1]['fields']) for fs in fieldsets]

        if not getattr(self, 'model_info', None):
            class_name = 'Info%s%s'%(self.opts.app_label.capitalize(), self.opts.object_name)
            self.model_info = type(class_name, (CustomModelInfo,), {})

            # Prepares Meta child class
            self.model_info.Meta = type('Meta', (CustomModelInfo.Meta,), {})

            self.model_info.Meta.model = self.model

            # Uses the same of this model admin
            if getattr(self, 'fieldsets', None):
                self.model_info.Meta.fieldsets = make_fieldsets(self.fieldsets)
            elif getattr(self, 'fields', None):
                self.model_info.Meta.fields = self.fields

            if getattr(self, 'exclude', None):
                self.model_info.Meta.exclude = self.exclude

        return self.model_info

    def get_model_info(self, request, obj):
        """Returns an instance of model info for the given object"""

        return self.get_model_info_class(request, obj)(obj)

class CustomModelInfo(ModelInfo):
    class Meta(object):
        row_template = '<div class="form-row"><label>%s</label> <span>%s</span></div>'
        fieldset_title_template = '<h2>%s</h2>'
        render_fieldset_title_in_row = False


