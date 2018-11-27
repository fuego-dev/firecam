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
@author: Kinshuk Govil

This is the main code for reading images from webcams and detecting fires

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import collect_args
import rect_to_squares
import goog_helper
import tf_helper
import db_manager
import email_helper

import os
import pathlib
import tempfile
from shutil import copyfile
import time, datetime
import random
import re
from urllib.request import urlretrieve
import tensorflow as tf
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True


def getNextImage(dbManager, cameras):
    """Gets the next image to check for smoke

    Uses a shared counter being updated by all cooperating detection processes
    to index into the list of cameras to download the image to a local
    temporary directory

    Args:
        dbManager (DbManager):
        cameras (list): list of cameras

    Returns:
        Tuple containing camera name, current timestamp, and filepath of the image
    """
    if getNextImage.tmpDir == None:
        getNextImage.tmpDir = tempfile.TemporaryDirectory()
        print('TempDir', getNextImage.tmpDir.name)

    index = dbManager.getNextSourcesCounter() % len(cameras)
    camera = cameras[index]
    timestamp = int(time.time())
    timeStr = datetime.datetime.fromtimestamp(timestamp).isoformat()
    timeStr = timeStr.replace(':', ';') # make windows happy
    imgName = '_'.join([camera['name'], timeStr])
    imgPath = os.path.join(getNextImage.tmpDir.name, imgName + '.jpg')
    # print('urlr', camera['url'], imgPath)
    try:
        urlretrieve(camera['url'], imgPath)
    except Exception as e:
        print('Error fetching image from', camera['name'], e)
        return getNextImage(dbManager, cameras)
    return (camera['name'], timestamp, imgPath)
getNextImage.tmpDir = None

# XXXXX Use a fixed stable directory for testing
# from collections import namedtuple
# Tdir = namedtuple('Tdir', ['name'])
# getNextImage.tmpDir = Tdir('c:/tmp/dftest')


def segmentImage(imgPath):
    """Segment the given image into sections to for smoke classificaiton

    Args:
        imgPath (str): filepath of the image

    Returns:
        List of dictionary containing information on each segment
    """
    img = Image.open(imgPath)
    ppath = pathlib.PurePath(imgPath)
    segments = rect_to_squares.cutBoxes(img, str(ppath.parent), imgPath)
    img.close()
    return segments


def recordScores(dbManager, camera, timestamp, segments):
    """Record the smoke scores for each segment into SQL DB

    Args:
        dbManager (DbManager):
        camera (str): camera name
        timestamp (int):
        segments (list): List of dictionary containing information on each segment
    """
    # regexSize = '.+_Crop_(\d+)x(\d+)x(\d+)x(\d+)'
    dt = datetime.datetime.fromtimestamp(timestamp)
    secondsInDay = (dt.hour * 60 + dt.minute) * 60 + dt.second

    for segmentInfo in segments:
        # matches = re.findall(regexSize, imgScore['imgPath'])
        # if len(matches) == 1:
        if True:
            dbRow = {
                'CameraName': camera,
                'Timestamp': timestamp,
                'MinX': segmentInfo['MinX'],
                'MinY': segmentInfo['MinY'],
                'MaxX': segmentInfo['MaxX'],
                'MaxY': segmentInfo['MaxY'],
                'Score': segmentInfo['score'],
                'SecondsInDay': secondsInDay
            }
            dbManager.add_data('scores', dbRow, commit=False)
    dbManager.commit()


