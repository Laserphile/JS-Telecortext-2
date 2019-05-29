#!/bin/bash

BASE_URL=https://github.com/Laserphile/JS-Telecortex-2/releases/download
RELEASE=v0.1.1-alpha
BINARY=essential-build-artifacts-arm.zip
UNZIPPED_BINARY=essential-build-artifacts-arm

echo 'pwd'
pwd
echo 'ls'
ls

if [[ -f ./$BINARY ]]
then
  echo "zip file found"
  unzip -q $BINARY
  rm -rdf node_modules/opencv4nodejs node_modules/opencv-build
  cp -R $UNZIPPED_BINARY/ node_modules/
  exit 0
else
  echo "zip file not found"
  echo ./$BINARY
fi

if [[ -d ./UNZIPPED_BINARY ]]
then
  echo "folder found"
  rm -rdf node_modules/opencv4nodejs node_modules/opencv-build
  cp -R $UNZIPPED_BINARY/ node_modules/
  exit 0
else
  echo "folder not found"
  echo ./$UNZIPPED_BINARY
fi

URL="$BASE_URL/$RELEASE/$BINARY"

set -e
echo "Fetching from: $URL"
wget -q -O $BINARY "$URL"
file $BINARY
chmod a+x $BINARY
unzip -q $BINARY
rm -rdf node_modules/opencv4nodejs node_modules/opencv-build
cp -R $UNZIPPED_BINARY/ node_modules/