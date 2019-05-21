#!/bin/sh

if [ "$1" = "" ]; then
  echo "Usage: $0 <dest> <files...>" 1>&2
  exit 1
fi

DEST="$1"
shift;
BASE=`dirname "$DEST"`
DEST=`basename "$DEST"`
DATE=`date "+%Y%m%d"`
CDAP_VERSION="CPTAC3-CDAP.r1.${DATE}"

mkdir -p "$BASE/$DEST"
mkdir -p "$BASE/$DEST/${DEST}_mzML"
mkdir -p "$BASE/$DEST/${DEST}_PSM"
mkdir -p "$BASE/$DEST/${DEST}_PSM/${DEST}_PSM.${CDAP_VERSION}_mzIdentML"
mkdir -p "$BASE/$DEST/${DEST}_PSM/${DEST}_PSM.${CDAP_VERSION}_tsv"
MZML="$BASE/$DEST/${DEST}_mzML"
MZID="$BASE/$DEST/${DEST}_PSM/${DEST}_PSM.${CDAP_VERSION}_mzIdentML"
PSM="$BASE/$DEST/${DEST}_PSM/${DEST}_PSM.${CDAP_VERSION}_tsv"
QCMETRICS="$BASE/qcmetrics.txt"

touch "$MZML.cksum"
touch "$PSM.cksum"
touch "$MZID.cksum"

for f in "$@"; do
  case "$f" in
    *.mzML.gz) echo "$f"; cp -f "$f" "$MZML";;
    *.mzid.gz) echo "$f"; cp -f "$f" "$MZID";;
    *.psm)     echo "$f"; cp -f "$f" "$PSM";;
    *.qcmetrics.tsv) echo "$f"; [ -s "$QCMETRICS" ] && tail -n 1 "$f" >> "$QCMETRICS" || cat "$f" > "$QCMETRICS" ;;
    *.cksum) echo "$f"; grep '.mzML.gz$' "$f" >> "$MZML.cksum"; grep '.mzid.gz$' "$f" >> "$MZID.cksum"; grep '.psm$' "$f" >> "$PSM.cksum";;
  esac
done
