from obspy import Stream
from pandas import DataFrame
import matplotlib.pyplot as pyplot
import numpy


def check(waveforms: Stream, plotted=False, a=2.7, b=10):
    raw = waveforms.traces[0]
    raw_nam = raw.stats.station
    raw_srt = raw.stats.sampling_rate
    try:
        raw.detrend(type="demean")
        raw.detrend(type="linear")
        tim = raw.times()
        dta = raw.data

        win = int(raw_srt) * 30  # Window!
        ofs = win // 2  # Window offset!
        dta_dno = DataFrame(dta).rolling(window=win).mean()[0].values  # Denoised signal!
        dta_dna = numpy.abs(dta_dno)  # Denoised and absolute-ed signal!
        dta_dnt = numpy.median(numpy.abs(dta)) * a  # Threshold for this signal!
        dst = (dta_dna > dta_dnt).any()  # Are there any distortions?

        dta_dfo = DataFrame(dta_dno).diff()[0].values  # `dta_dfo[0] = nan`.
        dta_dfa = numpy.abs(dta_dfo)
        dta_dft = numpy.median(numpy.abs(dta_dfo[win:])) * b
        shi = (dta_dfa > dta_dft).any() and dst  # Are there any spikes?

        if plotted:
            fig, axi = pyplot.subplots(3, figsize=(18, 9))
            axi[0].plot(tim, dta, lw=.5, color="red" if shi else "blue")
            axi[0].plot(tim[:-ofs], dta_dno[ofs:], lw=1, color="black")
            axi[1].plot(tim[:-ofs], dta_dna[ofs:], lw=1, color="red" if shi else "blue")
            axi[1].plot(tim, dta_dnt * numpy.ones(dta.size), lw=1, color="black")
            axi[2].plot(tim[:-ofs], dta_dfa[ofs:], lw=.5, color="red" if shi else "blue")
            axi[2].plot(tim, dta_dft * numpy.ones(dta.size), lw=1, color="black")
            fig.suptitle(f"Differences: {raw_nam}")
            pyplot.show()
        else:
            return shi
    except Exception as e:
        print(str(e))
