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


class HpwrenHTMLParser(HTMLParser):
    def __init__(self, fileType):
        self.table = []
        self.filetype = fileType
        super().__init__()


    def handle_starttag(self, tag, attrs):
        if (tag == 'a') and len(attrs) > 0:
            # print('Found <a> %s', len(attrs), attrs)
            for attr in attrs:
                # print('Found attr %s', len(attr), attr)
                if len(attr) == 2 and attr[0]=='href' and attr[1][-4:] == self.filetype:
                    self.table.append(attr[1])

    def getTable(self):
        return self.table


def parseDirHtml(dirHtml, fileType):
    parser = HpwrenHTMLParser(fileType)
    parser.feed(dirHtml)
    return parser.getTable()


def fetchImgOrDir(url, verboseLogs):
    try:
        resp = urllib.request.urlopen(url)
    except Exception as e:
        if verboseLogs:
            logging.error('Result of fetch from %s: %s', url, str(e))
        return (None, None)
    if resp.getheader('content-type') == 'image/jpeg':
        return ('img', resp)
    else:
        return ('dir', resp)


def readUrlDir(urlPartsQ, verboseLogs, fileType):
    # logging.warning('Dir URLparts %s', urlPartsQ)
    url = '/'.join(urlPartsQ)
    # logging.warning('Dir URL %s', url)
    (imgOrDir, resp) = fetchImgOrDir(url, verboseLogs)
    if not imgOrDir:
        return None
    assert imgOrDir == 'dir'
    dirHtml = resp.read().decode('utf-8')
    return parseDirHtml(dirHtml, fileType)


def listTimesinQ(urlPartsQ, verboseLogs):
    files = readUrlDir(urlPartsQ, verboseLogs, '.jpg')
    if files:
        return list(map(lambda x: {'time': int(x[:-4])}, files))
    return None


