import time
import numpy as np
from recorder import SoundCardDataSource
import threading

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
            bands = [0, 0, 0]
            bass = int(round( self.length * self._piylights.parameters["upper_limit_bass"]))
            mid = int(round(self.length * self._piylights.parameters["upper_limit_mid"]))
            intervals = [0, bass, mid, self.length]
            for i in range(3):
                for element in Pxx[intervals[i] : intervals[i+1]]:
                    bands[i] += element
            self._piylights.update(bands)


    def __init__(self, piylights):
        # Setup recorder
        FS = 44100
        recorder = SoundCardDataSource(num_chunks=1, sampling_rate=FS, chunk_size=441)
        #chunk size set for updates every 10ms

        win = self.LiveFFTWindow(recorder, piylights)
        self.interval_s = win.interval_s
        win.daemon = True
        win.start()
