#import RPi.GPIO as gp 
import time
import socket
import socketserver as SocketServer
import sys

class Piylights:

        class Livefft:
            def call(self):
                print("livefft called")

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
            #handler = self.UPDHandler(self._livefft, port)
            self._server = SocketServer.UDPServer(("localhost", port), self.UDPHandler)
            self._server._livefft = self._livefft
            self._server.serve_forever()

		

#def red(percentage):
	#set red thing









if __name__ == "__main__":
    channels = [2, 4, 6, 8, 10, 12]
    #gp.setmode(gp.BOARD)
    #gp.setup(channels, gp.OUT)
    #gp.output(channels,0)
    _piylights = Piylights(12345)
