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
import requests

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


def listTimesinQ(UrlPartsQ):
    # logging.warn('Dir URLparts %s', UrlPartsQ)
    url = '/'.join(UrlPartsQ)
    logging.warn('Dir URL %s', url)
    (imgOrDir, resp) = fetchImgOrDir(url)
    if not imgOrDir:
        return None
    assert imgOrDir == 'dir'
    dirHtml = resp.read().decode('utf-8')
    times = parseDirHtml(dirHtml)
    return times


def getImgPath(outputDir, cameraID, timestamp):
    timeStr = datetime.datetime.fromtimestamp(timestamp).isoformat()
    timeStr = timeStr.replace(':', ';') # make windows happy
    imgName = '_'.join([cameraID, timeStr])
    imgPath = os.path.join(outputDir, imgName + '.jpg')
    logging.warn('Local file %s', imgPath)
    return imgPath


def downloadFileAtTime(outputDir, urlPartsQ, cameraID, closestTime):
    imgPath = getImgPath(outputDir, cameraID, closestTime)
    if os.path.isfile(imgPath):
        logging.warn('File %s already downloaded', imgPath)
        return # file already downloaded

    closestFile = str(closestTime) + '.jpg'
    urlParts = urlPartsQ[:] # copy URL parts array
    urlParts.append(closestFile)
    # logging.warn('File URLparts %s', urlParts)
    url = '/'.join(urlParts)
    logging.warn('File URL %s', url)

    urllib.request.urlretrieve(url, imgPath)


def downloadFilesHttp(outputDir, cameraID, startTimeDT, endTimeDT, gapMinutes):
    hpwrenBase = 'http://c1.hpwren.ucsd.edu/archive'
    dateUrlParts = [hpwrenBase, cameraID, 'large']
    if startTimeDT.year != 2019:
        dateUrlParts.append(str(startTimeDT.year))
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=startTimeDT.year, month=startTimeDT.month, date=startTimeDT.day)
    dateUrlParts.append(dateDirName)

    timeGapDelta = datetime.timedelta(seconds = 60*gapMinutes)
    dirTimes = None
    lastQNum = 0
    curTimeDT = startTimeDT
    while curTimeDT <= endTimeDT:
        qNum = 1 + int(curTimeDT.hour/3)
        urlPartsQ = dateUrlParts[:] # copy URL
        urlPartsQ.append('Q' + str(qNum))
        if qNum != lastQNum:
            # List times of files in Q dir and cache
            dirTimes = listTimesinQ(urlPartsQ)
            if not dirTimes:
                logging.error('Bad URL %s', urlPartsQ)
                exit(1)
            lastQNum = qNum

        desiredTime = time.mktime(curTimeDT.timetuple())
        closestTime = min(dirTimes, key=lambda x: abs(x-desiredTime))
        downloadFileAtTime(outputDir, urlPartsQ, cameraID, closestTime)

        curTimeDT += timeGapDelta


def listAjax(cookieJar, dirsOrFiles, subPath):
    baseUrl = 'http://dl-hpwren.ucsd.edu/filerun/?module=fileman_myfiles&section=ajax&page='
    if dirsOrFiles == 'dirs':
        baseUrl += 'tree'
    elif dirsOrFiles == 'files':
        baseUrl += 'grid'
    else:
        logging.error('Invalid list type: %s', dirsOrFiles)
        return None
    fullPath = '/ROOT/HOME/' + subPath
    resp = requests.post(baseUrl, cookies=cookieJar, data={'path': fullPath})
    respJson = resp.json()
    resp.close()
    return respJson


