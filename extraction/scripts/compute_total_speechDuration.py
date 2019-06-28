import os
import sys
import numpy

fold = sys.argv[1]

dur_tot = 0
gaps = []

for annot in os.listdir(fold):
    with open(os.path.join(fold,annot), 'r') as fin: 
        rttm = fin.readlines()
        all_segments = []
        for line in rttm:
            try:
                _, _, _, on, dur, _, _, _, _ = line.split('\t')
            except:
                _, _, _, on, dur, _, _, _, _, _ = line.split(' ')

            all_segments.append((float(on), float(on) + float(dur)))
    
    prev_on = 0
    prev_off = 0
    last_off = 0
    no_overlap = []
    
    for i, (on, off) in enumerate(all_segments):    
        if on > prev_off:
            no_overlap.append((prev_on, prev_off))
            gaps.append((last_off, prev_on))
            last_off = prev_off
            dur_tot += prev_off - prev_on 
            prev_on = on
            prev_off = off
        elif on <= prev_on:
            prev_on = on
            prev_off = max(off, prev_off)
        else:
            prev_off = off
 
print("total speech duration is of {} hours".format(dur_tot/3600))

gaps_dur = [b - a for a,b in gaps[1:]]

print("mean gap duration is {} seconds, variance is {}, max is {}, min is {}, sum is {}".format(numpy.mean(gaps_dur), 
                                                               numpy.var(gaps_dur),
                                                               numpy.min(gaps_dur),
                                                               numpy.max(gaps_dur),
                                                               numpy.sum(gaps_dur)/(3600*dur_tot)))
