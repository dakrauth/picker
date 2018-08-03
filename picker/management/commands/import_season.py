import json
from django.core.management.base import BaseCommand
from picker import models as picker


class Command(BaseCommand):
    help = "Loads a new sports league"
    requires_migrations_checks = True
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('filenames', nargs='+')

    def handle(self, *args, **options):
        for arg in options['filenames']:
            with open(arg) as fin:
                data = json.loads(fin.read())

            new_old = picker.League.import_season(data)
            print('Created {} new, {} old games'.format(*new_old))
