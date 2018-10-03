import threading
from django.contrib.staticfiles.management.commands import runserver

from dnskey.server import DNSKeyServer


class Command(runserver.Command):

    def handle(self, *args, **options):
        server = DNSKeyServer()
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return runserver.Command.handle(self, *args, **options)