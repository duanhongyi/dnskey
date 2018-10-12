import ssl
import logging
import socket

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from contextlib import closing

from django.conf import settings

logger = logging.getLogger(__name__)

def check_tcp(host, port, timeout):
    try:
        addrinfo = socket.getaddrinfo(
            host, port, 0,0,socket.SOL_TCP)[0][-1]
        if len(addrinfo) == 2:  # ipv4
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        else:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0) 
        sock.settimeout(timeout)
        with closing(sock):
           status = sock.connect((addrinfo[0], addrinfo[1]))
           return True, str(status)
    except (socket.timeout, socket.gaierror) as e:
        return False, str(e)

def check_http(url, method, data, headers, timeout):
    no_check_ssl_context = ssl.create_default_context()
    no_check_ssl_context.check_hostname=False
    no_check_ssl_context.verify_mode=ssl.CERT_NONE
    request = Request(url, data, headers)
    request.get_method = lambda : method
    try:
        with closing(urlopen(
            request, timeout=timeout, context=no_check_ssl_context
        )) as response:
            return 200 <= response.status < 300, str(response.status)
    except URLError as e:
        return False, str(e)
    except HTTPError as e:
        return False, str(e.status)