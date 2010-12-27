"""
Examples
========

my_app/models.py
----------------

    from django.db import models

    class CustomerType(models.Model):
        name = models.CharField(max_length=50)

        def __unicode__(self):
            return self.name

    class Customer(models.Model):
        name = models.CharField(max_length=50)
        type = models.ForeignKey('CustomerType')
        is_active = models.BooleanField(default=True, blank=True)
        employer = models.CharField(max_length=100)

        def __unicode__(self):
            return self.name

another_app/models.py
---------------------

    from django.db import models
    from django.contrib.auth.models import User

    from djangoplus.modify_models import ModifiedModel

    class City(models.Model):
        name = models.CharField(max_length=50)

        def __unicode__(self):
            return self.name

    class HelperCustomerType(ModifiedModel):
        class Meta:
            model = 'my_app.CustomerType'

        description = models.TextField()

    class HelperCustomer(ModifiedModel):
        class Meta:
            model = 'my_app.Customer'
            exclude = ('employer',)

        type = models.CharField(max_length=50)
        address = models.CharField(max_length=100)
        city = models.ForeignKey(City)

        def __unicode__(self):
            return '%s - %s'%(self.pk, self.name)

    class HelperUser(ModifiedModel):
        class Meta:
            model = User

        website = models.URLField(blank=True, verify_exists=False)

"""
import types

from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model
from django.db.models.fields import FieldDoesNotExist

class ModifiedModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(ModifiedModelMetaclass, cls).__new__(cls, name, bases, attrs)

        if name == 'ModifiedModel' and bases[0] == object:
            return new_class

        try:
            meta = attrs['Meta']()
        except KeyError:
            raise ImproperlyConfigured("Helper class %s hasn't a Meta subclass!" % name)

        # Find model class for this helper
        if isinstance(getattr(meta, 'model', None), basestring):
            model_class = get_model(*meta.model.split('.'))
        elif issubclass(getattr(meta, 'model', None), models.Model):
            model_class = meta.model
        else:
            raise ImproperlyConfigured("Model informed by Meta subclass of %s is improperly!" % name)

        def remove_field(f_name):
            # Removes the field form local fields list
            model_class._meta.local_fields = [f for f in model_class._meta.local_fields
                    if f.name != f_name]

            # Removes the field setter if exists
            if hasattr(model_class, f_name):
                delattr(model_class, f_name)

        # Removes fields setted in attribute 'exclude'
        if isinstance(getattr(meta, 'exclude', None), (list,tuple)):
            for f_name in meta.exclude:
                remove_field(f_name)

        # Calls 'contribute_to_class' from field to sender class
        for f_name, field in attrs.items():
            if isinstance(field, models.Field):
                # Removes the field if it already exists
                remove_field(f_name)

                # Appends the new field to model class
                field.contribute_to_class(model_class, f_name)

        # Attaches methods
        for m_name, func in attrs.items():
            if callable(func) and type(func) == types.FunctionType:
                setattr(model_class, m_name, func)

        new_class._meta = meta

        return new_class

class ModifiedModel(object):
    """
    Make your inheritance from this class and set a Meta subclass with attribute
    'model' with the model class you want to modify: add/replace/exclude fields
    and/or add/replace methods.
    """
    __metaclass__ = ModifiedModelMetaclass

