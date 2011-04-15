from django.db import models
from django import template
from django.template.defaultfilters import slugify
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils.translation import get_language

import app_settings

class DynamicTemplate(models.Model):
    class Meta:
        ordering = ('title',)

    title = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, unique=True)
    group = models.SlugField(blank=True)
    content = models.TextField()

    def __unicode__(self):
        return self.title

    def render(self, context):
        from djangoplus.translation import ugettext_field
        content = ugettext_field(self, 'content')
        return template.Template(content).render(template.Context(context))

class StaticFile(models.Model):
    file = models.FileField(upload_to=app_settings.STATIC_FILES_PATH)
    label = models.CharField(max_length=50, blank=True)
    group = models.CharField(max_length=50, blank=True)
    mimetype = models.CharField(max_length=50, blank=True)

    def __unicode__(self):
        return self.label or self.file.name

# SIGNALS AND LISTENERS
from django.db.models import signals

# DynamicTemplate
def dynamictemplate_pre_save(sender, instance, signal, *args, **kwargs):
    # Cria slug
    if not instance.slug:
        instance.slug = slugify(instance.title)

    if not instance.group:
        instance.group = slugify(instance.group)

signals.pre_save.connect(dynamictemplate_pre_save, sender=DynamicTemplate)

# Signal that creates the 'view_*' permission
from django.db.models import get_models
from django.contrib.auth.management import _get_permission_codename

def _get_all_permissions(opts):
    """Copied from django.contrib.auth.management._get_all_permissions
    and modified to supply permission 'view'"""
    perms = []
    for action in ('view',):
        perms.append((_get_permission_codename(action, opts), u'Can %s %s' % (action, opts.verbose_name_raw)))
    return perms + list(opts.permissions)

def create_permissions(app, created_models, verbosity, **kwargs):
    """Copied from django.contrib.auth.management.create_permissions
    and is still as it was"""

    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        ctype = ContentType.objects.get_for_model(klass)
        for codename, name in _get_all_permissions(klass._meta):
            p, created = Permission.objects.get_or_create(codename=codename, content_type__pk=ctype.id,
                defaults={'name': name, 'content_type': ctype})
            if created and verbosity >= 2:
                print "Adding permission '%s'" % p    

signals.post_syncdb.connect(create_permissions,
    dispatch_uid = "djangoplus.models.create_permissions")

class TranslatedFieldManager(models.Manager):
    def make_cache_key_with_args(self, prefix, language, app_name, model_name, field_name, pk):
        return '%s:%s:%s.%s.%s:%s'%(
            prefix,
            language,
            app_name,
            model_name,
            field_name,
            pk,
            )

    def make_cache_key(self, obj, field_name, language):
        return self.make_cache_key_with_args(
            settings.CACHE_MIDDLEWARE_KEY_PREFIX,
            language,
            obj._meta.app_label,
            obj.__class__.__name__,
            field_name,
            obj.pk,
            )

    def delete_from_cache(self, trans):
        """
        This method is used for cache invalidation of translated fields, so we can
        keep them in memory to be as faster as would be use gettext.
        """
        cache_key = self.make_cache_key_with_args(
            settings.CACHE_MIDDLEWARE_KEY_PREFIX,
            trans.language,
            trans.content_type.model_class()._meta.app_label,
            trans.content_type.model_class().__name__,
            trans.field_name,
            trans.object_id,
            )
        cache.set(cache_key, None)

    def get_from_cache(self, obj, field_name, language=None):
        language = format_language(language or get_language())
        return cache.get(self.make_cache_key(obj, field_name, language), None)

    def save_to_cache(self, obj, field_name, value, language=None):
        language = format_language(language or get_language())
        return cache.set(self.make_cache_key(obj, field_name, language), value, 60 * 30) # minutes

class TranslatedField(models.Model):
    class Meta:
        unique_together = (
                ('language','content_type','field_name','object_id'),
                )

    objects = TranslatedFieldManager()

    language = models.CharField(max_length=5, choices=settings.LANGUAGES,
            null=True, blank=True, db_index=True)
    content_type = models.ForeignKey(ContentType)
    field_name = models.CharField(max_length=50, db_index=True)
    object_id = models.CharField(max_length=250, db_index=True)
    value = models.TextField(blank=True)

def format_language(lang):
    """
    Just returns the lowercase replacing underline to hifen to avoid conflicts between
    formats ll_CC to ll-cc
    """
    return lang.lower().replace('_','-')

# SIGNALS

def translatedfield_post_save(sender, instance, **kwargs):
    """
    Cache invalidation for a translated field in cache when it is changed in database
    """
    sender.objects.delete_from_cache(instance)

models.signals.post_save.connect(translatedfield_post_save, sender=TranslatedField)

