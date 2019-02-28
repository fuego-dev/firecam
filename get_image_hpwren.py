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


def parseDirHtml(dirHtml):
    parser = MyHTMLParser()
    parser.feed(dirHtml)
    files = parser.getTable()
    times = list(map(lambda x: int(x[:-4]), files))
    return times


def fetchImgOrDir(url):
    try:
        resp = urllib.request.urlopen(url)
    except Exception as e:
        logging.error('Error fetching image from %s %s', url, str(e))
        return (None, None)
    if resp.getheader('content-type') == 'image/jpeg':
        return ('img', resp)
    else:
        return ('dir', resp)


def listTimesinQ(UrlPartsQ, qNum):
    logging.warn('Dir URLparts %s', UrlPartsQ)
    url = '/'.join(UrlPartsQ)
    logging.warn('Dir URL %s', url)
    (imgOrDir, resp) = fetchImgOrDir(url)
    if not imgOrDir:
        return None
    assert imgOrDir == 'dir'
    dirHtml = resp.read().decode('utf-8')
    times = parseDirHtml(dirHtml)
    return times


def main():
    reqArgs = [
        ["c", "cameraID", "ID of camera"],
        ["s", "startTime", "starting date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
        ["o", "outputDir", "directory to save the output image"],
    ]
    optArgs = [
        ["e", "endTime", "ending date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
        ["d", "dirData", "(for testing) use this filename as directory data"],
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    hpwrenBase = 'http://c1.hpwren.ucsd.edu/archive'
    dateUrlParts = [hpwrenBase, args.cameraID, 'large']
    startTimeDT = dateutil.parser.parse(args.startTime)
    if args.endTime:
        endTimeDT = dateutil.parser.parse(args.endTime)
    else:
        endTimeDT = startTimeDT
    assert startTimeDT.year == endTimeDT.year
    assert startTimeDT.month == endTimeDT.month
    assert startTimeDT.day == endTimeDT.day
    assert endTimeDT >= startTimeDT

    if startTimeDT.year != 2019:
        dateUrlParts.append(str(startTimeDT.year))
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=startTimeDT.year, month=startTimeDT.month, date=startTimeDT.day)
    dateUrlParts.append(dateDirName)

    oneMinute = datetime.timedelta(seconds=60)
    dirTimes = None
    lastQNum = 0
    curTimeDT = startTimeDT
    while curTimeDT <= endTimeDT:
        qNum = 1 + int(curTimeDT.hour/3)
        urlParts = dateUrlParts[:] # copy URL up to date
        urlParts.append('Q' + str(qNum))
        if qNum != lastQNum:
            # List times of files in Q dir and cache
            dirTimes = listTimesinQ(urlParts, qNum)
            if not dirTimes:
                logging.error('Bad URL %s', urlParts)
                exit(1)
            lastQNum = qNum

        desiredTime = time.mktime(curTimeDT.timetuple())
        closestTime = min(dirTimes, key=lambda x: abs(x-desiredTime))
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

        curTimeDT += oneMinute



if __name__=="__main__":
    main()
