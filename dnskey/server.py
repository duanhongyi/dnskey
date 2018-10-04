import socket

from dnslib.server import DNSServer, UDPServer, TCPServer

from django.conf import settings

class UDPServerIPV6(UDPServer):
    address_family = socket.AF_INET6


class TCPServerIPV6(TCPServer):
    address_family = socket.AF_INET6


class DnskeyResolver(object):

    def resolve(self, request, handler):
        """
        todo:
            获取解析结果
            settings.DNSKEY_NAMESERVERS为上游服务器
            根据每次应答时间确认上游服务的优先级
            解析结果等信息充分利用memcache以及cache的ttl特性
        """
        pass 


class DNSKeyServer(object):

    def start_server_ipv4(self):
        host = settings.DNSKEY_DNS_IPV4_SERVE_HOST
        port = settings.DNSKEY_DNS_IPV4_SERVE_PORT
        udp_server_ipv4 = DNSServer(
            DnskeyResolver(),
            address=host,
            port=port,
        )
        tcp_server_ipv4 = DNSServer(
            DnskeyResolver(),
            address=host,
            port=port,
            tcp=True,
        )
        udp_server_ipv4.start_thread()
        tcp_server_ipv4.start_thread()
        return udp_server_ipv4.thread, tcp_server_ipv4.thread

    def start_server_ipv6(self):
        host = settings.DNSKEY_DNS_IPV6_SERVE_HOST
        port = settings.DNSKEY_DNS_IPV6_SERVE_PORT
        udp_server_ipv6 = DNSServer(
            DnskeyResolver(),
            address=host,
            port=port,
            server=UDPServerIPV6
        )
        tcp_server_ipv6 = DNSServer(
            DnskeyResolver(),
            address=host,
            port=port,
            tcp=True,
            server=TCPServerIPV6
        )
        udp_server_ipv6.start_thread()
        tcp_server_ipv6.start_thread()
        return udp_server_ipv6.thread, tcp_server_ipv6.thread

    def serve_forever(self):
        jobs = []
        jobs.extend(self.start_server_ipv4())
        jobs.extend(self.start_server_ipv6())
        [job.join() for job in jobs]

    def serve(self):
        thread = threading.Thread(target=self.serve_forever)
        thread.daemon = True
        thread.start()