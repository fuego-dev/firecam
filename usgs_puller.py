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
Fetch images from USGS archives

@author: fuego
"""
from skimage import io
import os
import numpy as np
import time
#from multiprocessing import Pool #The current code is kind of slow - perhaps parallelizing the process would help?

###### Inputs Explained #######
#camera = url
#date = YYYYMMDD in string format
#start = [hour, minute] in float format
#end = [hour, minute] in float format
#output_folder = file path to folder where images are stored

def usgs_puller(camera, date, start, end, output_folder):
    start_time = time.time()
    camera_dir = output_folder + '/' + camera + '/'
    if not os.path.exists(camera_dir):
        os.makedirs(camera_dir)
        
    image_url = 'https://rockyags.cr.usgs.gov/outgoing/camHist/swfrs/'+ date[:4] + '/' + camera + '/'+ date + '/'+ camera + '-'
    
    #This currently renames the image to our google drive naming format, we may want to change this to a unix time name to better match sort_images.py    
    image_filename = camera_dir + camera + '__' + date[:4] + '-' + date[4:6] + '-' + date[6:8] + 'T'
    
    start_hour = start[0]
    start_minute = start[1]
    end_hour = end[0]
    end_minute = end[0]
    
    time_elapsed = (end_hour*60 + end_minute) - (start_hour*60 + start_minute)
    
    #Initialize counting and timing variables. These are commented out, but can be reintroduced for testing purposes.
    #count = 0
    #calc_time = 0
    #name_time = 0
    #read_time = 0
    #save_time = 0
    fail_count = 0
    #fail_time = 0
    
    #front_end_time = time.time() - start_time
    for minute in range(time_elapsed):
        #start_calc_time = time.time()
    
        current_minute = int(start_minute + minute - np.floor((start_minute + minute)/60)*60)
        current_hour = int(start_hour + np.floor((start_minute + minute)/60))
        #calc_time += time.time() - start_calc_time
        
        #start_name_time = time.time()
        filetime = str(current_hour).zfill(2) + str(current_minute).zfill(2) + '.jpg'
        image_time =  str(current_hour).zfill(2) + ';' + str(current_minute).zfill(2) + ';' + '00' + '.jpg'
        #name_time += time.time() - start_name_time
        url = image_url + filetime
        #fail_start = time.time()
        try:
            #start_read_time = time.time()
            image = io.imread(url, plugin='matplotlib')
            #read_time += time.time() - start_read_time
        
            filename = image_filename + image_time
            
            #start_save_time = time.time()
            io.imsave(filename, image)
            #save_time += time.time() - start_save_time
            #count += 1
        except:
            #fail_time += time.time() - fail_start
            fail_count += 1
    print(time.time() - start_time)
#for testing
if __name__=="__main__":
    input_camera = 'ahwahnee_1'
    input_date = '20161215'
    input_start = [4,1]
    input_end = [20,1]
    output_folder = '/home/fuego/Desktop/USGS_testing'
    usgs_puller(input_camera, input_date, input_start, input_end, output_folder)