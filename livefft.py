#!/usr/bin/env python2

from __future__ import division

import numpy as np
from scipy.signal import filtfilt
from numpy import nonzero, diff

from recorder import SoundCardDataSource
import threading
import time


# Based on function from numpy 1.8
def rfftfreq(n, d=1.0):
    """
    Return the Discrete Fourier Transform sample frequencies
    (for usage with rfft, irfft).

    The returned float array `f` contains the frequency bin centers in cycles
    per unit of the sample spacing (with zero at the start). For instance, if
    the sample spacing is in seconds, then the frequency unit is cycles/second.

    Given a window length `n` and a sample spacing `d`::

    f = [0, 1, ..., n/2-1, n/2] / (d*n) if n is even
    f = [0, 1, ..., (n-1)/2-1, (n-1)/2] / (d*n) if n is odd

    Unlike `fftfreq` (but like `scipy.fftpack.rfftfreq`)
    the Nyquist frequency component is considered to be positive.

    Parameters
    ----------
    n : int
    Window length.
    d : scalar, optional
    Sample spacing (inverse of the sampling rate). Defaults to 1.

    Returns
    -------
    f : ndarray
    Array of length ``n//2 + 1`` containing the sample frequencies.
    """
    if not isinstance(n, int):
        raise ValueError("n should be an integer")
    val = 1.0/(n*d)
    N = n//2 + 1
    results = np.arange(0, N, dtype=int)
    return results * val


def fft_slices(x):
    Nslices, Npts = x.shape
    window = np.hanning(Npts)

    # Calculate FFT
    fx = np.fft.rfft(window[np.newaxis, :] * x, axis=1)

    # Convert to normalised PSD
    Pxx = abs(fx)**2 / (np.abs(window)**2).sum()

    # Scale for one-sided (excluding DC and Nyquist frequencies)
    Pxx[:, 1:-1] *= 2

    # And scale by frequency to get a result in (dB/Hz)
    # Pxx /= Fs
    return Pxx ** 0.5


def find_peaks(Pxx):
    # filter parameters
    b, a = [0.01], [1, -0.99]
    Pxx_smooth = filtfilt(b, a, abs(Pxx))
    peakedness = abs(Pxx) / Pxx_smooth

    # find peaky regions which are separated by more than 10 samples
    peaky_regions = nonzero(peakedness > 1)[0]
    edge_indices = nonzero(diff(peaky_regions) > 10)[0]  # RH edges of peaks
    edges = [0] + [(peaky_regions[i] + 5) for i in edge_indices]
    if len(edges) < 2:
        edges += [len(Pxx) - 1]

    peaks = []
    for i in range(len(edges) - 1):
        j, k = edges[i], edges[i+1]
        peaks.append(j + np.argmax(peakedness[j:k]))
    return peaks


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
        self.logScale = True
        self.showPeaks = False

        self.timeValues = self.recorder.timeValues
        self.freqValues = rfftfreq(len(self.timeValues), 1./self.recorder.fs)


    def run(self):
        interval_s = (self.recorder.chunk_size / self.recorder.fs)
        print ("Updating graphs every %.1f ms" % (interval_s*1000))
        while(True):
            time.sleep(interval_s)
            self.update()

    def resetRanges(self):
        self.timeValues = self.recorder.timeValues
        self.freqValues = rfftfreq(len(self.timeValues), 1./self.recorder.fs)


    def update(self):
        data = self.recorder.get_buffer()
        weighting = np.exp(self.timeValues / self.timeValues[-1])
        Pxx = fft_buffer(weighting * data[:, 0])
        Pxx = np.log10(Pxx + 1)
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

        #vvvvvv this is what we want!!!!
        #self.spec.setData(x=self.freqValues, y=(20*np.log10(Pxx) if self.logScale else Pxx))
        

    def keyPressEvent(self, event):
        text = event.text()
        if text == "l":
            self.logScale = not self.logScale
            self.resetRanges()
        elif text == "+":
            self.recorder.num_chunks *= 2
            self.resetRanges()
        elif text == "-":
            self.recorder.num_chunks /= 2
            self.resetRanges()
        else:
            super(LiveFFTWindow, self).keyPressEvent(event)

# Setup recorder
#FS = 12000
#FS = 22000
FS = 44100
recorder = SoundCardDataSource(num_chunks=1,
                               sampling_rate=FS,
                               chunk_size=4096)
#WHAT tweak chunk size to make this shit faster
win = LiveFFTWindow(recorder)

if __name__ == '__main__':
    import sys
    win.start()
