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
    """Generate properly formatted image filename path following Fuego conventions
       E.g.: lo-s-mobo-c__2018-06-06T11;12;23_Diff1_Crop_627x632x1279x931.jpg

    Args:
        outputDir (str): Output directory
        cameraID (str): ID of camera
        timestamp (int): timestamp
        cropCoords (tuple): (x0, y0, x1, y1) coordinates of the crop rectangle
        diffMinutes (int): number of minutes separating the images (for subtracted images)

    Returns:
        String to full path name
    """
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
    """Generate properly formatted image filename following Fuego conventions
       based on information from parsedName dictionary
       E.g.: lo-s-mobo-c__2018-06-06T11;12;23_Diff1_Crop_627x632x1279x931.jpg

    Args:
        parsedName (dict): Dictionary containing various attributes of image
                            (likely result from earlier call to parseFilename())

    Returns:
        String to file name
    """
    cropCoords = None
    if 'minX' in parsedName:
        cropCoords=(parsedName['minX'], parsedName['minY'], parsedName['maxX'], parsedName['maxY'])
    return getImgPath('', parsedName['cameraID'], parsedName['unixTime'],
                      cropCoords=cropCoords,
                      diffMinutes=parsedName['diffMinutes'])


def parseFilename(fileName):
    """Parse the image source attributes given the properly formatted image filename

    Args:
        fileName (str):

    Returns:
        Dictionary with parsed out attributes
    """
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
    """Dervied class from HTMLParser to pull out file information from HTML directory listing pages
        Allows caller to specify fileType (extension) the caller cares about
    """
    def __init__(self, fileType):
        self.table = []
        self.filetype = fileType
        super().__init__()


    def handle_starttag(self, tag, attrs):
        """Handler for HTML starting tag (<).
           If the tag type is <a> and it contains an href link pointing to file of specified type,
           then save the name for extraction by getTable()

        """
        if (tag == 'a') and len(attrs) > 0:
            # print('Found <a> %s', len(attrs), attrs)
            for attr in attrs:
                # print('Found attr %s', len(attr), attr)
                if len(attr) == 2 and attr[0]=='href' and attr[1][-4:] == self.filetype:
                    self.table.append(attr[1])

    def getTable(self):
        return self.table


def parseDirHtml(dirHtml, fileType):
    """Wrapper around HpwrenHTMLParser to pull out entries of given fileType

    Args:
        dirHtml (str): HTML page for directory listing
        fileType (str): File extension (e.g.: '.jpg')

    Returns:
        List of file names matching extension
    """
    parser = HpwrenHTMLParser(fileType)
    parser.feed(dirHtml)
    return parser.getTable()


def fetchImgOrDir(url, verboseLogs):
    """Read the given URL and return the data.  Also note if data is an image

    Args:
        url (str): URL to read
        verboseLogs (bool): Write verbose logs for debugging

    Returns:
        Tuple indicating image or directory and the data
    """
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
    """Get the files of given fileType from the given HPWREN Q directory URL

    Args:
        urlPartsQ (list): HPWREN Q directory URL as list of string parts
        verboseLogs (bool): Write verbose logs for debugging
        fileType (str): File extension (e.g.: '.jpg')

    Returns:
        List of file names matching extension
    """
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
    """Get the timestamps of images from the given HPWREN Q directory URL

    Args:
        urlPartsQ (list): HPWREN Q directory URL as list of string parts
        verboseLogs (bool): Write verbose logs for debugging

    Returns:
        List of timestamps
    """
    files = readUrlDir(urlPartsQ, verboseLogs, '.jpg')
    if files:
        return list(map(lambda x: {'time': int(x[:-4])}, files))
    return None


