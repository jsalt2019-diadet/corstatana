#!/usr/bin/env Rscript
library(readr)
library("dplyr")

fl=NULL
for(f in dir(pattern="test.txt"))    fl <- rbind(fl,cbind(f,read.table(f)))

mydir="res/"

allres=NULL
for(res in dir(path=mydir)){
#print(res)
  file_eval <- read_table(paste0(mydir,res), comment = "--")
#print(summary(file_eval))
  #the first col must be renamed
  colnames(file_eval)[1]<-"file"

  #standardize out
  if(length(grep("diarization",colnames(file_eval)))==1) {
    colnames(file_eval)[grep("diarization",colnames(file_eval))]<-"main"
    task="diar"} else {
      colnames(file_eval)[grep("detection",colnames(file_eval))]<-"main"
      task="det"}
  #clean and write
  file_eval=subset(file_eval,main!="Total")
#print(summary(file_eval))
  allres=rbind(allres,cbind(as.data.frame(file_eval)[,c("file","main")],res,task))
} #allres has 24108 obs
allres=merge(allres,fl,by.x="file",by.y="V1",all=T)

allres$corpus=gsub("_.*","",allres$f)
for(thisc in c("babytrain","ami","chime5","sri")) allres$main=gsub(thisc,"",allres$main)
allres[!is.na(allres$corpus),]->allres #attn removing files not assigned to a corpus we go from 23k to 9k results

write.table(allres,"allres.txt",row.names = F,sep=",",quote=F,append=T,col.names=F)

