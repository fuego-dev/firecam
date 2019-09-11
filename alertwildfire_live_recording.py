
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





def cleanup_archive(googleServices, timethreshold):
    """initializes a continual cleaning function that only acts to remove archived data past a given threshold.
    Args:
        googleServices: Drive service (from getGoogleServices())
        timethreshold (flt): hours to keep data in archive
    Returns:
        continual should never return must be manually killed
    """
    img_archive.getImgPath
    timestamp = time.mktime(datetime.datetime.now().timetuple()) -60*timethreshold
    current_target = img_archive.getImgPath("./", "test", timestamp)[-23:-4]
    while True:
        for folder in goog_helper.driveListFilesByName(googleServices['drive'], settings.alertwildfire_archive):
            for fileobj in goog_helper.driveListFilesByName(googleServices['drive'], folder['id']):
                if fileobj['name'][-23:-4]< current_target:
                    logging.error('deleting file', fileobj['name'])
                    goog_helper.deleteItem(googleServices['drive'], file_id)
            
    return True

def capture_and_record(googleServices, outputDir, cameras_in_drive, camera_name):
    """requests current image from camera and uploads it to drive
    Args:
        googleServices: Drive service (from getGoogleServices())
        outputDir (str): folder path to download into
        cameras_in_drive (dict): dictionary of all camera archive folders with respective google IDs
        camera_name (str): name of camera as recorded by alertwildfire
    Returns:
        imgPath: local path to downloaded object
    """
    if not camera_name in cameras_in_drive.keys():
        cameras_in_drive[camera_name] = goog_helper.createFolder(googleServices['drive'], settings.alertwildfire_archive,  camera_name)
    dirID = cameras_in_drive[camera_name]
    imgPath = alertwildfire_API.request_current_image(outputDir, camera_name)
    goog_helper.uploadFile(googleServices['drive'], dirID, imgPath)
    print(imgPath)


def camera_management(obj):
    """manages the continual observation of a given set of cameras to watch.
    Args:
        obj (tuple): holds the googleServices, cameras_in_drive, camera_names_to_watch arguments
            googleServices: Drive service (from getGoogleServices())
            cameras_in_drive (dict): dictionary of all camera archive folders with respective google IDs
            camera_names_to_watch (List): list of camera names that are to be watched by this process
    Returns:
        None
    """
    googleServices, cameras_in_drive, camera_names_to_watch = obj[0], obj[1], obj[2]
    toggle=True
    while toggle:
        temporaryDir = tempfile.TemporaryDirectory()
        print(temporaryDir.name)
        for camera_name in camera_names_to_watch:   
            try:
                capture_and_record(googleServices, temporaryDir.name, cameras_in_drive, camera_name)
            except Exception as e:
                print()
        try:
            shutil.rmtree(temporaryDir.name)
        except Exception as e:
            #log error
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
        listofrotatingCameras = list(args.cameras_overide.replace(" ", "").strip('[]').split(','))
    else:
        listofCameras = alertwildfire_API.get_all_camera_info()
        listofrotatingCameras = [camera["name"] for camera in listofCameras if ("2" in camera["name"]) ]
    if args.parallelize:
        parallel = args.parallelize
    else:
        parallel = False

    #print(len(listofrotatingCameras))
    #print(goog_helper.driveListFilesByName(googleServices['drive'], settings.alertwildfire_archive))
    cameras_in_drive = {}
    for elem in goog_helper.driveListFilesByName(googleServices['drive'], settings.alertwildfire_archive):
        cameras_in_drive[elem['name']] = elem['id']

    if parallel:#having issues
        num_cameras_per_process = 5
        camera_bunchs = [listofrotatingCameras[num_cameras_per_process*num:num_cameras_per_process*num+num_cameras_per_process] for num in range(0, math.ceil(len(listofrotatingCameras)/num_cameras_per_process))]
    
        agents = 3
        agents = len(camera_bunchs)
        chunksize = 3
        with Pool(processes=agents) as pool:
            data = [(googleServices, cameras_in_drive, bunch) for bunch in camera_bunchs ]
            result = pool.map(camera_management, data , chunksize)
    else:
        input_obj = (googleServices, cameras_in_drive, listofrotatingCameras)
        camera_management(input_obj)




if __name__=="__main__":
    main()

