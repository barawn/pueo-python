#!/bin/bash
# this script builds the SURF portion of pueo-python
# in a target.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

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

cp ${SCRIPT_DIR}/pueo/surf/*.py $DEST/pueo/surf/
cp ${SCRIPT_DIR}/pueo/common/__init__.py $DEST/pueo/common/
for p in ${COMMON_FILES} ; do
    cp ${SCRIPT_DIR}/pueo/common/$p $DEST/pueo/common/
done
