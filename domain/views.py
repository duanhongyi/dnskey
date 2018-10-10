from dnslib.dns import DNSRecord, DNSQuestion
from django.shortcuts import render
from django.http import JsonResponse

from domain.query import LocalQueryProxy

# Create your views here.

def query(request):
    qname = request.GET.get('qname')
    qtype = int(request.GET.get('qtype', 1))
    qclass = int(request.GET.get('qclass', 1))
    origin = request.GET.get('origin', request.META.get(
        'HTTP_X_FORWARDED_FOR', request.META['REMOTE_ADDR']))
    return JsonResponse({
        "qname": qname,
        "qtype": qtype,
        "qclass": qclass,
        "rr":[
            {
                "rname": "%s" % r.rname,
                "rtype": r.rtype,
                "rclass": r.rclass,
                "rdata": "%s" % r.rdata,
                "ttl": r.ttl,
            }
            for r in LocalQueryProxy().query(DNSRecord(
                q=DNSQuestion(qname=qname, qtype=qtype, qclass=qclass)),
                origin).rr
        ]
    })