def downloadHttpFileAtTime(outputDir, urlPartsQ, cameraID, closestTime):
    imgPath = getImgPath(outputDir, cameraID, closestTime)
    logging.warning('Local file %s', imgPath)
    if os.path.isfile(imgPath):
        logging.warning('File %s already downloaded', imgPath)
        return imgPath

    closestFile = str(closestTime) + '.jpg'
    urlParts = urlPartsQ[:] # copy URL parts array
    urlParts.append(closestFile)
    # logging.warning('File URLparts %s', urlParts)
    url = '/'.join(urlParts)
    logging.warning('File URL %s', url)

    # urllib.request.urlretrieve(url, imgPath)
    resp = requests.get(url, stream=True)
    with open(imgPath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
    resp.close()
    return imgPath


def downloadDriveFileAtTime(driveSvc, outputDir, hpwrenSource, closestEntry):
    imgPath = os.path.join(outputDir, closestEntry['name'])
    logging.warning('Local file %s', imgPath)
    if os.path.isfile(imgPath):
        logging.warning('File %s already downloaded', imgPath)
        return imgPath

    goog_helper.downloadFileByID(driveSvc, closestEntry['id'], imgPath)
    return imgPath


def getMp4Url(urlPartsDate, qNum, verboseLogs):
    urlPartsMp4 = urlPartsDate[:] # copy URL
    urlPartsMp4.append('MP4')
    files = readUrlDir(urlPartsMp4, verboseLogs, '.mp4')
    logging.warning('MP4s %s', files)
    qMp4Name = 'Q' + str(qNum) + '.mp4'
    if files and (qMp4Name in files):
        urlPartsMp4.append(qMp4Name)
        return '/'.join(urlPartsMp4)
    return None


def callGCF(gcfUrl, creds, hpwrenSource, qNum, folderID):
    headers = {'Authorization': f'bearer {creds.id_token_jwt}'}
    gcfParams = {
        'hostName': hpwrenSource['server'],
        'cameraID': hpwrenSource['cameraID'],
        'yearDir': hpwrenSource['year'],
        'dateDir': hpwrenSource['dateDirName'],
        'qNum': qNum,
        'uploadDir': folderID
    }
    response = requests.post(gcfUrl, headers=headers, data=gcfParams)
    return response.content


def getDriveMp4(googleServices, settings, hpwrenSource, qNum):
    folderName = hpwrenSource['cameraID'] + '__' + hpwrenSource['dateDirName'] + 'Q' + str(qNum)
    dirs = goog_helper.searchFiles(googleServices['drive'], settings.ffmpegFolder, prefix=folderName)
    logging.warning('Found drive dirs %s', dirs)
    folderID = dirs[0]['id'] if dirs else None
    if not folderID:
        logging.warning('Creating drive folder %s', folderName)
        folderID = goog_helper.createFolder(googleServices['drive'], settings.ffmpegFolder, folderName)
        hpwrenSource['gDriveFolder'] = folderID
        logging.warning('Calling Cloud Function for folder %s', folderID)
        gcfRes = callGCF(settings.ffmpegUrl, googleServices['creds'], hpwrenSource, qNum, folderID)
        logging.warning('Cloud function result %s', gcfRes)
    files = goog_helper.searchAllFiles(googleServices['drive'], folderID)
    # logging.warning('GDM4: files %d %s', len(files), files)
    imgTimes = []
    for fileInfo in files:
        nameParsed = parseFilename(fileInfo['name'])
        imgTimes.append({
            'time': nameParsed['unixTime'],
            'id': fileInfo['id'],
            'name': fileInfo['name']
        })
    return {
        'folderID': folderID,
        'imgTimes': imgTimes
    }


def checkMp4(googleServices, settings, hpwrenSource, urlPartsDate, qNum, verboseLogs):
    url = getMp4Url(urlPartsDate, qNum, verboseLogs)
    if not url:
        return None
    return getDriveMp4(googleServices, settings, hpwrenSource, qNum)


outputDirCheckOnly = '/CHECK:WITHOUT:DOWNLOAD'
def downloadFilesForDate(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs):
    startTimeDT = hpwrenSource['startTimeDT']
    endTimeDT = hpwrenSource['endTimeDT']
    dateDirName = '{year}{month:02d}{date:02d}'.format(year=startTimeDT.year, month=startTimeDT.month, date=startTimeDT.day)
    hpwrenSource['dateDirName'] = dateDirName
    urlPartsDate = hpwrenSource['urlParts'][:] # copy URL
    urlPartsDate.append(dateDirName)
    hpwrenSource['urlPartsDate'] = urlPartsDate

    timeGapDelta = datetime.timedelta(seconds = 60*gapMinutes)
    imgTimes = None
    lastQNum = 0 # 0 never matches because Q numbers start with 1
    curTimeDT = startTimeDT
    downloaded_files = []
    while curTimeDT <= endTimeDT:
        qNum = 1 + int(curTimeDT.hour/3)
        urlPartsQ = urlPartsDate[:] # copy URL
        urlPartsQ.append('Q' + str(qNum))
        if qNum != lastQNum:
            # List times of files in Q dir and cache
            useHttp = True
            imgTimes = listTimesinQ(urlPartsQ, verboseLogs)
            if not imgTimes:
                if verboseLogs:
                    logging.error('No images in Q dir %s', '/'.join(urlPartsQ))
                mp4Url = getMp4Url(urlPartsDate, qNum, verboseLogs)
                if not mp4Url:
                    return downloaded_files
                if outputDir != outputDirCheckOnly:
                    mp4Info = getDriveMp4(googleServices, settings, hpwrenSource, qNum)
                    useHttp = False
                    hpwrenSource['gDriveFolder'] = mp4Info['folderID']
                    imgTimes = mp4Info['imgTimes']
                    # logging.warning('imgTimes %d %s', len(imgTimes), imgTimes)
            lastQNum = qNum

        if outputDir == outputDirCheckOnly:
            downloaded_files.append(outputDirCheckOnly)
        else:
            desiredTime = time.mktime(curTimeDT.timetuple())
            closestEntry = min(imgTimes, key=lambda x: abs(x['time']-desiredTime))
            closestTime = closestEntry['time']
            downloaded = None
            if useHttp:
                downloaded = downloadHttpFileAtTime(outputDir, urlPartsQ, hpwrenSource['cameraID'], closestTime)
            else:
                downloaded = downloadDriveFileAtTime(googleServices['drive'], outputDir, hpwrenSource, closestEntry)
            if downloaded and verboseLogs:
                logging.warning('Successful download for time %s', str(datetime.datetime.fromtimestamp(closestTime)))
            if downloaded:
                downloaded_files.append(downloaded)

        curTimeDT += timeGapDelta
    return downloaded_files


def downloadFilesHttp(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs):
    regexDir = '(c[12])/([^/]+)/large/?'
    matches = re.findall(regexDir, hpwrenSource['dirName'])
    if len(matches) != 1:
        logging.error('Could not parse dir: %s', hpwrenSource['dirName'])
        return None
    match = matches[0]
    (server, subdir) = match
    hpwrenBase = 'http://{server}.hpwren.ucsd.edu/archive'.format(server=server)
    hpwrenSource['server'] = server
    urlParts = [hpwrenBase, subdir, 'large']
    hpwrenSource['urlParts'] = urlParts

    # first try without year directory
    hpwrenSource['year'] = ''
    downloaded_files = downloadFilesForDate(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs)
    if downloaded_files:
        return downloaded_files
    # retry with year directory
    hpwrenSource['year'] = str(hpwrenSource['startTimeDT'].year)
    urlParts.append(hpwrenSource['year'])
    hpwrenSource['urlParts'] = urlParts
    return downloadFilesForDate(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs)


def getHpwrenCameraArchives(sheetSvc, settings):
    data = goog_helper.readFromSheet(sheetSvc, settings.camerasSheet, settings.camerasSheetRange)
    camArchives = []
    for camInfo in data:
        # logging.warning('info %d, %s', len(camInfo), camInfo)
        if len(camInfo) != 3:
            continue
        camData = {'id': camInfo[1], 'dir': camInfo[2], 'name': camInfo[0]}
        # logging.warning('data %s', camData)
        camArchives.append(camData)
    logging.warning('Discovered total %d camera archive dirs', len(camArchives))
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

