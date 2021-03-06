#!/usr/bin/env python3

import socket
import socketserver
import threading

class TCPController:
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    class RequestHandler(socketserver.BaseRequestHandler):
        def handle(self):
            print("new connection from: " + str(self.client_address[0]))
            while True:
                self.data = self.request.recv(2048)
                if not self.data:
                    break
                self.data = str(self.data.strip(),'utf-8')
                ret = bytes(self.server.piylights.controlString(self.data), "utf-8")
                if ret != None:
                    self.request.sendall(ret)

    def __init__(self, port, piylights):
        self.server = self.ThreadedTCPServer(("localhost", port), self.RequestHandler)
        self.server.piylights = piylights
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def kill(self):
        self.server.socket.shutdown(socket.SHUT_RDWR)
        self.server.socket.close()
        self.server.server_close()
