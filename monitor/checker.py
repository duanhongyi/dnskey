import ssl
import json
import time
import socket

from urllib.request import urlopen, Request
from django.core.cache import cache
from django.core import signals

from .helper import check_tcp, check_http

class BaseChecker(object):

    def __init__(self, record, monitor):
        self.record = record
        self.monitor = monitor

    def check(self):
        raise NotImplementedError
    
    def __call__(self):
        try:
            signals.request_started.send(sender='checker')
            last_checked_time = cache.get('last_checked_time', 0)
            if (time.time() - last_checked_time) < self.monitor.frequency \
                    or self.record.status == 2 \
                    or self.monitor.status == 2:
                return
            if not self.check():
                error_count =  cache.get_or_set(
                    'check_error_count:%s' % self.monitor.pk, 0)
                error_count = cache.incr(
                    'check_error_count:%s' % self.monitor.pk)
                if error_count > self.monitor.allowable_failure_times \
                        and self.record.status == 1:
                    self.record.status = 0
                    self.record.save()
            elif self.record.status == 0:
                self.record.status = 1
                self.record.save()
            cache.set('last_checked_time', time.time(), self.monitor.frequency)
        finally:
            signals.request_finished.send(sender='checker')


class TcpChecker(BaseChecker):

    def check(self):
        content = json.loads(self.monitor.content)
        host, port, timeout = (
            content['host'], content['port'], content.get('timeout', 30))
        return check_tcp(host, port, timeout)
        


class HttpChecker(BaseChecker):

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