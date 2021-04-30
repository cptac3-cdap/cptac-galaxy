#!/bin/sh

help() {
  if [ "$1" != "" ]; then
    echo "" 1>&2
    echo "$1" 1>&2
  fi
  cat <<EOF | fmt -w80 -s 1>&2

cptac-galaxy/execute_mzml.sh [ options ] <base>.params

Options:

  -n	Do not execute commands, just show commands to be executed. 
  -v	Verbose logging. 
  -h	Help text.

Parameter file sets the follwing variable:

  INST="{Thermo Velos HCD,Thermo Q-Exactive HCD}" #Use Q-Exactive for all high-accuracy instruments

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

if [ "$INST" = "" ]; then
    help "INST missing from parameter file $1"
fi

if [ ! -f "$RAW" ]; then
    help "RAW file \"$RAW\" not found"
fi

case "$INST" in
  "Thermo Velos HCD"|"Thermo Q-Exactive HCD") ;;
  *) help "Bad INST $INST in parameter file" ;;
esac


WORKFLOW="Raw to mzML.gz"
DATA="--data \"$RAW\" "

echo "PARAMETERS:"
echo "Instrument: $INST"
echo "Workflow: $WORKFLOW"
echo ""

WORKFLOW="--workflow \"$WORKFLOW\" "
CMD="$DIR/execute $WORKFLOW $DATA $EXTRA"

if [ $ECHO -eq 1 ]; then
  echo "$CMD"
else
  sh -c "$CMD" 
fi

