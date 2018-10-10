import socket
import threading

from multiprocessing import cpu_count, Process
from dnslib.server import UDPServer, TCPServer, DNSLogger, DNSHandler
from django.conf import settings

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
        return self.query.query(request)


class DNSKeyServer(object):
    
    daemon = True
    worker_processes = cpu_count() * 2

    def __init__(self):
        address = settings.DNSKEY_DNS_SERVE_HOST
        port = settings.DNSKEY_DNS_SERVE_PORT
        resolver = DNSkeyResolver()
        logger = DNSLogger(log="-send,-recv,-request,-reply,-truncated,-data")
        self.tcp_server = DNSTCPServer((address, port), DNSHandler)
        self.tcp_server.resolver = resolver
        self.tcp_server.logger = logger
        self.udp_server = DNSUDPServer((address, port), DNSHandler)
        self.udp_server.resolver = resolver
        self.udp_server.logger = logger

    def _start_threads(self, *targets):
        threads = []
        for target in targets:
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        [thread.join() for thread in threads]

    def serve(self):
        workers = []
        for _ in range(self.worker_processes):
            process = Process(target=self._start_threads, args=(
                self.tcp_server.serve_forever,
                self.udp_server.serve_forever,
            ))
            process.daemon = self.daemon
            process.start()
            workers.append(process)
        return workers