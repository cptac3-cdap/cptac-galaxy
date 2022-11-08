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

  SPECIES="{Human,Mouse,Rat,Human+Mouse}"
  PROTEOME="{Proteome,Phosphoproteome,Acetylome,Ubiquitylome,Glycoproteome}"
  QUANT="{TMT6,TMT10,TMT11,TMT16,TMT18,iTRAQ,Label-free}"
  TARGETFDR="<Protein FDR%>" #Optional. Default is 1.0%
  INITSPECFDR="<Spec. FDR%>" #Optional. Default is \$TARGETFDR
  PROTOCOL="{CPTAC3-CDAP,...}" #Optional. Default is CPTAC3-CDAP
  VERSION="{1,2,...}" #Optional. Default is no version

Files <base>.mzIdentML.txt, <base>.sample.txt, <base>.qcmetrics.tsv, <base>.label.txt  are expected in the same directory as <base>.params.

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

if [ "$1" = "" ]; then
  help "Parameter file not provided on the command-line"
fi

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
LABF="$WORK/$BASE.label.txt"

shift
if [ "$1" = "--" ]; then
  shift
fi

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

if [ "$BATCH" = "" -a -f "$LABF" ]; then
    BATCH=`basename "$LABF" .txt`
fi

if [ "$TARGETFDR" = "" ]; then
    TARGETFDR="1.0"
fi
if [ "$INITSPECFDR" = "" ]; then
    INITSPECFDR="$TARGETFDR"
fi
if [ "$PROTOCOL" = "" ]; then
    PROTOCOL="CPTAC3-CDAP"
fi


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

case $SPECIES in
  Human|Mouse|Rat|Human+Mouse) ;;
  *) help "Bad SPECIES $SPECIES in parameter file" ;;
esac
                                                                                                                             
case $PROTEOME in
  Proteome|Phosphoproteome|Acetylome|Ubiquitylome|Glycoproteome) ;;
  *) help "Bad PROTEOME $PROTEOME in parameter file" ;;
esac

case $QUANT in
  TMT6|TMT10|TMT11|TMT16|TMT18|iTRAQ|Label-Free) ;;
  *) help "Bad QUANT $QUANT in parameter file" ;;
esac

SPECIES_FOR_WF="$SPECIES"
if [ "$SPECIES" = "Human+Mouse" ]; then
  SPECIES_FOR_WF="Human-Mouse Xenograft"
fi
QUANT_FOR_WF="$QUANT"
PROTEOME_FOR_WF="$PROTEOME"
if [ "$PROTEOME" = "Proteome" ]; then
  PROTEOME_FOR_WF="Whole Proteome"
fi

VERSION_FOR_WF=""
if [ "$VERSION" != "" ]; then
  VERSION_FOR_WF=" (v$VERSION)"
fi

if [ $GENEFDR -eq 1 ]; then
  FILES="--file \"$MZID\" "
  PARAM="--param cdapreports_parsnipfdr:1:initspecfdr:$INITSPECFDR --param cdapreports_parsnipfdr:1:targetprotfdr:$TARGETFDR"
  WORKFLOW="Summary Reports: $SPECIES_FOR_WF Gene FDR Estimation"
else
  BATCHFILES=""
  for B in $BATCH; do
      BATCHFILES="$BATCHFILES --file \"$WORK/$B.txt\" "
  done
  FILES="--file \"$MZID\" --file \"$SAMP\" $BATCHFILES --file \"$QCMT\" "
  PARAM="--param cdapreports_parsnipfdr:1:initspecfdr:$INITSPECFDR --param cdapreports_parsnipfdr:1:targetprotfdr:$TARGETFDR"
  WORKFLOW="${PROTOCOL}${VERSION_FOR_WF}: Summary Reports - $SPECIES_FOR_WF, $QUANT_FOR_WF, $PROTEOME_FOR_WF"
fi

echo "PARAMETERS:"
echo "Species: $SPECIES"
echo "Proteome: $PROTEOME"
echo "Quantitation: $QUANT"
echo "Label Reagent Batch IDs: $BATCH"
echo "Workflow: $WORKFLOW"
echo "Protocol: $PROTOCOL"
echo "Version: $VERSION"
echo ""

WORKFLOW="--workflow \"$WORKFLOW\" "
CMD="$DIR/execute $WORKFLOW $FILES $PARAM --max_retries 0 $EXTRA"

if [ $ECHO -eq 1 ]; then
  echo "$CMD"
else
  sh -c "$CMD" 
fi

