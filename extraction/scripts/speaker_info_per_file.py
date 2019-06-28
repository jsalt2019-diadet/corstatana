#!/usr/bin/env python
#
# author= julien karadayi - CoML Team
#
""" Extract information about the type, quantity and quality of speech 
    from the databases used at the JSALT 2019 workshop.
    The input is a database $corpus formatted the following way:
        
        $corpus/
                [train|dev|test]/
                    gold/
                        *.rttm
                    wav/
                        *.wav

    The output is a csv with the following columns:
        
        file, key_child_age, clip_length, nb_diff_speakers, nb_children, 
        nb_fem_ad, nb_mal_ad, nb_uncertain, prop_ovl_speech, prop_nonovl_speech,
        avg_voc_dur, snr
"""

import io
import os
import sys
import sox
import ipdb
import wave
import argparse
import numpy as np
import scipy.io.wavfile

from spk_map import spk_map
from operator import itemgetter
from collections import defaultdict

# for debug
DEBUG = True

# BUGFIX FOR AMI
# from https://github.com/pyannote/pyannote-audio/issues/146#issuecomment-463657241
def normalize_wav(input_file, output_file):
    with wave.open(input_file, "rb") as r_wav, wave.open(output_file, "wb") as w_wav:
        w_wav.setparams(r_wav.getparams())
        w_wav.writeframes(r_wav.readframes(w_wav.getnframes()))

def parse_rttms(rttm):
    """ rttm format used by jsalt is tab separated, the columns are the following:
            SPEAKER file_name 1 onset duration <NA> <NA> label <NA>
        
        INPUT
        -----
            rttm: the path to the all_${SET}.rttm that contains all the annotations
                  of the set
        OUTPUT
        ------
            annot: a dict {file : [(onset, offset, label)]} where, for each file, 
                   the list is order by onsets and offsets
    """
    assert os.path.isfile(rttm), '{} does not exist! exiting...'.format(rttm)

    annot = defaultdict(list)
    with open(rttm, 'r') as fin:
        annotations = fin.readlines()

        for line in annotations:
            try:
                _, wav, _, onset, dur, _, _, label, _ = line.split()
            except:
                # some annotations are different 
                # TODO Look into, they should all be the same (not latest version ?)
                _, wav, _, onset, dur, _, _, label, _ , _= line.split()

            annot[wav].append((float(onset), float(onset) + float(dur), label))
    if DEBUG:
        for wav in annot:
            annot[wav] = sorted(annot[wav], key=itemgetter(0, 1))
            #if not annot[wav] == sorted(annot[wav], key=itemgetter(0, 1)):
            #    print("annotations for {} are not sorted, check out".format(wav))
            #    print(annot[wav])
            #    exit()
    return annot

def get_wav_len(annot, corpus_path, subset, info):
    """ for each wav file in the annotation get its duration """

    for wav in annot:
        wav_path = os.path.join(corpus_path,
                                subset, "wav",
                                "{}.wav".format(wav))

        # get wav duration w/ sox
        duration = sox.file_info.duration(wav_path)

        # update information dict
        info[wav].append(duration)

        # add SNR
        # Compute SNR as mean(wav) / std(wav)
        buff = io.BytesIO()
        normalize_wav(wav_path, buff)
        buff.seek(0)
        rate, sig = scipy.io.wavfile.read(buff)
        #sig = scipy.io.wavfile.read(wav_path)[1] # scipy return (sample_rate, array)
        m = sig.mean()
        sd = sig.std()

        info[wav].append(float(np.where(sd == 0, 0, m/sd)))
    return info

def count_labels(annot, info):
    """ gather quantity information about speakers for each file"""

    for wav in annot:
        labels = [spk_map[lab] for on, off, lab in annot[wav]]

        ##FOR DEBUG PURPOSE
        if DEBUG:
            print('different speaker for {} are'.format(wav))
            print(set(labels))
        
        # count number of children, femal adult, male adult, uncertain 
        CHIs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "CHI" or spk_map[lab] == "KCHI"]
        FAs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "FEM"]
        MAs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "MAL"]
        uncertains = [lab for on, off, lab in annot[wav] if spk_map[lab] == "SPEECH"]

        # append information about speaker for wav
        info[wav].append(len(set(labels))) ## number of speakers in total
        info[wav].append(len(set(CHIs))) ## number of children
        info[wav].append(len(set(FAs))) ## number of female adults
        info[wav].append(len(set(MAs))) ## number of male adults
        info[wav].append(len(set(uncertains))) ## number of uncertains
    return info

def measure_overlap(annot, info):
    """ Measure quantity of overlap speech in each wav. Uses the fact
        that the annotations are sorted for each wav."""

    
    for wav in annot:
       

        prev_on = -1
        prev_off= -1
        dur_ovl = 0
        dur_speech = 0
        all_vocs = []
        for on, off, _ in annot[wav]:
            # if current annotation starts before end of previous, add to
            # overlap duration
            if on <= prev_off:
                dur_ovl += prev_off - on

            dur_speech += off - on
            all_vocs.append(dur_speech)

            prev_on = on
            prev_off = off

        # get duration of non overlapping speech and compute ratios
        dur_nonovl = dur_speech - dur_ovl
        
        if dur_speech > 0:
            info[wav].append(dur_ovl/dur_speech) # ratio of overlap speech
            info[wav].append(dur_nonovl/dur_speech) # ratio of non overlapping speech
            info[wav].append(np.mean(all_vocs))

    return info

def write_info(corpus_name, subset, info):
    """ write output """

    with open(os.path.join('..','results',"{}_{}.csv".format(corpus_name, subset)), "w") as fout: 
        fout.write(u'file,key_child_age,clip_length,nb_diff_speakers,nb_children,nb_fem_ad,nb_mal_ad,nb_uncertain,prop_ovl_speech,prop_nonovl_speech,avg_voc_dur,snr\n')
        for wav in info:
            (dur, snr, n_spk, n_chi,
             n_fa, n_ma, n_unk, ovl,
             non_ovl, mean_voc) = info[wav]
            fout.write(u'{wav},,{dur:.2f},{n_spk},{chi}'
                    ',{f},{m},{u},{ovl:.2f},{novl:.2f},'
                    '{voc:.2f},{snr:.2f}\n'.format(wav=wav, dur=dur, n_spk=n_spk,
                                             chi=n_chi, f=n_fa, m=n_ma, u=n_unk,
                                             ovl=ovl, novl=non_ovl, voc=mean_voc,
                                             snr=snr))

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('corpus', type=str,
                        help='path to the corpus')
    args = parser.parse_args()

    # get name of corpus
    ## first do abspath to remove possible trailing /
    corpus_name = os.path.basename(os.path.abspath(args.corpus))

    ## for me, on oberon...
    if corpus_name == "BabyTrain_new": 
        corpus_name = "BabyTrain"

    corpus2rttm = {'CHiME5': 'allU01_{}.rttm',
                   'AMI': 'allMix-Headset_{}.rttm',
                   'BabyTrain': 'all_{}.rttm'}
    for subset in ['train', 'dev', 'test']:
        # read annotations
        rttm = os.path.join(args.corpus, subset,
                            corpus2rttm[corpus_name].format(subset))
        annot = parse_rttms(rttm)

        # get wav info
        info = defaultdict(list)
        info = get_wav_len(annot, args.corpus, subset, info)

        # get speakers info
        info =count_labels(annot, info)

        # measure overlap
        info = measure_overlap(annot, info)

        # write output
        write_info(corpus_name, subset, info)

if __name__ == '__main__': 
    main()
