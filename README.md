Corpus Statistics Analyses (corstatana)
==========================

By Julien Karadayi and Alejandrina Cristia
For JSALT 2019 Speaker detection from single microphone in adverse scenarios

The goal is to link voice, role, or talker diarization/detection system performance to characteristics of files and/or speakers on files. Look inside computation/scripts for the scripts, computation/results for the csv's describing files and speakers in files, and `description/` for examples of analyses (e.g. [example](https://github.com/jsalt-coml/corstatana/blob/master/description/system.pdf), visualization on p. 5)

#  Explanation

We aimed to provide trial, file, and corpus level descriptors that can allow us to describe what different pipelines or systems are doing right or wrong. 

By trial we mean the 60 second regions that have been identified as trials for the talker detection task.
By file we mean a sound file, which is typically a recording (in all corpora except for babytrain) or extract from a recording (in the daylong sections of babytrain).
By corpus we mean AMI, SRI, Chime5, and the subcorpora within babytrain.

Typically, the descriptors explained next will be measured only at the trial and file level, with descriptors for corpora being derived from those at the trial and file level.

Note that some of this information is already in Marvin's README for the datasets (notably child age, proportion overlapping and non-overlapping).

## Properties derived from metadata

if babytrain, key child's age

## Properties derived from the reference rttm
This is done at the file level for the whole file and for the trials, this is derived from that file.

- file length
- number of different speakers
- number of speakers in each category: child, female adult, male adult, uncertain
- proportion of speech that is overlapping
- proportion of speech that is not overlapping
- average vocalization duration
- for each speaker, their total speech duration that is overlapping, total speech duration that is not overlapping

## Properties derived from the reference rttm + the audio

- signal to noise ratio (average loudness in speech portions divided by average loudness in nonspeech portions)
- for each speaker, their average signal to noise ratio (average loudness during their non-overlapping speech portions divided by average loudness in nonspeech portions)

### Properties derived from the reference rttm + the system rttm
This is done at the file level for the whole file and for the trials, this is derived from that file.

- for each file and for the trials derived from that file, diarization: miss rate, false alarm rate, confusion rate, correct rate
- for each speaker in each file, the amount of time in each of the following cases: correct (duration that was correctly recovered by the system); missed (duration that was missed ie classified as non-speech); confused (duration that was attributed to a different speaker)


# Instructions to reproduce analyses

To generate your own report by reusing the code in `description/`, you will need [RStudio](https://www.rstudio.com/). For further information on using Rmd for transparent (knittable) analyses, see [Mike Frank & Chris Hartgerink's tutorial](https://libscie.github.io/rmarkdown-workshop/handout.html).

1. Clone the folder with `git clone https://github.com/jsalt-coml/corstatana/` then `cd corstatana`
2. Launch RStudio by double-clicking on system.Rmd -- (or otherwise ensure that your working directory points to the Rmd location by doing `set.wd("RIGHT PATH")`.
3. Click on the button "knit".

If you have any errors, the most likely reason is that you are missing a package. Do `install.packages("MISSING PACKAGE NAME")` in the RStudio terminal. If you are having trouble knitting to a pdf, you are probably missing a latex package. To avoid that hassle, just click on the small triangle to the right of knit and choose "knit to html".