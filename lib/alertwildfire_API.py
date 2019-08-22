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
import exifread
import urllib.parse as urlp
baseApiUrl =urlp.ParseResult(scheme='https', netloc='data.alertwildfire.org', path='/api/firecams/v0', params='', query='', fragment='')#initialize



if settings.alertwildfirekey == 'do not put real key in files in open source git repo':
    logging.warning('Please update settings.alertwildfirekey with the key provided to you')


def getApiUrl(endpoint, queryParams = None):
    if queryParams:
        urlParts = baseApiUrl._replace(path = baseApiUrl.path+endpoint, query = queryParams)
    else:
        urlParts = baseApiUrl._replace(path = baseApiUrl.path+endpoint)
    url = urlp.urlunparse(urlParts)
    return url

def invokeApi(endpoint, queryParams = None, stream = False, url_override = False):
    headers = {'X-Api-Key': settings.alertwildfirekey}
    if url_override:
        url = url_override
    else:
        url = getApiUrl(endpoint, queryParams )
    response = requests.get(url, headers = headers, stream = stream)
    return response


def get_all_camera_info():
    response = invokeApi("/cameras", queryParams = None, stream = False)
    if response.status_code == 404:
        return 
    listofCameras = response.json()
    return listofCameras

def get_individual_camera_info(cameraID):
    response = invokeApi("/cameras", queryParams = "name="+cameraID, stream = False)
    if response.status_code == 404:
        return 
    listofCameras = response.json()
    return listofCameras[0]

def request_current_image(outputDir, cameraID):
    camera_info = get_individual_camera_info(cameraID)
    if camera_info["image"]["time"]:
        timeStamp = camera_info["image"]["time"]###need to convert their format


        logging.warning('not yet implemented camera_info/image/time')
        timeStamp = time.mktime(datetime.datetime.now().timetuple())


    elif camera_info["position"]["time"]:
        timeStamp = camera_info["position"]["time"]###need to convert their format


        logging.warning('not yet implemented camera_info/image/time')
        timeStamp = time.mktime(datetime.datetime.now().timetuple())

    else:
        timeStamp = time.mktime(datetime.datetime.now().timetuple())
    imgPath = img_archive.getImgPath(outputDir, cameraID, timeStamp)
    if os.path.isfile(imgPath):
        logging.warning('File %s already downloaded', imgPath)
        return imgPath
    if camera_info["image"]["url"]:
        url_override = camera_info["image"]["url"]
    else:
        url_override = False
    response = invokeApi("/currentimage", queryParams = "name="+cameraID, stream = True, url_override = url_override)
    if response.status_code == 200:
        with open(imgPath, 'wb') as f:
            for chunk in response:
                f.write(chunk)
            f.close()
        response.close()
        f = open(imgPath, 'rb')
        f_tags = exifread.process_file(f)
        f.close()
        if "Image DateTime" in f_tags.keys():
            timeStamp = time.mktime(datetime.datetime.strptime(str(f_tags["Image DateTime"]), '%Y:%m:%d %H:%M:%S').timetuple())
            newimgPath = img_archive.getImgPath(outputDir, cameraID, timeStamp)
            os.rename(imgPath, newimgPath)
            imgPath=newimgPath
        return imgPath 
    response.close()
    return


"""#time expensive POC
def request_all_current_images(outputDir, delay_between_requests=None):
    listofCameras = get_all_camera_info()
    list_of_failed = []
    list_of_downloaded_img_paths =[]
    for camera in listofCameras:
        cameraID = camera["name"]
        if camera["position"]["time"]:
            timeStamp = camera["position"]["time"]###need to convert their format
        elif camera["image"]["time"]:
            timeStamp = camera["image"]["time"]###need to convert their format
        else:
            timeStamp = None
        path = request_current_image(outputDir, cameraID, timeStamp)
        if not path:# if failed request put it in a queue to try one more time
            if not (camera in list_of_failed):
                list_of_failed.append(camera)
                listofCameras.append(camera)
        list_of_downloaded_img_paths.append(path)
        
        if delay_between_requests:###delay to prevent api lockout
            time.sleep(delay_between_requests)
    return list_of_downloaded_img_paths
"""



def record_camera_info():
    #the future ability to correlate image, position and direction
    return


