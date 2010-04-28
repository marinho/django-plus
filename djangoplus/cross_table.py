import copy, sets

from django.forms.forms import BoundField
from django.db import models
from django.utils.safestring import mark_safe
from django import forms

class CrossTableForm(forms.Form):
    """Customized form class to be extended and used to let users inform
    fields in a cross reference table matrix.
    
    A cross table is a 3-D relationship in a mode classe where you can
    inform an X and an Y fields, and a field to be used as a cross
    between them."""

    class Meta: pass
    class CrossFields: pass
    class InfoFields: pass

    class _Meta:
        model = None
        x_model = None # Still to be checked and used TODO
        y_model = None # Still to be checked and used TODO
        x_field = None
        y_field = None
        cross_fields_template = 'col-%s-%s-'

    x_values = None
    y_values = None
    queryset = None

    def __init__(self, *args, **kwargs):
        # Meta class
        self.init_meta()

        # Cross and Info fields
        self.init_info_fields()
        self.init_cross_fields()

        # X and Y values lists
        self.x_values = kwargs.pop('x_values', [])
        self.y_values = kwargs.pop('y_values', [])

        # Queryset to base on
        self.queryset = kwargs.pop('queryset', None)

        # Create cross fields
        self.create_fields()

        super(CrossTableForm, self).__init__(*args, **kwargs)

        # Loads initial values from queryset
        if self.queryset:
            self.load_initial_from_queryset(self.queryset)

    def init_meta(self):
        """Set meta object from meta class"""
        self._meta = self.Meta()
        _meta = self._Meta()

        for attr in ('model','x_model','y_model','x_field','y_field','cross_fields_template',):
            if not hasattr(self._meta, attr):
                setattr(self._meta, attr, getattr(_meta, attr))

        # Find X relation field TODO
        # Find Y relation field TODO

    def init_info_fields(self):
        """Transform fields from InfoFields subclass into info_fields dictionary"""
        self.info_fields = [(k, getattr(self.InfoFields, k)) for k in dir(self.InfoFields)
            if isinstance(getattr(self.InfoFields, k), forms.Field)]

    def init_cross_fields(self):
        """Transform fields from CrossFields subclass into cross_fields dictionary"""
        self.cross_fields = [(k, getattr(self.CrossFields, k)) for k in dir(self.CrossFields)
            if isinstance(getattr(self.CrossFields, k), forms.Field)]

    def create_fields(self):
        """Create fields for Y values"""
        for x_value in self.x_values:
            for y_value in self.y_values:
                for name, field in self.cross_fields:
                    field_prefix = self._meta.cross_fields_template%(
                            self.get_x_value(x_value),
                            self.get_y_value(y_value),
                            )
                    self.base_fields[field_prefix + name] = copy.deepcopy(field)

    def get_x_value(self, value):
        """This method is to get a valid referene (and unique) value from a field
        value.
        
        This value is used to make the field names, then you can't use rich
        formatted values here. Only simple values with no spaces, special chars,
        symbols, etc.
        
        You can extend it to customize your form."""

        if isinstance(value, models.Model):
            return value.pk

        return value

    def get_y_value(self, value):
        """See 'get_x_value' docs. It's the same, but used for Y field values."""

        if isinstance(value, models.Model):
            return value.pk

        return value

    @property
    def columns(self):
        """Returns a generator with column headers"""
        column_labels = [field[1].label for field in self.info_fields] + [unicode(value) for value in self.y_values]

        for label in column_labels:
            yield u'<th>%s</th>'%unicode(label)

    @property
    def rows(self):
        """Returns a generator with table rows"""
        for x_value in self.x_values:
            tds = []

            # Info fields
            for name, field in self.info_fields:
                field = BoundField(self, field, name)
                tds.append(u'<td>%s</td>'%unicode(field))

            # Cross fields
            for y_value in self.y_values:
                field_prefix = self._meta.cross_fields_template%(
                        self.get_x_value(x_value),
                        self.get_y_value(y_value),
                        )

                for field_name, field in self.fields.items():
                    if field_name.startswith(field_prefix):
                        errors = '' # TODO
                        bfield = BoundField(self, field, field_name)

                        tds.append(u'<td>%s %s</td>'%(errors, unicode(bfield)))

            tds = u''.join(tds)

            yield u'<tr><th>%s</th>%s</tr>'%(x_value, tds)

    def as_table(self):
        """Returns form renderized to HTML TABLE format"""

        ths = u''.join([th for th in self.columns])
        ths = u'<tr><th>&nbsp;</th>%s</tr>'%ths

        trs = u'\n'.join([tr for tr in self.rows])

        return mark_safe('\n'.join([ths, trs]))

    def __unicode__(self):
        return self.as_table()

    def get_cross_object(self, queryset, x_value, y_value):
        """Find object for the cross between X and Y relationship"""

        filters = {
                self._meta.x_field: x_value,
                self._meta.y_field: y_value,
                }

        try:
            return queryset.get(**filters)
        except queryset.model.DoesNotExist:
            return None

    def get_field_value_from_queryset(self, queryset, x_value, y_value, name, field):
        """Used be initials loader from queryset method to get the value for just a
        field crossed by X and Y values"""
        
        obj = self.get_cross_object(queryset, x_value, y_value)

        return getattr(obj, name)

    def load_initial_from_queryset(self, queryset):
        """Loads intial values from queryset, using meta defined fields and their
        values to find the cross fields values"""

        # Loads initials for cross fields
        for x_value in self.x_values:
            for y_value in self.y_values:
                field_prefix = self._meta.cross_fields_template%(x_value, y_value)
                fields = [f for f in self.cross_fields if f[0].startswith(field_prefix)]

                for name, field in fields:
                    field.initial = self.get_field_value_from_queryset(queryset, x_value, y_value, name, field)

        # Loads initials for info fields TODO

    def create_cross_object(self, queryset, x_value, y_value, extra_fields=None):
        """Returns an object with X and Y fields informed, and additional extra
        fields values if they are informed, also, to be saved as a new object."""

        obj = self._meta.model()
        setattr(obj, self._meta.x_field, x_value)
        setattr(obj, self._meta.y_field, y_value)

        # Sets additional fields
        extra_fields = extra_fields or {}
        for k, v in extra_fields.items():
            setattr(obj, k, v)

        return obj

    def save_cross(self, x_value, y_value):
        """Saves all values to the database"""

        # Get object to save into
        obj = self.get_cross_object(
                self.queryset,
                x_value,
                y_value,
                ) or self.create_cross_object(
                        self.queryset,
                        x_value,
                        y_value,
                        )

        # Sets cross fields values
        for field in self.cross_fields:
            field_prefix = self._meta.cross_fields_template%(
                self.get_x_value(x_value),
                self.get_y_value(y_value),
                )
            field_name = field_prefix + field[0]

            setattr(obj, field[0], self.cleaned_data[field_name])

        obj.save()

    def save(self):
        """Saves all values to the database"""
        for x_value in self.x_values:
            for y_value in self.y_values:
                self.save_cross(x_value, y_value)

