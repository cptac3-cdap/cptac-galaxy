#!/bin/sh
# set -x
VERSION=`cat VERSION`
DIR=/data/www/html/software/downloads/Galaxy
TGZ=cptac-galaxy-$VERSION.python27.tgz
TGZ1=cptac-galaxy-$VERSION.linux-x86_64.tgz
TGZ2=cptac-galaxy-$VERSION.linux-i686.tgz
LNK=$DIR/cptac-galaxy.python27.tgz
LNK1=$DIR/cptac-galaxy.linux-x86_64.tgz
LNK2=$DIR/cptac-galaxy.linux-i686.tgz
FORCE=0
if [ "$1" = "-F" ]; then
  FORCE=1
fi
if [ -f "$DIR/$TGZ" -a "$FORCE" = "0" ]; then
    echo "Version $VERSION already exported, please increment version..."
    exit 1
fi
if [ -f "$DIR/$TGZ" ]; then
  rm -f "$DIR/$TGZ"
fi
if [ -f "$DIR/$TGZ1" ]; then
  rm -f "$DIR/$TGZ1"
fi
PY="clusters.py configure.py dfcollection.py execute.py launch.py lockfile.py terminate.py wfdownload.py wfupload.py dsdownload.py login.py awsresources.py cluster.py fixqcmetrics.py"
TXT=""
CKSUM=""
INI=".defaults.ini"
SH="organize0.sh organize1.sh organize1all.sh update.sh dfcoll.sh build.sh build.py execute_report.sh withdrawn.sh"
rm -f cptacdcc
ln -s cptacdcc.python27/cptacdcc cptacdcc
( cd cptacdcc;  ./cptacdcc_update.sh )
tar czf "$DIR/$TGZ" $PY $CKSUM $SH $INI VERSION workflows seqdb data etc cptacdcc
rm $LNK
ln -s "$DIR/$TGZ" $LNK
cp setup.python27.sh $DIR/cptac-galaxy-setup.python27.sh
cp setup.linux-x86_64.sh $DIR/cptac-galaxy-setup.linux-x86_64.sh
cp setup.linux-i686.sh $DIR/cptac-galaxy-setup.linux-i686.sh
rm -f $DIR/cptac-galaxy-setup.sh
ln -s $DIR/cptac-galaxy-setup.python27.sh $DIR/cptac-galaxy-setup.sh
./build.sh
rm -f "$LNK1" "$DIR/$TGZ1"
mv -f "$TGZ1" "$DIR/$TGZ1"
ln -s "$DIR/$TGZ1" $LNK1
rm -f "$LNK2"
ln -s "$DIR/$TGZ2" $LNK2
