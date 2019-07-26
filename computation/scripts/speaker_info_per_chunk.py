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

import os
import ipdb
import time
import argparse
import numpy as np
import intervaltree
import scipy.io.wavfile

from collections import defaultdict
from speaker_info_per_file import rms


def get_intervals(rttm):
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
    intervals = defaultdict(intervaltree.IntervalTree)
    with open(rttm, 'r') as fin:
        annotations = fin.readlines()

        for line in annotations:
            #tree = intervaltree.IntervalTree()

            try:
                _, wav, _, onset, dur, _, _, label, _ = line.split()
            except:
                # some annotations are different 
                # TODO Look into, they should all be the same (not latest version ?)
                _, wav, _, onset, dur, _, _, label, _ , _= line.split()

            if float(dur) > 0:
                intervals[wav].addi(float(onset), float(onset) + float(dur), label)

    # merge overlaps between segments to get simple VAD
    for wav in intervals:
        intervals[wav].merge_overlaps(data_reducer=lambda x,y: "%%".join([x, y]))

    return intervals

def chunk_SNR(intervals, corpus_path, subset, chunk_dur):
    """
        Cut speech segments in chunk_dur segments and compute SNR on those.
        For each chunk_dur chunk output SNR Value
    """

    corpus_snr = defaultdict(list)

    for wav in intervals:
        # load wav
        wav_path = os.path.join(corpus_path,
                            subset, "wav",
                            "{}.wav".format(wav))

        # read wav and get framerate w/ scipy
        frate, wav_sig = scipy.io.wavfile.read(wav_path)

        # get wav duration
        dur = len(wav_sig) / float(frate)

        # manage onsets and offsets in seconds
        for onset in np.arange(0, dur, chunk_dur):
            offset = onset + chunk_dur
            
            # get all labels occuring between onset and offset + silences
            ovls = intervals[wav].overlap(onset, offset)
            prev_on = onset
            prev_off = onset
            chunk_labels = []
            sils = []
            spch = []

            # get silences occuring in the examined chunk
            for interval in ovls: 
                ov_on, ov_off, ov_lab = interval
                spch.append((ov_on, ov_off))
                if ov_on > prev_on:
                    sils.append((prev_on, ov_on))
                prev_on = ov_on
                prev_off = ov_off

                # keep track of all labels speaker in current chunk
                chunk_labels += ov_lab.split('%%')
            else:
                if prev_off < offset:
                    sils.append((prev_off, min(offset, dur)))
        
            # if the chunk doesn't contain speech or silence, juste put "NA" as SNR value
            try:
                sil_idxs = np.concatenate([np.arange(int(frate * on), int(frate * off)-1) for on, off in sils])
            except:
                corpus_snr[wav].append((onset, offset, chunk_labels, 'NA'))
                continue
            try:
                spch_idxs = np.concatenate([np.arange(int(frate * on), int(frate * off)-1) for on, off in spch])
            except:
                corpus_snr[wav].append((onset, offset, chunk_labels, 0))
                continue

            sil_wav = wav_sig[sil_idxs]
            try:
                spch_wav = wav_sig[spch_idxs]
            except:
                # TODO: shouldn't happen, bad annotations ? to be checked..
                ipdb.set_trace()
                spch_wav = wav_sig[spch_idxs[spch_idxs < len(wav_sig)]]

            chunk_snr = rms(spch_wav) / rms(sil_wav) if (len(sil_wav) > 0 and len(spch_wav) > 0) else "NA"
            corpus_snr[wav].append((onset, offset, chunk_labels, chunk_snr))

    return corpus_snr

def read_uem(uem):
    '''for each wav get beginning and end with uem file'''
    with open(uem, 'r') as fin:
        uem_dict = {line.split()[0]: (float(line.split()[2]), float(line.split()[3])) for line in fin.readlines()}
    return uem_dict

def get_silences(rttm, uem):
    """ return interval tree of silences"""
    # Assume merged overlaps
    sils = defaultdict(intervaltree.IntervalTree)
    for wav in uem:
        beg, end = uem[wav]
        prev_on = beg
        prev_off = beg
        for interval in rttm[wav].iter():
            on, off, _ = interval
            if on > prev_on:
                sils[wav].addi(prev_on, on)
            prev_on = on
            prev_off = off
        else:
            if prev_off < end: 
                sils[wav].addi(prev_off, end)
    return sils


