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

def findCameraIndex(cameras, searchName):
    for (index, camera) in enumerate(cameras):
        if camera['name'] == searchName:
            return index

def getNextImage(cameras, lastProcessCamera):
    if getNextImage.tmpDir == None:
        getNextImage.tmpDir = tempfile.TemporaryDirectory()
        print('TempDir', getNextImage.tmpDir.name)
        getNextImage.counter = findCameraIndex(cameras, lastProcessCamera)
        print('lastCam', getNextImage.counter, lastProcessCamera)
        if getNextImage.counter == None:
            getNextImage.counter = random.randint(1,len(cameras))
        getNextImage.counter += 1

    index = getNextImage.counter % len(cameras)
    getNextImage.counter += 1
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
        return getNextImage(cameras, lastProcessCamera)
    return (camera['name'], timestamp, imgPath)
getNextImage.counter = 0
getNextImage.tmpDir = None

# XXXXX Use a fixed stable directory for testing
# from collections import namedtuple
# Tdir = namedtuple('Tdir', ['name'])
# getNextImage.tmpDir = Tdir('c:/tmp/dftest')


def segmentImage(imgPath):
    img = Image.open(imgPath)
    ppath = pathlib.PurePath(imgPath)
    segments = rect_to_squares.cutBoxes(img, str(ppath.parent), imgPath)
    img.close()
    return segments


def recordScores(dbManager, camera, timestamp, segments):
    # regexSize = '.+_Crop_(\d+)x(\d+)x(\d+)x(\d+)'
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
                'Score': segmentInfo['score']
            }
            dbManager.add_data('scores', dbRow, commit=False)
    dbManager.commit()


def postFilter(dbManager, camera, timestamp, segments):
    sqlTemplate = """SELECT * FROM scores
    where CameraName='%s' and timestamp = (
        SELECT timestamp FROM scores
        where CameraName='%s' and timestamp > %d and timestamp < %d
        order by abs(timestamp-%d) asc limit 1)"""
    desiredTime = timestamp - 60*60*24
    sqlStr = sqlTemplate % (camera, camera, desiredTime - 60*60, desiredTime + 60*60, desiredTime)
    # print('sql', sqlStr, timestamp)
    dbResult = dbManager.query(sqlStr)
    # if len(dbResult) > 0:
    #     print('post filter result', dbResult)
    for segmentInfo in segments:
        if segmentInfo['score'] < .5:
            break
        for row in dbResult:
            if (row['MinX'] == segmentInfo['MinX'] and row['MinY'] == segmentInfo['MinY'] and
                row['MaxX'] == segmentInfo['MaxX'] and row['MaxY'] == segmentInfo['MaxY']):
                if segmentInfo['score'] - row['Score'] >= .5:
                    return segmentInfo
    return False


def alertFire(service, camera, imgPath, newFireSegment):
    print('New fire detected by camera, image, segment', camera, imgPath, newFireSegment)
    # save file to local detection dir
    ppath = pathlib.PurePath(imgPath)
    copyfile(imgPath, os.path.join(settings.detectionDir, ppath.name))
    # upload file to google drive detection dir
    driveFile = goog_helper.uploadFile(service, settings.detectionPictures, imgPath)
    if driveFile:
        print('Uploaded to google drive detections folder', driveFile)
    # send email
    fromAccount = (settings.fuegoEmail, settings.fuegoPasswd)
    subject = 'Possible (%d%%) fire in camera %s' % (int(newFireSegment['score']*100), camera)
    body = 'Please check the attached image for fire.'
    if driveFile:
        driveTempl = '\nAlso available from google drive as https://drive.google.com/file/d/%s'
        driveBody = driveTempl % driveFile['id']
        body += driveBody
    email_helper.send_email(fromAccount, settings.detectionsEmail, subject, body, [imgPath])


def deleteImageFiles(imgPath, segments):
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
    pathlib.Path(filename).touch()


def main():
    optArgs = [
        ["b", "heartbeat", "filename used for heartbeating check"],
    ]
    args = collect_args.collectArgs([], optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    dbManager = db_manager.DbManager(settings.db_file)
    cameras = dbManager.get_sources()
    lastProcessCamera = getLastScoreCamera(dbManager)

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # quiet down tensorflow logging
    graph = tf_helper.load_graph(settings.model_file)
    labels = tf_helper.load_labels(settings.labels_file)
    config = tf.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 0.1 #hopefully reduces segfaults
    with tf.Session(graph=graph, config=config) as tfSession:
        while True:
            (camera, timestamp, imgPath) = getNextImage(cameras, lastProcessCamera)
            segments = segmentImage(imgPath)
            # print('si', segments)
            tf_helper.classifySegments(tfSession, graph, labels, segments)
            segments.sort(key=lambda x: -x['score'])
            timeStr = datetime.datetime.fromtimestamp(timestamp).strftime('%F %T')
            print('%s: Highest score for camera %s: %f' % (timeStr, camera, segments[0]['score']))
            # print('cs', segments)
            recordScores(dbManager, camera, timestamp, segments)
            newFireSegment = postFilter(dbManager, camera, timestamp, segments)
            if newFireSegment:
                alertFire(googleServices['drive'], camera, imgPath, newFireSegment)
            deleteImageFiles(imgPath, segments)
            if (args.heartbeat):
                heartBeat(args.heartbeat)

if __name__=="__main__":
    main()
