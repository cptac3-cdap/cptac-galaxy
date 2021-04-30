#!/bin/sh

help() {
  if [ "$1" != "" ]; then
    echo "" 1>&2
    echo "$1" 1>&2
  fi
  cat <<EOF | fmt -w80 -s 1>&2

execute_cdap_on_cluster.sh [ options ] <path>/<base>.params

Options:
  -a <analysis>
        One of mzML, PSM, Reports, or Complete. Default: Complete.
  -n	Do not execute commands, just show commands to be executed. 
  -v	Verbose logging. 
  -h	Help text.

<base> is presumed as the prefix for all input and summary report files.

Parameter file sets the follwing variables:

  SPECIES="{Human,Mouse,Rat,Human+Mouse}"
  PROTEOME="{Proteome,Phosphoproteome,Acetylome,Glycoproteome,Ubiquitylome}"
  QUANT="{TMT6,TMT10,TMT11,iTRAQ,Label-Free}"
  INST="{Thermo Q-Exactive HCD}" #Use Q-Exactive for all high-accuracy instruments
  BATCH="<TMT label batch(es)>" #Optional. Space separated batch names
  TARGETFDR="<Protein FDR%>" #Optional. Default is 1.0
  INITSPECFDR="<Spec. FDR%>" #Optional. Default is \$TARGETFDR

Files <base>.RAW.txt, <base>.sample.txt, \$BATCH.txt are expected in the same directory as <base>.params.

EOF
  exit 1;
}

ECHO=0
VERBOSE=0
ARGS=""
CLUSTER=""
ANALYSIS="Complete"
while getopts ":c:a:nvgh" o ; do
        case $o in
                n ) ECHO=1; ARGS="-n $ARGS";;
                v ) VERBOSE=1; ARGS="-v $ARGS";;
	        c ) CLUSTER="$OPTARG";;
		a ) ANALYSIS="$OPTARG";;
                h ) help "";;
                * ) help "Invalid option: -$OPTARG"
        esac
done

DOMZML=0
DOPSM=0
DOREP=0
case $ANALYSIS in 
  mzML) DOMZML=1;;
  PSM) DOPSM=1;;
  Reports) DOREP=1;;
  Complete) DOPSM=1; DOREP=1;;
  *) help "Bad analysis (-a) parameter: $ANALYSIS";;
esac

shift $(($OPTIND - 1)) 

if [ "$1" = "" ]; then
  help "Parameter file not provided on the command-line"
fi

DIR=`dirname "$0"`
DIR=`readlink -f "$DIR"`

PARAM=`readlink -f $1`
. "$PARAM"
BASE=`basename "$PARAM" .params`
FILES=`dirname "$PARAM"`
WORK="$FILES/.."
RESULTS="$WORK/results"

if [ $VERBOSE -eq 1 ]; then
  set -x
fi

RAW="$FILES/$BASE.RAW.txt"
SAMPLE="$FILES/$BASE.sample.txt"
MZID="$FILES/$BASE.mzIdentML.txt"

if [ $DOPSM = 1 -a "$INST" = "" ]; then
    help "PSM Analysis: INST missing from parameter file $1"
fi
if [ \( $DOPSM = 1 -o $DOREP = 1 \) -a "$SPECIES" = "" ]; then
    help "SPECIES missing from parameter file $1"
fi
if [ \( $DOPSM = 1 -o $DOREP = 1 \) -a "$PROTEOME" = "" ]; then
    help "PROTEOME missing from parameter file $1"
fi
if [ \( $DOPSM = 1 -o $DOREP = 1 \) -a "$QUANT" = "" ]; then
    help "QUANT missing from parameter file $1"
fi

if [ \( $DOMZML = 1 -o $DOPSM = 1 \) -a ! -f "$RAW" ]; then
    help "mzML or PSM Analysis: RAW file \"$RAW\" not found"
fi
if [ $DOREP = 1 -a ! -f "$SAMPLE" ]; then
    help "Reports: Sample file \"$SAMPLE\" not found"
fi
for B in $BATCH; do
  if [ $DOREP = 1 -a ! -f "$FILES/$B.txt" ]; then
    help "Reports: BATCH file \"$FILES/$B.txt\" not found"
  fi
