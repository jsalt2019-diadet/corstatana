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
import argparse
import pyannote
import pyannote-metrics

from collections import defaultdict
from pyannote.database.util import load_rttm
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.detection import DetectionErrorRate
from pyannote.metrics.diarization import DiarizationErrorRate

def get_mapping(system, reference):
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
            for r, h in r_label.co_iter(s_label):
                if r_spk == mapping[r_spk]:
                    correct[r_spk] += (r & h).duration
                else:
                    miss_spk[r_spk] += (r & h).duration
            # iterate on segments in common in reference and system_silences
            for r, h_ in reference.co_iter(s_label.gaps()):
                miss_speech[r_spk] += (r & h_).duration
    return correct, miss_spk, miss_speech
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
 
def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('system', type=str,
                           help='Path to the system\'s output')
    argparser.add_argument('protocol', type=str,
                           help='The protocol on which you want to evaluate
                                 your system')
    argparser.add_argument('subset', type=str,
                           help='The subset of the database on which you want
                                 to evaluate your system.\n
                                 Choose between [train, test, development].\n
                                 Default is test.')
    argparser.add_argument('--vad', action='store_false', 
                           help='(OPTIONNAL) Enable if Evaluation a VAD system'
                                ', this way only speech/non speech metrics '
                                'will be reported.')

    args = argparser.parse_args()

    # Create timeline for both reference & system
    system = load_rttm(args.system)
    system_sils = system.get_timeline().gaps()
    system_spch = system.get_timeline()

    # get Reference using Pyannote Protocol
    protocol = get_protocol(args.protocol)

    items = list(getattr(protocol, subset)())
    reference = {item['uri']: item['annotation'] for item in items}

    for uri in reference: 
        # preffix r: reference
        # prefix s: system
        r_annot = reference[uri]
        s_annot = system[uri]

        r_labels = {lab: r_annot.label_timeline[lab] for lab in r_annot.labels()}
        s_labels = {lab: s_annot.label_timeline[lab] for lab in s_annot.labels()}

        mapping = get_mapping(system, reference)
        
        # accumulate results, reference side
        correct, miss_spk, miss_speech = accumulate_reference(r_labels, s_labels, mapping)

    # evaluate each wav referenced in system:
    # IF not vad:
    # for each label (FEM, MAL, CHI, KCHI), measure the time
    # in Correct/False alarm Speaker, False alarm Speech/Missed speaker/
    # Missed Speech



if __name__ == '__main__': 
    main()
