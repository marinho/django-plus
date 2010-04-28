import types, re, decimal
from datetime import date, time, datetime

from django.utils.safestring import mark_safe
from django.db import models
from django.template.defaultfilters import yesno, linebreaksbr, urlize
from django.utils.translation import get_date_formats
from django.utils.text import capfirst
from django.utils import dateformat
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from djangoplus.templatetags.djangoplus_tags import moneyformat
from djangoplus import app_settings

class ModelInfoBase(object):
    class _Meta:
        model = None
        fields = ()
        exclude = ()
        show_if_none = False
        show_if_empty = False
        auto_urlize = True
        auto_linebreaks = True
        list_display_links = ()

    request = None

    def get_model_fields(self):
        ret = [f.name for f in self._meta.model._meta.fields \
                if f.name != 'id' and \
                (f.name in self._meta.fields or \
                not f.name in self._meta.exclude)\
                ]
        return ret

    def get_field(self, f_name):
        try:
            return [f for f in self._meta.model._meta.fields if f.name == f_name][0]
        except IndexError, e:
            return None

    def get_field_display_text(self, f_name):
        """Returns the display text for the informed field. This allows you
        declare a method like 'get_FIELD_display' to returns a customized
        display text."""

        if hasattr(self, 'get_%s_display'%f_name):
            ret = getattr(self, 'get_%s_display'%f_name)()
        else:
            f = self.get_field(f_name)

            if f:
                ret = f.verbose_name
            else:
                ret = f_name

        return ret[0] == ret[0].lower() and ret.capitalize() or ret

    def get_field_display_value(self, f_name, instance):
        field = self.get_field(f_name)
        f_value = None

        try:
            return getattr(self, 'get_%s_value'%f_name)(instance)
        except AttributeError, e:
            pass

        if isinstance(instance, models.Model):
            try:
                f_value = getattr(instance, f_name)
            except ObjectDoesNotExist:
                f_value = None
        elif type(instance) == types.DictType:
            f_value = instance.get(f_name, None)

        if f_value is None:
            return None

        if callable(f_value):
            return f_value()
        
        if isinstance(f_value, models.Model):
            if self._meta.auto_urlize and hasattr(f_value, 'get_absolute_url') and not f_name in self._meta.list_display_links:
                return '<a href="%s">%s</a>'%(f_value.get_absolute_url(), unicode(f_value))
            else:
                return unicode(f_value)

        if field:
            if field.choices:
                return dict(field.choices).get(f_value, None)

            if isinstance(field, models.BooleanField):
                return yesno(f_value)

            date_format, datetime_format, time_format = get_date_formats()

        if f_value:
            if isinstance(f_value, datetime):
                return dateformat.format(f_value, datetime_format)

            if isinstance(f_value, time):
                return dateformat.time_format(f_value, time_format)

            if isinstance(f_value, date):
                return dateformat.format(f_value, date_format)

            if isinstance(f_value, decimal.Decimal):
                return moneyformat(f_value, None, app_settings.THOUSANDS_SEPARATOR)

            if isinstance(f_value, models.Manager):
                return ', '.join(map(unicode, f_value.all()))

            if field and isinstance(field, models.TextField):
                if self._meta.auto_urlize: f_value = urlize(f_value)
                if self._meta.auto_linebreaks: f_value = linebreaksbr(f_value)

        return f_value

    def get_linkable_field_value(self, instance, f_name, f_value, force=False):
        url = ''

        if isinstance(instance, models.Model) and hasattr(instance, 'get_absolute_url'):
            url = instance.get_absolute_url()
        elif type(instance) == types.DictType and instance.has_key('get_absolute_url'):
            url = instance['get_absolute_url']

        if hasattr(instance, 'get_absolute_url') and ( force or f_name in self._meta.list_display_links ):
            return '<a href="%s">%s</a>' %(instance.get_absolute_url(), f_value)

        return f_value

    def as_string(self):
        raise NotImplemented

    def __unicode__(self):
        return self.as_string()

