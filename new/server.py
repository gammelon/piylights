#!/usr/bin/env python3
RASPI = True
from socketserver import ThreadingUDPServer, BaseRequestHandler
import time
if RASPI:
    import pigpio
PORT = 15300
PWM_FREQUENCY = 100
PWM_RANGE = 500
LED_CHANNELS_BROADCOM = [18, 23, 24, 25]


class PiylightsUDPServer:

    class MyServer(ThreadingUDPServer):
        def __init__(self, server_address, RequestHandlerClass, data_ex):
            ThreadingUDPServer.__init__(self, server_address, RequestHandlerClass)
            self.data_ex = data_ex
            self.data_ex['avg-interval'] = 0
            self.data_ex['tick'] = 0

    class RequestHandler(BaseRequestHandler):

        def handle(self):
            interval = time.time()
            alpha = .85
            self.server.data_ex['avg-interval'] *= alpha
            self.server.data_ex['avg-interval'] -= (1-alpha) * interval

            self.server.data_ex['tick'] = (self.server.data_ex['tick'] + 1) % 10
            if self.server.data_ex['tick'] == 0:
                print(self.server.data_ex['tick'])


            data = self.request[0]
            socket = self.request[1]
            if data[0] == 0x99:
                pwm_bytes = [data[1:3], data[3:5], data[5:7]]
                pwm_percentage = [int.from_bytes(b, byteorder='big', signed=False) / 65535 for b in pwm_bytes]
                pwm_duty = [PWM_RANGE * p for p in pwm_percentage]
                #print(pwm_bytes)
                # print(pwm_percentage)
                if RASPI:
                    for i in range(3):
                        self.server.data_ex['pig'].set_PWM_dutycycle(LED_CHANNELS_BROADCOM[i+1], pwm_duty[i])

    def __init__(self):
        if RASPI:
            self.pig = pigpio.pi()
            for c in LED_CHANNELS_BROADCOM:
                self.pig.set_mode(c, pigpio.OUTPUT)
            for c in LED_CHANNELS_BROADCOM[1:]:
                self.pig.set_PWM_range(c, PWM_RANGE)
                self.pig.set_PWM_frequency(c, PWM_FREQUENCY)
            self.pig.write(LED_CHANNELS_BROADCOM[0], 0)

        try:
            self.pig
        except:
            self.pig = None
        self.data_ex = {}
        self.data_ex['pig'] = self.pig

        with self.MyServer(('0.0.0.0', PORT), self.RequestHandler, self.data_ex) as server:
            server.serve_forever()

if __name__ == "__main__":
    PiylightsUDPServer()

