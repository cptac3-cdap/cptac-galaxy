#!/bin/sh
PYTHON=${PYTHON:-python}
PYTHON=`which "$PYTHON"`
PYTHON=`readlink -f "$PYTHON"`
if [ ! -e "$PYTHON" ]; then
  echo "Can't find python absolute path, set \"PYTHON\" as needed." 1>&2
  exit 1
fi
PYBIN=`dirname "$PYTHON"`
VENV="$PYBIN/virtualenv"
if [ ! -e "$VENV" ]; then
  echo "virtualenv not installed for python $PYTHON" 1>&2
  exit 1
fi
PYTHON=`$VENV -h | sed -n 's/^ *[(]\(\/.*\)[)] *$/\1/p'`
PYVER=`$PYTHON --version 2>&1`
echo "Install using $PYVER at $PYTHON"
echo "Set the python binary via environment variable \"PYTHON\" as needed."
echo "Stop the install using <Ctrl-C> if this is not intended!"
sleep 10

VERSION=""
if [ "$1" != "" ]; then
  VERSION="-$1"
fi

$VENV cptac-galaxy
cd cptac-galaxy
. ./bin/activate
./bin/easy_install awscli
./bin/easy_install bioblend==0.9.0
wget -q -O - http://edwardslab.bmcb.georgetown.edu/software/downloads/Galaxy/cptac-galaxy$VERSION.python27.tgz | tar zxvf -
( cd lib/python2.7/site-packages/bioblend-0.9.0-py2.7.egg; patch -p0 ) < etc/bioblend-0.9.0.patch.txt
sed -i "s%#\!bin/python$%#\!$PWD/bin/python%" *.py
echo "python27" > PLATFORM
echo "CPTAC-Galaxy `cat VERSION` (`cat PLATFORM`)"