def postFilter(dbManager, camera, timestamp, segments):
    """Post classification filter to reduce false positives

    Many times smoke classification scores segments with haze and glare
    above 0.5.  Haze and glare occur tend to occur at similar time over
    multiple days, so this filter raises the threshold based on the max
    smoke score for same segment at same time of day over the last few days.
    Score must be > halfway between max value and 1.  Also, minimum .1 above max.

    Args:
        dbManager (DbManager):
        camera (str): camera name
        timestamp (int):
        segments (list): List of dictionary containing information on each segment

    Returns:
        Dictionary with information for the segment most likely to be smoke
        or None
    """
    sqlTemplate = """SELECT MinX,MinY,MaxX,MaxY,count(*) as cnt, avg(score) as avgs, max(score) as maxs FROM scores
    WHERE CameraName='%s' and Timestamp > %s and Timestamp < %s and SecondsInDay > %s and SecondsInDay < %s
    GROUP BY MinX,MinY,MaxX,MaxY"""

    dt = datetime.datetime.fromtimestamp(timestamp)
    secondsInDay = (dt.hour * 60 + dt.minute) * 60 + dt.second
    sqlStr = sqlTemplate % (camera, timestamp - 60*60*int(24*3.5), timestamp - 60*60*12, secondsInDay - 60*60, secondsInDay + 60*60)
    # print('sql', sqlStr, timestamp)
    dbResult = dbManager.query(sqlStr)
    # if len(dbResult) > 0:
    #     print('post filter result', dbResult)
    maxFireSegment = None
    maxFireScore = 0
    for segmentInfo in segments:
        if segmentInfo['score'] < .5:
            break
        for row in dbResult:
            if (row['minx'] == segmentInfo['MinX'] and row['miny'] == segmentInfo['MinY'] and
                row['maxx'] == segmentInfo['MaxX'] and row['maxy'] == segmentInfo['MaxY']):
                threshold = (row['maxs'] + 1)/2 # threshold is halfway between max and 1
                threshold = max(threshold, row['maxs'] + 0.1) # threshold at least .1 above max
                # print('thresh', row['minx'], row['miny'], row['maxx'], row['maxy'], row['maxs'], threshold)
                if (segmentInfo['score'] > threshold) and (segmentInfo['score'] > maxFireScore):
                    maxFireScore = segmentInfo['score']
                    maxFireSegment = segmentInfo
                    maxFireSegment['HistAvg'] = row['avgs']
                    maxFireSegment['HistMax'] = row['maxs']
                    maxFireSegment['HistNumSamples'] = row['cnt']

    return maxFireSegment


def recordDetection(dbManager, service, camera, timestamp, imgPath, fireSegment):
    """Record that a smoke/fire has been detected

    Record the detection with useful metrics in 'detections' table in SQL DB.
    Also, upload image file to google drive

    Args:
        dbManager (DbManager):
        service:
        camera (str): camera name
        timestamp (int):
        imgPath: filepath of the image
        fireSegment (dictionary): dictionary with information for the segment with fire/smoke

    Returns:
        Google drive ID for the uploaded image file
    """
    print('Fire detected by camera, image, segment', camera, imgPath, fireSegment)
    # save file to local detection dir
    ppath = pathlib.PurePath(imgPath)
    copyfile(imgPath, os.path.join(settings.detectionDir, ppath.name))
    # upload file to google drive detection dir
    driveFile = goog_helper.uploadFile(service, settings.detectionPictures, imgPath)
    driveFileID = None
    if driveFile:
        print('Uploaded to google drive detections folder', driveFile)
        driveFileID = driveFile['id']

    dbRow = {
        'CameraName': camera,
        'Timestamp': timestamp,
        'MinX': fireSegment['MinX'],
        'MinY': fireSegment['MinY'],
        'MaxX': fireSegment['MaxX'],
        'MaxY': fireSegment['MaxY'],
        'Score': fireSegment['score'],
        'HistAvg': fireSegment['HistAvg'],
        'HistMax': fireSegment['HistMax'],
        'HistNumSamples': fireSegment['HistNumSamples'],
        'ImageID': driveFileID
    }
    dbManager.add_data('detections', dbRow)
    return driveFileID


def checkAndUpdateAlerts(dbManager, camera, timestamp, driveFileID):
    """Check if alert has been recently sent out for given camera

    If an alert of this camera has't been recorded recently, record this as an alert

    Args:
        dbManager (DbManager):
        camera (str): camera name
        timestamp (int):
        driveFileID (str): Google drive ID for the uploaded image file

    Returns:
        True if this is a new alert, False otherwise
    """
    sqlTemplate = """SELECT * FROM alerts
    where CameraName='%s' and timestamp > %s"""
    sqlStr = sqlTemplate % (camera, timestamp - 60*60*12) # suppress alerts for 12 hours
    dbResult = dbManager.query(sqlStr)
    if len(dbResult) > 0:
        print('Supressing new alert due to recent alert')
        return False

    dbRow = {
        'CameraName': camera,
        'Timestamp': timestamp,
        'ImageID': driveFileID
    }
    dbManager.add_data('alerts', dbRow)
    return True


