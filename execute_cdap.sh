#!/bin/sh

help() {
  if [ "$1" != "" ]; then
    echo "" 1>&2
    echo "$1" 1>&2
  fi
  cat <<EOF | fmt -w80 -s 1>&2

cptac-galaxy/execute_cdap.sh [ options ] <path> 

cptac-galaxy/execute_cdap.sh [ options ] <path>/<base>.params 

Options:
  -a <analysis>
        One of PSM, Reports, or Complete. Default: Complete.
  -c <clustername>
	CPTAC-Galaxy cluster name to execute the CDAP on. Only necessary if multiple clusters are running. 
  -n	Do not execute commands, just show commands to be executed. 
  -v	Verbose logging. 
  -h	Help text.

If only <path> is provided, the single file with extension *.params (<base>.params) is presumed to be the parameter file. 

<base> is presumed as the prefix for all input and summary report files.

Parameter file sets the follwing variables:

  SPECIES="{Human,Mouse,Rat,Human+Mouse}"
  PROTEOME="{Proteome,Phosphoproteome,Acetylome,Ubiquitylome,Glycoproteome}"
  QUANT="{TMT6,TMT10,TMT11,TMT16,TMT18,iTRAQ,Label-Free}"
  INST="{Thermo Q-Exactive HCD}" #Use Q-Exactive for all high-accuracy instruments
  BATCH="<TMT label batch(es)>" #Optional. Space separated batch names
  TARGETFDR="<Protein FDR%>" #Optional. Default is 1.0
  INITSPECFDR="<Spec. FDR%>" #Optional. Default is \$TARGETFDR
  PROTOCOL="{CPTAC3-CDAP,...}" #Optional. Default is CPTAC3-CDAP

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

DOPSM=0
DOREP=0
case $ANALYSIS in 
  PSM) DOPSM=1;;
  Reports) DOREP=1;;
  Complete) DOPSM=1; DOREP=1;;
  *) help "Bad analysis (-a) parameter: $ANALYSIS";;
esac

if [ $VERBOSE -eq 1 ]; then
  set -x
fi

shift $(($OPTIND - 1)) 

if [ "$1" = "" ]; then
  help "Parameter file not provided on the command-line"
fi

