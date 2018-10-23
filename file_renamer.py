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
Created on Thu Sep  6 08:17:57 2018

@author: John Solts

Use this file to instantly rename files downloaded from the HPWREN archives. Put it in the directory where the images are located.

Sequential files from the archive are given names that are in seconds. Two files that are of images a minute apart have number sequences 60 apart. I use this to quickly rename all the files to the standard camera_name + date + time format.
"""
from os import rename



def sequential_file_rename(initial_file, date, initial_hour, initial_min, seconds, Camera_Name, m_step):
    t = 0
    minutes = initial_min
    hours = initial_hour
    while True:
        file = str(initial_file + t) + '.jpg'
        
        if minutes >= 60:
            minutes -= 60
            hours = hours + 1
            
        new_file_name = Camera_Name + date + str(hours).zfill(2) + ':' + str(minutes).zfill(2) + ':' + str(seconds).zfill(2) + '.jpg'
        try:
            #print(file)
            #print(new_file_name)
            rename(file, new_file_name)
        except:
            print(file, "Does Not Exist!")
            print(new_file_name, "Failed")
            return
        t+= (60*m_step)
        minutes += m_step
        
if __name__=="__main__":
    camera_name = input("What is the camera's code name? (Enter must be in quotes)") #Please use the camera's code name.
    initial_filename = int(input("What is the number sequence of the first file? "))
    m_step = int(input("How many minutes elapse between images (Standard is 1)"))
    file_year = str(input("What year was the picture taken? "))
    file_month = str(input("What month was the picture taken? ")).zfill(2)
    file_day = str(input("What day was the picture taken? ")).zfill(2)
    file_hour = input("What hour was the picture taken? ")
    file_minute = input("Minute? ")
    file_second = input("Second? ")
    initial_date = file_year + '-' + file_month + '-' + file_day + 'T'
    print("Date ", initial_date)
    print("Camera Name (Enter in Code) ",camera_name)
    correct = input("If the above is correct enter 1 ")
    if correct == 1:
        sequential_file_rename(initial_filename, initial_date, int(file_hour), int(file_minute), int(file_second), camera_name, m_step)
