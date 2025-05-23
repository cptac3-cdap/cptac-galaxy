#!/bin/sh
rm -rf build
( cd cptacdcc.linux-`uname -m`/cptacdcc; ./update.sh )
# rm -rf cptacdcc
# ln -s cptacdcc.linux-`uname -m`/cptacdcc cptacdcc
rm -rf build/exe.linux-`uname -m`-3.6
./bin/python build.py build
cp /lib64/libssl.so.10 /lib64/libcrypto.so.10 build/exe.linux-`uname -m`-3.6/lib
cp -r cptacdcc.linux-`uname -m`/cptacdcc build/exe.linux-`uname -m`-3.6
TGZ="cptac-galaxy-`cat VERSION`.linux-`uname -m`.tgz"
rm -f cptac-galaxy-*.linux-`uname -m`.tgz
tar --exclude "./seqdb/.git" --exclude "./workflows/.git" -cz -C build/exe.linux-`uname -m`-3.6 -f "$TGZ" .
# rm -rf cptacdcc
# ln -s cptacdcc.python/cptacdcc cptacdcc
