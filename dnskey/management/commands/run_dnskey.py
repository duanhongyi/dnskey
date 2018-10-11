import threading
import multiprocessing
from django.contrib.staticfiles.management.commands import runserver

from dnskey.server import DNSKeyServer


class Command(runserver.Command):

    started_dnskey_server = False

    def get_handler(self, *args, **options):
        if not self.started_dnskey_server:
            server = DNSKeyServer()
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            started_dnskey_server = True
            self.started_dnskey_server = True
        return runserver.Command.get_handler(self, *args, **options)