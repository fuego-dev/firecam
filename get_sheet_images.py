# Copyright 2018 The Fuego Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""

This script reads cells in Fuego Images sheet that contains names of images.
It then downloads those iamges.

"""

import sys
import os
fuegoRoot = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import collect_args
import goog_helper


def readFromMainSheet(service, cellRange):
    return goog_helper.readFromSheet(service, settings.imagesSheet, cellRange)


def main():
    reqArgs = [
        ["l", "imgClass", "image class (smoke, nonSmoke, motion)"],
        ["o", "outputDir", "local directory to save images and segments"]
    ]
    optArgs = [
        ["c", "cellRange", "cells to read and process"],
        ["i", "image", "file name of the image in google drive"]
    ]
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])

    googleServices = goog_helper.getGoogleServices(settings, args)
    if args.cellRange:
        values = readFromMainSheet(googleServices['sheet'], args.cellRange)
        for [fileName] in values:
            print(fileName)
            goog_helper.downloadClassImage(googleServices['drive'], settings.IMG_CLASSES,
                                            args.imgClass, fileName, args.outputDir)
    if args.image:
            goog_helper.downloadClassImage(googleServices['drive'], settings.IMG_CLASSES,
                                            args.imgClass, args.image, args.outputDir)

if __name__=="__main__":
    main()
