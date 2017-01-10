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
                self.interval_s = (self.recorder.chunk_size / self.recorder.fs)

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
                print ("Updating graphs every %.1f ms" % (self.interval_s*1000))
                while(True):
                    time.sleep(self.interval_s)
                    self.update()

            def update(self):
                data = self.recorder.get_buffer()
                weighting = np.exp(self.timeValues / self.timeValues[-1])
                Pxx = self.fft_buffer(weighting * data[:, 0])
                Pxx = np.log10(Pxx + 1)*20
                self.length = int(len(Pxx) / 1)
                pA, pB, pC = 0, 0, 0
                bass = self._piylights.parameters["upper_limit_bass"]
                mid = self._piylights.parameters["upper_limit_mid"]
                #print(int(round(bass * self.length)))
                #print(int(round(mid * self.length)))
                for element in Pxx[0: int(round(bass * self.length))]:
                    pA+=element
                for element in Pxx[int(round(bass * self.length)): int(round(mid * self.length))]:
                    pB+=element
                for element in Pxx[int(round(mid * self.length)): self.length]:
                    pC+=element
                self._piylights.update([pA, pB, pC])

                ##print(str(round(pA)) + "   #   " + str(round(pB)) + "   #   " + str(round(pC)))


        def __init__(self, piylights):
            # Setup recorder
            FS = 44100
            recorder = SoundCardDataSource(num_chunks=1, sampling_rate=FS, chunk_size=768)
            #WHAT tweak chunk size to make this shit faster

            win = self.LiveFFTWindow(recorder, piylights)
            self.interval_s = win.interval_s
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
        self.parameters = { "range_narrow_constant" : .000,\
                "active" : True,\
                "range_extend_linear" : .4,\
                "range_narrow_linear" : .005,\
                "colorchange_cooldown" : .1,\
                "next_color_step" : 1/6.0,\
                "upper_limit_bass" : 1/100.0,\
                "upper_limit_mid" : 1/10.0,\
                "extend_autorange_method" : "max", # "max", "linear"\
                "next_color_method" : "step",\
                "pp_minimal_difference" : 4.0,\
                "pp_minimal_difference_weight" : .42,\
                }
        self.lastchange = os.times()[4]
        self.lastcolor = (1, 0, 0)
        #self.channelthreshold = [ ( [0], 0.7 ), ( [1], 0.75 ), ( [2], 0.75), ( [0, 1, 2], 0.65 ) ] #0 bass 1 mid 2 treble
        self.channelthreshold = [ ( [0], 0.65 ) ] #0 bass 1 mid 2 treble
        self.triples = {"min" : [0] * 3, "max" : [10] * 3}
        self.colorswitch = 0 
        self._livefft = self.Livefft(self)
        self.updatesPerSecond = self._livefft.interval_s * 60
        self._server = self.ThreadedUDPServer(("localhost", port), self.UDPHandler)
        self._server.piylights = self
        server_thread = threading.Thread(target=self._server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def update(self, rgb):
        if not self.parameters["active"]:
            writeValues([0,0,0])
            return
        self.narrow_autorange(rgb)
        self.extend_autorange(rgb)
        self.post_process(rgb)
        processed = self.writeValues(self.raw(rgb))
        self.writeValues(self._method(processed))

    def raw(self, rgb):
        for i in range(3):
            rgb[i] = (rgb[i] - self.triples["min"][i]) \
                    / (self.triples["max"][i] - self.triples["min"][i])
            rgb[i] = 0 if rgb[i] < 0 else rgb[i]
            rgb[i] = 1 if rgb[i] > 1 else rgb[i]
        return rgb

    def extend_autorange(self, rgb):
        if self.parameters["extend_autorange_method"] is "max":
            for i in range(3):
                self.triples["min"][i] = min(self.triples["min"][i], rgb[i])
                self.triples["max"][i] = max(self.triples["max"][i], rgb[i]) + 0.000001
        elif self.parameters["extend_autorange_method"] is "linear": 
            for i in range(3):
                self.triples["min"][i] += (rgb[i] - self.triples["min"][i]) * self.parameters["range_extend_linear"] * self.updatesPerSecond if self.triples["min"][i] > rgb[i] else 0
                self.triples["max"][i] += (rgb[i] - self.triples["max"][i]) * self.parameters["range_extend_linear"] *self.updatesPerSecond if self.triples["max"][i] < rgb[i] else 0
        return rgb


    def narrow_autorange(self, rgb):
        for i in range(3):
            d = self.triples["max"][i] - self.triples["min"][i]
            self.triples["max"][i] -= self.parameters["range_narrow_linear"] * d * self.updatesPerSecond
            self.triples["max"][i] -= self.parameters["range_narrow_constant"] * self.updatesPerSecond
            self.triples["min"][i] += self.parameters["range_narrow_linear"] * d * self.updatesPerSecond
            self.triples["min"][i] += self.parameters["range_narrow_constant"] * self.updatesPerSecond
        return rgb

    def post_process(self, rgb):
        for i in range(3):
            d = self.parameters["pp_minimal_difference"] - (self.triples["max"][i] - self.triples["min"][i])
            if d > 0:
                w = self.parameters["pp_minimal_difference_weight"]
                self.triples["min"][i] -= d * w * self.updatesPerSecond
                self.triples["max"][i] += d * (1 - w) * self.updatesPerSecond



    def nextColor(self):
        if self.parameters["next_color_method"] is "random":
            return self.randomColor()
        elif self.parameters["next_color_method"] is "step":
            return self.stepColor()


    def randomColor(self):
        return colorsys.hsv_to_rgb(random.random(), 1, 1)
    
    def stepColor(self):
        self.colorswitch = 0 \
                if self.colorswitch >= 1 - (self.parameters["next_color_step"] + 0.0000001) else \
                self.colorswitch + self.parameters["next_color_step"]
        return colorsys.hsv_to_rgb(self.colorswitch, 1, 1)
    
    def changeWithChannel(self, rgb):
        if (os.times()[4] - self.lastchange) < self.parameters["colorchange_cooldown"]:
            return self.lastcolor
        self.lastchange = os.times()[4]

        for channels, threshold in self.channelthreshold:
            if (sum([rgb[i] for i in channels]) > (threshold * (len(channels)))):
                self.lastcolor = self.nextColor()
                return self.lastcolor
        return self.lastcolor


    def controlString(self, s):
        print(s)
        if (s == "quit"):
            print("quits called")
            quit()
            #todo make this work

    def writeValues(self, rgb):
        limit = 30
        scaled = list(map(lambda x: int(x * limit), rgb))
        for i in range(3):
            print(str(int(self.triples["min"][i])) + "][" + scaled[i] * "=" + (limit-scaled[i]) * " " + "][" + str(int(self.triples["max"][i])))
        print("\n")
        return rgb


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
