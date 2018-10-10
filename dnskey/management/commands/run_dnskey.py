import threading
from django.contrib.staticfiles.management.commands import runserver

from dnskey.server import DNSKeyServer


class Command(runserver.Command):

    def _handle(self, *args, **options):
        runserver.Command.handle(self, *args, **options)


    def handle(self, *args, **options):
        thread = threading.Thread(
            target=self._handle, args=args, kwargs=options)
        thread.start()
        server = DNSKeyServer()
        server.serve()
        thread.join()