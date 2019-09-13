
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

def capture_and_record(googleServices, outputDir, camera_name):
    """requests current image from camera and uploads it to cloud
    Args:
        googleServices: Drive service (from getGoogleServices())
        outputDir (str): folder path to download into
        camera_name (str): name of camera as recorded by alertwildfire
    Returns:
        imgPath: local path to downloaded object
    """
    imgPath = alertwildfire_API.request_current_image(outputDir, camera_name)
    cloud_file_path = camera_name + '/' + pathlib.PurePath(imgPath).name
    goog_helper.uploadBucketObject(googleServices["storage"],"fuego-firecam-a",cloud_file_path, imgPath)

    


def fetchAllCameras(obj):
    """manages the continual observation of a given set of cameras to watch.
    Args:
        obj (tuple): holds the googleServices, camera_names_to_watch arguments
            googleServices: Drive service (from getGoogleServices())
            camera_names_to_watch (List): list of camera names that are to be watched by this process
    Returns:
        None
    """
    googleServices, camera_names_to_watch = obj[0], obj[1]
    while True:
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




def main():
    """directs the funtionality of the process ie start a cleanup, record all cameras on 2min refresh, record a subset of cameras, manage multiprocessed recording of cameras
    Args:
        "-c  cleaning_threshold" (flt): time in hours to store data
        "-o  cameras_overide"    (str): list of specific cameras to watch
        "-p  parallelize"       (bool): toggle to parallelize
    Returns:
        None
    """
    reqArgs = []
    optArgs = [["c", "cleaning_threshold", "time in hours to store data"],
 ["o", "cameras_overide", "specific cameras to watch"],
 ["p", "parallelize", "toggle parallelisation"]
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
    if args.parallelize:
        parallel = args.parallelize
    else:
        parallel = False

    if parallel:#having issues
        num_cameras_per_process = 5
        camera_bunchs = [listofRotatingCameras[num_cameras_per_process*num:num_cameras_per_process*num+num_cameras_per_process] for num in range(0, math.ceil(len(listofRotatingCameras)/num_cameras_per_process))]
    
        agents = 3
        agents = len(camera_bunchs)
        chunksize = 3
        with Pool(processes=agents) as pool:
            data = [(googleServices, bunch) for bunch in camera_bunchs ]
            result = pool.map(fetchAllCameras, data , chunksize)
    else:
        input_obj = (googleServices, listofRotatingCameras)
        fetchAllCameras(input_obj)




if __name__=="__main__":
    main()