def downloadHttpFileAtTime(outputDir, urlPartsQ, cameraID, closestTime):
    """Download HPWREN image from given HPWREN Q directory URL at given time

    Args:
        outputDir (str): Output directory path
        urlPartsQ (list): HPWREN Q directory URL as list of string parts
        cameraID (str): ID of camera
        closestTime (int): Desired timestamp

    Returns:
        Local filesystem path to downloaded image
    """
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
    """Download HPWREN image from google drive folder from ffmpeg Google Cloud Function

    Args:
        driveSvc: Drive service (from getGoogleServices()['drive'])
        outputDir (str): Output directory path
        hpwrenSource (dict): Dictionary containing various HPWREN source information
        closestEntry (dict): Desired timestamp and drive file ID

    Returns:
        Local filesystem path to downloaded image
    """
    imgPath = os.path.join(outputDir, closestEntry['name'])
    logging.warning('Local file %s', imgPath)
    if os.path.isfile(imgPath):
        logging.warning('File %s already downloaded', imgPath)
        return imgPath

    goog_helper.downloadFileByID(driveSvc, closestEntry['id'], imgPath)
    return imgPath


def getMp4Url(urlPartsDate, qNum, verboseLogs):
    """Get the URL for the MP4 video for given Q

    Args:
        urlPartsDate (list): HPWREN date directory URL as list of string parts
        qNum (int): Q number (1-8) where each Q represents 3 hour period
        verboseLogs (bool): Write verbose logs for debugging

    Returns:
        URL to Q diretory
    """
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
    """invoke the Google Cloud Function for ffpeg decompression with proper parameters and credentials

    Args:
        gcfUrl (str): URL for ffmpeg cloud function
        creds (): Google credentials to identify caller
        hpwrenSource (dict): Dictionary containing various HPWREN source information
        qNum (int): Q number (1-8) where each Q represents 3 hour period
        folderID (str): google drive ID of folder where to extract images

    Returns:
        Cloud function result
    """
    headers = {'Authorization': 'bearer {}'.format(creds.id_token_jwt)}
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
    """Extract images from Q MP4 video into google drive folder

    Args:
        googleServices (): Google services and credentials
        settings (): settings module
        hpwrenSource (dict): Dictionary containing various HPWREN source information
        qNum (int): Q number (1-8) where each Q represents 3 hour period

    Returns:
        Dictionary with drive folder ID containing images and imgTimes metadata
    """
    folderName = hpwrenSource['cameraID'] + '__' + hpwrenSource['dateDirName'] + 'Q' + str(qNum)
    dirs = goog_helper.searchFiles(googleServices['drive'], settings.ffmpegFolder, prefix=folderName)
    logging.warning('Found drive dirs %s', dirs)
    folderID = dirs[0]['id'] if dirs else None
    if not folderID:
        logging.warning('Creating drive folder %s', folderName)
        folderID = goog_helper.createFolder(googleServices['drive'], settings.ffmpegFolder, folderName)
        hpwrenSource['gDriveFolder'] = folderID

    files = goog_helper.searchAllFiles(googleServices['drive'], folderID)
    if len(files) == 0:
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


outputDirCheckOnly = '/CHECK:WITHOUT:DOWNLOAD'
def downloadFilesForDate(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs):
    """Download HPWREN images from given given date time range with specified gaps

    If outputDir is special value outputDirCheckOnly, then just check if files are retrievable

    Args:
        googleServices (): Google services and credentials
        settings (): settings module
        outputDir (str): Output directory path
        hpwrenSource (dict): Dictionary containing various HPWREN source information
        gapMinutes (int): Number of minutes of gap between images for downloading
        verboseLogs (bool): Write verbose logs for debugging

    Returns:
        List of local filesystem paths to downloaded images
    """
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


def downloadFilesHpwren(googleServices, settings, outputDir, hpwrenSource, gapMinutes, verboseLogs):
    """Download HPWREN images from given given date time range with specified gaps

    Calls downloadFilesForDate to do the heavy lifting, but first determines the hpwren server.
    First tries without year directory in URL path, and if that fails, then retries with year dir

    Args:
        googleServices (): Google services and credentials
        settings (): settings module
        outputDir (str): Output directory path
        hpwrenSource (dict): Dictionary containing various HPWREN source information
        gapMinutes (int): Number of minutes of gap between images for downloading
        verboseLogs (bool): Write verbose logs for debugging

    Returns:
        List of local filesystem paths to downloaded images
    """
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
    """Get the HPWREN camera archive directories from Google sheet settings.camerasSheet

    Args:
        sheetSvc: Google sheet service (from getGoogleServices()['sheet'])
        settings: settings module

    Returns:
        List of archive directories
    """
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


