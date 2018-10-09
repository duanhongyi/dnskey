from gevent import monkey
monkey.patch_all()
import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import sys
import getopt
import socket
from gevent.pywsgi import WSGIServer

from dnskey.wsgi import application
from dnskey.server import DNSKeyServer

dns_server = DNSKeyServer()
dns_server.serve()

addr, port = '::', 8080
opts, _ = getopt.getopt(sys.argv[1:], "b:")
for opt, value in opts:
    if opt == '-b':
        addr, port = value.rsplit(":", 1)
server = WSGIServer((addr, int(port)), application)
server.backlog = 256
server.max_accept = 30000
server.serve_forever()
