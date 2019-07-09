#!/usr/bin/env python
#
# author = julienkaradayi

""" Take as input a .rttm file containing the output of a VAD system or 
    of a Speaker Diarization System, and output several metrics at different
    granularity (file level or speaker level.
    This script wraps several pyannote-metrics and pyannote-core functions.
"""

import os
import sys
import argparse
import pyannote
import pyannote-metrics

from pyannote.database.util import load_rttm
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.detection import DetectionErrorRate
from pyannote.metrics.diarization import DiarizationErrorRate




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
    reference = {item['uri']: item['annotated'] for item in items}

    # evaluate each wav referenced in system:
    # IF not vad:
    # for each label (FEM, MAL, CHI, KCHI), measure the time
    # in Correct/False alarm Speaker, False alarm Speech/Missed speaker/
    # Missed Speech



if __name__ == '__main__': 
    main()
