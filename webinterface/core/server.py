#!/usr/bin/env python3
import os, sys, inspect
script_path = os.path.dirname(os.path.abspath(__file__))
import random
from parser import Parser
from tcpcontroller import TCPController
RASPI = False
OUTPUT = False
OUTPUT_RAW = False
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
from config import Config

class Piylights:

    def controlStringHelp(self, s):
        ret = "commands:\n"
        for key in self.commands.keys():
            ret += self.commands[key][0] + "\n"
        return ret

    def controlStringGetparam(self, s):
        ret = "parameters:\n___________\n"
        for key in self.parameters.keys():
            ret += key + " : " + str(self.param[key]) + "\n"
        return ret

    def controlStringGetlimit(self, s):
        ret = "limits:\n___________\n"
        for key in self.limits.keys():
            ret += key + " : " + str(self.limit[key]) + "\n"
        return ret

    def controlStringShutdown(self, s):
        return self.shutdown()

    def setParam(self, p, key):
        if p in list(self.parameters.keys()):
            if type(key) == type(self.param(p)):
                self.parameters[p]["value"] = key
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
        self.methods = {
                "raw" : lambda x: x, \
                "change_with_channel_step" : self.changeWithChannelStep,\
                "change_with_channel_random" : self.changeWithChannelRandom, \
                "change_with_time" : self.changeWithTime, \
                "do_nothing" : self.doNothing, \
                "single_color" : self.singleColor, \
                "strobe_with_time" : self.strobeWithTime, \
                }
        self.method_params = {
                        "strobe_with_time" : {\
                                "params" : {\
                                    "color0" : {
                                        "name" : "Color 1",\
                                        "type" : "color",\
                                        "description" : "Color 1",\
                                        "default" : "#000000"
                                    },\
                                    "color1" : {
                                        "name" : "Color 2",\
                                        "type" : "color",\
                                        "description" : "Color 2",\
                                        "default" : "#ffffff"
                                    },\
                                    "tick0" : {
                                        "name" : "#ticks 1",\
                                        "type" : "num",\
                                        "description" : "how many ticks is Color 1 displayed",\
                                        "default" : 4
                                    },\
                                    "tick1" : {
                                        "name" : "#ticks 2",\
                                        "type" : "num",\
                                        "description" : "how many ticks is Color 2 displayed",\
                                        "default" : 8
                                    },\
                                },
                                "displayName" : "Strobe two colors"
                            },\
                        "change_with_time" : {\
                                "params" : {\
                                    "color0" : {
                                        "name" : "Start Color",\
                                        "type" : "color",\
                                        "description" : "Color at the start of transition",\
                                        "default" : "#000000"
                                    },\
                                    "color1" : {
                                        "name" : "End Color",\
                                        "type" : "color",\
                                        "description" : "Color at the end of transition",\
                                        "default" : "#ffffff"
                                    },\
                                },
                                "displayName" : "Fade two colors"
                            },\

                        "single_color" : {\
                                "params" : {\
                                    "color" : {
                                        "name" : "Color",\
                                        "type" : "color",\
                                        "description" : "duh!",\
                                        "default" : "#00ff00"
                                    },\
                                },
                                "displayName" : "Single color"
                            },\

                        "change_with_channel_step" : {\
                                "params" : {\
                                    "colorchange_cooldown" : {
                                            "name" : "Cooldown in s/100",\
                                            "type" : "num",\
                                            "description" : "minimal time between color changes",\
                                            "default" : 25
                                        },\
                                },\
                                "displayName" : "Music cyclic colorchange"
                                },\

                        "do_nothing" : {\
                                "params" :{},\
                                "displayName" : "Do nothing"

                                },\

                }

        self.parameters = { # parameters to process input
                "active" : \
                        {"value": True, "limit" : [], "type" : "bool", "description":"global switch" },\
                "upper_limit_bass" : \
                    {"value": 1/100, "limit": [0,1], "type" : "num", "description" : "percentage in frequency range where bass stops and mids begin" },\
                "upper_limit_mid" : \
                    {"value": 1/10 , "limit": [0,1], "type" : "num", "description" : "percentage in frequency range where mids stop and treble begins" },\
                "range_narrow_constant" : \
                    {"value": .000, "limit": [0,10], "type" : "num", "description" : "the dynamic range is narrowed each tick by this constant" },\
                "range_extend_linear" : \
                    {"value": .4, "limit": [0,10], "type" : "num", "description" : "the dynamic range is widened by this percentage each tick if the loudness exceeds the current dynamic range" },\
                "range_narrow_linear" : \
                    {"value": .005, "limit": [0,40], "type" : "num", "description" : "the dynamic range is narrowed by this percentage if the loudness is in the dynamic range" },\
                "extend_autorange_method" : \
                    {"value": "max", "limit": ["max", "linear"] , "type" : "str", "description" : "max: dynamic range is always max(dynamic_range, current_loudness); linear: only extend by percentage (see other values *_linear)" },\
                "pp_minimal_difference" : \
                    {"value": [2.5, 2.5, 2.5], "limit": [0,100], "type" : "arr", "description" : "minimal wideness of dynamic range for each channel" },\
                "global_offset_percent" : \
                    {"value": [.25, .25, .25], "limit": [0,1], "type" : "arr", "description" : "loudness needs to cross this percentage to be considered for color production" },\
                "chain" : \
                    {"value": {"chainOptions": {"loop" : True, "mult" : 1}, "chain" : [(100, "change_with_time", {"color0" : "#000000", "color1": "#0000ff"})]}, "limit": [], "type" : "special", "description" : "chain of command..." },\
                }
        
        self.config = Config(script_path + "/config.json")
        if "+" in self.config.presets:
            self.parameters = self.config.loadPreset("+", self.parameters)


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
        self.htmlColors = {}
        self.channelthreshold = [ ( [0], 0.7 ), ( [1], 0.75 ), ( [2], 0.75), ( [0, 1, 2], 0.65 ) ] #0 bass 1 mid 2 treble
        #self.channelthreshold = [ ( [0], 0.65 ) ] #0 bass 1 mid 2 treble
        self.triples = {"min" : [0] * 3, "max" : [5] * 3}
        self.colorswitch = 0
        self.chainTicks = 0
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
        self.tcp_controller = TCPController(self.port, self)

    def param(self, name):
        return self.parameters[name]["value"]
    def limit(self, name):
        return self.parameters[name]["limit"]
    def loadPreset(self, name):
        self.parameters = self.config.loadPreset(name, self.parameters)
    def getPresets(self):
        return self.config.presets
    def storePreset(self, name, preset):
        return self.config.storePreset(name, preset)
    def deletePreset(self, name):
        return self.config.deletePreset(name)

    def htmlColorToRGB(self, htmlstring):
        if htmlstring in self.htmlColors.keys():
            return self.htmlColors[htmlstring]
        rgb=[0,0,0]
        for i in range(3):
            rgb[i] = int(htmlstring[1+i*2:1+(i+1)*2], 16) / 255.0
        self.htmlColors[htmlstring] = rgb
        return rgb

    def update(self, rgb):
        if not self.param("active"):
            self.writeValues([0,0,0])
            return
        rgb = list(map(self.preprocess_function, rgb))

        self.narrow_autorange(rgb)
        self.extend_autorange(rgb)
        self.post_process(rgb)
        raw = self.raw(rgb)
        #self.lastcolor = self.methods[self.param("active_method")](raw)
        self.lastcolor = self.operationChain(raw)
        if OUTPUT_RAW:
            self.printValues(raw)
        if not self.lastcolor is None:
            self.printValues(self.lastcolor)
            self.writeValues(self.lastcolor)

    def operationChain(self, rgb):
        s = 0
        for ticks, name, param in self.param("chain")["chain"]:
            s += ticks
        self.param("chain")["chainOptions"]["chainLength"] = s
        if not self.chainTicks == s - 1:
            self.chainTicks += 1
        elif self.param("chain")["chainOptions"]["loop"]:
            self.chainTicks = 0
        return self._getPosInChain(self.param("chain"), self.chainTicks, rgb)

    def _getPosInChain(self, chain, tick, rgb):
        chain = { "chainOptions" : {"loop" : True, "mult" : 1},
                    "chain" : [(100, "change_with_time", [[0,0,0],[1,0,0]])]
                }
        for totalTicks, name, params in self.param("chain")["chain"]:
            if tick >= totalTicks:
                tick -= totalTicks
            else:
                return self.methods[name](params, rgb, tick, totalTicks)

    def raw(self, rgb):
        res = rgb
        for i in range(3):
            res[i] = (rgb[i] - self.triples["min"][i]) \
                    / (self.triples["max"][i] - self.triples["min"][i])
            res[i] = 0 if res[i] < 0 else res[i]
            res[i] = 0 if res[i] < self.param("global_offset_percent")[i] * (self.triples["max"][i] - self.triples["min"][i]) else res[i]
            res[i] = 1 if res[i] > 1 else res[i]
        return res

    def extend_autorange(self, rgb):
        if self.param("extend_autorange_method") is "max":
            for i in range(3):
                self.triples["min"][i] = min(self.triples["min"][i], rgb[i])
                self.triples["max"][i] = max(self.triples["max"][i], rgb[i]) + 0.000001
        elif self.param("extend_autorange_method") is "linear": 
            for i in range(3):
                self.triples["min"][i] += (rgb[i] - self.triples["min"][i]) * self.param("range_extend_linear") * self.updatesPerSecond if self.triples["min"][i] > rgb[i] else 0
                self.triples["max"][i] += (rgb[i] - self.triples["max"][i]) * self.param("range_extend_linear") *self.updatesPerSecond if self.triples["max"][i] < rgb[i] else 0
        return rgb

    def narrow_autorange(self, rgb):
        if self.param("range_narrow_linear") != 0:
            linear = self.param("range_narrow_linear")
            for i in range(3):
                d = self.triples["max"][i] - self.triples["min"][i]
                self.triples["max"][i] -= linear * d * self.updatesPerSecond
                self.triples["min"][i] += linear * d * self.updatesPerSecond
        if self.param("range_narrow_constant") != 0:
            for i in range(3):
                constant = self.param("range_narrow_constant")
                self.triples["max"][i] -= constant * self.updatesPerSecond
                self.triples["min"][i] += constant * self.updatesPerSecond
        return rgb

    def post_process(self, rgb):
        for i in range(3):
            d = self.param("pp_minimal_difference")[i] - (self.triples["max"][i] - self.triples["min"][i])
            if d > 0:
                self.triples["max"][i] += d * self.updatesPerSecond

    def randomColor(self):
        return colorsys.hsv_to_rgb(random.random(), 1, 1)
    
    def stepColor(self, step):
        self.colorswitch = 0 \
                if self.colorswitch >= 1 - (step + 0.0000001) else \
                self.colorswitch + step
        return colorsys.hsv_to_rgb(self.colorswitch, 1, 1)

    def changeWithChannelRandom(self, params, rgb, tick, totalTicks):
        if self._changeColorCheck(rgb, params):
            return self.randomColor()
        return self.lastcolor
    
    def changeWithChannelStep(self, params, rgb, tick, totalTicks):
        if self._changeColorCheck(rgb, params):
            return self.stepColor(params["next_color_step"])
        return self.lastcolor

    def _changeColorCheck(self, rgb, params):
        if (os.times()[4] - self.lastchange) < (params["colorchange_cooldown"] / 100):
            return False
        self.lastchange = os.times()[4]

        for channels, threshold in self.channelthreshold:
            if (sum([rgb[i] for i in channels]) > (threshold * (len(channels)))):
                return True
        return False

    def doNothing(self, params, rgb, tick, totalTicks):
        return self.lastcolor
    
    def changeWithTime(self, params, rgb, tick, totalTicks):
        res=[0,0,0]
        percentage = tick / totalTicks
        start = self.htmlColorToRGB(params["color0"])
        end = self.htmlColorToRGB(params["color1"])

        for i in range(3):
            res[i] += start[i] + percentage * (end[i] - start[i])
        return res

    def singleColor(self, params, rgb, tick, totalTicks):
        return self.htmlColorToRGB(params["color"])

    def strobeWithTime(self, params, rgb, tick, totalTicks): #ignored for the time...
        t0 = params["tick0"]
        t1 = params["tick1"]
        if (tick - 0) % (t0 + t1) < t0:
            return self.htmlColorToRGB(params["color0"])
        return self.htmlColorToRGB(params["color1"])

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

    def shutdown(self):
        self._livefft.win.kill()
        self.tcp_controller.kill()
        self.config.storeCurrentAndWrite(self.parameters)
        print("shutting down core")
        quit()

if __name__ == "__main__":
    _piylights = Piylights()
    while(True):
        time.sleep(10)

