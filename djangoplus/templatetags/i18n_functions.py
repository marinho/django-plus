import re

from django.conf import settings
from django import template
from django.utils.safestring import mark_safe
from django.template.defaultfilters import title, linebreaks, escape
from django.core.urlresolvers import reverse

from djangoplus.translation import ugettext_field

register = template.Library()

class TransFieldNode(template.Node):
    def __init__(self, obj, field_name, safe, title, linebreaks, upper, escape):
        self.obj = template.Variable(obj)
        self.field_name = field_name
        self.safe = safe
        self.title = title
        self.linebreaks = linebreaks
        self.upper = upper
        self.escape = escape

    def render(self, context):
        obj = self.obj.resolve(context)

        if obj is None:
            return ''

        value = ugettext_field(obj, self.field_name)

        if not value:
            value = getattr(obj, self.field_name, '')

        value = unicode(value)

        if self.safe: value = mark_safe(value)
        if self.title: value = title(value)
        if self.linebreaks: value = linebreaks(value)
        if self.upper: value = value.upper()
        if self.escape: value = escape(value)

        return value

@register.tag
def trans_field(parser, token):
    parts = token.split_contents()

    obj, field_name = parts[1], parts[2]
    safe = 'safe' in parts[3:]
    title = 'title' in parts[3:]
    linebreaks = 'linebreaks' in parts[3:]
    upper = 'upper' in parts[3:]
    escape = 'escape' in parts[3:]

    return TransFieldNode(obj, field_name, safe, title, linebreaks, upper, escape)

ADMIN_FIELDS_SCRIPT_TPL = """
<style type="text/css">
    .set_translation {
        float: right;
        font-weight: bold;
    }
</style>

<script type="text/javascript">
    (function($){
        $(document).ready(function(){
            $('div.form-row').each(function(){
                if (%(has_classes)s) {
                    var link = $('<a class="set_translation" href="javascript: void(0)">Set translation</a>');
                    link.prependTo($(this));

                    var field_name = $(this).attr('class').split(' ')[1];

                    link.click(function(){
                        var url = '%(url_popup)s?';
                        url += 'content_type=%(content_type_id)s&';
                        url += 'field_name=' + field_name + '&';
                        url += 'object_id=%(original_pk)s';
                        window.open(url, 'set_field_trans', 'width=700,height=550,popup=yes')
                    });
                }
            });
        });
    })(django.jQuery);
</script>
"""

class AdminFields(template.Node):
    def render(self, context):
        app_name, tmp = context['original'].__class__.__module__.rsplit('.', 1)
        model_name = context['original'].__class__.__name__

        try:
            model_fields = settings.TRANSLATED_MODELS[app_name][model_name]
        except KeyError:
            return ''

        return mark_safe(ADMIN_FIELDS_SCRIPT_TPL % {
            'has_classes': ' || '.join(["$(this).hasClass('%s')"%f for f in model_fields]),
            'url_popup': reverse('i18n_set_field_translation'),
            'content_type_id': context['content_type_id'],
            'original_pk': context['original'].pk,
            })

@register.tag
def i18n_admin_fields(parser, token):
    return AdminFields()