class ModelInfo(ModelInfoBase):
    """Automatic info creator for model classes, basing on objects"""
    class _Meta(ModelInfoBase._Meta):
        fieldsets = None
        row_template = '<tr><th>%s</th><td>%s</td></tr>'
        fieldset_title_template = '<h3>%s</h3>'
        show_fieldset_title = True
        render_fieldset_title_in_row = True

    def __init__(self, instance, *args, **kwargs):
        self.instance = instance

        if 'request' in kwargs:
            self.request = kwargs['request']

        self._meta = self.Meta()
        _meta = self._Meta()

        for attr in ('model','fields','exclude','fieldsets','row_template','show_if_none',
                'show_if_empty','auto_urlize','auto_linebreaks','list_display_links',
                'fieldset_title_template','show_fieldset_title','render_fieldset_title_in_row'):
            if not hasattr(self._meta, attr):
                setattr(self._meta, attr, getattr(_meta, attr))

    def get_field_display_value(self, f_name):
        return super(ModelInfo, self).get_field_display_value(f_name, self.instance)

    def fieldset_render(self, s_name, s_fields):
        ret = []

        if s_name and self._meta.show_fieldset_title:
            if self._meta.render_fieldset_title_in_row:
                ret.append(self._meta.row_template%('&nbsp;', self._meta.fieldset_title_template % s_name))
            else:
                ret.append(self._meta.fieldset_title_template % s_name)
                
        for f_name in s_fields:
            f_display = self.get_field_display_text(f_name)

            f_value = self.get_field_display_value(f_name)
            f_value = self.get_linkable_field_value(self.instance, f_name, f_value)

            if (self._meta.show_if_none or f_value is not None) and\
               (self._meta.show_if_empty or f_value != ''):
                ret.append(self._meta.row_template%(f_display, f_value))

        return ret

    def __getitem__(self, num):
        fieldsets = self._meta.fieldsets or ((None, self._meta.fields or self.get_model_fields()),)

        s_name, s_fields = fieldsets[num]

        ret = self.fieldset_render(s_name, s_fields)

        return mark_safe(u'\n'.join(ret))

    def as_string(self):
        ret = []

        fieldsets = self._meta.fieldsets or ((None, self._meta.fields or self.get_model_fields()),)

        for s_name, s_fields in fieldsets:
            ret += self.fieldset_render(s_name, s_fields)

        return mark_safe(u'\n'.join(ret))

class ModelListItem(object):
    model_list = None
    _row_str = ''
    obj = None

    def __init__(self, model_list, row_str, obj):
        self.model_list = model_list
        self._row_str = row_str
        self.obj = obj

    def __unicode__(self):
        return self.row_str

    def get_row_str(self):
        return self._row_str
    row_str = property(get_row_str)