DIR=`dirname "$0"`
DIR=`readlink -f "$DIR"`
EXECUTEPSM="$DIR/execute_psm.sh"
EXECUTEREP="$DIR/execute_report.sh"
PARAM=`readlink -f $1`
if [ -d $PARAM ]; then
  PARAM1=""
  for pf in "$PARAM"/*.params; do
    if [ "$PARAM1" != "" ]; then
      help "More than one *.params file in directory $PARAMS"
    fi
    PARAM1="$pf"
  done
  if [ "$PARAM1" = "" ]; then
    help "No *.params file in directory $PARAMS"
  fi
  PARAM="$PARAM1"
fi
. "$PARAM"
BASE=`basename "$PARAM" .params`
WORK=`dirname "$PARAM"`
exec >>$WORK/$BASE.log 2>&1
RAW="$WORK/$BASE.RAW.txt"
SAMPLE="$WORK/$BASE.sample.txt"

if [ $DOPSM = 1 -a "$INST" = "" ]; then
    help "PSM Analysis: INST missing from parameter file $1"
fi
if [ "$SPECIES" = "" ]; then
    help "SPECIES missing from parameter file $1"
fi
if [ "$PROTEOME" = "" ]; then
    help "PROTEOME missing from parameter file $1"
fi
if [ "$QUANT" = "" ]; then
    help "QUANT missing from parameter file $1"
fi

if [ $DOPSM = 1 -a ! -f "$RAW" ]; then
    help "PSM Analysis: RAW file \"$RAW\" not found"
fi
if [ $DOREP = 1 -a ! -f "$SAMPLE" ]; then
    help "Reports: Sample file \"$SAMPLE\" not found"
fi
for B in $BATCH; do
  if [ $DOREP = 1 -a ! -f "$WORK/$B.txt" ]; then
    help "Reports: BATCH file \"$WORK/$B.txt\" not found"
  fi
done
if [ $DOPSM = 1 -a -d "$WORK/mzIdentML" ]; then
    help "PSM Analysis: mzIdentML directory \"$WORK/mzIdentML\" already present"
fi
if [ $DOREP = 1 -a $DOPSM = 0 -a ! -d "$WORK/mzIdentML" ]; then
    help "Reports: mzIdentML directory \"$WORK/mzIdentML\" not found"
fi
if [ $DOREP = 1 -a $DOPSM = 0 -a ! -f "$WORK/SummaryReports/${BASE}.qcmetrics.tsv" ]; then
    help "Reports: QCMetrics \"$WORK/SummaryReports/${BASE}.qcmetrics.tsv\" not found"
fi

cmd() {
  if [ $ECHO -eq 1 ]; then
    echo "$*" 1>&2
  else
    sh -c "$*" || exit 1
  fi
}

if [ "$CLUSTER" != "" ]; then
  CLUSTERARG="--cluster $CLUSTER"
fi

TMPFILE=`mktemp`

echo "VERSIONS:"
cmd $DIR/cluster $CLUSTER version
echo ""

sleep 10
cmd $DIR/cluster $CLUSTER list > $TMPFILE
if [ `fgrep ${BASE}_PSM $TMPFILE | wc -l` -ne 0 ]; then
  sleep 10
  cmd $DIR/cluster $CLUSTER remove ${BASE}_PSM
fi
if [ $DOREP = 1 -a `fgrep ${BASE}_REP $TMPFILE | wc -l` -ne 0 ]; then
  sleep 10
  cmd $DIR/cluster $CLUSTER remove ${BASE}_REP
fi

if [ $DOPSM = 1 ]; then
  sleep 10
  cmd $DIR/execute_psm.sh $ARGS $PARAM -- $CLUSTERARG --remote_jobname ${BASE}_PSM --remote_nostatus
  while true; do
    sleep 10
    $DIR/cluster $CLUSTER shortlog ${BASE}_PSM > $TMPFILE 2>/dev/null
    fgrep "Workflows:" $TMPFILE | tail -n 1
    if [ "`tail -n 1 $TMPFILE`" = "Done." ]; then
      break
    fi
    sleep 60
  done
  if [ `fgrep "Workflows:" $TMPFILE | tail -n 1 | fgrep ' Failed 0, ' | wc -l ` -eq 0 ]; then
    exit 1;
  fi

  cmd $DIR/cluster $CLUSTER verify ${BASE}_PSM ; sleep 10
  cmd $DIR/cluster $CLUSTER organize ${BASE}_PSM ; sleep 10
  cmd $DIR/cluster $CLUSTER download $WORK ${BASE}_PSM mzML; sleep 10
  cmd $DIR/cluster $CLUSTER download $WORK ${BASE}_PSM mzIdentML; sleep 10
  cmd $DIR/cluster $CLUSTER download $WORK ${BASE}_PSM PSM.tsv; sleep 10

  mkdir -p $WORK/SummaryReports
  cmd $DIR/cluster $CLUSTER download $WORK ${BASE}_PSM SummaryReports; sleep 10
  mv -f $WORK/SummaryReports/${BASE}_PSM.qcmetrics.tsv $WORK/SummaryReports/${BASE}.qcmetrics.tsv
  echo ""
else
  # upload mzIdentML
  cmd $DIR/cluster $CLUSTER upload $WORK/mzIdentML ${BASE}_PSM mzIdentML > /dev/null; sleep 10
fi

if [ $DOREP = 1 ]; then
  cmd $DIR/cluster $CLUSTER manifest ${BASE}_PSM mzIdentML > $WORK/SummaryReports/${BASE}.mzIdentML.txt
  cp $PARAM $SAMPLE $WORK/SummaryReports
  for B in $BATCH; do
    cp "$WORK/$B.txt" $WORK/SummaryReports
  done

  sleep 10
  cmd $DIR/execute_report.sh $ARGS $WORK/SummaryReports/${BASE}.params -- $CLUSTERARG --remote_jobname ${BASE}_REP --remote_nostatus
  while true; do
    sleep 10
    $DIR/cluster $CLUSTER shortlog ${BASE}_REP > $TMPFILE 2>/dev/null
    fgrep "Workflows:" $TMPFILE | tail -n 1
    if [ "`tail -n 1 $TMPFILE`" = "Done." ]; then
      break
    fi
    sleep 60
  done
  if [ `fgrep "Workflows:" $TMPFILE | tail -n 1 | fgrep ' Failed 0, ' | wc -l ` -eq 0 ]; then
    exit 1;
  fi

  sleep 10
  cmd $DIR/cluster $CLUSTER download $WORK/SummaryReports ${BASE}_REP
fi

if [ $DOPSM = 1 ]; then
  sleep 10
  cmd $DIR/cluster $CLUSTER remove ${BASE}_PSM
fi
if [ $DOREP = 1 ]; then
  sleep 10
  cmd $DIR/cluster $CLUSTER remove ${BASE}_REP
fi
echo "Done."
