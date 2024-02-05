#!/bin/sh

help() {
  if [ "$1" != "" ]; then
    echo "" 1>&2
    echo "$1" 1>&2
  fi
  cat <<EOF | fmt -w80 -s 1>&2

cptac-galaxy/execute_psm.sh [ options ] <base>.params

Options:

  -n	Do not execute commands, just show commands to be executed. 
  -v	Verbose logging. 
  -h	Help text.

Parameter file sets the follwing variables:

  SPECIES="{Human,Mouse,Rat,Human+Mouse}"
  PROTEOME="{Proteome,Phosphoproteome,Acetylome,Ubiquitylome,Glycoproteome}"
  QUANT="{TMT6,TMT10,MS3-TMT10,TMT11,MS3-TMT11,TMT16,MS3-TMT16,TMT18,MS3-TMT18,iTRAQ,Label-Free}"
  INST="{Thermo Velos HCD,Thermo Q-Exactive HCD,Thermo Q-Exactive CID}" #Use Q-Exactive for all high-accuracy instruments
  PROTOCOL="{CPTAC4-CDAP,...}" #Optional. Default is CPTAC4-CDAP.
  VERSION="{1,2,...}" #Optional. Default is version 2.1.

File <base>.RAW.txt is expected in the same directory as <base>.params.

EOF
  exit 1;
}

ECHO=0
VERBOSE=0
while getopts ":nvgh" o ; do
        case $o in
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
EXECUTE="$DIR/execute.sh"
PARAM=`readlink -f "$1"`
. "$PARAM"
BASE=`basename "$PARAM" .params`
WORK=`dirname "$PARAM"`
RAW="$WORK/$BASE.RAW.txt"

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
if [ "$INST" = "" ]; then
    help "INST missing from parameter file $1"
fi
if [ "$PROTOCOL" = "" ]; then
    PROTOCOL="CPTAC4-CDAP"
fi
if [ "$VERSION" = "" ]; then
    VERSION="2.1"
fi

if [ ! -f "$RAW" ]; then
    help "RAW file \"$RAW\" not found"
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
  TMT6|TMT10|MS3-TMT10|TMT11|MS3-TMT11|TMT16|MS3-TMT16|TMT18|MS3-TMT18|iTRAQ|Label-Free) ;;
  *) help "Bad QUANT $QUANT in parameter file" ;;
esac

case "$INST" in
  "Thermo Velos HCD"|"Thermo Q-Exactive HCD"|"Thermo Q-Exactive CID") ;;
  *) help "Bad INST $INST in parameter file" ;;
esac

if [ "$QUANT" = "TMT10" ]; then
  QUANT_FOR_PSM_WF="TMT 10-plex"
elif [ "$QUANT" = "TMT11" ]; then
  QUANT_FOR_PSM_WF="TMT 11-plex"
elif [ "$QUANT" = "TMT16" ]; then
  QUANT_FOR_PSM_WF="TMT 16-plex"
elif [ "$QUANT" = "TMT18" ]; then
  QUANT_FOR_PSM_WF="TMT 18-plex"
elif [ "$QUANT" = "MS3-TMT10" ]; then
  QUANT_FOR_PSM_WF="MS3-TMT 10-plex"
elif [ "$QUANT" = "MS3-TMT11" ]; then
  QUANT_FOR_PSM_WF="MS3-TMT 11-plex"
elif [ "$QUANT" = "MS3-TMT16" ]; then
  QUANT_FOR_PSM_WF="MS3-TMT 16-plex"
elif [ "$QUANT" = "MS3-TMT18" ]; then
  QUANT_FOR_PSM_WF="MS3-TMT 18-plex"
elif [ "$QUANT" = "TMT6" ]; then
  QUANT_FOR_PSM_WF="TMT 6-plex"
elif [ "$QUANT" = "iTRAQ" ]; then
  QUANT_FOR_PSM_WF="iTRAQ 4-plex"
elif [ "$QUANT" = "Label-Free" ]; then
  QUANT_FOR_PSM_WF="Label-free"
fi

if [ "$SPECIES" = "Human" ]; then
  SPECIES_FOR_PSM_WF=""
elif [ "$SPECIES" = "Mouse" ]; then 
  SPECIES_FOR_PSM_WF=" for Mouse"
elif [ "$SPECIES" = "Rat" ]; then 
  SPECIES_FOR_PSM_WF=" for Rat"
elif [ "$SPECIES" = "Human+Mouse" ]; then
  SPECIES_FOR_PSM_WF=" for Human-Mouse Xenograft"
fi

PROT_FOR_WF=""
if [ "$PROTEOME" = "Phosphoproteome" ]; then
  PROT_FOR_WF="Phospho "
elif [ "$PROTEOME" = "Acetylome" ]; then
  PROT_FOR_WF="Acetyl "
elif [ "$PROTEOME" = "Ubiquitylome" ]; then
  PROT_FOR_WF="Ubiquitylation "
elif [ "$PROTEOME" = "Glycoproteome" ]; then
  PROT_FOR_WF="Deglycosylated N-Glycosite "
fi 

VERSION_FOR_WF=""
if [ "$VERSION" != "" ]; then
  VERSION_FOR_WF=" (v$VERSION)"
fi

WORKFLOW="${PROTOCOL}${VERSION_FOR_WF}: MSGF+ $PROT_FOR_WF$QUANT_FOR_PSM_WF ($INST)$SPECIES_FOR_PSM_WF"
DATA="--data \"$RAW\" "

echo "PARAMETERS:"
echo "Species: $SPECIES"
echo "Proteome: $PROTEOME"
echo "Quantitation: $QUANT"
echo "Instrument: $INST"
echo "Protocol: $PROTOCOL"
echo "Protocol Version: $VERSION"
echo "Workflow: $WORKFLOW"
echo ""

WORKFLOW="--workflow \"$WORKFLOW\" "
CMD="$DIR/execute $WORKFLOW $DATA $EXTRA"

if [ $ECHO -eq 1 ]; then
  echo "$CMD"
else
  sh -c "$CMD" 
fi

