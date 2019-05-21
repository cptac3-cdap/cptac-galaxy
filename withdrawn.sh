#!/bin/sh

BAD="$1"
shift

for f in "$@"; do
  if fgrep -q "$BAD" "$f"; then
    echo $f
    sed -i -e "s/$BAD/Withdrawn:$BAD/g" $f
  fi
done
