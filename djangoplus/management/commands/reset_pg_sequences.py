from optparse import make_option

from django.core.management import BaseCommand
from django.conf import settings
from django.db import connection, transaction, models

def get_auto_fields(model):
    return [f for f in model._meta.fields if isinstance(f, models.AutoField)]

SQL_RESET_TPL = "select setval('%(table)s_%(field)s_seq', (SELECT max(%(field)s) + 1 from %(table)s));"
#SQL_RESET_TPL = "select setval('%(table)s_%(field)s_seq', 1);"

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--execute',
                default=False,
                dest='execute',
                action='store_true',
                ),
            )

    def handle(self, execute=False, **kwargs):
        print 'Checking...'

        if execute:
            cur = connection.cursor()

        # All applications
        commands = []
        for app in models.get_apps():
            app_name = app.__name__.split('.')[-2]
            model_list = models.get_models(app)
            
            for model in model_list:
                fields = get_auto_fields(model)
                if not fields:
                    continue

                for field in fields:
                    sql = SQL_RESET_TPL%{
                            'table': model._meta.db_table, 
                            'field': field.db_column or field.name,
                            }
                    print sql
                    
                    if execute:
                        cur.execute(sql)

