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

Helper functions for google cloud APIs (drive, sheets)

"""

import os
import sys
import re
import io
import shutil
import pathlib
import logging
import time, datetime, dateutil.parser

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaIoBaseDownload
from apiclient.http import MediaFileUpload

import collect_args
import img_archive

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]


def getGoogleServices(settings, args):
    store = file.Storage(settings.googleTokenFile)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(settings.googleCredsFile, ' '.join(SCOPES))
        creds = tools.run_flow(flow, store, args)
    driveService = build('drive', 'v3', http=creds.authorize(Http()))
    sheetService = build('sheets', 'v4', http=creds.authorize(Http()))
    return {
        'drive': driveService,
        'sheet': sheetService
    }


def driveListFilesQueryWithNextToken(service, parentID, customQuery=None, pageToken=None):
    param = {}
    param['q'] = "'" + parentID + "' in parents and trashed = False"
    if customQuery:
        param['q'] += " and " + customQuery
    param['fields'] = 'nextPageToken, files(id, name)'
    param['pageToken'] = pageToken
    param['supportsTeamDrives'] = True
    param['includeTeamDriveItems'] = True
    # print(param)
    results = service.files().list(**param).execute()
    items = results.get('files', [])
    nextPageToken = results.get('nextPageToken')
    # print('Files: ', items)
    return (items, nextPageToken)


def driveListFilesQuery(service, parentID, customQuery=None):
    (items, nextPageToken) = driveListFilesQueryWithNextToken(service, parentID, customQuery)
    return items


def driveListFilesByName(service, parentID, searchName=None):
    if searchName:
        customQuery = "name = '" + searchName + "'"
    return driveListFilesQuery(service, parentID, customQuery)


def readFromSheet(service, sheetID, cellRange):
    result = service.spreadsheets().values().get(spreadsheetId=sheetID,
                                                range=cellRange).execute()
    # print(result)
    values = result.get('values', [])
    return values


def searchFiles(service, parentID, minTime=None, maxTime=None, prefix=None, npt=None):
    constraints = []
    if minTime:
        constraints.append(" modifiedTime > '" + minTime + "' ")
    if maxTime:
        constraints.append(" modifiedTime < '" + maxTime + "' ")
    if prefix:
        constraints.append(" name contains '" + prefix + "' ")
    customQuery = ' and '.join(constraints)
    # logging.warning('Query %s', customQuery)
    if npt:
        if npt == 'init': # 'init' is special value to indicate desire to page but with exiting token
            npt = None
        return driveListFilesQueryWithNextToken(service, parentID, customQuery, npt)
    else:
        return driveListFilesQuery(service, parentID, customQuery)


def getDirForClassCamera(service, classLocations, imgClass, cameraID):
    parent = classLocations[imgClass]
    dirs = driveListFilesByName(service, parent, cameraID)
    if len(dirs) != 1:
        logging.error('Expected 1 directory with name %s, but found %d: %s', cameraID, len(dirs), dirs)
        logging.error('Searching in dir: %s', parent)
        logging.error('ImgClass %s, locations: %s', imgClass, classLocations)
        raise Exception('getDirForClassCam: Directory not found')
    dirID = dirs[0]['id']
    dirName = dirs[0]['name']
    return (dirID, dirName)


def downloadFileByID(service, fileID, localFilePath):
    # download file from drive to memory object
    request = service.files().get_media(fileId=fileID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download", int(status.progress() * 100))

    # store memory object data to local file
    fh.seek(0)
    with open(localFilePath, 'wb') as f:
        shutil.copyfileobj(fh, f)


def downloadFile(service, dirID, fileName, localFilePath):
    files = driveListFilesByName(service, dirID, fileName)
    if len(files) != 1:
        print('Expected 1 file but found', len(files), files)
    if len(files) < 1:
        exit(1)
    fileID = files[0]['id']
    fileName = files[0]['name']
    print(fileID, fileName)

    downloadFileByID(service, fileID, localFilePath)


def uploadFile(service, dirID, localFilePath):
    file_metadata = {'name': pathlib.PurePath(localFilePath).name, 'parents': [dirID]}
    media = MediaFileUpload(localFilePath,
                            mimetype='image/jpeg')
    retriesLeft = 5
    while retriesLeft > 0:
        retriesLeft -= 1
        try:
            file = service.files().create(body=file_metadata,
                                            media_body=media,
                                            supportsTeamDrives=True,
                                            fields='id').execute()
            return file
        except Exception as e:
            logging.warning('Error uploading image %s. %d retries left. %s', localFilePath, retriesLeft, str(e))
            if retriesLeft > 0:
                time.sleep(5) # wait 5 seconds before retrying
    logging.error('Too many upload failures')
    return None


def downloadClassImage(service, classLocations, imgClass, fileName, outputDirectory):
    localFilePath = os.path.join(outputDirectory, fileName)
    if os.path.isfile(localFilePath):
        return localFilePath # already downloaded, nothing to do

    # parse cameraID from fileName
    parsed = img_archive.parseFilename(fileName)
    cameraID = parsed['cameraID']

    # find subdir for camera
    (dirID, dirName) = getDirForClassCamera(service, classLocations, imgClass, cameraID)

    # find file in camera subdir
    downloadFile(service, dirID, fileName, localFilePath)
    return localFilePath


def getParentParser():
    return tools.argparser
