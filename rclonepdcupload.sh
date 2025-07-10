#!/bin/sh

# set -x
if [ "$1" = "-n" ]; then
  CMD="echo"
  shift
fi
DIR1="$1"
DIR2="$2"
DIR4="$DIR2/$DIR1"
if [ "$DIR1" = "." ]; then
  DIR4="$DIR2"
fi
if [ "$DIR2" = "" ]; then
  DIR4="$DIR1"
fi
for DIR3 in mzML mzIdentML PSM.tsv; do
  if [ -d "$DIR1/$DIR3" ]; then
    echo "Copying $DIR1/$DIR3 $DIR4/$DIR3"
    $CMD rclone copy -v --progress "$DIR1/$DIR3" "pdc-s3:pdc-cdap/$DIR4/$DIR3"
  fi
done
if [ -d "$DIR1/SummaryReports/forportal" ]; then
  echo "Copying $DIR1/SummaryReports/forportal to $DIR4/SummaryReports"
  $CMD rclone copy -v --progress "$DIR1/SummaryReports/forportal" "pdc-s3:pdc-cdap/$DIR4/SummaryReports"
fi
for FN in "$DIR1"/SummaryReports/*.versions.log; do 
  FN1=`basename "$DIR1"/SummaryReports/*.versions.log`
  echo "Copying $FN to $DIR4/$FN1"
  $CMD rclone copyto -v --progress "$FN" "pdc-s3:pdc-cdap/$DIR4/$FN1"
done

