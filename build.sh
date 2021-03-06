#!/bin/sh
rm -rf build
rm -rf cptacdcc
ln -s cptacdcc.linux-`uname -m`/cptacdcc cptacdcc
( cd cptacdcc; ./cptacdcc_update.sh )
./bin/python build.py build
TGZ="cptac-galaxy-`cat VERSION`.linux-`uname -m`.tgz"
rm -f cptac-galaxy-*.linux-`uname -m`.tgz
tar cz -C build/exe.linux-`uname -m`-2.7 -f "$TGZ" .
rm -rf cptacdcc
ln -s cptacdcc.python27/cptacdcc cptacdcc
