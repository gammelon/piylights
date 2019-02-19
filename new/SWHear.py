"""
this is a stripped down version of the SWHear class.
It's designed to hold only a single audio sample in memory.
check my githib for a more complete version:
    http://github.com/swharden
"""

import math
import socket
import time
import threading
import numpy as np
import pyaudio
import yappi

def getFFT(data,rate):
    """Given some data and rate, returns FFTfreq and FFT (half)."""
    data=data*np.hamming(len(data))
    fft=np.fft.fft(data)
    fft=np.abs(fft)
    #fft=10*np.log10(fft)
    freq=np.fft.fftfreq(len(fft),1.0/rate)
    return freq[:int(len(freq)/2)],fft[:int(len(fft)/2)]

class SWHear():
    """
    The SWHear class is provides access to continuously recorded
    (and mathematically processed) microphone data.
    
    Arguments:
        
        device - the number of the sound card input to use. Leave blank
        to automatically detect one.
        
        rate - sample rate to use. Defaults to something supported.
        
        updatesPerSecond - how fast to record new data. Note that smaller
        numbers allow more data to be accessed and therefore high
        frequencies to be analyzed if using a FFT later
    """

    def __init__(self,device=None,rate=None,updatesPerSecond=10):
        self.p=pyaudio.PyAudio()
        self.chunk=4096 # gets replaced automatically
        self.updatesPerSecond=updatesPerSecond
        self.chunksRead=0
        self.device=device
        self.rate=rate

    ### SYSTEM TESTS

    def valid_low_rate(self,device):
        """set the rate to the lowest supported audio rate."""
        for testrate in [44100]:
            if self.valid_test(device,testrate):
                return testrate
        print("SOMETHING'S WRONG! I can't figure out how to use DEV",device)
        return None

    def valid_test(self,device,rate=44100):
        """given a device ID and a rate, return TRUE/False if it's valid."""
        try:
            self.info=self.p.get_device_info_by_index(device)
            if not self.info["maxInputChannels"]>0:
                return False
            stream=self.p.open(format=pyaudio.paInt16,channels=1,
               input_device_index=device,frames_per_buffer=self.chunk,
               rate=int(self.info["defaultSampleRate"]),input=True)
            stream.close()
            return True
        except:
            return False

    def valid_input_devices(self):
        """
        See which devices can be opened for microphone input.
        call this when no PyAudio object is loaded.
        """
        mics=[]
        for device in range(self.p.get_device_count()):
            if self.valid_test(device):
                mics.append(device)
        if len(mics)==0:
            print("no microphone devices found!")
        else:
            print("found %d microphone devices: %s"%(len(mics),mics))
        return mics

    ### SETUP AND SHUTDOWN

    def initiate(self):
        """run this after changing settings (like rate) before recording"""
        if self.device is None:
            self.device=self.valid_input_devices()[0] #pick the first one
        if self.rate is None:
            self.rate=self.valid_low_rate(self.device)
        self.chunk = int(self.rate/self.updatesPerSecond) # hold one tenth of a second in memory
        log = np.log2(self.chunk)
        self.lim_a = int(pow(2,(1/3 * log)))
        self.lim_b = int(pow(2,(2/3 * log)))
        #  self.alpha = 0.5
        #  self.beta = 0.5
        #  self.level = [0, 0, 0]
        #  self.trend = [0, 0, 0]
        self.max = [0, 0, 0]
        self.mavg = [0, 0, 0]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = ('localhost', 15300)

        if not self.valid_test(self.device,self.rate):
            print("guessing a valid microphone device/rate...")
            self.device=self.valid_input_devices()[0] #pick the first one
            self.rate=self.valid_low_rate(self.device)
        self.datax=np.arange(self.chunk)/float(self.rate)
        msg='recording from "%s" '%self.info["name"]
        msg+='(device %d) '%self.device
        msg+='at %d Hz'%self.rate
        print(msg)

    def close(self):
        """gently detach from things."""
        print(" -- sending stream termination command...")
        self.keepRecording=False #the threads should self-close
        while(self.t.isAlive()): #wait for all threads to close
            time.sleep(.1)
        self.stream.stop_stream()
        self.p.terminate()

    ### STREAM HANDLING

    def stream_readchunk(self):
        """reads some audio and re-launches itself"""
        try:
            self.data = np.fromstring(self.stream.read(self.chunk),dtype=np.int16)
            self.fftx, self.fft = getFFT(self.data,self.rate)
            fft_sum = sum(self.fft[:self.lim_a]), sum(self.fft[self.lim_a:self.lim_b]), sum(self.fft[self.lim_b:])

            factor = 0.000000005
            # h = 20
            N = 64
            # mavg_factor = 0.8
            # level, trend = [0,0,0], [0,0,0]
            value = [0] * 3
            for i, x in enumerate(fft_sum):
                self.mavg[i] = -self.mavg[i] / N + x / N
                #level[i] = self.alpha * x + (1-self.alpha)*(self.level[i] + self.trend[i])
                #trend[i] = self.beta * (level[i] - self.level[i]) + (1-self.beta) * self.trend[i]
                #self.level[i] = level[i]
                #self.trend[i] = trend[i]
                # print(d)
                value[i] = max( min((x - self.mavg[i]) * factor, 1), 0)
                self.max[i] = max(self.max[i], value[i])
                # print(self.max[i])

                # print('#' * int(value[i] *100))
            bytes_value = bytearray().join([b'\x99'] + [int(v * 65535).to_bytes(2, byteorder='big', signed=False) for v in value])
            # print(value)
            # print(bytes_value)

            # print(bytes_value)
            self.sock.sendto(bytes_value, self.address)


        except Exception as E:
            print(" -- exception! terminating...")
            print(E,"\n"*5)
            self.keepRecording=False
        if self.keepRecording:
            self.stream_thread_new()
        else:
            self.stream.close()
            self.p.terminate()
            print(" -- stream STOPPED")
        self.chunksRead+=1

    def stream_thread_new(self):
        self.t=threading.Thread(target=self.stream_readchunk)
        self.t.start()

    def stream_start(self):
        """adds data to self.data until termination signal"""
        self.initiate()
        print(" -- starting stream")
        self.keepRecording=True # set this to False later to terminate stream
        self.data=None # will fill up with threaded recording data
        self.fft=None
        self.dataFiltered=None #same
        self.stream=self.p.open(format=pyaudio.paInt16,channels=1,
                      rate=self.rate,input=True,frames_per_buffer=self.chunk)
        self.stream_thread_new()

if __name__=="__main__":
    ear=SWHear(updatesPerSecond=10) # optinoally set sample rate here
    yappi.start()
    ear.stream_start() #goes forever
    try:
        while(True):
            time.sleep(1)
    except KeyboardInterrupt:
        yappi.get_func_stats().print_all()
    #  lastRead=ear.chunksRead
    #  while True:
    #      while lastRead==ear.chunksRead:
    #          time.sleep(.01)
    #      print(ear.chunksRead,len(ear.data))
    #      lastRead=ear.chunksRead
    #  print("DONE")
