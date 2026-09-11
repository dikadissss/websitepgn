import sys
import pandas as pd
from obspy import UTCDateTime
from datetime import datetime, timedelta
from obspy.clients.fdsn import Client
import matplotlib.pyplot as plt
import os
import shifts3

class CheckingSignal(object):
    def __init__(self):
        self.blank = []
        self.gaps = []
        self.spikes = []
    
    def run(self):
        station = pd.read_csv('/home/sysop/bin/template.txt', delim_whitespace=True, header=None)
        
        client = Client(
            "https://geof.bmkg.go.id",
            user=,
            password=
        )

        now = datetime.now()
        # now = UTCDateTime("2025-02-10 06:00:00.304302")
        t0 = UTCDateTime(now - timedelta(hours=7, minutes=30))
        t1 = UTCDateTime(now - timedelta(hours=7))

        for index, row in station.iterrows():
            print(row[0], row[1], row[2], row[3])
            try:
                if row[2] == "Null":
                    st = client.get_waveforms(row[0], row[1], "", row[3], t0, t1)
                else:
                    st = client.get_waveforms(row[0], row[1], row[2], row[3], t0, t1)
            except:
                self.blank.append(row[1])
                continue

            if st.get_gaps():
                self.gaps.append(row[1])

            # script_directory = os.path.dirname(os.path.abspath(__file__))
            # fld = f"{script_directory}/shifts/{now}"
            # if not os.path.exists(fld):
            #     os.makedirs(fld, exist_ok=True)
            if shifts3.check(st) and not st.get_gaps():
                self.spikes.append(row[1])
                # fig = st.plot(outfile=f"{fld}/{row[1]}.png")
                # plt.close(fig)

        txt = f"Update {datetime.now()}\n\n"
        txt += "Blank\n"
        for item in self.blank:
            txt += "%s\n" % item

        txt += "\nGaps\n"
        for item in self.gaps:
            txt += "%s\n" % item

        txt += "\nSpikes\n"
        for item in self.spikes:
            txt += "%s\n" % item

        file = open("/home/sysop/current/www/checklist.txt", "w")
        file.write(txt)
        file.close()

        file = open("/home/sysop/Fajar/ebast/cl_seiscomp/static/cl_seiscomp/checklist.txt", "w")
        file.write(txt)
        file.close()

        return True

def main():
    app = CheckingSignal()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
