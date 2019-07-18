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


def rms(x):
    'compute RMS of signal x'
    n = len(x)
    return np.sqrt( (1/n) * np.sum(np.square(x)))

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
            annot: a dict {file : [(onset, offset, label)]} where, for each file, 
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
        try:
            sig = scipy.io.wavfile.read(wav_path)[1] # scipy return (sample_rate, array)
        except:
            buff = io.BytesIO()
            normalize_wav(wav_path, buff)
            buff.seek(0)
            rate, sig = scipy.io.wavfile.read(buff)

        #m = sig.mean()
        #sd = sig.std()
        ##info[wav].append(float(np.where(sd == 0, 0, m/sd)))
        #print('mean sig rsn is {}'.format(float(np.where(sd == 0, 0, m/sd))))
    return info

def count_labels(annot, info):
    """ gather quantity information about speakers for each file"""

    for wav in annot:
        labels = [lab for on, off, lab in annot[wav]]

        ##FOR DEBUG PURPOSE
        if DEBUG:
            print('different speaker for {} are'.format(wav))
            print(set(labels))
        
        # count number of children, femal adult, male adult, uncertain 
        CHIs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "CHI" or spk_map[lab] == "KCHI"]
        FAs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "FEM"]
        MAs = [lab for on, off, lab in annot[wav] if spk_map[lab] == "MAL"]
        uncertains = [lab for on, off, lab in annot[wav] if spk_map[lab] == "SPEECH"]
        the_rest = [lab for on, off, lab in annot[wav] if spk_map[lab] != 'CHI'
                                                       and spk_map[lab] != 'FEM'
                                                       and spk_map[lab] != 'MAL'
                                                       and spk_map[lab] != 'SPEECH']
        print(the_rest)
        # append information about speaker for wav
        info[wav].append(len(set(labels))) ## number of speakers in total
        info[wav].append(len(set(CHIs))) ## number of children
        info[wav].append(len(set(FAs))) ## number of female adults
        info[wav].append(len(set(MAs))) ## number of male adults
        info[wav].append(len(set(uncertains))) ## number of uncertains
    return info

def vad_no_ovl(annot):
    """ return a vad in which all segments from the annotations 
        are aggregated to remove overlaps between segments.
    """

    vad = defaultdict(list)
    for wav in  annot:
        prev_on = annot[wav][0][0]
        prev_off = annot[wav][0][1]
        for i, (on, off, lab) in enumerate(annot[wav]):
            if on > prev_off: 
                vad[wav].append((prev_on, prev_off))
                prev_on = on
                prev_off = off
            elif on < prev_off and off > prev_off:
                prev_off = off
            elif i == len(annot[wav]) and off < prev_off:
                vad[wav].append((prev_on, prev_off))
    return vad

def measure_overlap(annot, info):
    """ Measure quantity of overlap speech in each wav. Uses the fact
        that the annotations are sorted for each wav."""

    #/TODO MOVE OUTSIDE 
    info_perSpk = defaultdict(list)
    for wav in annot:
       

        prev_on = -1
        prev_off= -1
        dur_ovl = 0
        dur_ovl_perSpk = defaultdict(float)
        dur_nonovl_perSpk = defaultdict(float)
        dur_speech = 0
        dur_speech_perSpk = defaultdict(float)
        all_vocs = []
        for on, off, lab in annot[wav]:
            # if current annotation starts before end of previous, add to
            # overlap duration
            if on <= prev_off:
                dur_ovl += prev_off - on
                dur_ovl_perSpk[lab] += prev_off - on

            dur_speech += off - on
            dur_speech_perSpk[lab] += off - on
            all_vocs.append(off - on)

            prev_on = on
            prev_off = off

        # get duration of non overlapping speech and compute ratios
        dur_nonovl = dur_speech - dur_ovl
        dur_nonovl_perSpk[lab] += dur_speech_perSpk[lab] - dur_ovl_perSpk[lab]
        
        if dur_speech > 0:
            info[wav].append(dur_ovl/dur_speech) # ratio of overlap speech
            info[wav].append(dur_nonovl/dur_speech) # ratio of non overlapping speech
            info[wav].append(np.mean(all_vocs))
            info_perSpk[wav].append(dur_ovl_perSpk)
            info_perSpk[wav].append(dur_nonovl_perSpk)
            info_perSpk[wav].append(dur_speech_perSpk)
    return info, info_perSpk

