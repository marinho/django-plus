from django.db import models
from django import template
from django.template.defaultfilters import slugify

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
        return template.Template(self.content).render(template.Context(context))

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

