#!/bin/sh

VERSION=""
if [ "$1" != "" ]; then
  VERSION="-$1"
fi

if [ ! -f update.sh ]; then
  echo "Please execute in cptac-galaxy directory" 1>&2
  exit 1
fi

if [ -d cptacdcc/rclone ]; then
  rm -rf cptacdcc/rclone
fi
PLATFORM=`cat PLATFORM`
wget -q -O - http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com/cptac-galaxy$VERSION.$PLATFORM.tgz | tar xvzf -
if [ "$PLATFORM" = "python36"  ]; then
  sed -i "s%#\!bin/python$%#\!$PWD/bin/python%" *.py
fi
echo "CPTAC-Galaxy `cat VERSION` (`cat PLATFORM`)"