def write_info_per_file(corpus_name, subset, info):
    """ write information per file """

    with open(os.path.join('..','results',"{}_{}.csv".format(corpus_name, subset)), "w") as fout: 
        fout.write(u'file,key_child_age,clip_length,nb_diff_speakers,nb_children,nb_fem_ad,nb_mal_ad,nb_uncertain,prop_ovl_speech,prop_nonovl_speech,avg_voc_dur,snr\n')
        for wav in info:
            try:
                (dur, n_spk, n_chi,
                 n_fa, n_ma, n_unk, ovl,
                 non_ovl, mean_voc, snr) = info[wav]
                fout.write(u'{wav},,{dur:.2f},{n_spk},{chi}'
                        ',{f},{m},{u},{ovl:.2f},{novl:.2f},'
                        '{voc:.2f},{snr}\n'.format(wav=wav, dur=dur, n_spk=n_spk,
                                                 chi=n_chi, f=n_fa, m=n_ma, u=n_unk,
                                                 ovl=ovl, novl=non_ovl, voc=mean_voc,
                                                 snr=snr))
            except:
                print(wav)

def write_info_per_speaker(corpus_name, subset, info_perSpk):
    """ write information per speaker """

    with open(os.path.join('..', 'results', '{}_{}_perSpeaker.csv'.format(corpus_name,
              subset)), 'w') as fout:
        fout.write(u'file,speaker,role,tot_ovl_speech,tot_nonovl_speech,snr\n')
        for wav in info_perSpk:
            #TODO PUT SNR 
            dur_ovl, dur_nonovl, dur_speech, snr= info_perSpk[wav]
            for spk in dur_speech:
                fout.write(u'{w},{s},{r},{o},{no},{snr}\n'.format(w=wav, s=spk, r=spk_map[spk],
                                                                o=dur_ovl[spk],no= dur_nonovl[spk],
                                                                snr=snr[spk]))

def get_silence_times(annot, info):
    """ Extract silences timestamps from annotations.
        Add "SIL" label to follow same format as annotation."""

    sils = defaultdict(list)

    # annotations are already sorted
    for wav in annot:
        prev_on = 0
        prev_off = 0
        wav_dur = info[wav][0]
        for i, (on, off, lab) in enumerate(annot[wav]):
            # count as silence from 0 to first annotation,
            # if there's a gap between previous offset and 
            # current onset, and from last offset to end of wav
            if on > prev_off:
                sils[wav].append((prev_off, on, "SIL"))
            if off > prev_off:
                prev_off = off
            prev_on = on
        # check last label vs wav duration
        if wav_dur > annot[wav][-1][1]:
            sils[wav].append((annot[wav][-1][1], wav_dur, "SIL"))
    return sils

                
def extract_wav_from_label(wav, corpus_path, subset, annot, label):
    """ extract array from wav file that contain only parts indicated by label
        in annotation.
        input 
            wav: array containing the wav file
            annot : annotations of the wav
            label: label you want to extract - if label is "ALL", get all speech 
                   intervals
        output
            label_wav : array containing parts of the wav indicated by label
    """
    wav_path = os.path.join(corpus_path,
                            subset, "wav",
                            "{}.wav".format(wav))

    frate, wav = scipy.io.wavfile.read(wav_path)

    # get onsets and offsets
    if label == "ALL":
        labs = [np.arange(int(frate*on), int(frate*off))
                for on, off, lab in annot]
    else:
        labs = [np.arange(int(frate*on), int(frate*off))
                for on, off, lab in annot 
                if spk_map[lab] == label]
    try:
        lab_idx = np.concatenate(labs)
    except:
        return

    # get array that contains signal only from requested label
    lab_sig = wav[lab_idx]
    
    return lab_sig

def estimate_snr(annot, corpus, subset, sils, info, info_perSpk):
    """ Estimate SNR by computing ration of regions w/ signal and 
        region without signal"""
    
    per_label_snr = defaultdict(list)

    for wav in annot:

        sil_sig = extract_wav_from_label(wav, corpus, subset, sils[wav], "SIL")
        speech_sig = extract_wav_from_label(wav, corpus, subset, annot[wav], "ALL")
      
        # global SNR
        try:
            sil_rms = rms(sil_sig)
        except:
            print(wav)
            sil_rms = None
             
        if (speech_sig is not None) and (sil_sig is not None):
            info[wav].append(rms(speech_sig) / sil_rms)
        else:
            info[wav].append("NA")

        print('Global snr is {}'.format(info[wav][-1]))
        
        for label in ['KCHI', 'CHI', 'FEM', 'MAL', 'SPEECH']:
            lab_sig = extract_wav_from_label(wav, corpus, subset, annot[wav], label)
             
            # per label SNR
            if (lab_sig is not None) and (sil_sig is not None):
                per_label_snr[label] = rms(lab_sig) / sil_rms
            else:
                per_label_snr[label] = "NA"


        info_perSpk[wav].append(per_label_snr)
    return info, info_perSpk       

