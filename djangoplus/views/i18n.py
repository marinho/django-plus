from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.utils.translation import get_language
from django.forms.models import modelformset_factory
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from djangoplus.models import TranslatedField, format_language

class FormTranslatedField(forms.ModelForm):
    class Meta:
        model = TranslatedField
        fields = ('language','value')

    language = forms.Field(widget=forms.HiddenInput)

def set_field_translation(request):
    c_type = ContentType.objects.get(pk=request.GET['content_type'])
    original = c_type.get_object_for_this_type(pk=request.GET['object_id'])
    original_value = getattr(original, request.GET['field_name'])

    # Creates objects for translation for available languages
    for lang, display in settings.LANGUAGES:
        TranslatedField.objects.get_or_create(
            language=format_language(lang),
            content_type=c_type,
            object_id=request.GET['object_id'],
            field_name=request.GET['field_name'],
            )

    # Gets queryset with translations
    translations = TranslatedField.objects.filter(
            content_type=c_type,
            object_id=request.GET['object_id'],
            field_name=request.GET['field_name'],
            )

    # Makes the formset class
    FormSet = modelformset_factory(
            TranslatedField,
            form=FormTranslatedField,
            max_num=len(settings.LANGUAGES),
            extra=len(settings.LANGUAGES),
            )

    if request.method == 'POST':
        formset = FormSet(request.POST, queryset=translations)

        if formset.is_valid():
            formset.save()
            return HttpResponse('<script type="text/javascript">window.close()</script>')
    else:
        formset = FormSet(queryset=translations)

    return render_to_response(
            'i18n_functions/set_field_translation.html',
            locals(),
            context_instance=RequestContext(request),
            )

