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
fuegoRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import datetime
import requests
import time
import img_archive



if settings.alertwildfirekey == 'do not put real key in files in open source git repo':
    logging.warning('Please update settings.alertwildfirekey with the key provided to you')


def get_all_camera_info():
    headers = {'X-Api-Key': settings.alertwildfirekey}
    response = requests.get('https://data.alertwildfire.org/api/firecams/v0/cameras', headers=headers)
    if response.status_code == 404:
        return 
    exec('listofcameras = '+response.text, locals(),globals())
    return listofcameras

def get_individual_camera_info(cameraID):

    headers = {'X-Api-Key': settings.alertwildfirekey}
    response = requests.get('https://data.alertwildfire.org/api/firecams/v0/cameras'+'?name='+cameraID, headers=headers)
    if response.status_code == 404:
        return 
    exec('listofcameras = '+response.text, locals(),globals())
    return listofcameras[0]

def request_current_image(outputDir,cameraID,closestTime = None,display=False):
    headers = {'X-Api-Key': settings.alertwildfirekey}
    response = requests.get('https://data.alertwildfire.org/api/firecams/v0/currentimage'+'?name='+cameraID, headers=headers,stream = True)
    if not closestTime:
        closestTime = time.mktime(datetime.datetime.now().timetuple())
    imgPath = img_archive.getImgPath(outputDir, cameraID, closestTime)
    if os.path.isfile(imgPath):
        logging.warning('File %s already downloaded', imgPath)
        return imgPath
    if response.status_code == 200:
        with open(imgPath, 'wb') as f:
            for chunk in response:
                f.write(chunk)
            f.close()
        response.close()
        if display:
            import matplotlib.image as mpimg
            import matplotlib.pyplot as plt
            img = mpimg.imread(imgPath)
            plt.imshow(img) 
            plt.show()
        return imgPath
    response.close()
    return



def request_all_current_images(outputDir,delay_between_requests=None):
    listofcameras = get_all_camera_info()
    list_of_failed = []
    list_of_downloaded_img_paths =[]
    for camera in listofcameras:
        cameraID = camera["name"]
        if camera["position"]["time"]:
            closestTime = camera["position"]["time"]##########need to convert there format
        elif camera["image"]["time"]:
            closestTime = camera["image"]["time"]##########need to convert there format
        else:
            closestTime = None
        path = request_current_image(outputDir,cameraID,closestTime,display=False)
        if not path:# if failed request put it in a queue to try one more time
            if not (camera in list_of_failed):
                list_of_failed.append(camera)
                listofcameras.append(camera)
        list_of_downloaded_img_paths.append(path)
        
        if delay_between_requests:###########################reminate code
            time.sleep(delay_between_requests)
    return list_of_downloaded_img_paths

def record_camera_info():
    #the future ability to correlate image, position and direction
    return


