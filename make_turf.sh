#!/bin/bash

# for now just friggin grab everything
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

DEST=$1

mkdir -p $DEST/pueo/surf
mkdir -p $DEST/pueo/turf
mkdir -p $DEST/pueo/turfio
mkdir -p $DEST/pueo/common

cp ${SCRIPT_DIR}/pueo/surf/*.py $DEST/pueo/surf/
cp ${SCRIPT_DIR}/pueo/turf/*.py $DEST/pueo/turf/
cp ${SCRIPT_DIR}/pueo/turfio/*.py $DEST/pueo/turfio/
# common has subdirs, no one else does
cp ${SCRIPT_DIR}/pueo/common/*.py $DEST/pueo/common/
for i in `cd ${SCRIPT_DIR}/pueo/common ; ls -d */ | grep -v __pycache__`
do
    mkdir $DEST/pueo/common/$i
    cp ${SCRIPT_DIR}/pueo/common/${i}*.py ${DEST}/pueo/common/$i
done

