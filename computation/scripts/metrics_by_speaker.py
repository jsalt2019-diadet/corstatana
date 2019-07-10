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
import argparse
import pyannote
import pyannote.metrics

from collections import defaultdict
from pyannote.database import get_protocol
from pyannote.database.util import load_rttm
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.detection import DetectionErrorRate
from pyannote.metrics.diarization import DiarizationErrorRate

def get_mapping(reference, system):
    """ get speaker mapping between system and reference"""

    metric = DiarizationErrorRate()
    mapping = metric.optimal_mapping(reference, system)

    return mapping

def accumulate_reference(r_labels, s_labels, mapping):
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
                if s_spk in mapping and r_spk == mapping[s_spk]:
                    correct[r_spk] += (r & s).duration
                else:
                    miss_spk[r_spk] += (r & s).duration
            # iterate on segments in common in reference and system_silences
            for r, s_ in r_label.co_iter(s_label.gaps()):
                miss_speech[r_spk] += (r & s_).duration
    return correct, miss_spk, miss_speech

def  accumulate_system(r_labels, s_labels, mapping):
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
                if s_spk in mapping and r_spk == mapping[s_spk]:
                    correct[r_spk] += (s & r).duration
                else:
                    FA_spk[r_spk] += (s & r).duration
            # iterate on segments in common in reference and system_silences
            for s, r_ in s_label.co_iter(r_label.gaps()):
                FA_speech[r_spk] += (s & r_).duration


    return correct, FA_spk, FA_speech

def write_evaluation(results):
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
    print('been there')
    for uri in results:
        print('done that {}'.format(uri))
        with open('{}_perSpk.txt', 'w') as fout:
            correct, FA_spk, FA_spch, miss_spk, miss_spch = results[uri]
            for spk in correct: 
                fout.write('{}:'
                          ' ________________________________________________________________ \n' 
                          '|        |              |               Reference                |\n'
                          '|________|______________|________________________________________|\n'
                          '|        |              | Speaker   | other speaker | no speaker |\n'
                          '|________|______________|___________|_______________|____________|\n'
                          '|        |   Speaker    | {:.4f}   | {:.4f}  | {:.4f} |\n'
                          '|        |______________|___________|_______________|____________|\n'
                          '| System | Other Speaker| {:.4f}|    NA      |   NA    |\n'
                          '|        |______________|___________|_______________|____________|\n'
                          '|        |  No Speaker  | {:.4f} |    NA      |   NA    |\n'
                          '|________|______________|___________|_______________|____________|\n'.format(spk, correct[spk], FA_spk[spk],
                              FA_spch[spk], miss_spk[spk], miss_spch[spk]))
                          

 
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
        s_annot = system[uri]

        r_labels = {lab: r_annot.label_timeline(lab) for lab in r_annot.labels()}
        s_labels = {lab: s_annot.label_timeline(lab) for lab in s_annot.labels()}

        mapping = get_mapping(r_annot, s_annot)
        
        # accumulate results, reference side
        correct, miss_spk, miss_speech = accumulate_reference(r_labels, s_labels, mapping)
        
        # Both "correct" should be the same
        _, FA_spk, FA_speech = accumulate_system(r_labels, s_labels, mapping)

        results[uri] = (correct, FA_spk, FA_speech, miss_spk, miss_speech)
    # evaluate each wav referenced in system:
    # IF not vad:
    # for each label (FEM, MAL, CHI, KCHI), measure the time
    # in Correct/False alarm Speaker, False alarm Speech/Missed speaker/
    # Missed Speech
    write_evaluation(results)


if __name__ == '__main__': 
    main()
