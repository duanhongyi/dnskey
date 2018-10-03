import logging
import socket

from dnslib.dns import DNSRecord, DNSQuestion, QTYPE, RR
from django.conf import settings
from django.db.models import Q, Exists

from .models import Record, Region

logger = logging.getLogger(__name__)


class QueryProxy(object):

    def question(self, *qlist):
        dns_record = DNSRecord()
        dns_record.add_question(*[
            DNSQuestion(domain, getattr(QTYPE, qtype)) \
            for domain, qtype in qlist
        ])        
        return dns_record

    def query(self, *qlist, origin=None):
        """
        q: tuple list for (domain, qtype)
        origin: Request IP
        """
        raise NotImplementedError

class RemoteQueryProxy(QueryProxy):

    def __init__(self):
        self.nameservers = settings.DNSKEY_REMOTE_NAMESERVERS
        self.timeout = settings.DNSKEY_REMOTE_QUERY_TIMEOUT
        self.protocol = DNSKEY_REMOTE_QUERY_PROTOCOL

    def _query(self, *qlist):
        dns_record = self.question(*qlist)
        address, port = self.nameservers[0].split(":")
        port = int(port or 53)
        addrinfo = socket.getaddrinfo(address, port)
        try:
            if len(addrinfo[0][-1]) == 2:  # ipv4
                a_pkt = dns_record.send(
                    address, port, self.protocol == "TCP", self.timeout, False
                )
            else:
                a_pkt = dns_record.send(
                    address, port, self.protocol == "TCP", self.timeout, True
                )
            return DNSRecord.parse(a_pkt)
        except socket.timeout as e:
            logger.exception(e)
            self.nameservers.append(self.nameservers.pop(0))

    def query(self, *qlist, origin=None):
        response = None
        for _ in range(len(self.nameservers)):
            response = self._query(*qlist)
            if response: break
        return response


class LocalQuery(QueryProxy):

    def query_region_name(self, origin):
        if not origin: return
        addrinfo = socket.getaddrinfo(origin, 0)    
        if len(addrinfo[0][-1]) == 2:  # ipv4
            address_family = socket.AF_INET
        else:
            address_family = socket.AF_INET6
        ip = int.from_bytes(
            socket.inet_pton(address_family, origin), 'big')
        regions = Region.objects.filter(
            start_address__gte=ip, end_address__lt=ip)
        if regions:
            return regions[0]


    def query(self, *qlist, origin=None):
        region = self.query_region_name(origin)
        q = None
        for domain, qtype in q:
            sub_q = Q(name=domain, type=getattr(QTYPE, qtype), status=1)
            if not q:
                q = sub_q
            else:
                q = q | sub_q
        if region:
            q_region = Q(region_name__in=[
                region.state, region.province, region.city, region.zone
            ])
            regions = Record.objects.filter(q & q_region)
            q = (q & q_region) | (~Exists(regions) & q)
        records = Record.objects.filter(q)
        dns_record = self.question(*qlist)
        dns_record.add_answer(
            *[
                RR.fromZone("%s IN %s %s" % (
                    record.name, QTYPE.get(record.type), record.content
                ), origin=origin, ttl=record.ttl)
                for record in records
            ]
        )
        return dns_record


class MixinQueryProxy(QueryProxy):

    def __init__(self):
        self.local = LocalQuery()
        self.remote = RemoteQueryProxy()
        self.timeout = settings.DNSKEY_REMOTE_QUERY_CACHED_TIMEOUT
    
    def query(self, *qlist, origin=None):
        dns_record = self.local.query(*qlist, origin)
        if len(dns_record.rr) == 0:
            dns_record = self.remote.query(*qlist, origin)
        return dns_record