class ModelList(ModelInfoBase):
    """Automatic list creator for model classes, basing on QuerySets"""
    item_class = ModelListItem

    class _Meta(ModelInfoBase._Meta):
        td_template = '<td class="%(field_name)s">%(value)s</td>'
        th_template = '<th class="%(field_name)s">%(display)s</th>'
        tr_template = '<tr>%s</tr>'
        thead_template = '<thead><tr>%s</tr></thead>'
        tbody_template = '<tbody>%s</tbody>'
        icon_edit_template = '<a href="%(edit_url)s" title="Edit this" class="edit"><img src="%(media_url)simg/admin/icon_changelink.gif" alt="Edit"/></a>'
        icon_delete_template = '<a href="%(delete_url)s" title="Delete this" class="delete"><img src="%(media_url)simg/admin/icon_deletelink.gif" alt="Edit"/></a>'
        group_template = '<tr><td colspan="%(cols)s" class="group"><h3>%(display)s</h3></td></tr>'
        groups = []
        show_header = True
        show_summary = True
        summary_fields = None
        summary_td_template = '<td class="%(field_name)s">%(value)s</td>'
        summary_tr_template = '<tr>%(cells)s</tr>'

    def __init__(self, queryset, *args, **kwargs):
        self.queryset = queryset

        if 'request' in kwargs:
            self.request = kwargs['request']

        self._meta = self.Meta()
        _meta = self._Meta()

        for attr in ('model','fields','exclude','td_template','th_template','tr_template',
                'thead_template','tbody_template','show_if_none','auto_urlize',
                'auto_linebreaks','list_display_links','icon_edit_template',
                'icon_delete_template','group_template','groups','show_header',
                'summary_fields','summary_td_template','summary_tr_template','show_summary'):
            if not hasattr(self._meta, attr):
                setattr(self._meta, attr, getattr(_meta, attr))

        # Replace "%s" for "%(value)s" on td_template to accept old uses
        self._meta.td_template = self._meta.td_template.replace(r'%s', r'%(value)s')

    def render_buttons_header(self):
        """Renders the header cell for the column that will have util buttons"""
        if self._meta.icon_edit_template or self._meta.icon_delete_template:
            return '<th class="buttons">&nbsp;</th>'
        else:
            return ''

    def render_buttons_cell(self, instance, edit_url=None, delete_url=None, additional_code=''):
        """Renders the cell with util buttons for each row in the grid"""
        ret = []

        url = hasattr(instance, 'get_absolute_url') and getattr(instance, 'get_absolute_url')() or ''
        edit_url = edit_url or (url and url+'edit/' or '')
        delete_url = delete_url or (url and url+'delete/' or '')

        if self._meta.icon_edit_template and edit_url:
            ret.append(self._meta.icon_edit_template%{'edit_url':edit_url, 'media_url':settings.ADMIN_MEDIA_PREFIX})

        if self._meta.icon_delete_template and delete_url:
            ret.append(self._meta.icon_delete_template%{'delete_url':delete_url, 'media_url':settings.ADMIN_MEDIA_PREFIX})

        if ret:
            return '<td class="buttons">%s %s</td>'%(' '.join(ret), additional_code)
        else:
            return ''

    def header(self):
        """Renders a header with field labels on the top of the grid"""
        fields = self._meta.fields or self.get_model_fields()

        # THead
        thead = []

        for f_name in fields:
            f_display = self.get_field_display_text(f_name)
            f_display = f_display[0] == f_display[0].lower() and f_display.capitalize() or f_display

            thead.append(self._meta.th_template%{'field_name': f_name, 'display': f_display})

        return self._meta.thead_template %(''.join(thead) + self.render_buttons_header())

    def summary(self):
        """Renders a summary with aggregation in the end of the grid.
        
        Uses the meta attributes:
            
         * show_summary
         * summary_fields
         * summary_td_template
         * summary_tr_template
        """
        fields = self._meta.fields or self.get_model_fields()

        try:
            qs = self.queryset.all()
        except AttributeError:
            qs = self.queryset

        tsummary = []

        for f_name in fields:
            if f_name in self._meta.summary_fields:
                val = self._meta.summary_fields[f_name](qs)
            else:
                val = '&nbsp'
            
            if isinstance(val, decimal.Decimal):
                val = moneyformat(val, None, app_settings.THOUSANDS_SEPARATOR)

            tsummary.append(self._meta.summary_td_template%{
                'field_name': f_name,
                'value': val,
                })

        return self._meta.summary_tr_template%{
                'cells': ''.join(tsummary) + self.render_button_cell_summary(),
                }

    def render_button_cell_summary(self):
        return '<td>&nbsp;</td>'

    def get_columns_count(self):
        fields = self._meta.fields or self.get_model_fields()
        return len(fields)+1

    def rows(self):
        """Iterator with the list of rows in the grid"""
        fields = self._meta.fields or self.get_model_fields()

        tbody = []

        groups_values = {}
        if self._meta.groups:
            groups_values = groups_values.fromkeys(self._meta.groups)

        try:
            qs = self.queryset.all()

            if self._meta.groups:
                try:
                    qs = qs.order_by(*self._meta.groups)
                except AssertionError, e:
                    # Ignores the error if it doesn't get to order
                    if e.message != 'Cannot reorder a query once a slice has been taken.':
                        raise

        except AttributeError:
            qs = self.queryset

        for obj in qs:
            # Groups
            group_rows = []

            if self._meta.groups:
                for group in self._meta.groups:
                    field_value = self.get_field_display_value(group, obj)
                    if groups_values[group] != field_value:
                        groups_values[group] = field_value
                        group_row = self._meta.group_template%{'cols': self.get_columns_count(), 'display': field_value}
                        group_rows.append(group_row)

            # Single row
            row = self.render_single_object(obj)
            ret = self.item_class(self, '\n'.join(group_rows) + row, obj)
            ret.obj = obj

            yield ret

    def render_single_object(self, obj, tr_template=None, td_template=None):
        """Renders a single object. It is util internally or can be used for
        granulary customizations"""
        # Customized templates
        tr_template = tr_template or self._meta.tr_template
        td_template = td_template or self._meta.td_template

        fields = self._meta.fields or self.get_model_fields()
        row = []

        for i, f_name in enumerate(fields):
            f_value = self.get_field_display_value(f_name, obj)
            f_value = self.get_linkable_field_value(
                    obj, f_name, f_value,
                    force=not self._meta.list_display_links and i == 0,
                    )

            if isinstance(f_value, decimal.Decimal):
                f_value = moneyformat(f_value, None, app_settings.THOUSANDS_SEPARATOR)

            if self._meta.show_if_none or f_value is not None:
                row.append(td_template%{'field_name': f_name, 'value': f_value})
            else:
                row.append(td_template%{'field_name': f_name, 'value': '&nbsp;'})

        tds = ''.join(row) + self.render_buttons_cell(obj)

        return self.format_tr_by_template(obj, tr_template, tds)

    def format_tr_by_template(self, obj, tr_template, tds):
        return tr_template % tds

    def as_string(self):
        """Returns the whole string with the grid HTML code"""
        fields = self._meta.fields or self.get_model_fields()

        # THead
        if self._meta.show_header:
            thead = self.header()
        else:
            thead = ''

        # TBody
        tbody = [r.row_str for r in self.rows()]

        if tbody:
            tbody = self._meta.tbody_template % u'\n'.join(tbody)
            ret = u'\n'.join([thead, tbody])
        else:
            ret = u''

        # Summary
        if self._meta.show_summary and self._meta.summary_fields:
            ret += self.summary()

        return mark_safe(ret)

