#!/bin/sh

DIR=`dirname "$0"`
DIR=`readlink -f "$DIR"`
CKSUM="$DIR/cptacdcc/cksum.sh"

rm -rf forportal
mkdir -p forportal
cp *.txt *.html *.tsv *.cksum forportal
if [ -d forportal ]; then
  cd forportal
  DIR1=`pwd`
  DIR1=`basename $DIR1`
  if [ "$DIR1" = "forportal" ]; then
    rm -f *pars* *mayu* *mzIdentML* *raw* *.peptide.*
    sed -i '/-raw/d' *.cksum
    sed -i '/\.peptide\./d' *.cksum
    $CKSUM -q -q -V -f *.cksum . 
    ls -l 
  fi
fi
