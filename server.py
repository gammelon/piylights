import RPi.GPIO as gp 
import time
import socket
import sys

class Piylights:
	_server
	_livefft
	class Server:
		_livefft
		
		def __init__(self, livefft):
			self._livefft = livefft
	
	def __init__(self, port):
		
		 
class RequestHandler(SocketServer.BaseRequestHandler):
	def processData
	def handle(self):
		data = self.request.recv(128)
		self.request.close()

def red(percentage):
	#set red thing




channels = [2, 4, 6, 8, 10, 12]
gp.setmode(gp.BOARD)
gp.setup(channels, gp.OUT)
gp.output(channels,0)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('localhost', 12345))





if __name__ == "__main__":
	do_something()
