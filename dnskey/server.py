import socket
import threading

from dnslib.server import DNSServer, UDPServer, TCPServer

from django.conf import settings

from domain.query import LocalQueryProxy

class DNSUDPServer(UDPServer):
    address_family = socket.AF_INET6


class DNSTCPServer(TCPServer):
    address_family = socket.AF_INET6


class DNSkeyResolver(object):

    def __init__(self):
        self.query = LocalQueryProxy()

    def resolve(self, request, handler):
        """
        todo:
            获取解析结果
            settings.DNSKEY_NAMESERVERS为上游服务器
            根据每次应答时间确认上游服务的优先级
            解析结果等信息充分利用memcache以及cache的ttl特性
        """
        return self.query.query(request)


class DNSKeyServer(object):

    def start_server(self):
        host = settings.DNSKEY_DNS_SERVE_HOST
        port = settings.DNSKEY_DNS_SERVE_PORT
        udp_server = DNSServer(
            DNSkeyResolver(),
            address=host,
            port=port,
            server=DNSUDPServer
        )
        tcp_server = DNSServer(
            DNSkeyResolver(),
            address=host,
            port=port,
            tcp=True,
            server=DNSTCPServer
        )
        udp_server.start_thread()
        tcp_server.start_thread()
        return udp_server.thread, tcp_server.thread

    def serve_forever(self):
        jobs = []
        jobs.extend(self.start_server())
        [job.join() for job in jobs]

    def serve(self):
        thread = threading.Thread(target=self.serve_forever)
        thread.daemon = True
        thread.start()
