import threading
from django.contrib.staticfiles.management.commands import runserver

from dnskey.server import DNSKeyServer


class Command(runserver.Command):

    def handle(self, *args, **options):
        server = DNSKeyServer()
        server.serve()
        return runserver.Command.handle(self, *args, **options)