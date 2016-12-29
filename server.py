#import RPi.GPIO as gp 
import time
import socket
import socketserver as SocketServer
import sys
import threading

class Piylights:

        class Livefft:
            def call(self):
                print("livefft called")

        class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
            pass

        class UDPHandler(SocketServer.BaseRequestHandler):

            def handle(self):
                self.data = self.request[0].strip()
                self.server._livefft.call()
                self.data = str(self.data,'utf-8')
                if (self.data == "quit"):
                    print("quits called")
                    quit()
                    #todo kill complete program
                print(str(self.data))
	
        def __init__(self, port):
            self._livefft = self.Livefft()
            self._server = self.ThreadedUDPServer(("localhost", port), self.UDPHandler)
            self._server._livefft = self._livefft
            server_thread = threading.Thread(target=self._server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((ip, port))
    try:
        sock.sendall(b"test")
    finally:
        sock.close()

if __name__ == "__main__":
    channels = [2, 4, 6, 8, 10, 12]
    #gp.setmode(gp.BOARD)
    #gp.setup(channels, gp.OUT)
    #gp.output(channels,0)
    _piylights = Piylights(12345)
    client("localhost", 12345, "heyo")
    client("localhost", 12345, "heyo")
    client("localhost", 12345, "heyo")
    client("localhost", 12345, "heyo")
    input("mhh")
