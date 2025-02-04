#!/bin/sh

set -x
VERSION=`cat VERSION`
DIR=${PWD}/dist
TGZ=cptac-galaxy-$VERSION.python36.tgz
TGZ1=cptac-galaxy-$VERSION.linux-x86_64.tgz
LNK=$DIR/cptac-galaxy.python36.tgz
LNK1=$DIR/cptac-galaxy.linux-x86_64.tgz
FORCE=0
if [ "$1" = "-F" ]; then
  FORCE=1
  shift
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
PY="clusters.py configure.py dfcollection.py execute.py launch.py lockfile.py terminate.py wfdownload.py wfupload.py dsdownload.py login.py awsresources.py cluster.py fixqcmetrics.py expand_wftemplate.py pdcsetup.py clustermanager.py PDC.py"
TXT="template* Identity*"
CKSUM=""
INI=".defaults.ini"
SH="organize0.sh organize1.sh organize1all.sh update.sh dfcoll.sh build.sh build.py execute_cdap.sh execute_psm.sh execute_report.sh withdrawn.sh execute_cdap_on_cluster.sh execute_mzml.sh forportal.sh"
rm -f cptacdcc
ln -s cptacdcc.python/cptacdcc cptacdcc
( cd cptacdcc;  ./update.sh )
tar --exclude "seqdb/.git" --exclude "workflows/.git" -czhf "$DIR/$TGZ" $PY $TXT $CKSUM $SH $INI VERSION workflows seqdb data etc docs cptacdcc
# cp setup.python36.sh $DIR/cptac-galaxy-setup.python36.sh
# cp setup.linux-x86_64.sh $DIR/cptac-galaxy-setup.linux-x86_64.sh
# rm -f $DIR/cptac-galaxy-setup.sh
# ln -s $DIR/cptac-galaxy-setup.cptac-galaxy-setup.linux-x86_64.sh $DIR/cptac-galaxy-setup.sh
./build.sh
# rm -f "$LNK1" "$DIR/$TGZ1"
mv -f "$TGZ1" "$DIR/$TGZ1"
# ln -s "$DIR/$TGZ1" $LNK1
# rm -f "$LNK2"
# ln -s "$DIR/$TGZ2" $LNK2

rm -f $DIR/cptac-galaxy-$VERSION
( cd $DIR; md5sum cptac-galaxy-$VERSION.*.tgz > cptac-galaxy-$VERSION.md5 ; touch cptac-galaxy-$VERSION.txt; touch cptac-galaxy-$VERSION.empty.txt )
if [ "$1" ]; then 
  for comment in "$@"; do 
    echo "* $comment" >> $DIR/cptac-galaxy-$VERSION.txt
  done
fi

gh release delete "CPTAC-Galaxy-$VERSION" -y 
git push --delete origin "refs/tags/CPTAC-Galaxy-$VERSION"
git tag --delete "CPTAC-Galaxy-$VERSION"

( cd workflows; \
  gh release delete "CPTAC-Galaxy-$VERSION" -y ; \
  git push --delete origin "refs/tags/CPTAC-Galaxy-$VERSION" ; \
  git tag --delete "CPTAC-Galaxy-$VERSION" )

( cd seqdb; \
  gh release delete "CPTAC-Galaxy-$VERSION" -y ; \
  git push --delete origin "refs/tags/CPTAC-Galaxy-$VERSION" ; \
  git tag --delete "CPTAC-Galaxy-$VERSION" )

gh release create "CPTAC-Galaxy-$VERSION" $DIR/cptac-galaxy-$VERSION.*.tgz $DIR/cptac-galaxy-$VERSION.md5 -t "CPTAC-Galaxy-$VERSION" -F $DIR/cptac-galaxy-$VERSION.txt
( cd workflows; gh release create "CPTAC-Galaxy-$VERSION" -t "CPTAC-Galaxy-$VERSION" -F $DIR/cptac-galaxy-$VERSION.empty.txt )
( cd seqdb; gh release create "CPTAC-Galaxy-$VERSION" -t "CPTAC-Galaxy-$VERSION" -F $DIR/cptac-galaxy-$VERSION.empty.txt )
rclone copy $DIR/$TGZ1 cptac-s3:cptac-cdap.georgetown.edu
rclone copy $DIR/$TGZ cptac-s3:cptac-cdap.georgetown.edu
rclone copyto setup.linux-x86_64.sh cptac-s3:cptac-cdap.georgetown.edu/cptac-galaxy-setup.linux-x86_64.sh
rclone copyto setup.python36.sh cptac-s3:cptac-cdap.georgetown.edu/cptac-galaxy-setup.python36.sh
aws --profile cptac s3api put-object --bucket cptac-cdap.georgetown.edu --key "cptac-galaxy-setup.sh" --website-redirect-location "/cptac-galaxy-setup.linux-x86_64.sh"
aws --profile cptac s3api put-object --bucket cptac-cdap.georgetown.edu --key "cptac-galaxy.python36.tgz" --website-redirect-location "/$TGZ"
aws --profile cptac s3api put-object --bucket cptac-cdap.georgetown.edu --key "cptac-galaxy.linux-x86_64.tgz" --website-redirect-location "/$TGZ1"