def alertFire(camera, imgPath, driveFileID, fireSegment):
    """Send an email alert for a potential new fire

    Send email with information about the camera and fire score includeing
    image attachments

    Args:
        camera (str): camera name
        imgPath: filepath of the image
        driveFileID (str): Google drive ID for the uploaded image file
        fireSegment (dictionary): dictionary with information for the segment with fire/smoke
    """
    # send email
    fromAccount = (settings.fuegoEmail, settings.fuegoPasswd)
    subject = 'Possible (%d%%) fire in camera %s' % (int(fireSegment['score']*100), camera)
    body = 'Please check the attached image for fire.'
    if driveFileID:
        driveTempl = '\nAlso available from google drive as https://drive.google.com/file/d/%s'
        driveBody = driveTempl % driveFileID
        body += driveBody
    email_helper.send_email(fromAccount, settings.detectionsEmail, subject, body, [imgPath])


def deleteImageFiles(imgPath, segments):
    """Delete all image files given in segments

    Args:
        segments (list): List of dictionary containing information on each segment
    """
    for segmentInfo in segments:
        os.remove(segmentInfo['imgPath'])
    os.remove(imgPath)
    ppath = pathlib.PurePath(imgPath)
    leftoverFiles = os.listdir(str(ppath.parent))
    if len(leftoverFiles) > 0:
        print('leftover files', leftoverFiles)


def getLastScoreCamera(dbManager):
    sqlStr = "SELECT CameraName from scores order by Timestamp desc limit 1;"
    dbResult = dbManager.query(sqlStr)
    if len(dbResult) > 0:
        return dbResult[0]['CameraName']
    return None


def heartBeat(filename):
    """Inform monitor process that this detection process is alive

    Informs by updating the timestamp on given file

    Args:
        filename (str): file path of file used for heartbeating
    """
    pathlib.Path(filename).touch()


def main():
    optArgs = [
        ["b", "heartbeat", "filename used for heartbeating check"],
    ]
    args = collect_args.collectArgs([], optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    # commenting out the print below to reduce showing secrets in settings
    # print('Settings:', list(map(lambda a: (a,getattr(settings,a)), filter(lambda a: not a.startswith('__'), dir(settings)))))
    googleServices = goog_helper.getGoogleServices(settings, args)
    if settings.db_file:
        print('using sqlite', settings.db_file)
        dbManager = db_manager.DbManager(sqliteFile=settings.db_file)
    else:
        print('using postgres', settings.psqlHost)
        dbManager = db_manager.DbManager(psqlHost=settings.psqlHost, psqlDb=settings.psqlDb,
                                        psqlUser=settings.psqlUser, psqlPasswd=settings.psqlPasswd)
    cameras = dbManager.get_sources()

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # quiet down tensorflow logging
    graph = tf_helper.load_graph(settings.model_file)
    labels = tf_helper.load_labels(settings.labels_file)
    config = tf.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 0.1 #hopefully reduces segfaults
    with tf.Session(graph=graph, config=config) as tfSession:
        while True:
            (camera, timestamp, imgPath) = getNextImage(dbManager, cameras)
            segments = segmentImage(imgPath)
            # print('si', segments)
            tf_helper.classifySegments(tfSession, graph, labels, segments)
            segments.sort(key=lambda x: -x['score'])
            timeStr = datetime.datetime.fromtimestamp(timestamp).strftime('%F %T')
            print('%s: Highest score for camera %s: %f' % (timeStr, camera, segments[0]['score']))
            # print('cs', segments)
            recordScores(dbManager, camera, timestamp, segments)
            fireSegment = postFilter(dbManager, camera, timestamp, segments)
            if fireSegment:
                driveFileID = recordDetection(dbManager, googleServices['drive'], camera, timestamp, imgPath, fireSegment)
                if checkAndUpdateAlerts(dbManager, camera, timestamp, driveFileID):
                    alertFire(camera, imgPath, driveFileID, fireSegment)
            deleteImageFiles(imgPath, segments)
            if (args.heartbeat):
                heartBeat(args.heartbeat)

if __name__=="__main__":
    main()
