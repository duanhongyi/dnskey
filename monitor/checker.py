import ssl
import json
import socket

from urllib.request import urlopen, Request
from django.core.cache import cache
from django.core import signals

from .icmp import ping
from .models import Monitor

class BaseChecker(object):

    def __init__(self, monitor_id):
        self.monitor_id = monitor_id

    def _get_monitor(self):
        return cache.get_or_set(
            'monitor:%s' % self.monitor_id,
            Monitor.objects.get(pk=self.monitor_id),
        )

    def _get_record(self):
        monitor = self._get_monitor()
        return cache.get_or_set(
            'record:%s' % monitor.record_id,
            monitor.record,
        )
    
    def check(self, monitor):
        raise NotImplementedError
    
    def __call__(self):
        try:
            signals.request_started.send(sender='checker')
            record = self._get_record()
            monitor = self._get_monitor()
            if record.status == 2 or monitor.status == 2:
                return
            if not self.check(monitor):
                error_count =  cache.get_or_set(
                    'check_error_count:%s' % self.monitor_id, 0)
                cache.incr('check_error_count:%s' % self.monitor_id)
                if error_count > allowable_failure_times \
                        and record.status == 1:
                    record.status = 0
                    record.save()
            elif record.status == 0:
                record.status = 1
                record.save()
        finally:
            signals.request_finished.send(sender='checker')


class TcpChecker(object):

    def check(self, monitor):
        content = json.loads(monitor.content)
        host, port, timeout = (
            content['host'], content['port'], content['timeout'])
        try:
            addrinfo = socket.getaddrinfo(
                host, port, 0,0,socket.SOL_TCP)[0][-1]
            if len(addrinfo) == 2:  # ipv4
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            else:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0) 
            sock.settimeout(timeout)
            return sock.connect_ex(addrinfo[0], addrinfo[1]) == 0
        except socket.error as e:
            logger.debug(e)
        return False


class HttpChecker(object):

    def check(self, monitor):
        content = json.loads(monitor.content)
        url, method, data, headers, timeout = (
            content["url"],
            content["method"]
            content["data"],
            content["headers"],
            content["timeout"]
        )

        no_check_ssl_context = ssl.create_default_context()
        no_check_ssl_context.check_hostname=False
        no_check_ssl_context.verify_mode=ssl.CERT_NONE
        request = Request(url, data, headers)
        request.get_method = lambda : method
        try
            response = urlopen(
                request, timeout=timeout, context=no_check_ssl_context)
            return 200 <= response.status < 300
        except urllib.error.URLError as e:
            logger.debug(e)
        return False