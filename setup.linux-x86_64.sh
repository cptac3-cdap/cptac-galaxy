#!/bin/sh

VERSION=""
if [ "$1" != "" ]; then
  VERSION="-$1"
fi

mkdir -p cptac-galaxy
cd cptac-galaxy
wget -q -O - http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com/cptac-galaxy$VERSION.linux-x86_64.tgz | tar zxvf -
echo "linux-x86_64" > PLATFORM
echo "CPTAC-Galaxy `cat VERSION` (`cat PLATFORM`)"
