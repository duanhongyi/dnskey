import socket
import threading

from multiprocessing import cpu_count, Process
from dnslib.server import UDPServer, TCPServer, DNSLogger, DNSHandler

from django.conf import settings
from django.core.signals import request_started, request_finished
from domain.query import LocalQueryProxy

logger = DNSLogger(log="-send,-recv,-request,-reply,-truncated,-data")


class DNSUDPServer(UDPServer):
    address_family = socket.AF_INET6


class DNSTCPServer(TCPServer):
    address_family = socket.AF_INET6


class DNSkeyResolver(object):
    def __init__(self):
        self.query = LocalQueryProxy()

    def resolve(self, request, handler):
        try:
            request_started.send(sender=__name__)
            return self.query.query(
                request, handler.request[1].getsockname()[0])
        finally:
            request_finished.send(sender=__name__)


class DNSKeyServer(object):
    
    def __init__(self, servers=None):
        self.servers = servers or self._get_default_servers()
        self.daemon = True
        self.worker_processes = settings.DNSKEY_SERVER_WORKER_PROCESSES
        self.worker_processes = self.worker_processes or cpu_count() * 2

    def _get_default_servers(self):
        address = settings.DNSKEY_DNS_SERVE_HOST
        port = settings.DNSKEY_DNS_SERVE_PORT
        resolver = DNSkeyResolver()
        logger = DNSLogger(log="-send,-recv,-request,-reply,-truncated,-data")
        servers = []
        for server_cls in [DNSTCPServer, DNSUDPServer]:
            server = server_cls((address, port), DNSHandler)
            server.resolver = resolver
            server.logger = logger
            servers.append(server)
        return servers

    def add_server(self, *servers):
        self.servers.extend(servers)

    def serve_forever(self):
        threads = []
        for server in self.servers:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        [thread.join() for thread in threads]

    def serve(self):
        workers = []
        for _ in range(self.worker_processes):
            process = Process(target=self.serve_forever)
            process.daemon = self.daemon
            process.start()
            workers.append(process)
        return workers