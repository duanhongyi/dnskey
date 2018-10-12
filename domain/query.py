import os
import hashlib
import logging
import socket
import random

from dnslib.dns import DNSRecord, DNSQuestion, QTYPE, CLASS, RR

from django.conf import settings
from django.db.models import Q, Exists
from django.core.cache import cache

from .models import Record, Region
from .signals import query_records

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
            logger.debug(e)
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

    def _get_or_set_cached_region(self, origin):
        def get_region():
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
            return Region()

        if not origin: return
        region = cache.get_or_set("region_by_ip:%s" % origin, get_region)
        return region if region.pk else None

    def _get_database_records(self, questions, region):
        q = None
        for question in questions:
            sub_q = Q(full_subdomain=str(question.qname), rtype=question.qtype,
                rclass=question.qclass)
            sub_q = sub_q | Q(full_subdomain=str(question.qname),
                rtype=QTYPE.CNAME, rclass=question.qclass)
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
        return list(Record.objects.filter(q).all())

    def _recursive_query(self, questions, region, tracking_chain, records):
        unanswers_questions, recursive_questions = [], []
        for question in questions:
            has_reply = False
            for record in records:
                if question.qname == record.full_subdomain \
                        and record.status == 1 \
                        and question.qclass == record.rclass:
                    if question.qtype == record.rtype: 
                        has_reply = True
                    elif record.rtype == QTYPE.CNAME:
                        has_reply = True
                        question = DNSQuestion(
                            qname=record.content, qtype=question.qtype,
                            qclass=record.rclass
                        )
                        if question in tracking_chain: continue
                        tracking_chain.append(question)
                        recursive_questions.append(question)
            if not has_reply: unanswers_questions.append(question)
        if len(unanswers_questions) > 0:
            request = DNSRecord()
            request.add_question(*unanswers_questions)
            records = [
                Record(full_subdomain=r.rname, rtype=r.rtype, rclass=r.rclass,
                    content=str(r.rdata), ttl=r.ttl, status=1) 
                for r in self.remote.query(request).rr
            ]
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
        record_ids_key = []
        for values in cache.get_many(
            [question_cname_key, question_record_key,]).values():
            record_ids_key.extend(["record:%s" % i for i in values])
        records = list(cache.get_many(record_ids_key).values())
        random.shuffle(records)
        return records

    def _set_cached_records(self, records, region):
        ids_map, records_map = {}, {}
        for record in records:
            question_record_key =  '{qname}:{qtype}:{qclass}:{zone}'.format(
                qname=record.full_subdomain,
                qtype=record.rtype,
                qclass=record.rclass,
                zone=region.zone if region else None,
            )
            if question_record_key not in ids_map:
                ids_map[question_record_key] = {"record_ids": [], 'ttl': 3600}
            ids_map[question_record_key]["record_ids"].append(record.pk)
            if ids_map[question_record_key]["ttl"] > record.ttl:
                ids_map[question_record_key]["ttl"] = record.ttl    
            records_map["record:%s" % record.pk] = record
        for key, value in ids_map.items():
            cache.set(key, value["record_ids"], value["ttl"])
        cache.set_many(records_map)

    def _get_records(self, questions, region):
        uncached_questions = []
        for question in questions:
            records = self._get_cached_records(question, region)
            if len(records) > 0:
                return records
            else:
                uncached_questions.append(question) 
        records = self._get_database_records(uncached_questions, region)
        self._set_cached_records(records, region)
        random.shuffle(records)
        return records

    def _query(self, questions, region, tracking_chain):
        if len(questions) == 0: return
        zone_list = []
        tracking_chain.extend(questions)
        records = list(self._get_records(questions, region))
        yield from records
        yield from self._recursive_query(
            questions, region, tracking_chain, records)

    def query(self, request, origin=None):
        tracking_chain = []  # Prevent infinite recursion
        region = self._get_or_set_cached_region(origin)
        records, checker_records = [], []
        for index, record in enumerate(self._query(
            request.questions, region, tracking_chain)):
            if index > settings.DNSKEY_MAXIMUM_QUERY_DEPTH:
                break
            if record.subdomain:
                checker_records.append(record)
            if record.status == 1:
                rr = RR.fromZone(
                        "{rr} {ttl} {rclass} {rtype} {rdata}".format(
                    rr=record.full_subdomain, ttl=record.ttl, 
                    rclass=CLASS.get(record.rclass),
                    rtype=QTYPE.get(record.rtype), rdata=record.content
                ))
                records.append(record)
                request.add_answer(*rr)
        if len(checker_records) > 0:
            query_records.send(
                sender=LocalQueryProxy, records=checker_records)
        return request