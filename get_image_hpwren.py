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

Download images from HPWREN archive for given camera with date/time closest
to the specified time

"""

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import collect_args
import goog_helper
import img_archive

import os
import logging
import time, datetime, dateutil.parser


def main():
    reqArgs = [
        ["c", "cameraID", "ID (code name) of camera"],
        ["s", "startTime", "starting date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
    ]
    optArgs = [
        ["d", "cameraDirInput", "Human readable name of camera to use in seraching directories"],
        ["e", "endTime", "ending date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
        ["g", "gapMinutes", "override default of 1 minute gap between images to download"],
        ["o", "outputDir", "directory to save the output image"],
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    gapMinutes = int(args.gapMinutes) if args.gapMinutes else 1
    outputDir = int(args.outputDir) if args.outputDir else settings.downloadDir
    startTimeDT = dateutil.parser.parse(args.startTime)
    if args.endTime:
        endTimeDT = dateutil.parser.parse(args.endTime)
    else:
        endTimeDT = startTimeDT
    assert startTimeDT.year == endTimeDT.year
    assert startTimeDT.month == endTimeDT.month
    assert startTimeDT.day == endTimeDT.day
    assert endTimeDT >= startTimeDT

    cookieJar = img_archive.loginAjax()
    if args.cameraDirInput:
        cameraDir = img_archive.chooseCamera(cookieJar, args.cameraDirInput)
        if not cameraDir:
            exit(1)
        archiveDirs = [cameraDir]
    else:
        camArchives = img_archive.getHpwrenCameraArchives(googleServices['sheet'], settings)
        matchingCams = list(filter(lambda x: args.cameraID == x['id'], camArchives))
        if len(matchingCams) != 1:
            logging.error('Expected 1, but found %d matching cameras.', len(matchingCams))
            exit(1)
        archiveDirs = matchingCams[0]['dirs']
        logging.warn('Found %s directories', archiveDirs)
    # downloadFilesHttp(outputDir, args.cameraID, startTimeDT, endTimeDT, gapMinutes)
    for dirName in archiveDirs:
        logging.warn('Searching for files in dir %s', dirName)
        found = img_archive.getFilesAjax(cookieJar, outputDir, args.cameraID, dirName, startTimeDT, endTimeDT, gapMinutes)
        if found:
            return # done


if __name__=="__main__":
    main()
