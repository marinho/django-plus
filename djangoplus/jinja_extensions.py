import django
from django import template

from djangoplus.utils import path_to_object
from djangoplus.models import DynamicTemplate

from jinja2.ext import Extension
from jinja2 import nodes

class tcp(dict):
    """
    This class works like a context processor function
    """

    def __init__(self, request):
        self.request = request
        self['model_info_for_list'] = self.model_info_for_list
        self['model_info_for_object'] = self.model_info_for_object
        self['model_info_fields'] = self.model_info_fields
        self['dynamic_template'] = self.dynamic_template

    def model_info_for_list(self, class_path, list_obj, piece=None):
        """
        Example:

        {% set list = model_info_for_list('myapp.info.ListUser', my_objects) %}
        <table>
            {{ list }}
        </table>
        """
        cls = path_to_object(class_path)

        # Constructing the output
        model_list = cls(list_obj, request=self.request)

        if piece:
            model_list = getattr(model_list, piece, None)

            if callable(model_list):
                model_list = model_list()

        return model_list

    def model_info_for_object(self, class_path, obj, as_part=None):
        """
        Example:

        {% set info = model_info_for_object('myapp.info.InfoUser', user) %}
        <table>
            {{ info }}
        </table>
        """
        cls = path_to_object(class_path)

        model_info = cls(obj, request=self.request)

        if not as_part:
            return model_info

        return model_info

    def model_info_fields(self, class_path):
        cls = path_to_object(class_path)
        m_obj = cls(None, request=self.request)
        fields = [(f, m_obj.get_field_display_text(f)) for f in m_obj._meta.fields]

        return fields

    def dynamic_template(self, slug, is_group=False, **context):
        ret = ''

        if self.is_group:
            templates = DynamicTemplate.objects.filter(group=self.slug)
        else:
            templates = DynamicTemplate.objects.filter(slug=self.slug)

        for tpl in templates:
            ret += tpl.render(context)

        return ret

