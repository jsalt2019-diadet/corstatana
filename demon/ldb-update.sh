find /export/fs01/jsalt19/output_rttms/ -name result.pyannote* > newfilelist.txt

diff filelist.txt newfilelist.txt | grep ">" | sed "s/> //" > dif.txt
nlines=`wc -l dif.txt | awk '{print $1}'`

#if there are new lines
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

   #push it online
   git pull
   git commit -a -m "updated file"
   git push

   #replace the file list file
   mv newfilelist.txt filelist.txt
fi
