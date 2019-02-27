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

import os
import logging
import urllib.request
import time, datetime, dateutil.parser
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.table = []
        super().__init__()


    def handle_starttag(self, tag, attrs):
        if (tag == 'a') and len(attrs) > 0:
            # print('Found <a> %s', len(attrs), attrs)
            for attr in attrs:
                # print('Found attr %s', len(attr), attr)
                if len(attr) == 2 and attr[0]=='href' and attr[1][-4:] == '.jpg':
                    self.table.append(attr[1])

    def getTable(self):
        return self.table


def findClosestTime(dirHtml, desiredTime):
    parser = MyHTMLParser()
    parser.feed(dirHtml)
    files = parser.getTable()

    times = list(map(lambda x: int(x[:-4]), files))
    return min(times, key=lambda x: abs(x-desiredTime))


def fetchImgOrDir(url):
    resp = urllib.request.urlopen(url)
    if resp.getheader('content-type') == 'image/jpeg':
        return ('img', resp)
    else:
        return ('dir', resp)


def main():
    reqArgs = [
        ["c", "cameraID", "ID of camera"],
        ["t", "time", "date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
        ["o", "outputDir", "directory to save the output image"],
    ]
    optArgs = [
        ["d", "dirData", "(for testing) use this filename as directory data"],
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    hpwrenBase = 'http://c1.hpwren.ucsd.edu/archive'
    urlParts = [hpwrenBase, args.cameraID, 'large']
    ptime = dateutil.parser.parse(args.time)
    if ptime.year != 2019:
        urlParts.append(str(ptime.year))
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=ptime.year, month=ptime.month, date=ptime.day)
    urlParts.append(dateDirName)
    qNum = 1 + int(ptime.hour/3)
    urlParts.append('Q' + str(qNum))
    logging.warn('Dir URLparts %s', urlParts)
    url = '/'.join(urlParts)
    logging.warn('Dir URL %s', url)
    if args.dirData:
        dirHtml = open(args.dirData, 'r').read()
        imgOrDir = 'dir'
    else:
        (imgOrDir, resp) = fetchImgOrDir(url)
        assert imgOrDir == 'dir'
        dirHtml = resp.read().decode('utf-8')
    # logging.warn('IOD: %s, %s', imgOrDir, dirHtml[:12])

    desiredTime = time.mktime(ptime.timetuple())
    closestTime = findClosestTime(dirHtml, desiredTime)
    closestFile = str(closestTime) + '.jpg'
    urlParts.append(closestFile)
    logging.warn('File URLparts %s', urlParts)
    url = '/'.join(urlParts)
    logging.warn('File URL %s', url)

    timeStr = datetime.datetime.fromtimestamp(closestTime).isoformat()
    timeStr = timeStr.replace(':', ';') # make windows happy
    imgName = '_'.join([args.cameraID, timeStr])
    imgPath = os.path.join(args.outputDir, imgName + '.jpg')
    logging.warn('Local file %s', imgPath)

    urllib.request.urlretrieve(url, imgPath)


if __name__=="__main__":
    main()
