#!/usr/bin/env python
#
# author = julienkaradayi

""" Take as input a .rttm file containing the output of a VAD system or 
    of a Speaker Diarization System, and output several metrics at different
    granularity (file level or speaker level.
    This script wraps several pyannote-metrics and pyannote-core functions.
    The output is an ascii file with the following table filled out:
             ________________________________________________________________
            |        |              |               Reference                |
            |________|______________|________________________________________|
            |        |              | Speaker   | other speaker | no speaker |
            |________|______________|___________|_______________|____________|
            |        |   Speaker    | Correct   | F.A. speaker  | F.A. speech|
            |        |______________|___________|_______________|____________|
            | System | Other Speaker| M. speaker|    other      |   other    |
            |        |______________|___________|_______________|____________|
            |        |  No Speaker  | M. speech |    other      |   other    |
            |________|______________|___________|_______________|____________|

"""

import os
import sys
import ipdb
import numpy
import argparse
import pyannote
import pyannote.metrics

from collections import defaultdict
from pyannote.database import get_protocol
from speaker_info_per_file import vad_no_ovl
from pyannote.database.util import load_rttm
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.detection import DetectionErrorRate
from pyannote.metrics.diarization import DiarizationErrorRate

def get_mapping(reference, system):
    """ get speaker mapping between system and reference"""

    metric = DiarizationErrorRate()
    mapping = metric.optimal_mapping(reference, system)

    return mapping

def get_speech_duration(annot, uri):
    """ return the speech duration (counting overlapping segments only once)

    """
    #if uri == 'namibia_uebn_20161112_19980':
    #    ipdb.set_trace()
    timeline = annot.get_timeline()
    dur = 0
    prev_on = timeline[0][0]
    prev_off = timeline[0][1]
    for i, (on, off) in enumerate(timeline):
        if on > prev_off: 
            dur += prev_off - prev_on
            prev_on = on
            prev_off = off
        elif on < prev_off and off > prev_off:
            prev_off = off
            if i == len(timeline) - 1:
                dur += prev_off - prev_on
        elif i == len(timeline) - 1 and off <= prev_off:
            dur += prev_off - prev_on
    return dur


def accumulate_reference(r_labels, s_labels, mapping, dur):
    """ Using the mapping, fill the first column of the results table"""
    correct = defaultdict(int)
    miss_spk = defaultdict(int)
    miss_speech = defaultdict(int)

    for r_spk in r_labels: 
        for s_spk in s_labels:
            r_label = r_labels[r_spk]
            s_label = s_labels[s_spk]
            # iterate on segments in common in reference and system
            for r, s in r_label.co_iter(s_label):
                if ((mapping == None) 
                    or (s_spk in mapping 
                        and r_spk == mapping[s_spk])): 
                    correct[r_spk] += (r & s).duration
                else:
                    miss_spk[r_spk] += (r & s).duration
            # iterate on segments in common in reference and system_silences
            for r, s_ in r_label.co_iter(s_label.gaps()):
                miss_speech[r_spk] += (r & s_).duration

            correct[r_spk] = correct[r_spk] / dur
            miss_spk[r_spk] = miss_spk[r_spk] / dur
            miss_speech[r_spk] = miss_speech[r_spk] / dur
    return correct, miss_spk, miss_speech

def  accumulate_system(r_labels, s_labels, mapping, dur):
    """ Using the mapping, fill the first row of the results table"""
    correct = defaultdict(int)
    FA_spk = defaultdict(int)
    FA_speech = defaultdict(int)

    for r_spk in r_labels: 
        for s_spk in s_labels:
            r_label = r_labels[r_spk]
            s_label = s_labels[s_spk]
            # iterate on segments in common in reference and system
            for s, r in s_label.co_iter(r_label):
                if ((mapping == None)
                    or (s_spk in mapping 
                        and r_spk == mapping[s_spk])):
                    correct[r_spk] += (s & r).duration
                else:
                    FA_spk[r_spk] += (s & r).duration
            # iterate on segments in common in reference and system_silences
            for s, r_ in s_label.co_iter(r_label.gaps()):
                FA_speech[r_spk] += (s & r_).duration

            correct[r_spk] = correct[r_spk] / dur
            FA_spk[r_spk] = FA_spk[r_spk] / dur
            FA_speech[r_spk] = FA_speech[r_spk] / dur


    return correct, FA_spk, FA_speech

