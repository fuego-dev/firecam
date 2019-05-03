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

Library code to manage image archives

"""

import goog_helper

import os
import logging
import urllib.request
import time, datetime, dateutil.parser
from html.parser import HTMLParser
import requests
import re
from PIL import Image, ImageMath


def getImgPath(outputDir, cameraID, timestamp, cropCoords=None, diffMinutes=0):
    timeStr = datetime.datetime.fromtimestamp(timestamp).isoformat()
    timeStr = timeStr.replace(':', ';') # make windows happy
    imgName = '__'.join([cameraID, timeStr])
    if diffMinutes:
        imgName += ('_Diff%d' % diffMinutes)
    if cropCoords:
        imgName += '_Crop_' + 'x'.join(list(map(lambda x: str(x), cropCoords)))
    imgPath = os.path.join(outputDir, imgName + '.jpg')
    return imgPath


def repackFileName(parsedName):
    cropCoords = None
    if 'minX' in parsedName:
        cropCoords=(parsedName['minX'], parsedName['minY'], parsedName['maxX'], parsedName['maxY'])
    return getImgPath('', parsedName['cameraID'], parsedName['unixTime'],
                      cropCoords=cropCoords,
                      diffMinutes=parsedName['diffMinutes'])


def parseFilename(fileName):
    # regex to match names like Axis-BaldCA_2018-05-29T16_02_30_129496.jpg
    # and bm-n-mobo-c__2017-06-25z11;53;33.jpg
    regexExpanded = '([A-Za-z0-9-_]+[^_])_+(\d{4}-\d\d-\d\d)T(\d\d)[_;](\d\d)[_;](\d\d)'
    # regex to match diff minutes spec for subtracted images
    regexDiff = '(_Diff(\d+))?'
    # regex to match optional crop information e.g., Axis-Cowles_2019-02-19T16;23;49_Crop_270x521x569x820.jpg
    regexOptionalCrop = '(_Crop_(\d+)x(\d+)x(\d+)x(\d+))?'
    matchesExp = re.findall(regexExpanded + regexDiff + regexOptionalCrop, fileName)
    # regex to match names like 1499546263.jpg
    regexUnixTime = '(1\d{9})'
    matchesUnix = re.findall(regexUnixTime + regexDiff + regexOptionalCrop, fileName)
    cropInfo = None
    if len(matchesExp) == 1:
        match = matchesExp[0]
        parsed = {
            'cameraID': match[0],
            'date': match[1],
            'hours': match[2],
            'minutes': match[3],
            'seconds': match[4]
        }
        isoStr = '{date}T{hour}:{min}:{sec}'.format(date=parsed['date'],hour=parsed['hours'],min=parsed['minutes'],sec=parsed['seconds'])
        dt = dateutil.parser.parse(isoStr)
        unixTime = time.mktime(dt.timetuple())
        parsed['diffMinutes'] = int(match[6] or 0)
        cropInfo = match[-4:]
    elif len(matchesUnix) == 1:
        match = matchesUnix[0]
        unixTime = int(match[0])
        dt = datetime.datetime.fromtimestamp(unixTime)
        isoStr = datetime.datetime.fromtimestamp(unixTime).isoformat()
        parsed = {
            'cameraID': 'UNKNOWN_' + fileName,
            'date': dt.date().isoformat(),
            'hours': str(dt.hour),
            'minutes': str(dt.minute),
            'seconds': str(dt.second)
        }
        parsed['diffMinutes'] = int(match[2] or 0)
        cropInfo = match[-4:]
    else:
        logging.error('Failed to parse name %s', fileName)
        return None
    if cropInfo[0]:
        parsed['minX'] = int(cropInfo[0])
        parsed['minY'] = int(cropInfo[1])
        parsed['maxX'] = int(cropInfo[2])
        parsed['maxY'] = int(cropInfo[3])
    parsed['isoStr'] = isoStr
    parsed['unixTime'] = unixTime
    return parsed


"""
There are two ways to access hpwren archives:
1) Directories accesssible via raw HTTP to c1.xxx endpoint
2) AJAX based FileRun server on dl.xxx endpoint

Code for both of them are here, but we only use the AJAX FileRun endpoint currently

"""
class HpwrenHTMLParser(HTMLParser):
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
    parser = HpwrenHTMLParser()
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


def downloadFileAtTime(outputDir, urlPartsQ, cameraID, closestTime):
    imgPath = getImgPath(outputDir, cameraID, closestTime)
    logging.warn('Local file %s', imgPath)
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


"""
The following is the code for AJAX FileRun server for HPWREN

