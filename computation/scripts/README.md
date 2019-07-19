Corstatana Computation
======================

This module computes several metrics on corpora
and on Speaker Diarization systems outputs.

Requirements
------------

- sox/pysox : https://github.com/rabitt/pysox
- numpy
- scipy
- pyannote metrics
- pyannote database

you can install those using the environment.yml file:

```
$ conda create env -f environment.yml
$ source activate corstatana
```

metrics_by_speaker.py
---------------------

This script takes as input a RTTM file that is the output of a Speaker Diarization system, 
the pyannote protocol to define it, and the subset of the corpus that was evaluated.
An optionnal argument "--vad" can be used to specify that the output is only a VAD and does not
specify user names.

The output is written in the same folder as the script, and is one .txt file per wav in the 
subset containing the metrics in a table format.

Example of use: 
    `python metrics_by_speaker.py /home/${USER}/all.rttm BabyTrain.SpeakerDiarization.All test`

speaker_info_per_file.py
------------------------

Takes as input the path to the corpus, plus optional arguments specific to certain corpus.
This scripts assumes that the folder given in argument contains the following structure:

    ` corpus/
            train/
                gold/*.rttm
                wav/*.wav
            test/
                gold/*.rttm
                wav/*.wav
           
            dev/
                gold/*.rttm
                wav/*.wav
    `

Example of use:
    `python speaker_info_per_file.py /home/${USER}/BabyTrain

speaker_info_per_chunk.py
-------------------------

Compute SNR on small chunks of 10s, and given 
a system's output in rttm format, compute false alarm and miss rates for small chunks of 10s.
An optionnal --chunk_dur can be used to change de duration of the chunks.

Example of use:

    `python speaker_info_per_chunk.py /home/${USER}/BabyTrain/  /home/${USER}/all.rttm`
