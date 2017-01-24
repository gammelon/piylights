#!/usr/bin/env python3
import os
import random
from parser import Parser
RASPI = False
OUTPUT = True
OUTPUT_RAW = True
if "arm" in os.uname()[4]:
    RASPI = True
    OUTPUT = False
    OUTPUT_RAW = False
#OUTPUT = False
if RASPI:
    import RPi.GPIO as gp 
import time
import socket
import socketserver
import threading
import math
import time
import colorsys
from livefft import Livefft

class Piylights:

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        pass

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

    def __init__(self, port):
        self.parameters = { # parameters to process input
                "active" : "True",\
                "led_channels" : [12, 16, 18, 22],\
                "upper_limit_bass" : 1/100.0,\
                "upper_limit_mid" : 1/10.0,\
                "range_narrow_constant" : .000,\
                "range_extend_linear" : .4,\
                "range_narrow_linear" : .005,\
                "extend_autorange_method" : "max", # "max", "linear"\
                "pp_minimal_difference" : 2.5,\
                "pp_minimal_difference_weight" : .42,\
                # parameters to configure methods etc...\
                "active_method" : "change_with_channel",\
                "colorchange_cooldown" : .1,\
                "next_color_step" : 1/6.0,\
                "next_color_method" : "step",\
                }
        self.methods = {
                "raw" : lambda x: x, \
                "change_with_channel" : self.changeWithChannel, \
                #"change_with_time" : self.changeWithTime, \
                #"single_color" : self.singleColor, \
                }
        self.preprocess_function = lambda x: math.log(x + 1) #logarithmic scale
        #self.preprocess_function = lambda x: x #linear


        self.lastchange = os.times()[4]
        self.lastcolor = (1, 0, 0)
        self.channelthreshold = [ ( [0], 0.7 ), ( [1], 0.75 ), ( [2], 0.75), ( [0, 1, 2], 0.65 ) ] #0 bass 1 mid 2 treble
        #self.channelthreshold = [ ( [0], 0.65 ) ] #0 bass 1 mid 2 treble
        self.triples = {"min" : [0] * 3, "max" : [5] * 3}
        self.colorswitch = 0
        frequency = 90
        if RASPI:
            print("detected raspi")
            gp.setmode(gp.BOARD)
            gp.setwarnings(False)
            gp.setup(self.parameters["led_channels"], gp.OUT)
            gp.output(self.parameters["led_channels"][0], gp.LOW)
            self.rpiOut = [gp.PWM(self.parameters["led_channels"][1],frequency), \
                    gp.PWM(self.parameters["led_channels"][2],frequency), \
                    gp.PWM(self.parameters["led_channels"][3],frequency)]
            for x in self.rpiOut:
                x.start(0)
        self._livefft = Livefft(self)
        self.updatesPerSecond = self._livefft.interval_s * 60
        self._server = self.ThreadedTCPServer(("localhost", port), self.RequestHandler)
        self._server.piylights = self
        server_thread = threading.Thread(target=self._server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def update(self, rgb):
        if self.parameters["active"] not in ["True", "true", "TRUE", "1", "+"]:
            self.writeValues([0,0,0])
            return
        rgb = list(map(self.preprocess_function, rgb))

        self.narrow_autorange(rgb)
        self.extend_autorange(rgb)
        self.post_process(rgb)
        raw = self.raw(rgb)
        processed = self.methods[self.parameters["active_method"]](raw)
        if OUTPUT_RAW:
            self.printValues(raw)
        self.printValues(processed)
        self.writeValues(processed)

    def raw(self, rgb):
        res = rgb
        for i in range(3):
            res[i] = (rgb[i] - self.triples["min"][i]) \
                    / (self.triples["max"][i] - self.triples["min"][i])
            res[i] = 0 if res[i] < 0 else res[i]
            res[i] = 1 if res[i] > 1 else res[i]
        return res

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
    
    #def changeWithTime(self):

    def writeValues(self, rgb):
        if RASPI:
            for x in range(3):
                self.rpiOut[x].ChangeDutyCycle(rgb[x]*100)
        return rgb

    def printValues(self, rgb):
        if OUTPUT:
            limit = 60
            scaled = list(map(lambda x: int(x * limit), rgb))
            for i in range(3):
                print(str(int(self.triples["min"][i])) + "][" + scaled[i] * "=" + (limit-scaled[i]) * " " + "][" + str(int(self.triples["max"][i])))
            print("\n")
        return rgb

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def controlString(self, s):
        s = Parser.parse(s)
        if len(s) < 1:
            return
        if s[0] == "setparam":
            if len(s) < 3:
                return
            if s[1] in list(self.parameters.keys()):
                if type(s[2]) == type(self.parameters[s[1]]):
                    self.parameters[s[1]] = s[2]
                    return "changed parameter"
        elif s[0] == "help":
            return "commands:\n" + \
                    "help - show help\n" + \
                    "getparam - get names and values of all parameters\n" + \
                    "setparam [name] [value] - set value of parameter\n" + \
                    "shutdown - stop piylights"
        elif s[0] == "getparam":
            print("getparam")
            s = "parameters:\n___________\n"
            for key in self.parameters.keys():
                s += key + " : " + str(self.parameters[key]) + "\n"
            return s
        elif s[0] == "shutdown":
            print("quits called")
            shutdown()
            return
        return "command not recognized"

def shutdown():
    _piylights._server.socket.shutdown(socket.SHUT_RDWR)
    _piylights._server.socket.close()
    _piylights._server.server_close()
    _piylights._livefft.win.kill()
    print("graceful shutdown")
    quit()

if __name__ == "__main__":
    _piylights = Piylights(12345)
    while True:
        time.sleep(10)
    #shutdown()
