import os
import logging
import socket
import random

from dnslib.dns import DNSRecord, DNSQuestion, QTYPE, CLASS, RR
from django.conf import settings
from django.db.models import Q, Exists
from django.core import signals
from django.core.cache import cache

from .models import Record, Region

logger = logging.getLogger(__name__)


class QueryProxy(object):

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
        self.protocol = settings.DNSKEY_REMOTE_QUERY_PROTOCOL

    def _query(self, request):
        address, port = self.nameservers[0].split(":")
        port = int(port or 53)
        addrinfo = socket.getaddrinfo(address, port)
        try:
            if len(addrinfo[0][-1]) == 2:  # ipv4
                a_pkt = request.send(
                    address, port, self.protocol == "TCP", self.timeout, False
                )
            else:
                a_pkt = request.send(
                    address, port, self.protocol == "TCP", self.timeout, True
                )
            return DNSRecord.parse(a_pkt)
        except socket.timeout as e:
            logger.exception(e)
            self.nameservers.append(self.nameservers.pop(0))

    def query(self, request, origin=None):
        response = None
        for _ in range(len(self.nameservers)):
            response = self._query(request)
            if response: break
        return response


class LocalQueryProxy(QueryProxy):

    def __init__(self):
        self.remote = RemoteQueryProxy()

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
        if regions: return regions[0]

    def _get_database_query(self, questions, region):
        q = None
        for question in questions:
            sub_q = Q(full_subdomain=str(question.qname), rtype=question.qtype,
                status=1, rclass=question.qclass)
            sub_q = sub_q | Q(full_subdomain=str(question.qname),
                rtype=QTYPE.CNAME, status=1, rclass=question.qclass)
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
        return q

    def _recursive_query(self, questions, region, tracking_chain, records):
        unanswers_questions, recursive_questions = [], []
        for question in questions:
            has_reply = False
            for record in records:
                if question.qname == record.rname \
                        and question.qclass == record.rclass:
                    if question.qtype == record.rtype: 
                        has_reply = True
                    elif record.rtype == QTYPE.CNAME:
                        has_reply = True
                        question = DNSQuestion(
                            qname=str(record.rdata), qtype=question.qtype,
                            qclass=record.rclass
                        )
                        if question in tracking_chain: continue
                        tracking_chain.append(question)
                        recursive_questions.append(question)
            if not has_reply: unanswers_questions.append(question)
        if len(unanswers_questions) > 0:
            request = DNSRecord()
            request.add_question(*unanswers_questions)
            records = self.remote.query(request).rr
            self._set_cached_records(records, region)
            yield from records
        yield from self._query(recursive_questions, region, tracking_chain)

    def _get_cached_records(self, question, region):
        question_cname_key = '{qname}:{qtype}:{qclass}:{zone}'.format(
            qname=question.qname,
            qtype=QTYPE.CNAME,
            qclass=question.qclass,
            zone=region.zone if region else None,
        )
        question_record_key =  '{qname}:{qtype}:{qclass}:{zone}'.format(
            qname=question.qname,
            qtype=question.qtype,
            qclass=question.qclass,
            zone=region.zone if region else None,
        )
        records = []
        for values in cache.get_many(
            [question_cname_key, question_record_key,]).values():
            records.extend(values)
        random.shuffle(records)
        return records

    def _set_cached_records(self, records, region):
        results = {}
        for record in records:
            question_record_key =  '{qname}:{qtype}:{qclass}:{zone}'.format(
                qname=record.rname,
                qtype=record.rtype,
                qclass=record.rclass,
                zone=region.zone if region else None,
            )
            if question_record_key not in results:
                results[question_record_key] = {"records": [], 'ttl': 3600}
            results[question_record_key]["records"].append(record)
            if results[question_record_key]["ttl"] > record.ttl:
                results[question_record_key]["ttl"] = record.ttl    
        for key, value in results.items():
            cache.set(key, value["records"], value["ttl"])

    def _get_records(self, questions, region):
        uncached_questions = []
        for question in questions:
            records = self._get_cached_records(question, region)
            if len(records) > 0:
                yield from records
            else:
                uncached_questions.append(question) 
        if len(uncached_questions) > 0:
            q = self._get_database_query(uncached_questions, region)
            zone_list = []
            for record in Record.objects.filter(q).all():
                zone_list.append("{rr} {ttl} {rclass} {rtype} {rdata}".format(
                    rr=record.full_subdomain, ttl=record.ttl, 
                    rclass=CLASS.get(record.rclass),
                    rtype=QTYPE.get(record.rtype), rdata=record.content
                ))
            records = RR.fromZone(
                os.linesep.join(zone_list),
                origin=region.zone if region else None)
            self._set_cached_records(records, region)
            random.shuffle(records)
            yield from records

    def _query(self, questions, region, tracking_chain):
        if len(questions) == 0: return
        zone_list = []
        tracking_chain.extend(questions)
        records = list(self._get_records(questions, region))
        yield from records
        yield from self._recursive_query(questions, region, tracking_chain, records)

    def query(self, request, origin=None):
        try:
            signals.request_started.send(sender=__name__)
            tracking_chain = []  # Prevent infinite recursion
            region = self.query_region_name(origin)
            for index, rr in enumerate(self._query(
                request.questions, region, tracking_chain)):
                if index > settings.DNSKEY_MAXIMUM_QUERY_DEPTH:
                    break
                request.add_answer(rr)
            return request
        finally:
            signals.request_finished.send(sender=__name__)