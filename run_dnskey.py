from gevent import monkey
monkey.patch_all()
import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import sys
import getopt
import threading

from gevent.pywsgi import WSGIServer as BaseWSGIServer

from dnskey.wsgi import application
from dnskey.server import DNSKeyServer

class WSGIServer(BaseWSGIServer):

    def serve_forever(self):
        self.start_accepting()
        self._stop_event.wait()


def get_http_server():
    addr, port = '::', 8080
    opts, _ = getopt.getopt(sys.argv[1:], "b:")
    for opt, value in opts:
        if opt == '-b':
            addr, port = value.rsplit(":", 1)
    server = WSGIServer((addr, int(port)), application)
    server.backlog = 256
    server.max_accept = 30000
    server.start()
    return server


if __name__ == '__main__':
    server = DNSKeyServer()
    server.add_server(get_http_server())
    [worker.join() for worker in server.serve()]