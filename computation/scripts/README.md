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
$ conda env create -f environment.yml
$ source activate corstatana
```

After that, you need to create in your home directory a .pyannote folder, and inside that folder, create a file database.yml with the following content: 

```
Databases:
   AMI: /PATH/TO/AMI/*/wav/{uri}.wav
   BabyTrain: /PATH/TO/BabyTrain/*/wav/{uri}.wav
   CHiME5: /PATH/TO/CHiME5/*/wav/{uri}.wav
   MUSAN: /PATH/TO/musan/{uri}.wav

Protocols:

   AMI:
      SpeakerDiarization:
         # AMI.SpeakerDiarization.MixHeadset
         MixHeadset:
           train:
              annotation: /PATH/TO/AMI/train/allMix-Headset_train.rttm
              annotated: /PATH/TO/AMI/train/allMix-Headset_train.uem
           development:
              annotation: /PATH/TO/AMI/dev/allMix-Headset_dev.rttm
              annotated: /PATH/TO/AMI/dev/allMix-Headset_dev.uem
           test:
              annotation: /PATH/TO/AMI/test/allMix-Headset_test.rttm
              annotated: /PATH/TO/AMI/test/allMix-Headset_test.uem

   BabyTrain:
      SpeakerDiarization:
         # BabyTrain.SpeakerDiarization.All
         All:
            train:
              annotation: /PATH/TO/BabyTrain/train/all_train.rttm
              annotated: /PATH/TO/BabyTrain/train/all_train.uem
            development:
              annotation: /PATH/TO/BabyTrain/dev/all_dev.rttm
              annotated: /PATH/TO/BabyTrain/dev/all_dev.uem
            test:
              annotation: /PATH/TO/BabyTrain/test/all_test.rttm
              annotated: /PATH/TO/BabyTrain/test/all_test.uem

   CHiME5:
      SpeakerDiarization:
         # CHiME5.SpeakerDiarization.U01
         U01:
           train:
             annotation: /PATH/TO/CHiME5/train/allU01_train.rttm
             annotated: /PATH/TO/CHiME5/train/allU01_train.uem
           development:
             annotation: /PATH/TO/CHiME5/dev/allU01_dev.rttm
             annotated: /PATH/TO/CHiME5/dev/allU01_dev.uem
           test:
             annotation: /PATH/TO/CHiME5/test/allU01_test.rttm
             annotated: /PATH/TO/CHiME5/test/allU01_test.uem


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
