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
    echo "Copying $DIR1/$DIR3 $DIR4"
    $CMD cptacdcc put -f "$DIR1/$DIR3" "Data3_5TB_Disk/PDC_Data_in_progress/CDAP/$DIR4"
  fi
done
if [ -d "$DIR1/SummaryReports/forportal" ]; then
  echo "Copying $DIR1/SummaryReports/forportal to $DIR4/SummaryReports"
  $CMD cptacdcc mkdir "Data3_5TB_Disk/PDC_Data_in_progress/CDAP/$DIR4/SummaryReports"
  $CMD cptacdcc put -f "$DIR1/SummaryReports/forportal/*" "Data3_5TB_Disk/PDC_Data_in_progress/CDAP/$DIR4/SummaryReports"
fi
for FN in "$DIR1"/SummaryReports/*.versions.log; do 
  echo "Copying $FN to $DIR4/$FN1"
  $CMD cptacdcc put -f "$FN" "Data3_5TB_Disk/PDC_Data_in_progress/CDAP/$DIR4"
done