done
if [ $DOPSM = 1 -a -f "$MZID" ]; then
    echo "PSM Analysis: mzIdentML file \"$MZID\" already present"
    DOPSM=0
fi
if [ $DOREP = 1 -a $DOPSM = 0 -a ! -f "$MZID" ]; then
    help "Reports: mzIdentML file \"$MZID\" not found"
fi
if [ $DOREP = 1 -a $DOPSM = 0 -a ! -f "$FILES/${BASE}.qcmetrics.tsv" ]; then
    help "Reports: QCMetrics \"$FILES/${BASE}.qcmetrics.tsv\" not found"
fi

cmd() {
  if [ $ECHO -eq 1 ]; then
    echo "$*" 1>&2
  else
    sh -c "$*" || exit 1
  fi
}

adddate() {
    while IFS= read -r line; do
        printf '[%s] %s\n' "$(date)" "$line";
    done
}

rotate() {
  if [ -f "$1" ]; then
    timestamp=`date +%s`
    mv "$1" "$1.$(date +%s)"
  fi
}

if [ "$CLUSTER" != "" ]; then
  CLUSTERARG="--cluster $CLUSTER"
fi

if [ $DOMZML = 1 ]; then

  rotate mzml.log
  cmd $DIR/execute_mzml.sh $ARGS $PARAM -- $CLUSTERARG --history "${BASE}" --outdir $RESULTS > mzml.log 2>&1 &
  echo $! > mzml.pid
  sleep 5
  echo "*** mzML Analysis ***" | adddate
  fgrep "Workflow:" mzml.log | adddate
  while true; do
    if [ -f mzml.log ]; then
	fgrep "Workflows:" mzml.log | sed 's/^Workflows: //' | tail -n 1 | adddate
        if [ "`tail -n 1 mzml.log`" = "Done." ]; then
            break
	    fi
    fi
    if ! kill -0 `cat mzml.pid` >/dev/null 2>&1; then
      break
    fi
    sleep 60
  done
  if [ `fgrep "Workflows:" mzml.log | tail -n 1 | fgrep ' Failed 0, ' | wc -l ` -eq 0 ]; then
    exit 1;
  fi
  if [ "`tail -n 1 mzml.log`" != "Done." ]; then
    exit 1;
  fi
  echo "*** mzML Analysis Complete ***" | adddate

  cd $RESULTS
  for ck in `find . -name "*.cksum" -type f`; do
      as=`dirname $ck`
      if ! $DIR/cptacdcc/cksum.sh -V -f $ck $as >$WORK/cksum.log 2>&1; then
          cat $WORK/cksum.log | fgrep -v "Checking" | fgrep -v "All checksums" | adddate
          exit 1;
      fi
  done
  rm -f $WORK/cksum.log
         
  $DIR/organize1all.sh ${BASE} `ls | egrep -v '^(mzML|mzIdentML|PSM.tsv|SummaryReports)$'` | adddate
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  mkdir -p $WORK/../data/${BASE}
  for d in mzML mzIdentML PSM.tsv SummaryReports; do
    if [ -d $d -a ! -d $WORK/../data/${BASE}/$d ]; then
      ln -s $RESULTS/$d $WORK/../data/${BASE}/$d
    fi
  done

