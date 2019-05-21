#!/bin/sh

if [ "$2" = "" ]; then
  echo "Usage: $0 <name> <dir> [ <dir> ]" 1>&2
  exit 1
fi

NAME="$1"
shift;
if [ -d "$NAME" ]; then
  echo "Bad study name: $NAME" 1>&2
  exit 1
fi

DIR=`dirname "$0"`
for d in "$@"; do
  base=`basename $d`
  $DIR/organize1.sh "$NAME" `pwd` $base $d/*
  rm -rf "$d"
done