def downloadFileAjax(cookieJar, subPath, outputFile):
    baseUrl = 'http://dl-hpwren.ucsd.edu/filerun/t.php?'
    fullPath = '/ROOT/HOME/' + subPath
    queryParams = {
        'sn': 1,
        'p': fullPath,
    }
    baseUrl += urllib.parse.urlencode(queryParams)
    resp = requests.get(baseUrl, cookies=cookieJar, stream=True)
    with open(outputFile, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
    resp.close()


def loginAjax():
    loginUrl = 'http://dl-hpwren.ucsd.edu/filerun/?page=login&action=login&nonajax=1&username=publicuser&password=publicuser1'
    resp = requests.get(loginUrl, allow_redirects=False) # some machines go into infinite redirect loop without the flag
    cookies = resp.cookies
    resp.close()
    return cookies


def chooseCamera(cookieJar, cameraInput):
    cameraDirs = listAjax(cookieJar, 'dirs', '')
    print('Num cameras:', len(cameraDirs))
    matchingCams = list(filter(lambda x: cameraInput in x['text'], cameraDirs))
    if len(matchingCams) == 0:
        logging.error('Camera %s not found', cameraInput)
        return None
    elif len(matchingCams) == 1:
        return matchingCams[0]['text']
    else:
        print('Multiple matching cameras')
        for (index, cam) in enumerate(matchingCams):
            print('%d: %s' % (index + 1, cam['text']))
        choice = int(input('Enter number for desired camera: '))
        assert choice <= len(matchingCams)
        cameraDir = matchingCams[choice-1]['text']
        print('Selected camera is', cameraDir)
        return cameraDir


def getFilesAjax(outputDir, cameraID, cameraInput, startTimeDT, endTimeDT, gapMinutes):
    cookieJar = loginAjax()
    cameraDir = chooseCamera(cookieJar, cameraInput)
    if not cameraDir:
        return
    pathToDate = cameraDir
    dateDirs = listAjax(cookieJar, 'dirs', pathToDate)
    # print('Dates1', len(dateDirs), dateDirs)
    matchingYear = list(filter(lambda x: str(startTimeDT.year) == x['text'], dateDirs))
    if len(matchingYear) == 1:
        pathToDate += '/' + str(startTimeDT.year)
        dateDirs = listAjax(cookieJar, 'dirs', pathToDate)
        # print('Dates2', len(dateDirs), dateDirs)
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=startTimeDT.year, month=startTimeDT.month, date=startTimeDT.day)
    matchingDate = list(filter(lambda x: dateDirName == x['text'], dateDirs))
    if len(matchingDate) == 1:
        pathToDate += '/' + dateDirName
    else:
        logging.error('Could not find matching date in list %d:%s', len(dateDirs), dateDirs)
        return

    timeGapDelta = datetime.timedelta(seconds = 60*gapMinutes)
    dirTimes = None
    lastQNum = 0
    curTimeDT = startTimeDT
    while curTimeDT <= endTimeDT:
        qNum = 1 + int(curTimeDT.hour/3)
        pathToQ = pathToDate + '/Q' + str(qNum)
        if qNum != lastQNum:
            # List times of files in Q dir and cache
            listOfFiles = listAjax(cookieJar, 'files', pathToQ)
            if not listOfFiles:
                logging.error('Unable to find files in path %s', pathToQ)
                exit(1)
            lastQNum = qNum
            logging.warn('Procesed Q dir %s with %d (%d) files', pathToQ, listOfFiles['count'], len(listOfFiles['files']))
            dirTimes = list(map(lambda x: int(x['n'][:-4]), listOfFiles['files']))

        desiredTime = time.mktime(curTimeDT.timetuple())
        closestTime = min(dirTimes, key=lambda x: abs(x-desiredTime))
        imgPath = getImgPath(outputDir, cameraID, closestTime)
        if os.path.isfile(imgPath):
            logging.warn('File %s already downloaded', imgPath)
        else:
            downloadFileAjax(cookieJar, pathToQ + '/' + str(closestTime) + '.jpg', imgPath)

        curTimeDT += timeGapDelta


def main():
    reqArgs = [
        ["c", "cameraID", "ID (code name) of camera"],
        ["d", "cameraDirInput", "Human readable name of camera to use in seraching directories"],
        ["s", "startTime", "starting date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
    ]
    optArgs = [
        ["e", "endTime", "ending date and time in ISO format (e.g., 2019-02-22T14:34:56 in Pacific time zone)"],
        ["g", "gapMinutes", "override default of 1 minute gap between images to download"],
        ["o", "outputDir", "directory to save the output image"],
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
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

    # downloadFilesHttp(outputDir, args.cameraID, startTimeDT, endTimeDT, gapMinutes)
    getFilesAjax(outputDir, args.cameraID, args.cameraDirInput, startTimeDT, endTimeDT, gapMinutes)


if __name__=="__main__":
    main()