elif [ $DOPSM = 1 ]; then

  rotate psm.log
  cmd $DIR/execute_psm.sh $ARGS $PARAM -- $CLUSTERARG --history "${BASE}" --outdir $RESULTS >psm.log 2>&1 &
  echo $! > psm.pid
  sleep 5
  echo "*** PSM Analysis ***" | adddate
  fgrep "Workflow:" psm.log | adddate
  while true; do
    if [ -f psm.log ]; then
	    fgrep "Workflows:" psm.log | sed 's/^Workflows: //' | tail -n 1 | adddate
        if [ "`tail -n 1 psm.log`" = "Done." ]; then
            break
	    fi
    fi
    if ! kill -0 `cat psm.pid` >/dev/null 2>&1; then
      break
    fi
    sleep 60
  done
  if [ `fgrep "Workflows:" psm.log | tail -n 1 | fgrep ' Failed 0, ' | wc -l ` -eq 0 ]; then
    exit 1;
  fi
  if [ "`tail -n 1 psm.log`" != "Done." ]; then
    exit 1;
  fi
  echo "*** PSM Analysis Complete ***" | adddate
  
  cd $RESULTS
  for ck in `find . -name "*.cksum" -type f`; do
      as=`dirname $ck`
      if ! $DIR/cptacdcc/cksum.sh -V -f $ck $as >$WORK/cksum.log 2>&1; then
          cat $WORK/cksum.log | fgrep -v "Checking" | fgrep -v "All checksums" | adddate
          exit 1;
      fi
  done
  rm -f $WORK/cksum.log
         
  $DIR/organize1all.sh ${BASE} `ls | egrep -v '^(mzML|mzIdentML|PSM.tsv|SummaryReports)$'` | adddate
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  find . -empty -exec rm -rf {} \; >/dev/null 2>&1
  mkdir -p $WORK/../data/${BASE}
  for d in mzML mzIdentML PSM.tsv SummaryReports; do
    if [ -d $d -a ! -d $WORK/../data/${BASE}/$d ]; then
      ln -s $RESULTS/$d $WORK/../data/${BASE}/$d
    fi
  done

  find $RESULTS/mzIdentML -name "*.cksum" | \
         sed -e 's/\.cksum$//' -e 's%^.*/%%' | \
         awk -v d=$RESULTS '{printf("%s\tlocal\t%s/mzIdentML/%s.cksum\n",$1,d,$1);}' \
         > $FILES/${BASE}.mzIdentML.txt

  cp $RESULTS/SummaryReports/${BASE}.qcmetrics.tsv $FILES

fi

if [ $DOREP = 1 ]; then

  cd $WORK

  mkdir -p $RESULTS/SummaryReports
  if [ -f $RESULTS/SummaryReports/${BASE}.qcmetrics.tsv ]; then
    rm -f $RESULTS/SummaryReports/${BASE}.qcmetrics.tsv
  fi

  rotate rep.log
  cmd $DIR/execute_report.sh $ARGS $FILES/${BASE}.params -- $CLUSTERARG --history "${BASE}" --outdir $RESULTS/SummaryReports >rep.log 2>&1 &
  echo $! > rep.pid
  sleep 5
  echo "*** Summary Reports ***" | adddate
  fgrep "Workflow:" rep.log | tail -n 1 | adddate
  while true; do
    if [ -f rep.log ]; then
	    fgrep "Workflows:" rep.log | sed 's/^Workflows: //' | tail -n 1 | adddate
        if [ "`tail -n 1 rep.log`" = "Done." ]; then
            break
	    fi
    fi
    if ! kill -0 `cat rep.pid` >/dev/null 2>&1; then
      break
    fi
    sleep 60
  done
  if [ `fgrep "Workflows:" rep.log | tail -n 1 | fgrep ' Failed 0, ' | wc -l ` -eq 0 ]; then
    exit 1;
  fi
  if [ "`tail -n 1 rep.log`" != "Done." ]; then
    exit 1;
  fi
  echo "*** Summary Reports Done ***" | adddate

  # Add the input files that are part of the results...
  cp $SAMPLE $RESULTS/SummaryReports
  for B in $BATCH; do
    cp $FILES/$B.txt $RESULTS/SummaryReports
  done
  cp $FILES/${BASE}.qcmetrics.tsv $RESULTS/SummaryReports
  
  cd $RESULTS
  for ck in `find SummaryReports -name "*.cksum" -type f`; do
      as=`dirname $ck`
      if ! $DIR/cptacdcc/cksum.sh -V -f $ck $as >$WORK/cksum.log 2>&1; then
          cat $WORK/cksum.log | fgrep -v "Checking" | fgrep -v "All checksums" | adddate
          exit 1;
      fi
  done
  rm -f $WORK/cksum.log

  mkdir -p $WORK/../data/${BASE}
  for d in mzML mzIdentML PSM.tsv SummaryReports; do
    if [ -d $d -a ! -d $WORK/../data/${BASE}/$d ]; then
      ln -s $RESULTS/$d $WORK/../data/${BASE}/$d
    fi
  done
         
fi

echo "Done." | adddate
