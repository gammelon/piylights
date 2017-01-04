#!/usr/bin/env python3
import os
RASPI = False
if "arm" in os.uname():
    RASPI = True
if RASPI:
    import RPi.GPIO as gp 
import time
import socket
import socketserver as SocketServer
import sys
import threading
import numpy as np
from numpy import nonzero, diff
from recorder import SoundCardDataSource
import threading
import time

class Piylights:

    class Livefft:

        class LiveFFTWindow(threading.Thread):

            def __init__(self, recorder, piylights):
                super().__init__()
                self.recorder = recorder
                self._piylights = piylights
                self.timeValues = self.recorder.timeValues

            def fft_buffer(self, x):
                window = np.hanning(x.shape[0])

                # Calculate FFT
                fx = np.fft.rfft(window * x)

                # Convert to normalised PSD
                Pxx = abs(fx)**2 / (np.abs(window)**2).sum()

                # Scale for one-sided (excluding DC and Nyquist frequencies)
                Pxx[1:-1] *= 2

                # And scale by frequency to get a result in (dB/Hz)
                # Pxx /= Fs
                return Pxx ** 0.5

            def run(self):
                interval_s = (self.recorder.chunk_size / self.recorder.fs)
                print ("Updating graphs every %.1f ms" % (interval_s*1000))
                while(True):
                    time.sleep(interval_s)
                    self.update()

            def update(self):
                data = self.recorder.get_buffer()
                weighting = np.exp(self.timeValues / self.timeValues[-1])
                Pxx = self.fft_buffer(weighting * data[:, 0])
                Pxx = np.log10(Pxx + 1)*20
                self.length = int(len(Pxx) / 1)
                pA, pB, pC = 0, 0, 0
                bass = 1/50
                mid = 1/4
                for element in Pxx[0: int(round(bass * self.length))]:
                    pA+=element
                for element in Pxx[int(round(bass * self.length)): int(round(mid * self.length))]:
                    pB+=element
                for element in Pxx[int(round(mid * self.length)): self.length]:
                    pC+=element
                self._piylights.update(pA, pB, pC)

                #print(str(round(pA)) + "   #   " + str(round(pB)) + "   #   " + str(round(pC)))


        def __init__(self, piylights):
            # Setup recorder
            FS = 44100
            recorder = SoundCardDataSource(num_chunks=1, sampling_rate=FS, chunk_size=256)
            #WHAT tweak chunk size to make this shit faster

            win = self.LiveFFTWindow(recorder, piylights)
            win.daemon = True
            win.start()



    class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
        pass

    class UDPHandler(SocketServer.BaseRequestHandler):
        def handle(self):
            self.data = self.request[0].strip()
            self.data = str(self.data,'utf-8')
            self.server.piylights.controlString(self.data)

    
    def __init__(self, port):
        self._method = self.linearAutorange
        self.maxR = self.maxG = self.maxB = -99999
        self.minR = self.minG = self.minB = -self.maxR
        self._livefft = self.Livefft(self)
        self._server = self.ThreadedUDPServer(("localhost", port), self.UDPHandler)
        self._server.piylights = self
        server_thread = threading.Thread(target=self._server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def update(self, r, g, b):
        self._method(r, g, b)
        self.writeValues()

    def raw(self, r, g, b):
        self.maxR = max(r, self.maxR)
        self.minR = min(r, self.minR) - 0.00001 #avoid max-min = 0
        self.maxG = max(g, self.maxG)
        self.minG = min(g, self.minG) - 0.00001
        self.maxB = max(b, self.maxB)
        self.minB = min(b, self.minB) - 0.00001
        self.r = (r - self.minR) / (self.maxR - self.minR)
        self.g = (g - self.minG) / (self.maxG - self.minG)
        self.b = (b - self.minB) / (self.maxB - self.minB)

    def linearAutorange(self, r, g, b):
        linearFactor = 0.005
        self.maxR -= linearFactor
        self.maxG -= linearFactor
        self.maxB -= linearFactor
        self.minR += linearFactor
        self.minG += linearFactor
        self.minB += linearFactor
        self.raw(r, g, b)
        self.r = (r - self.minR) / (self.maxR - self.minR)
        self.g = (g - self.minG) / (self.maxG - self.minG)
        self.b = (b - self.minB) / (self.maxB - self.minB)

    def percentAutorange(self, r, g, b):
        percent = 0.0006
        self.maxR *= (1 - percent)
        self.maxG *= (1 - percent)
        self.maxB *= (1 - percent)
        self.minR *= (1 + percent)
        self.minG *= (1 + percent)
        self.minB *= (1 + percent)
        self.raw(r, g, b)
        self.r = (r - self.minR) / (self.maxR - self.minR)
        self.g = (g - self.minG) / (self.maxG - self.minG)
        self.b = (b - self.minB) / (self.maxB - self.minB)
    
    def controlString(self, s):
        print(s)
        if (s == "quit"):
            print("quits called")
            quit()
            #todo make this work

    def writeValues(self):
        limit = 30 
        r = int(self.r * limit)
        g = int(self.g * limit)
        b = int(self.b * limit)
        print(str(int(self.minR)) + "]R[" + r * "=" + (limit-r) * " " + "][" + str(int(self.maxR)))
        print(str(int(self.minG)) + "]G[" + g * "=" + (limit-g) * " " + "][" + str(int(self.maxG)))
        print(str(int(self.minB)) + "]B[" + b * "=" + (limit-b) * " " + "][" + str(int(self.maxB)))
        print("\n")


def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((ip, port))
    try:
        sock.sendall(b"test")
    finally:
        sock.close()

if __name__ == "__main__":
    _piylights = Piylights(12345)
    client("localhost", 12345, "heyo")
    input("")