def write_evaluation(results, vad):
    ''' Write the results in a table reporting the time spent in 
        each of the following cell:
             ________________________________________________________________
            |        |              |               Reference                |
            |________|______________|________________________________________|
            |        |              | Speaker   | other speaker | no speaker |
            |________|______________|___________|_______________|____________|
            |        |   Speaker    | Correct   | F.A. speaker  | F.A. speech|
            |        |______________|___________|_______________|____________|
            | System | Other Speaker| M. speaker|    other      |   other    |
            |        |______________|___________|_______________|____________|
            |        |  No Speaker  | M. speech |    other      |   other    |
            |________|______________|___________|_______________|____________|
    '''
    for uri in results:
        with open('{}_perSpk.txt'.format(uri), 'w') as fout:
            correct, FA_spk, FA_spch, miss_spk, miss_spch = results[uri]
            for spk in correct: 
                if vad:
                    FA_spk[spk] = numpy.nan
                    miss_spk[spk] = numpy.nan
                fout.write('ID|Ref|System|Duration\n'
                           '{ID}|speaker|speaker|{sp_sp}\n'
                           '{ID}|speaker|other-speaker|{sp_osp}\n'
                           '{ID}|speaker|no-speaker|{sp_nosp}\n'
                           '{ID}|other-speaker|speaker|{osp_sp}\n'
                           '{ID}|other-speaker|other-speaker|{osp_osp}\n'
                           '{ID}|other-speaker|no-speaker|{osp_nosp}\n'.format(
                           ID=spk, sp_sp=correct[spk], sp_osp=miss_spk[spk],
                           sp_nosp=miss_spch[spk], osp_sp=FA_spk[spk],
                           osp_osp='NA', osp_nosp='NA'))
                            
def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('system', type=str,
                           help='Path to the system\'s output')
    argparser.add_argument('protocol', type=str,
                           help='The protocol on which you want to evaluate'
                                 'your system')
    argparser.add_argument('subset', type=str,
                           help='The subset of the database on which you want'
                                 'to evaluate your system.\n'
                                 'Choose between [train, test, development].\n'
                                 'Default is test.')
    argparser.add_argument('--vad', action='store_false', 
                           help='(OPTIONNAL) Enable if Evaluation a VAD system'
                                ', this way only speech/non speech metrics '
                                'will be reported.')

    args = argparser.parse_args()

    # Create timeline for both reference & system
    system = load_rttm(args.system)
    #system_sils = system.get_timeline().gaps()
    #system_spch = system.get_timeline()

    # get Reference using Pyannote Protocol
    protocol = get_protocol(args.protocol)

    items = list(getattr(protocol, args.subset)())
    reference = {item['uri']: item['annotation'] for item in items}
    
    results = dict()
    for uri in reference: 
        # preffix r: reference
        # prefix s: system
        r_annot = reference[uri]
        # In case the uri was not evaluated, skip this one and go to the next
        try:
            s_annot = system[uri]
        except:
            continue

        r_labels = {lab: r_annot.label_timeline(lab) for lab in r_annot.labels()}
        s_labels = {lab: s_annot.label_timeline(lab) for lab in s_annot.labels()}
        
        if not args.vad:
            mapping = get_mapping(r_annot, s_annot)
        else:
            mapping = None
        
        # accumulate results, reference side
        dur = get_speech_duration(r_annot, uri)
        print(uri)
        print(dur)
        correct, miss_spk, miss_speech = accumulate_reference(r_labels, s_labels, mapping, dur)
        
        # Both "correct" should be the same
        _, FA_spk, FA_speech = accumulate_system(r_labels, s_labels, mapping, dur)

        results[uri] = (correct, FA_spk, FA_speech, miss_spk, miss_speech)
    # evaluate each wav referenced in system:
    # IF not vad:
    # for each label (FEM, MAL, CHI, KCHI), measure the time
    # in Correct/False alarm Speaker, False alarm Speech/Missed speaker/
    # Missed Speech
    write_evaluation(results, args.vad)


if __name__ == '__main__': 
    main()
