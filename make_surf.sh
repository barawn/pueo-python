#!/bin/bash
# this script builds the SURF portion of pueo-python
# in a target.

COMMON_FILES="bf.py \
	      dev_submod.py \
	      wbspi.py \
	      serialcobsdevice.py \
	      pueo_utils.py"

if [ "$#" -ne 1 ] ; then
    echo "usage: make_surf.sh <destination directory>"
    echo "usage: (e.g. make_surf.sh path/to/tmpsquashfs/pylib/ )"
    exit 1
fi

DEST=$1
mkdir -p $DEST/pueo/surf
mkdir -p $DEST/pueo/common

cp pueo/surf/*.py $DEST/pueo/surf/
cp pueo/common/__init__.py $DEST/pueo/common/
for p in ${COMMON_FILES} ; do
    cp pueo/common/$p $DEST/pueo/common/
