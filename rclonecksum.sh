#!/bin/sh
DIR=`dirname "$0"`

TMP1=`mktemp` || exit 1
TMP2=`mktemp` || exit 1
TMP3=`mktemp -d` || exit 1

BASE=`echo "$1" | sed -e 's/^.*\///'`
DIR1=`echo "$1" | sed -e 's/[^/]*$//'`
TMP4="$TMP3/$BASE.cksum"
$DIR/cptacdcc/rclone/rclone/rclone --config $DIR/.rclone.conf ls "$1" | grep -i '\.raw$' | sort -k2,2 > $TMP1
$DIR/cptacdcc/rclone/rclone/rclone --config $DIR/.rclone.conf md5sum "$1" | grep -i '\.raw$' | sort -k2,2 > $TMP2
paste $TMP1 $TMP2 | awk '$2 == $4 {printf("%s\t\t%s\t%s\n",$3,$1,$2);}' > "$TMP4"
if [ `wc -l < $TMP1` != `wc -l < "$TMP4"` ]; then
  rm -rf $TMP1 $TMP2 $TMP3
  echo "something went wrong!" 2>&1
  exit 1
fi
cat "$TMP4"
$DIR/cptacdcc/rclone/rclone/rclone --config $DIR/.rclone.conf copy "$TMP4" "$DIR1"
rm -rf $TMP1 $TMP2 $TMP3
