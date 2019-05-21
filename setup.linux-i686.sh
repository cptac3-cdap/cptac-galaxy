#!/bin/sh

VERSION=""
if [ "$1" != "" ]; then
  VERSION="-$1"
fi

mkdir -p cptac-galaxy
cd cptac-galaxy
wget -q -O - http://edwardslab.bmcb.georgetown.edu/software/downloads/Galaxy/cptac-galaxy$VERSION.linux-i686.tgz | tar zxvf -
echo "linux-i686" > PLATFORM
echo "CPTAC-Galaxy `cat VERSION` (`cat PLATFORM`)"