def findCameraInArchive(camArchives, cameraID):
    """Find the entries in the camera archive directories for the given camera

    Args:
        camArchives (list): Result of getHpwrenCameraArchives() above
        cameraID (str): ID of camera to fetch images from

    Returns:
        List of archive dirs that matching camera
    """
    matchingCams = list(filter(lambda x: cameraID == x['id'], camArchives))
    # logging.warning('Found %d match(es): %s', len(matchingCams), matchingCams)
    return matchingCams


def getHpwrenImages(googleServices, settings, outputDir, camArchives, cameraID, startTimeDT, endTimeDT, gapMinutes):
    """Download HPWREN images from given camera and date time range with specified gaps

    Iterates over all directories for given camera in the archives and then downloads the images
    by calling downloadFilesHpwren

    Args:
        googleServices (): Google services and credentials
        settings (): settings module
        outputDir (str): Output directory path
        camArchives (list): Result of getHpwrenCameraArchives() above
        cameraID (str): ID of camera to fetch images from
        startTimeDT (datetime): starting time of time range
        endTimeDT (datetime): ending time of time range
        gapMinutes (int): Number of minutes of gap between images for downloading

    Returns:
        List of local filesystem paths to downloaded images
    """
    matchingCams = findCameraInArchive(camArchives, cameraID)
    for matchingCam in matchingCams:
        hpwrenSource = {
            'cameraID': cameraID,
            'dirName': matchingCam['dir'],
            'startTimeDT': startTimeDT,
            'endTimeDT': endTimeDT
        }
        logging.warning('Searching for files in dir %s', hpwrenSource['dirName'])
        found = downloadFilesHpwren(googleServices, settings, outputDir, hpwrenSource, gapMinutes, True)
        if found:
            return found
    return None


def diffImages(imgA, imgB):
    """Subtract two images (r-r, g-g, b-b).  Also add 128 to reduce negative values
       If a pixel is exactly same in both images, then the result will be 128,128,128 gray
       Out of range values (<0 and > 255) are moved to 0 and 255 by the convert('L') function

    Args:
        imgA: Pillow image object to subtract from
        imgB: Pillow image object to subtract

    Returns:
        Pillow image object containing the results of the subtraction with 128 mean
    """
    bandsImgA = imgA.split()
    bandsImgB = imgB.split()
    bandsImgOut = []

    for bandNum in range(len(bandsImgA)):
        # out = ImageMath.eval("convert((128+a/2)-b/2,'L')", a=bandsImgA[bandNum], b=bandsImgB[bandNum])
        out = ImageMath.eval("convert(128+a-b,'L')", a=bandsImgA[bandNum], b=bandsImgB[bandNum])
        bandsImgOut.append(out)

    return Image.merge('RGB', bandsImgOut)


def addImageToArchiveDb(dbManager, cameraID, timestamp, storageID, fileID, pan, tilt, zoom, md5):
    """Add the given image information to the image archive DB

    Args:
        dbManager (DbManager):
        cameraID (str): camera ID for DB
        timestamp (int): time when image was taken
        storageID (str): location of storage
        fileID (str): ID for image file on storage above
        pan (float): Pan value for PTZ cameras
        tilt (float): Tilt value for PTZ cameras
        zoom (float): Zoom value for PTZ cameras
        md5 (str): md5 hash of the image data
    """
    dbRow = {
        'CameraName': cameraID,
        'Timestamp': timestamp,
        'StorageID': storageID,
        'FileID': fileID,
        'Pan': pan,
        'Tilt': tilt,
        'Zoom': zoom,
        'md5': md5
    }
    dbManager.add_data('archive', dbRow)

