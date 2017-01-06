#!/usr/bin/env python3
import os
import random
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
import colorsys

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
                bass = 1/100
                mid = 1/10
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
        self._method = self.changeWithChannel
        self._limitmethod = self.percentAutorange
        self._colormethod = self.nextColor
        self.lastchange = os.times()[4]
        self.lastcolor = (1, 0, 0)
        #self.channelthreshold = [ ( [0], 0.7 ), ( [1], 0.75 ), ( [2], 0.75), ( [0, 1, 2], 0.65 ) ] #0 bass 1 mid 2 treble
        self.channelthreshold = [ ( [0], 0.65 ) ] #0 bass 1 mid 2 treble
        self.cooldown = .1 # seconds to wait before changing again
        self.minimal = [100000] * 3
        self.maximal = [-100000] * 3
        self.triples = {"min" : self.minimal, "max" : self.maximal}
        self.rgb = (0, 0, 0)
        self.colorswitch = 0 
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
        self.rgb = [r, g, b]
        for i in range(3):
            self.triples["min"][i] = min(self.triples["min"][i], self.rgb[i])
            self.triples["max"][i] = max(self.triples["max"][i], self.rgb[i]) + 0.000001
        for i in range(3):
            self.rgb[i] = (self.rgb[i] - self.triples["min"][i]) \
                    / (self.triples["max"][i] - self.triples["min"][i])

    def linearAutorange(self, r, g, b):
        linearFactor = 0.005
        for i in range(3):
            self.triples["max"][i] -= linearFactor
            self.triples["min"][i] += linearFactor
        self.raw(r, g, b)

    def percentAutorange(self, r, g, b):
        percent = 0.0006
        for i in range(3):
            self.triples["max"][i] *= (1 - percent)
            self.triples["min"][i] *= (1 + percent)
        self.raw(r, g, b)

    def randomColor(self):
        return colorsys.hsv_to_rgb(random.random(), 1, 1)
    
    def nextColor(self):
        self.colorswitch = 0 if self.colorswitch >= 5/6 - 0.00001 else self.colorswitch + 1/6
        return colorsys.hsv_to_rgb(self.colorswitch, 1, 1)
    
    def changeWithChannel(self, r, g, b):
        self._limitmethod(r, g, b)
        self.writeValues()
        if (os.times()[4] - self.lastchange) < self.cooldown:
            self.rgb = self.lastcolor
            return
        self.lastchange = os.times()[4]

        for channels, threshold in self.channelthreshold:
            if (sum([self.rgb[i] for i in channels]) > (threshold * (len(channels)))):
                self.rgb = self._colormethod()
                self.lastcolor = self.rgb
                return
        self.rgb = self.lastcolor


    def controlString(self, s):
        print(s)
        if (s == "quit"):
            print("quits called")
            quit()
            #todo make this work

    def writeValues(self):
        limit = 30
        scaled = list(map(lambda x: int(x * limit), self.rgb))
        for i in range(3):
            print(str(int(self.triples["min"][i])) + "][" + scaled[i] * "=" + (limit-scaled[i]) * " " + "][" + str(int(self.triples["max"][i])))
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
