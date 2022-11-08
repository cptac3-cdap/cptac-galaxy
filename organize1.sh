#!/bin/sh

if [ "$3" = "" ]; then
  echo "Usage: $0 <dsname> <base> <dest> <files...>" 1>&2
  exit 1
fi

NAME="$1"
BASE="$2"
DEST="$3"
shift; shift; shift;
DEST=`basename "$DEST"`

MZML="$BASE/mzML/$DEST"
MZID="$BASE/mzIdentML/$DEST"
PSM="$BASE/PSM.tsv/$DEST"
SUMM="$BASE/SummaryReports"
QCMETRICS="$SUMM/$NAME.qcmetrics.tsv"
VERSIONS="$SUMM/$NAME.versions.log"

mkdir -p "$MZML"
mkdir -p "$MZID"
mkdir -p "$PSM"
mkdir -p "$SUMM"
touch "$MZML.cksum"
touch "$PSM.cksum"
touch "$MZID.cksum"

for f in "$@"; do
  case "$f" in
    *.mzML.gz) echo "$f"; mv -f "$f" "$MZML";;
    *.mzid.gz) echo "$f"; mv -f "$f" "$MZID";;
    *.psm)     echo "$f"; mv -f "$f" "$PSM";;
    *.qcmetrics.tsv) echo "$f"; [ -s "$QCMETRICS" ] && tail -n 1 "$f" >> "$QCMETRICS" || cat "$f" > "$QCMETRICS" ;;
    *.versions.log) echo "$f"; [ -s "$VERSIONS" ] && cat "$f" >> "${VERSIONS}.tmp" || cat "$f" > "${VERSIONS}.tmp" ;;
    *.cksum) echo "$f"; grep '.mzML.gz$' "$f" >> "$MZML.cksum"; grep '.mzid.gz$' "$f" >> "$MZID.cksum"; grep '.psm$' "$f" >> "$PSM.cksum";;
  esac
done

sort -u "${VERSIONS}.tmp" > "$VERSIONS"
rm -f "${VERSIONS}.tmp"
