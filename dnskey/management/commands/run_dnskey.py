import threading
from django.contrib.staticfiles.management.commands import runserver

from dnskey.server import DNSKeyServer


class Command(runserver.Command):

    def get_handler(self, *args, **options):
        handler = runserver.Command.get_handler(self, *args, **options)
        server = DNSKeyServer()
        server.serve()
        return handler