"""
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
    respJson = None
    try:
        respJson = resp.json()
    except Exception as e:
        logging.error('Error listAjax %s', subPath)
        return None

    resp.close()
    if isinstance(respJson, dict) and ('msg' in respJson):
        logging.error('Got error %s when searching %s in %s', respJson, dirsOrFiles, subPath)
        return None

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


def chooseCamera(cookieJar, cameraDirInput):
    cameraDirs = listAjax(cookieJar, 'dirs', '')
    if not cameraDirs:
        return None
    print('Num cameras:', len(cameraDirs))
    matchingCams = list(filter(lambda x: cameraDirInput in x['text'], cameraDirs))
    if len(matchingCams) == 0:
        logging.error('Camera %s not found', cameraDirInput)
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


def getFilesAjax(cookieJar, outputDir, cameraID, cameraDir, startTimeDT, endTimeDT, gapMinutes):
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=startTimeDT.year, month=startTimeDT.month, date=startTimeDT.day)
    camInfo = None
    camInfoList = list(filter(lambda x: (x['cameraID'] == cameraID) and (x['dateDirName'] == dateDirName), getFilesAjax.cachedMap))
    if camInfoList:
        camInfo = camInfoList[0]
        pathToDate = camInfo['pathToDate']
    else:
        camInfo = {
            'cameraID': cameraID,
            'dateDirName': dateDirName,
            'lastQNum': 0,
            'dirTimes': None
        }
        pathToDate = cameraDir
        dateDirs = listAjax(cookieJar, 'dirs', pathToDate)
        if not dateDirs:
            return None
        # print('Dates1', len(dateDirs), dateDirs)
        matchingYear = list(filter(lambda x: str(startTimeDT.year) == x['text'], dateDirs))
        if len(matchingYear) == 1:
            pathToDate += '/' + str(startTimeDT.year)
            dateDirs = listAjax(cookieJar, 'dirs', pathToDate)
            if not dateDirs:
                return None
            # print('Dates2', len(dateDirs), dateDirs)
        matchingDate = list(filter(lambda x: dateDirName == x['text'], dateDirs))
        if len(matchingDate) == 1:
            pathToDate += '/' + dateDirName
            camInfo['pathToDate'] = pathToDate
            getFilesAjax.cachedMap.append(camInfo)
        else:
            logging.error('Could not find matching date in list %d:%s', len(dateDirs), dateDirs)
            return None

    timeGapDelta = datetime.timedelta(seconds = 60*gapMinutes)
    curTimeDT = startTimeDT
    imgPaths = []
    while curTimeDT <= endTimeDT:
        qNum = 1 + int(curTimeDT.hour/3)
        pathToQ = pathToDate + '/Q' + str(qNum)
        if qNum != camInfo['lastQNum']:
            # List times of files in Q dir and cache
            listOfFiles = listAjax(cookieJar, 'files', pathToQ)
            if not listOfFiles:
                logging.error('Unable to find files in path %s', pathToQ)
                return imgPaths
            camInfo['lastQNum'] = qNum
            logging.warn('Procesed Q dir %s with %d (%d) files', pathToQ, listOfFiles['count'], len(listOfFiles['files']))
            if len(listOfFiles['files']) == 0:
                logging.error('Zero files in path %s', pathToQ)
                return imgPaths
            camInfo['dirTimes'] = list(map(lambda x: int(x['n'][:-4]), listOfFiles['files']))

        desiredTime = time.mktime(curTimeDT.timetuple())
        closestTime = min(camInfo['dirTimes'], key=lambda x: abs(x-desiredTime))
        imgPath = getImgPath(outputDir, cameraID, closestTime)
        logging.warn('Local file %s', imgPath)
        if os.path.isfile(imgPath):
            logging.warn('File %s already downloaded', imgPath)
        else:
            downloadFileAjax(cookieJar, pathToQ + '/' + str(closestTime) + '.jpg', imgPath)
        imgPaths.append(imgPath)
        curTimeDT += timeGapDelta
    return imgPaths
getFilesAjax.cachedMap=[]

def getHpwrenCameraArchives(service, settings):
    data = goog_helper.readFromSheet(service, settings.camerasSheet, settings.camerasSheetRange)
    camArchives = []
    for camInfo in data:
        if (len(camInfo) < 4) or (camInfo[2] != 'HPWREN'):
            continue
        camData = {'id': camInfo[1], 'dirs': []}
        for dirData in camInfo[3:]:
            dirArray = list(map(lambda x: x.strip(), dirData.split('+')))
            for dirName in dirArray:
                if dirName and (dirName not in camData['dirs']):
                    camData['dirs'].append(dirName)
        # print('Cam', camData)
        camArchives.append(camData)
    logging.warn('Found total %d cams.  %d with usable archives', len(data), len(camArchives))
    return camArchives


def diffImages(imgA, imgB):
    bandsImgA = imgA.split()
    bandsImgB = imgB.split()
    bandsImgOut = []

    for bandNum in range(len(bandsImgA)):
        # out = ImageMath.eval("convert((128+a/2)-b/2,'L')", a=bandsImgA[bandNum], b=bandsImgB[bandNum])
        out = ImageMath.eval("convert(128+a-b,'L')", a=bandsImgA[bandNum], b=bandsImgB[bandNum])
        bandsImgOut.append(out)

    return Image.merge('RGB', bandsImgOut)

