find /export/fs01/jsalt19/output_rttms/ -name result.pyannote* > newfilelist.txt

diff filelist.txt newfilelist.txt | grep ">" | sed "s/> //" > dif.txt
nlines=`wc -l dif.txt | awk '{print $1}'`

#if there are new lines for VAD or diarization
if [ $nlines -gt 0 ] ; then

  #generate clean versions for the new files
  cat dif.txt | while read -r line ; do
  clean=`echo $line | sed "s/result/clean/" | sed "s/\//_/g"`
  wn=`grep "hypoth" $line | wc -l | awk '{print $1}'`
  #echo $wn
  if [ $wn -eq 0 ] ; then
  #echo $clean
    grep -v "arn" $line > res/$clean
  fi
  done

   #run script that generates the allres.txt file
  ./regen_res.R

   #remove used res logs
   rm res/*

   #replace the file list file
   mv newfilelist.txt filelist.txt

   #push it online
   git pull
   git commit -a -m "updated Diar file"
   git push

fi

#REPEAT FOR TALKER DETECTION
myfolder="/export/fs01/jsalt19/output_rttms/"
#myfolder="/Users/acristia/Documents/gitrepos/corstatana/system_eval/2a.1.voxceleb_div2/"
toreplace=`echo $myfolder | sed "s/\//_/g"`
find $myfolder -name *results > newDetfilelist.txt

diff Detfilelist.txt newDetfilelist.txt | grep ">" | sed "s/> //" > dif.txt
nlines=`wc -l dif.txt | awk '{print $1}'`

#if there are new lines for detection
if [ $nlines -gt 0 ] ; then

  #generate clean versions for the new files
  cat dif.txt | while read -r line ; do 
  clean=`echo $line | sed "s/results/clean/" | sed "s/\//_/g" | sed "s/$toreplace//"`
  cp $line resDet/$clean
  done

   #generate new lines to append to the allresDet.txt file
   grep -H "EER" resDet/* | sed "s/EER//" | tr -s ":" | tr ":" "\t" | tr -d " " | sed "s/DCF.*//" >> allresDet.txt

   #remove used res logs
   rm resDet/*

   #replace the file list file
   mv newDetfilelist.txt fileDetlist.txt

   #push it online
   git pull
   git commit -a -m "updated Det file"
   git push

fi