def local_snr(annot, vad, corpus_path, subset, sils):
    """Cut speech segments in 100 ms frames and compute SNR on those.
       for each 100s chunk output SNR Value + all current labels

       TODO: First extract VAD with no gaps, the
    """

    local_snr = defaultdict(list)

    for wav in vad:
        # load wav
        wav_path = os.path.join(corpus_path,
                            subset, "wav",
                            "{}.wav".format(wav))
        frate, wav_sig = scipy.io.wavfile.read(wav_path)
       
        sil_sig = extract_wav_from_label(wav, corpus_path, subset, sils[wav], "SIL")
        speech_sig = extract_wav_from_label(wav, corpus_path, subset, annot[wav], "ALL")

        # rms of all silences
        sil_rms = rms(sil_sig)
        snr_speech = []
        for on, off in vad[wav]:
            segments = np.arange(on, off, 0.1)
            snr_speech += [(b, rms(wav_sig[int(frate * b):int(frate * (b+0.1))]) / sil_rms)
                         for b in segments[:-1]]
        local_snr[wav].append(snr_speech)

    return local_snr

def write_local_snr(snr):

    for wav in snr:
        with open('../results/snr/{}_snr.csv'.format(wav), 'w') as fout:
            for on, val in snr[wav][0]:
                fout.write(u'{},{}\n'.format(on, val))
   
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('corpus', type=str,
                        help='path to the corpus')
    parser.add_argument('--rttm', type=str, default=None,
                        help='(Optional) enable to link only test rttm, and not whole corpus.')
    parser.add_argument('--local_snr', action='store_true',
                        help='if enabled, compute only local snr')
    parser.add_argument('--SRI_far', action='store_true',
                        help='if analysing the SRI corpus, enable to take FAR field '
                             'instead of close field')

    args = parser.parse_args()

    # get name of corpus
    ## first do abspath to remove possible trailing /
    corpus_name = os.path.basename(os.path.abspath(args.corpus))

    ## for me, on oberon...
    if corpus_name == "BabyTrain_new":
        corpus_name = "BabyTrain"
    elif corpus_name == "SRI" and args.SRI_far:
        corpus_name = 'SRI_far'

    corpus2rttm = {'CHiME5': 'allU01_{}.rttm',
                   'AMI': 'allMix-Headset_{}.rttm',
                   'BabyTrain': 'all_{}.rttm',
                   'SRI': 'close_{}.rttm',
                   'SRI_far': 'far_{}.rttm'}

    if args.local_snr:
        for subset in ['train', 'dev', 'test']:
            if "SRI" in corpus_name and subset == "train":
                continue
            # read annotations
            rttm = os.path.join(args.corpus, subset,
                                corpus2rttm[corpus_name].format(subset))
            annot = parse_rttms(rttm)
            vad = vad_no_ovl(annot)
            info = defaultdict(list)

            info = get_wav_len(annot, args.corpus, subset, info)
            sils = get_silence_times(annot, info)

            snr = local_snr(annot, vad, args.corpus, subset, sils)
            write_local_snr(snr)
    elif not args.local_snr:
        if not args.rttm:
            for subset in ['train', 'dev', 'test']:
                # read annotations
                rttm = os.path.join(args.corpus, subset,
                                    corpus2rttm[corpus_name].format(subset))
                annot = parse_rttms(rttm)

                # get wav info
                info = defaultdict(list)
                info = get_wav_len(annot, args.corpus, subset, info)

                # get speakers info
                info = count_labels(annot, info)

                # measure overlap
                info, info_perSpk = measure_overlap(annot, info)

                # estimate SNR
                sils = get_silence_times(annot, info)
                info, info_perSpk = estimate_snr(annot, args.corpus, subset, sils,
                                                 info, info_perSpk)

                # write output
                write_info_per_file(corpus_name, subset, info)
                write_info_per_speaker(corpus_name, subset, info_perSpk)
        else:
            # analyze test
            subset = "test"

            # add " system" to name, to avoid overwriting corpus file
            corpus_name = corpus_name + "_system"
            # read annotations
            annot = parse_rttms(args.rttm)

            # get wav info
            info = defaultdict(list)
            info = get_wav_len(annot, args.corpus, subset, info)

            # get speakers info
            info = count_labels(annot, info)

            # measure overlap
            info, info_perSpk = measure_overlap(annot, info)

            # write output
            write_info_per_file(corpus_name, subset, info)
            write_info_per_speaker(corpus_name, subset, info_perSpk)

if __name__ == '__main__':
    main()
