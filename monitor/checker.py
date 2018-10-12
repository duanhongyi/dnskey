import os
import ssl
import json
import time
import socket
import hashlib


from urllib.request import urlopen, Request
from dnslib.dns import QTYPE, CLASS
from django.core.cache import cache
from django.core import signals
from django.core.mail import send_mail

from .helper import check_tcp, check_http

class BaseChecker(object):

    name = "UNKNOWN"

    def __init__(self, record, monitor):
        self.record = record
        self.monitor = monitor

    def check(self):
        raise NotImplementedError

    def check_alive(self):
        last_checked_time = cache.get('last_checked_time', 0)
        if (time.time() - last_checked_time) < self.monitor.frequency \
                or self.record.status == 2 or self.monitor.status == 2:
            return
        ok, status = self.check()
        subject = "Record %s: %s" % (ok, self.record.full_subdomain)
        message = "%s status: %s" % (self.name, status)
        if not ok:
            error_count =  cache.get_or_set(
                'check_error_count:%s' % self.monitor.pk, 0)
            error_count = cache.incr('check_error_count:%s' % self.monitor.pk)
            if error_count > self.monitor.allowable_failure_times \
                    and self.record.status == 1:
                self.send_mail(subject, message)
                self.record.status = 0
                self.record.save()
                self.send_mail(subject, message)
        elif self.record.status == 0:
            self.send_mail(subject, message)
            self.record.status = 1
            self.record.save()
            self.send_mail(subject, message)
        cache.set('last_checked_time', time.time(), self.monitor.frequency)
        return ok
        
    def check_recent_query_times(self):
        if self.record.recent_query_times < \
                self.monitor.recent_query_times_threshold:
            return True
        subject = "Record frequent query: %s" % self.record.full_subdomain
        message = os.linesep.join([
            "recent_query_times: %s" % self.record.recent_query_times,
            "recent_query_times_threshold: %s" % \
                    self.monitor.recent_query_times_threshold
        ])
        self.send_mail(subject, message)
        return False
    
    def send_mail(self, subject, message=None):
        record_message = os.linesep.join([
            "%s: %s" % (key, value)
            for key, value in { \
                "id": self.record.pk,
                "region": self.record.region_name,
                "subdomain": self.record.full_subdomain,
                "rtype": QTYPE.get(self.record.rtype),
                "rclass": CLASS.get(self.record.rclass),
                "rdata": self.record.content,
            }.items()
        ])
        message = os.linesep.join([record_message, message or ""])
        md5 = hashlib.md5()
        md5.update(subject + message)
        mail_id = md5.hexdigest()
        mail_interval = cache.get_or_set("mail_interval:%s" % mail_id,
                time.time(), settings.DNSKEY_EMAIL_INTERVAL)
        if (time.time() - mail_interval) > settings.DNSKEY_EMAIL_INTERVAL:
            recipient_list = [user.email for user in \
                    self.record.domain.operators.all() if user.email]
            send_mail(subject, message, from_email=None,
                recipient_list=recipient_list, fail_silently=False)

    def __call__(self):
        try:
            signals.request_started.send(sender='checker')
            if self.check_alive():
                self.check_recent_query_times()
        finally:
            signals.request_finished.send(sender='checker')


class TcpChecker(BaseChecker):

    name = "TCP"

    def check(self):
        content = json.loads(self.monitor.content)
        host, port, timeout = (
            content['host'], content['port'], content.get('timeout', 30))
        return check_tcp(host, port, timeout)
        


class HttpChecker(BaseChecker):

    name = "HTTP"

    def check(self):
        content = json.loads(self.monitor.content)
        url, method, data, headers, timeout = (
            content["url"],
            content.get("method", "GET"),
            content.get("data", None),
            content.get("headers", {}),
            content.get("timeout", 30),
        )
        return check_http(url, method, data, headers, timeout)