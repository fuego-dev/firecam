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

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaIoBaseDownload

import collect_args

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


def driveListFiles(service, parentID, searchName=None):
    page_token = None
    param = {}
    param['q'] = "'" + parentID + "' in parents and trashed = False"
    if (searchName != None):
        param['q'] = param['q'] + "and name = '" + searchName + "'"
    param['fields'] = 'nextPageToken, files(id, name)'
    param['pageToken'] = page_token
    param['supportsTeamDrives'] = True
    param['includeTeamDriveItems'] = True
    # print(param)
    results = service.files().list(**param).execute()
    items = results.get('files', [])
    # print('Files: ', items)
    return items


def readFromSheet(service, sheetID, cellRange):
    result = service.spreadsheets().values().get(spreadsheetId=sheetID,
                                                range=cellRange).execute()
    # print(result)
    values = result.get('values', [])
    return values


def downloadClassImage(service, classLocations, imgClass, fileName, outputDirectory):
    localFilePath = os.path.join(outputDirectory, fileName)
    if os.path.isfile(localFilePath):
        return localFilePath # already downloaded, nothing to do

    # parse cameraID from fileName
    regexExpanded = '([A-Za-z0-9-_]+[^_])_*(\d{4}-\d\d-\d\d)T(\d\d)[_;](\d\d)[_;](\d\d)'
    matchesExp = re.findall(regexExpanded, fileName)
    if len(matchesExp) != 1:
        print('Failed to parse name', fileName)
        exit(1)
    cameraID = matchesExp[0][0]

    # find subdir for camera
    parent = classLocations[imgClass]
    dirs = driveListFiles(service, parent, cameraID)
    if len(dirs) != 1:
        print('Expected 1 directory with name', cameraID, 'but found', len(dirs), dirs)
        exit(1)
    dirID = dirs[0]['id']
    dirName = dirs[0]['name']

    # find file in camera subdir
    files = driveListFiles(service, dirID, fileName)
    if len(files) != 1:
        print('Expected 1 file but found', len(files), files)
    if len(files) < 1:
        exit(1)
    fileID = files[0]['id']
    fileName = files[0]['name']
    print(fileID, fileName)

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
    return localFilePath

def getParentParser():
    return tools.argparser
