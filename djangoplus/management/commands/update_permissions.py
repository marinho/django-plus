from django.core.management import BaseCommand
from django.contrib.auth.management import create_permissions
from django.db.models.loading import get_apps

class Command(BaseCommand):
    def handle(self, **kwargs):
        print 'Updating permissions...'

        for app in get_apps():
            create_permissions(app, None, 2)