class CrossTableManager(models.Manager):
    """Manager to add support to cross table functions with 3 fields from a model
    class.
    
    Cross tables are matrix where you have an X field for rows, Y field for
    columns and a VALUE field for coordinates between X for Y to relate them."""

    def get_query_set(self):
        return CrossTableQuerySet(self.model)

    def crosstable(self, x_field, y_field, cross_fields, x_values=None, y_values=None):
        return self.get_query_set().crosstable(x_field, y_field, cross_fields, x_values,
                y_values)

class CrossTableQuerySet(models.query.QuerySet):
    """QuerySet class to add support to cross table functions with 3 fields from a
    model class. This should be used together with CrossTableManager"""

    def crosstable(self, x_field, y_field, cross_fields, x_values=None, y_values=None):
        """Returns a matrix with crosstable"""
        qs = self

        # Gets X values
        x_values = x_values or sets.Set([getattr(obj, x_field) for obj in qs])
        x_values = [i for i in x_values]

        # Gets Y values
        y_values = y_values or sets.Set([getattr(obj, y_field) for obj in qs])
        y_values = [i for i in y_values]

        # Make easier use of cross fields attribute
        cross_fields = isinstance(cross_fields, (list,tuple)) and cross_fields or [cross_fields]

        ret = [[None] + y_values]

        def get_attr_value(obj, attr):
            value = getattr(obj, attr)

            if callable(value):
                return value()

            return value

        # Values getter
        def get_xy_value(x_value, y_value):
            for obj in qs:
                if getattr(obj, x_field) == x_value and get_attr_value(obj, y_field) == y_value:
                    ret = [get_attr_value(obj, field) for field in cross_fields]
                    ret = len(ret) > 1 and ret or ret[0]
                    return ret

            return None

        for x_value in x_values:
            ret.append([x_value] + [get_xy_value(x_value, y_value) for y_value in y_values])

        return ret

