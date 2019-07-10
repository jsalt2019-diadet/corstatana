Corpus Statistics Analyses (corstatana)
==========================

The goal here is to link voice, role, or talker diarization/detection system performance to characteristics of files and/or speakers on files. See
[this file](https://docs.google.com/document/d/1Ef_lr6QAWSa8RKOvC6bbnb6ewd538bBHmQiMYjDRezE/edit) for explanation of the fields.


Look inside computation/scripts for the scripts, computation/results for the csv's describing files and speakers in files, and `description/` for examples of analyses (e.g. [example](https://github.com/jsalt-coml/corstatana/blob/master/description/system.pdf), visualization on p. 5)

# Instructions to reproduce analyses

To generate your own report by reusing the code in `description/`, you will need [RStudio](https://www.rstudio.com/). For further information on using Rmd for transparent (knittable) analyses, see [Mike Frank & Chris Hartgerink's tutorial](https://libscie.github.io/rmarkdown-workshop/handout.html).

1. Clone the folder with `git clone https://github.com/jsalt-coml/corstatana/` then `cd corstatana`
2. Launch RStudio by double-clicking on system.Rmd -- (or otherwise ensure that your working directory points to the Rmd location by doing `set.wd("RIGHT PATH")`.
3. Click on the button "knit".

If you have any errors, the most likely reason is that you are missing a package. Do `install.packages("MISSING PACKAGE NAME")` in the RStudio terminal. If you are having trouble knitting to a pdf, you are probably missing a latex package. To avoid that hassle, just click on the small triangle to the right of knit and choose "knit to html".