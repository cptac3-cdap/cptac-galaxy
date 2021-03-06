#!/bin/sh

help() {
  if [ "$1" != "" ]; then
    echo "" 1>&2
    echo "$1" 1>&2
  fi
  cat <<EOF | fmt -w80 -s 1>&2

cptac-galaxy/execute_report.sh [ options ] <base>.params \ 
                  [ -- ./cptac-galaxy/execute arguments ]

Options:

  -g	Use Gene FDR estimation workflow.
  -n	Do not execute command, just show command to be executed. 
  -v	Verbose logging. 
  -h	Help text.

Parameter file sets the follwing variables:

  SPECIES={Human,Mouse,Rat,Human+Mouse}
  PROTEOME={Proteome,Phosphoproteome}
  QUANT={TMT6,TMT10,TMT11,iTRAQ}
  BATCH=<TMT label batch>
  SPECFDR=<FDR% for parsimony <= 1.0>

Files <base>.mzIdentML.txt, <base>.sample.txt, <base>.qcmetrics.tsv, \$BATCH.txt are expected in the same directory as <base>.params.

EOF
  exit 1;
}

ECHO=0
VERBOSE=0
GENEFDR=0
while getopts ":nvgh" o ; do
        case $o in
		g ) GENEFDR=1;;
                n ) ECHO=1;;
                v ) VERBOSE=1;;
                h ) help "";;
                * ) help "Invalid option: -$OPTARG"
        esac
done

if [ $VERBOSE -eq 1 ]; then
  set -x
fi

shift $(($OPTIND - 1)) 

DIR=`dirname "$0"`
DIR=`readlink -f "$DIR"`
EXECUTE="$DIR/execute"
PARAM=`readlink -f $1`
. "$PARAM"
BASE=`basename "$PARAM" .params`
WORK=`dirname "$PARAM"`
MZID="$WORK/$BASE.mzIdentML.txt"
SAMP="$WORK/$BASE.sample.txt"
QCMT="$WORK/$BASE.qcmetrics.tsv"

shift; shift

EXTRA="$@"

if [ "$SPECIES" = "" ]; then
    help "SPECIES missing from parameter file $1"
fi
if [ "$PROTEOME" = "" ]; then
    help "PROTEOME missing from parameter file $1"
fi
if [ "$QUANT" = "" ]; then
    help "QUANT missing from parameter file $1"
fi
if [ "$SPECFDR" = "" ]; then
    help "SPECFDR missing from parameter file $1"
fi
# if [ "$BATCH" = "" ]; then
#     help "BATCH missing from parameter file $1"
# fi

if [ ! -f "$MZID" ]; then
    help "MZID file \"$MZID\" not found"
fi
if [ ! -f "$SAMP" ]; then
    help "Sample file \"$SAMP\" not found"
fi
for B in $BATCH; do
  if [ ! -f "$WORK/$B.txt" ]; then
    help "BATCH file \"$WORK/$B.txt\" not found"
  fi
done
if [ ! -f "$SAMP" ]; then
    help "Sample file \"$SAMP\" not found"
fi
if [ ! -f "$QCMT" ]; then
    help "QC metrics file \"$QCMT\" not found"
fi

SPECIES_FOR_WF="$SPECIES"
if [ "$SPECIES" = "Human+Mouse" ]; then
  SPECIES_FOR_WF="Human-Mouse Xenograft"
fi
QUANT_FOR_WF="$QUANT"
PROTEOME_FOR_WF="$PROTEOME"
if [ "$PROTEOME" = "Proteome" ]; then
  PROTEOME_FOR_WF="Whole Proteome"
fi

if [ $GENEFDR -eq 1 ]; then
  FILES="--file \"$MZID\" "
  PARAM="--param cdapreports_parsnipmayug:1:specfdr:$SPECFDR"
  WORKFLOW="Summary Reports: $SPECIES_FOR_WF Gene FDR Estimation"
else
  BATCHFILES=""
  for B in $BATCH; do
      BATCHFILES="$BATCHFILES --file \"$WORK/$B.txt\" "
  done
  FILES="--file \"$MZID\" --file \"$SAMP\" $BATCHFILES --file \"$QCMT\" "
  if [ "$PROTEOME" = "Proteome"  ]; then
    PARAM="--param cdapreports_parsnip:1:specfdr:$SPECFDR"
  elif [ "$PROTEOME" = "Phosphoproteome" ]; then
    PARAM="--param cdapreports_parsnip:1:specfdr:$SPECFDR --param cdapreports_parsnip:2:specfdr:$SPECFDR"
  fi
  WORKFLOW="Summary Reports: $SPECIES_FOR_WF, $QUANT_FOR_WF, $PROTEOME_FOR_WF"
fi
WORKFLOW="--workflow \"$WORKFLOW\" "

CMD="$DIR/execute $WORKFLOW $FILES $PARAM $EXTRA"

if [ $ECHO -eq 1 ]; then
  echo "$CMD"
else
  sh -c "$CMD" 
fi

