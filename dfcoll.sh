#!/bin/sh
# set -x
DIR=`dirname "$0"`

if [ -f "$DIR/cptacdcc/cptacportal.py" ]; then
  extn=".py"
else
  extn=".sh"
fi

dcclist() {
  "$DIR/cptacdcc/cptacportal$extn" "dccnodescrape" "$2" | awk -v R="$1" 'NR > 1 && $1 ~ /\.cksum$/ {print R,$1}' | sed 's/\.cksum//'
}

portallist() {
  "$DIR/cptacdcc/cptacportal$extn" "publicnodescrape" --accept "$1" | awk 'NR > 1 && $1 ~ /\.cksum$/ {print "portal",$1}' | sed 's/\.cksum//'
}

urllist() {
  wget -q -O - "$1" | sed -e 's/[<][^<]*[>]/ /g' | awk 'NR > 1 && $1 ~ /\.cksum$/ {print "url",$1}' | sed 's/\.cksum//'
}

case "$1" in
  dcc*)  CMD="dcclist $1 $2";;
  portal) CMD="portallist $2";;
  url)    CMD="urllist  $2";;
  *)      echo "Bad resource: $1" 1>&2; exit 1;;
esac

$CMD | awk -v P="$2" '{printf("%s\t%s\t%s/%s.cksum\n",$2,$1,P,$2);}'
