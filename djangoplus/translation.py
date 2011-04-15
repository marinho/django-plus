from django.conf import settings
from django.utils.translation import get_language
from django.contrib.contenttypes.models import ContentType

from djangoplus.models import TranslatedField, format_language

def ugettext_field(obj, field_name):
    """
    This function returns the translation for field value in the given object.

    It uses model class TranslatedField to find translation value or just returns
    the current field value if it doesn't exist or just it's empty.
    """

    # Gets from cache if it exists
    cached_value = TranslatedField.objects.get_from_cache(obj, field_name)
    if cached_value:
        return cached_value

    c_type = ContentType.objects.get_for_model(obj)

    try:
        trans = TranslatedField.objects.get(
                language=format_language(get_language()),
                content_type=c_type,
                object_id=obj.pk,
                field_name=field_name,
                )
        result = trans.value
    except TranslatedField.DoesNotExist:
        result = ''

    # If doesn't exists or is empty, get field value instead
    if not unicode(result).strip():
        result = getattr(obj, field_name)

    # Replaces static URLs for that including current language
    result = result.replace('/static/','/static/%s/' % get_language())

    # Stores in cache
    TranslatedField.objects.save_to_cache(obj, field_name, result)

    return result