def miss_FA_per_chunk(ref_tree, sys_tree, ref_sil_tree, sys_sil_tree, chunk_dur, uem):
    ''' Iterate over Chunks of $chunk_dur seconds and compute'''
    ''' False Alarm and Miss rates overs these chunks'''
    chunk_rates = defaultdict(list) 
   
    for wav in ref_tree:
        # get annotated boundaries from uem
        beg, end = uem[wav]
        for on in np.arange(beg, end, chunk_dur):
            false_dur = 0
            miss_dur = 0
            true_dur = 0
            spch_dur = 0
            off = chunk_dur + on
            ref_segs = ref_tree[wav].overlap(on, off)
            
            # duration of correct classification: overlap of system and reference
            for ovl in ref_segs:
                ref_on, ref_off, ov_lab = ovl
                sys_ovls = sys_tree[wav].overlap(max(ref_on, on), min(ref_off, off))
                spch_dur += min(off, ref_off) - max(on, ref_on)
                for sys_on, sys_off, sys_lab in sys_ovls:
                    true_dur += min(off, min(sys_off, ref_off)) - max(on, max(sys_on, ref_on))

            # duration of false alarm: overlap of system with silence_reference
            sil_segs = ref_sil_tree[wav].overlap(on,off)
            for ovl in sil_segs:
                sil_on, sil_off, sil_lab = ovl
                sys_ovls = sys_tree[wav].overlap(max(sil_on, on), min(sil_off, off))
                for sys_on, sys_off, sys_lab in sys_ovls:
                    false_dur += min(off, min(sys_off, sil_off)) - max(on, max(sys_on, sil_on))

            # duration of misses: overlap of silences from system with reference
            sys_sil_segs = sys_sil_tree[wav].overlap(on, off)
            for ovl in sys_sil_segs:
                ssil_on, ssil_off, ssil_lab = ovl
                ref_ovls = ref_tree[wav].overlap(max(ssil_on, on), min(ssil_off, off))
                for ref_on, ref_off, ref_lab in ref_ovls:
                    miss_dur += min(off, min(ref_off, ssil_off)) - max(on, max(ref_on, ssil_on))

            chunk_rates[wav].append((on, min(end, off), true_dur,
                                    false_dur, miss_dur))
        with open('chunk_rates_{}.csv'.format(wav), 'w') as fout:
            for on, off, true, false, miss in chunk_rates[wav]:
                fout.write(u'{},{},{},{},{}\n'.format(on, off, true, false, miss))

    return chunk_rates
            

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('corpus', type=str,
                        help='path to the corpus')
    parser.add_argument('rttm', type=str, default=None,
                        help='path to the system RTTM')
    parser.add_argument('--chunk_dur', type=int, default=10,
                        help='(Optional) duration in seconds of the chunks to be analysed')
    args = parser.parse_args()
    corpus_name = os.path.basename(os.path.abspath(args.corpus))

    ## for me, on oberon...
    if corpus_name == "BabyTrain_new":
        corpus_name = "BabyTrain"
    elif corpus_name == "SRI" and args.SRI_far:
        corpus_name = 'SRI_far'

    corpus2rttm = {'CHiME5': 'allU01_{}.rttm',
                   'AMI': 'allMix-Headset_{}.rttm',
                   'BabyTrain': 'all_{}.rttm',
                   'lena_eval': 'all_{}.rttm'}
    sys_rttm = get_intervals(args.rttm)
    for subset in ['train', 'dev', 'test']:
        if corpus_name == "lena_eval" and subset != 'test':
            continue
        # read annotations
        rttm = os.path.join(args.corpus, subset,
                            corpus2rttm[corpus_name].format(subset))
        
        uem = os.path.join(args.corpus, subset,
                            corpus2rttm[corpus_name].format(subset).replace('rttm', 'uem'))

        ref_rttm = get_intervals(rttm)
        uem_dict = read_uem(uem)

        sys_sils = get_silences(sys_rttm, uem_dict)

        ref_sils = get_silences(ref_rttm, uem_dict)


        chunk_rates = miss_FA_per_chunk(ref_rttm, sys_rttm, ref_sils, sys_sils, args.chunk_dur, uem_dict)

        corpus_snr = chunk_SNR(ref_rttm, args.corpus, subset, args.chunk_dur)

        with open('{}_{}_{}.csv'.format(corpus_name, subset, args.chunk_dur), 'w') as fout:
            for wav in corpus_snr:
                for onset, offset, chunk_labels, chunk_snr in corpus_snr[wav]:
                    fout.write(u'{},{},{},{},{}\n'.format(wav, onset, offset,
                                                          '/'.join(list(set(chunk_labels))),
                                                          chunk_snr))

if __name__ == '__main__': 
    main()
