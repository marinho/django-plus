"""Utilities for test modules"""
import os, unittest, doctest
from sets import Set

from django.core.serializers import deserialize
from django.db.models import get_apps
from django.test.simple import get_tests, run_tests as old_run_tests

def load_fixture(path, file_type='json'):
    """Load a fixture file"""
    fp = file(path)
    cont = fp.read()
    fp.close()

    for obj in deserialize(file_type, cont):
        obj.save()

def model_has_fields(model_class, fields):
    """Checks if a model class has all fields in fields list and returns a
    list of fields that aren't in one of them.
    
    This method returns an empty list ( [] ) when everything is ok"""
    fields = Set(fields)
    model_fields = Set(
            [f.name for f in model_class._meta.fields]+\
            [f.name for f in model_class._meta.many_to_many]
            )
    return list(fields - model_fields)

def is_model_class_fk(model_class_from, field, model_class_to):
    """Returns True if field is ForeignKey to model class informed"""
    return issubclass(
            model_class_from._meta.get_field_by_name(field)[0].rel.to,
            model_class_to,
            )

def is_field_type(model_class_from, field, field_type, **kwargs):
    """Checks if a field of a model class if of the type informed.
    If field_type value is a class, it compares just the class of field,
    if field_type is an instance of a field type class, it compares the
    max_length, max_digits and decimal_places, blank and null"""
    field = model_class_from._meta.get_field_by_name(field)[0]

    if field.__class__ != field_type:
        return False

    for k,v in kwargs.items():
        if k == 'to':
            if v != field.rel.to:
                raise Exception('%s: %s'%(k, unicode(field.rel.to)))
        elif v != getattr(field, k, None):
            raise Exception('%s: %s'%(k, unicode(getattr(field, k, None))))

    return True

def is_model_pk(model_class, field):
    """Checks if a field is the primary key of the model class"""
    return model_class._meta.pk.name == field

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """Test runner to support many DocTests *.txt files and TestUnits *.py
    using a setting TEST_FILES in app.tests module"""
    for app in get_apps():
        test_mod = get_tests(app)

        if not test_mod or hasattr(test_mod, 'suite'):
            continue

        suites = []

        # DocTest files
        for filename in getattr(test_mod, 'DOCTEST_FILES', []):
            try:
                suites.append(doctest.DocFileSuite(
                    filename,
                    package=test_mod,
                    encoding='utf-8',
                    ))
            except TypeError:
                suites.append(doctest.DocFileSuite(
                    filename,
                    package=test_mod,
                    ))

        # Unit Tests modules
        for module in getattr(test_mod, 'UNITTEST_MODULES', []):
            suites.append(unittest.TestLoader().loadTestsFromModule(module))

        # Sets the 'suites' attribute to test module
        if suites:
            print suites
            test_mod.suite = lambda: unittest.TestSuite(suites)

    return old_run_tests(test_labels, verbosity, interactive, extra_tests)

def url_status_code(url, status_code=200, content=None, client=None, return_response=False):
    """Checks if the informed URL returns the wanted status_code"""
    if not client:
        from django.test.client import Client
        client = Client()

    resp = client.get(url)

    if return_response:
        return resp

    ret = True

    if status_code and status_code == resp.status_code:
        ret = ret and True

    if content and content == resp.status_code:
        ret = ret and True

    return ret

