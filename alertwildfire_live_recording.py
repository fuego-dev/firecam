
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


import os
import sys
fuegoRoot = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)

import settings
settings.fuegoRoot = fuegoRoot 
import alertwildfire_API
import goog_helper
import collect_args
import tempfile
import time
import shutil
from multiprocessing import Pool
import math
import datetime
import img_archive
import pathlib
import logging
import db_manager



def cleanup_archive(googleServices, timethreshold):
    """initializes a continual cleaning function that only acts to remove archived data past a given threshold.
    Args:
        googleServices: Drive service (from getGoogleServices())
        timethreshold (flt): hours to keep data in archive
    Returns:
        continual should never return must be manually killed
    """
    #img_archive.getImgPath
    #timestamp = time.mktime(datetime.datetime.now().timetuple()) -60*timethreshold
    #current_target = img_archive.getImgPath("./", "test", timestamp)[-23:-4]
    #while True:
    #    for folder in goog_helper.driveListFilesByName(googleServices['drive'], settings.alertwildfire_archive):
    #        for fileobj in goog_helper.driveListFilesByName(googleServices['drive'], folder['id']):
    #            if fileobj['name'][-23:-4]< current_target:
    #                logging.error('deleting file', fileobj['name'])
    #                goog_helper.deleteItem(googleServices['drive'], file_id)
    #        
    return True

def build_name_with_metadata(image_base_name,metadata):
    """reformats image name to include positional metadata
    Args:
        image_base_name (str): original image name containing only camera name and timestamp
        metadata (dict): individual camera metadata pulled from alertwildfire_API.get_individual_camera_info
    Returns:
        imgname (str): name of image with positionalmetadata
    """


    cameraName_chunk = image_base_name[:-23]
    metadata_chunk = 'p'+str(metadata['position']['pan'])+'_t'+str(metadata['position']['tilt'])+'_z'+str(metadata['position']['zoom'])
    timeStamp_chunk = '__'+image_base_name[-23:]
    imgname = cameraName_chunk+metadata_chunk+timeStamp_chunk
    return imgname


def capture_and_record(googleServices, outputDir, camera_name):
    """requests current image from camera and uploads it to cloud
    Args:
        googleServices: Drive service (from getGoogleServices())
        outputDir (str): folder path to download into
        camera_name (str): name of camera as recorded by alertwildfire
    Returns:
        imgPath: local path to downloaded object
    """
    success = False
    retriesLeft = 5
    pull1 = alertwildfire_API.get_individual_camera_info(camera_name)
    while (not success) and  (retriesLeft > 0):
        
        imgPath = alertwildfire_API.request_current_image(outputDir, camera_name) 
        pull2 = alertwildfire_API.get_individual_camera_info(camera_name)
        if pull1['position'] == pull1['position']:
            success = True
        else:
            pull1 = pull2
            retriesLeft -= 1

    image_base_name = pathlib.PurePath(imgPath).name
    image_name_with_metadata = build_name_with_metadata(image_base_name,pull1)
    cloud_file_path =  'alert_archive/' + camera_name + '/' + image_name_with_metadata
    goog_helper.uploadBucketObject(googleServices["storage"], settings.archive_storage_bucket, cloud_file_path, imgPath)
    


    dbManager  = db_manager.DbManager(psqlHost = settings.psqlHost,
 psqlDb = settings.psqlDb,
 psqlUser = settings.psqlUser,
 psqlPasswd = settings.psqlPasswd)
    timeStamp = img_archive.parseFilename(image_base_name)['unixTime']
    img_archive.addImageToArchiveDb(dbManager, camera_name, timeStamp, 'gs://'+settings.archive_storage_bucket, cloud_file_path, pull1['position']['pan'], pull1['position']['tilt'], pull1['position']['zoom'])




def fetchAllCameras(googleServices, camera_names_to_watch):
    """manages the continual observation of a given set of cameras to watch.
    Args:
        googleServices: google service service (from getGoogleServices())
        camera_names_to_watch (List): list of camera names that are to be watched by this process
    Returns:
        None
    """
    while True:
        tic = time.time()
        temporaryDir = tempfile.TemporaryDirectory()
        for camera_name in camera_names_to_watch:   
            try:
                capture_and_record(googleServices, temporaryDir.name, camera_name)
                logging.warning('successfully fetched camera %s.', camera_name)
            except Exception as e:
                logging.error('Failed to fetch camera %s. %s', camera_name, str(e))
        try:
            shutil.rmtree(temporaryDir.name)
        except Exception as e:
            logging.error('Failed to delete temporaryDir %s. %s', temporaryDir.name, str(e))
            pass
        print('toc = '+str( time.time()-tic))



def main():
    """directs the funtionality of the process ie start a cleanup, record all cameras on 2min refresh, record a subset of cameras, manage multiprocessed recording of cameras
    Args:
        -c  cleaning_threshold" (flt): time in hours to store data
        -o  cameras_overide"    (str): list of specific cameras to watch
    Returns:
        None
    """
    reqArgs = []
    optArgs = [["c", "cleaning_threshold", "time in hours to store data"],
 ["o", "cameras_overide", "specific cameras to watch"]
]
    args = collect_args.collectArgs(reqArgs,  optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    if args.cleaning_threshold:
        cleaning_threshold = float(args.cleaning_threshold)
        cleanup_archive(googleServices, cleaning_threshold)
    if args.cameras_overide:
        listofRotatingCameras = list(args.cameras_overide.replace(" ", "").strip('[]').split(','))
    else:
        listofCameras = alertwildfire_API.get_all_camera_info()
        listofRotatingCameras = [camera["name"] for camera in listofCameras if (camera["name"][-1]=='2') ]

    fetchAllCameras(googleServices, listofRotatingCameras)




if __name__=="__main__":
    main()

