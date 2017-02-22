#!/usr/bin/env python3
import os, sys, inspect

import random
from parser import Parser
from tcpcontroller import TCPController
RASPI = False
OUTPUT = False
OUTPUT_RAW = True
if "arm" in os.uname()[4]:
    RASPI = True
    OUTPUT = False
    OUTPUT_RAW = False
#OUTPUT = False
if RASPI:
    import RPi.GPIO as gp 
import time
import threading
import math
import time
import colorsys
from livefft import Livefft

class Piylights:

    def controlStringHelp(self, s):
        ret = "commands:\n"
        for key in self.commands.keys():
            ret += self.commands[key][0] + "\n"
        return ret

    def controlStringGetparam(self, s):
        ret = "parameters:\n___________\n"
        for key in self.parameters.keys():
            ret += key + " : " + str(self.parameters[key]) + "\n"
        return ret

    def controlStringGetlimit(self, s):
        ret = "limits:\n___________\n"
        for key in self.limits.keys():
            ret += key + " : " + str(self.limits[key]) + "\n"
        return ret

    def controlStringShutdown(self, s):
        return self.shutdown()

    def setParam(self, p, key):
        if p in list(self.parameters.keys()):
            if type(key) == type(self.parameters[p]):
                self.parameters[p] = key
                return True
        else:
            return False

    def controlStringSetparam(self, s):
        if len(s) < 3:
            return "not enough arguments"
        res = self.setParam(s[1], s[2])
        if res:
            return "SUCCESS: changed parameter " + p
        else:
            return "FAILURE: parameter " + p + " not present in configuration"

    def __init__(self):
        self.port = 12345
        self.parameters = { # parameters to process input
                "active" : "True",\
                "upper_limit_bass" : 1/100.0,\
                "upper_limit_mid" : 1/10.0,\
                "range_narrow_constant" : .000,\
                "range_extend_linear" : .4,\
                "range_narrow_linear" : .005,\
                "extend_autorange_method" : "max", # "max", "linear"\
                "pp_minimal_difference" : [2.5, 2.5, 2.5],\
                # parameters to configure methods etc...\
                "active_method" : "change_with_channel_step",\
                "active_method" : "raw",\
                "colorchange_cooldown" : .1,\
                "next_color_step" : 1/6.0,\
                "global_offset_percent" : [.25, .25, .25],\
                }

        self.methods = {
                "raw" : lambda x: x, \
                "change_with_channel_step" : self.changeWithChannelStep, \
                "change_with_channel_random" : self.changeWithChannelRandom, \
                #"change_with_time" : self.changeWithTime, \
                #"single_color" : self.singleColor, \
                }

        self.limits = {
                "active" : ["True", "False"],\
                "upper_limit_bass" : [0, 1],\
                "upper_limit_mid" : [0, 1],\
                "range_narrow_constant" : [0, 10],\
                "range_extend_linear" : [0, 10],\
                "range_narrow_linear" : [0, 40],\
                "extend_autorange_method" : ["max", "linear"],\
                "pp_minimal_difference" : [0, 20],\
                # parameters to configure methods etc...\
                "active_method" : list(self.methods.keys()),\
                "colorchange_cooldown" : [0, 10],\
                "next_color_step" : [0, 1],\
                "global_offset_percent" : [0, 1],\
                }

        self.commands = {
                "help" : ("help - show help",\
                        self.controlStringHelp),\
                "setparam" : ("setparam [name] [value] - set value of parameter",\
                        self.controlStringSetparam),\
                "getparam" : ("getparam - get names and values of all parameters",\
                        self.controlStringGetparam),\
                "getlimit" : ("getlimit - get limits or possible values for each parameter",\
                        self.controlStringGetlimit),\
                "shutdown" : ("shutdown - stop piylights",\
                        self.controlStringShutdown),\
                }

        self.preprocess_function = lambda x: math.log(x + 1) #logarithmic scale
        #self.preprocess_function = lambda x: x #linear

        led_channels = [12, 16, 18, 22]

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
            gp.setup(led_channels, gp.OUT)
            gp.output(led_channels[0], gp.LOW)
            self.rpiOut = [
                    gp.PWM(led_channels[1],frequency), \
                    gp.PWM(led_channels[2],frequency), \
                    gp.PWM(led_channels[3],frequency)]
            for x in self.rpiOut:
                x.start(0)
        self._livefft = Livefft(self)
        self.updatesPerSecond = self._livefft.interval_s * 60
        tcp_controller = TCPController(self.port, self)

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
            res[i] = 0 if res[i] < self.parameters["global_offset_percent"][i] * (self.triples["max"][i] - self.triples["min"][i]) else res[i]
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
            d = self.parameters["pp_minimal_difference"][i] - (self.triples["max"][i] - self.triples["min"][i])
            if d > 0:
                self.triples["max"][i] += d * self.updatesPerSecond

    def randomColor(self):
        return colorsys.hsv_to_rgb(random.random(), 1, 1)
    
    def stepColor(self, step):
        self.colorswitch = 0 \
                if self.colorswitch >= 1 - (step + 0.0000001) else \
                self.colorswitch + step
        return colorsys.hsv_to_rgb(self.colorswitch, 1, 1)

    def changeWithChannelRandom(self, rgb):
        if self._changeColorCheck(self, rgb):
            self.lastcolor = self.randomColor()
        return self.lastcolor
    
    def changeWithChannelStep(self, rgb):
        if self._changeColorCheck(rgb):
            self.lastcolor = self.stepColor(self.parameters["next_color_step"])
        return self.lastcolor

    def _changeColorCheck(self, rgb):
        if (os.times()[4] - self.lastchange) < self.parameters["colorchange_cooldown"]:
            return False
        self.lastchange = os.times()[4]

        for channels, threshold in self.channelthreshold:
            if (sum([rgb[i] for i in channels]) > (threshold * (len(channels)))):
                return True
        return False
    
    def changeWithTime(self, startColor, endColor, percentage):
        res=[0,0,0]
        for i in range(3):
            res[i] += startColor[i] + percentage * (endColor[i] - startColor[i])
        return res

    #def setStrobeParam(self, frequency, dutyCycle):

    def resetStrobe(self):
        self.setStrobeParam(80, 1)

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

    def controlString(self, s):
        s = Parser.parse(s)
        if len(s) < 1:
            return
        for key in list(self.commands):
            if s[0] == key:
                return self.commands[key][1](s)
        return "command not recognized"

    def shutdown():
        _server.socket.shutdown(socket.SHUT_RDWR)
        _server.socket.close()
        _server.server_close()
        _livefft.win.kill()
        print("graceful shutdown")
        quit()

if __name__ == "__main__":
    _piylights = Piylights()
    while(True):
        time.sleep(10)

