#!/usr/bin/env python3

import numpy as np
from numpy import nonzero, diff

from recorder import SoundCardDataSource
import threading
import time


def fft_buffer(x):
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


class LiveFFTWindow(threading.Thread):
    def __init__(self, recorder):
        super(LiveFFTWindow, self).__init__()
        self.recorder = recorder
        self.timeValues = self.recorder.timeValues

    def run(self):
        interval_s = (self.recorder.chunk_size / self.recorder.fs)
        print ("Updating graphs every %.1f ms" % (interval_s*1000))
        while(True):
            time.sleep(interval_s)
            self.update()

    def update(self):
        data = self.recorder.get_buffer()
        weighting = np.exp(self.timeValues / self.timeValues[-1])
        Pxx = fft_buffer(weighting * data[:, 0])
        Pxx = np.log10(Pxx + 1)*20
        self.length = int(len(Pxx) / 1)
        #print (self.length)
        pA, pB, pC = 0, 0, 0
        for element in Pxx[0: int(round(1/3 * self.length))]:
            pA+=element
        for element in Pxx[int(round(1/3 * self.length)): int(round(2/3 * self.length))]:
            pB+=element
        for element in Pxx[int(round(2/3 * self.length)): self.length]:
            pC+=element

        print(str(round(pA)) + "   #   " + str(round(pB)) + "   #   " + str(round(pC)))

# Setup recorder
FS = 44100
recorder = SoundCardDataSource(num_chunks=1,
                               sampling_rate=FS,
                               chunk_size=256)
#WHAT tweak chunk size to make this shit faster

if __name__ == '__main__':
    import sys
    win = LiveFFTWindow(recorder)
    win.daemon = True
    win.start()
    input("")
