
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
import multiprocessing
from multiprocessing import Pool
import math
import datetime
import img_archive
import pathlib
import logging
import db_manager
import hashlib





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
    timeStamp_chunk = image_base_name[-23:-4]+'__'
    fileTag=image_base_name[-4:]
    imgname = cameraName_chunk+timeStamp_chunk+metadata_chunk+fileTag
    return imgname


def capture_and_record(googleServices, dbManager, outputDir, camera_name):
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
    #validate that it is new data
    md5 = hashlib.md5(open(imgPath, 'rb').read()).hexdigest()
    ###warning approximitly doubles image processing time
    SQLcommand="select FileID from archive where md5='"+str(md5)+"'"
    matches = dbManager.query(SQLcommand)
    if len(matches)>0:
        logging.warning('skipping %s, image has not changed since last upload.', camera_name)
        return 
    ###


    image_base_name = pathlib.PurePath(imgPath).name
    image_name_with_metadata = build_name_with_metadata(image_base_name,pull1)
    cloud_file_path =  'alert_archive/' + camera_name + '/' + image_name_with_metadata
    goog_helper.uploadBucketObject(googleServices["storage"], settings.archive_storage_bucket, cloud_file_path, imgPath)
    

    #add to Database
    timeStamp = img_archive.parseFilename(image_base_name)['unixTime']
    img_archive.addImageToArchiveDb(dbManager, camera_name, timeStamp, 'gs://'+settings.archive_storage_bucket, cloud_file_path, pull1['position']['pan'], pull1['position']['tilt'], pull1['position']['zoom'], md5)




def fetchAllCameras(camera_names_to_watch):
    """manages the continual observation of a given set of cameras to watch.
    Args:
        camera_names_to_watch (List): list of camera names that are to be watched by this process
    Returns:
        None
    """
    #please do not remove googleServices definintion from this function
    # it is needed for the parallel processing authentication
    googleServices = goog_helper.getGoogleServices(settings, [])
    num_of_watched_cameras = len(camera_names_to_watch)
    dbManager = db_manager.DbManager(sqliteFile=settings.db_file,
                                    psqlHost=settings.psqlHost,              psqlDb=settings.psqlDb,
                                    psqlUser=settings.psqlUser, psqlPasswd=settings.psqlPasswd)
    while True:
        tic = time.time()
        temporaryDir = tempfile.TemporaryDirectory()
        for camera_name in camera_names_to_watch:   
            try:
                capture_and_record(googleServices, dbManager, temporaryDir.name, camera_name)
                logging.warning('successfully fetched camera %s.', camera_name)
            except Exception as e:
                logging.error('Failed to fetch camera %s. %s', camera_name, str(e))
        try:
            shutil.rmtree(temporaryDir.name)
        except Exception as e:
            logging.error('Failed to delete temporaryDir %s. %s', temporaryDir.name, str(e))
            pass
        logging.warning('retrieval of %s cameras took %s seconds.',num_of_watched_cameras, time.time()-tic)



def cleanup_archive(googleServices, dbManager, timethreshold):
    """initializes a continual cleaning function that only acts to remove archived data past a given threshold.
    Args:
        googleServices: Drive service (from getGoogleServices())
        dbManager: Database service
        timethreshold (flt): hours to keep data in archive
    Returns:
        continual should never return must be manually killed
    """
    Default_refresh_time = 10*60#10 min in seconds
    while True:
        current_time = time.time()
        target_time = current_time - timethreshold*60*60
        SQLcommand="select FileID from archive where timestamp<"+str(target_time)
        matches = dbManager.query(SQLcommand)
        for match in matches:
            goog_helper.deleteBucketObject(googleServices['storage'], settings.archive_storage_bucket, match['fileID'])
            #does not yet change database
        time.sleep(Default_refresh_time)
    



def main():
    """directs the funtionality of the process ie start a cleanup, record all cameras on 2min refresh, record a subset of cameras, manage multiprocessed recording of cameras
    Args:
        -c  cleaning_threshold" (flt): time in hours to store data
        -o  cameras_overide    (str): list of specific cameras to watch
        -a  agents            (int): number of agents to assign for parallelization
    Returns:
        None
    """
    reqArgs = []
    optArgs = [
        ["c", "cleaning_threshold", "time in hours to store data"],
        ["o", "cameras_overide", "specific cameras to watch"],
        ["a", "agents", "number of agents to assign for parallelization"]
    ]
    args = collect_args.collectArgs(reqArgs,  optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    dbManager = db_manager.DbManager(sqliteFile=settings.db_file,
                                    psqlHost=settings.psqlHost, psqlDb=settings.psqlDb,    
                                    psqlUser=settings.psqlUser, psqlPasswd=settings.psqlPasswd)
    
    if args.cleaning_threshold:
        cleaning_threshold = float(args.cleaning_threshold)
        cleanup_archive(googleServices, dbManager, cleaning_threshold)
    if args.cameras_overide:
        listofRotatingCameras = list(args.cameras_overide.replace(" ", "").strip('[]').split(','))
    else:
        listofCameras = alertwildfire_API.get_all_camera_info()
        listofRotatingCameras = [camera["name"] for camera in listofCameras if (camera["name"][-1]=='2') ]
    if args.agents:
        agents = int(args.agents)
        #num of camera's per process
        test = "Axis-Briar2"

        temporaryDir = tempfile.TemporaryDirectory()
        trial = [x for x in range(0,10)]
        tic = time.time()
        for x in trial:
            capture_and_record(googleServices, dbManager, temporaryDir.name, test)
        toc =time.time()-tic
        toc_avg = toc/len(trial)
        # target estimate of camera refresh time
        target_refresh_time_per_camera = 12#secs
        num_cameras_per_process = math.floor(target_refresh_time_per_camera / toc_avg)
        #future ability to re-adjust as needed

        #divy the cameras
        camera_bunchs= []
        num_of_processes_needed  =  math.ceil(len(listofRotatingCameras)/num_cameras_per_process)
        if num_of_processes_needed>agents:
            logging.warning('unable to process all given cameras on this machine with %s agents and maintain a target refresh rate of %s seconds, please reduce number of cameras to less than %s',agents, target_refresh_time_per_camera,num_cameras_per_process*agents)
            return

        for num in range(0, num_of_processes_needed):
            split_start = num_cameras_per_process*num
            split_stop = num_cameras_per_process*num+num_cameras_per_process
            camera_bunchs.append(listofRotatingCameras[split_start:split_stop])

        with Pool(processes=agents) as pool:
            result = pool.map(fetchAllCameras, camera_bunchs)
            pool.close()
    else:
        fetchAllCameras(listofRotatingCameras)




if __name__=="__main__":
    main()

