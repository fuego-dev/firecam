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
Created on Tue Aug 14 12:22:23 2018

@author: fuego
"""

import db_manager
#import fire_detector
import warning_manager
import image_handler
import math as math
from skimage import io
import numpy as np
import tensorflow as tf
from segmentation_library import sliding_window, segment_check, live_reader
from categorizer import categorizer

from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

import os, sys

import settings

sys.path.insert(0, settings.caffe_root + 'python')
#import caffe

import datetime

import multiprocessing
from multiprocessing import Pool
import threading
import time

os.environ['TF_CPP_MIN_LOG_LEVEL']='2' #stops a ton of warning messages from showing up
sys.path.insert(0, '/home/fuego/tensorflow/tensorflow/examples/image_retraining')

#the emails we want to send alerts to
#emails = ['wcschultz@berkeley.edu', 'crpennypacker@lbl.gov','a.denonfoux@hotmail.fr', 'nathanielheidt@gmail.com', 'jim.niswander@gmail.com']
#emails = settings.emails
emails = ['johnsol@lbl.gov','tim@fireballit.com']#['lufifer@lbl.gov','johnsol@lbl.gov', 'tim@fireballit.com']

"""
Some setup below
"""          
images_processed_this_run=0#Tally of images processed before error. Debugging only.

#if settings.use_GPU == True:
    #caffe.set_mode_gpu()
#create the managers for the db and detector
manager = db_manager.DbManager()
urllist = manager.get_sources()

#tf  GPU config
config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.1

camdat = {}
for line in urllist:
    urlstr = str(line['url'])
    namestr = str(line['name'])
    t_of_dload = time.time()
    try:
        img = io.imread(urlstr)
    except:
        print('No dice for '+urlstr+', skipping...')
        continue
    camdat[urlstr] = [namestr, t_of_dload, img]

#if settings.which_model == 'caffeAlexNet':
#    print("using caffe")
#    detector = fire_detector.FireDetector()
#elif settings.which_model == 'kerasCNN':
#    print("using keras")
#    detector = fire_detector.KerasDetector()

m = multiprocessing.Manager()     #this imagequeue is used to pass images between the image detection thread and the url crawler
imagequeue = m.Queue(16)          #number of images in queue at once

p = threading.Thread(target = image_handler.start_image_process, #we create a thread not a process b/c python no likey
                            args = (urllist, imagequeue,))
p.daemon = True                   #daemonize so the thread and its children die when we kill the main process
p.start()

def grab_some_urls(number_of_urls):
    outlist = []
    for n in range(number_of_urls):
        try: 
            item = imagequeue.get()
        except:
            continue
        url = str(item['url']) # remember you can also get the image via item['image'], but using that effectively is a little too complicated for now...
        outlist.append(url)
    return outlist
        

print("\n\nBeginning to parse photos.\n\n")
date_dir = str(datetime.datetime.now().date()) + '/'
out_dir = 'MOTIONdetections'+date_dir
# create a directory in which to store cropped images
if not os.path.exists(out_dir):
    os.makedirs(out_dir)
# define amount of padding to add to cropped image
pad = 0
boxcolor_r = np.array([255, 0, 0], dtype=np.uint8)
boxcolor_y = np.array([255,255,0], dtype=np.uint8)
# Loads label file, strips off carriage return
label_lines = [line.rstrip() for line
                    in tf.gfile.GFile("retrained_labels_2018_08_21.txt")]
for i in range(len(label_lines)):
    if label_lines[i] == 'smoke':
        smoke_index = i
        print(label_lines[i])
        print(i)
graph_def = tf.GraphDef()#Pulled this from inside while loop
        
def parallel_run(url):
    image_url  =str(url)
    image, old_image, ntime, image_name = live_reader(camdat, url, out_dir, images_processed_this_run)
    if isinstance(image,basestring):
        return (image_url, image_name, ntime, old_image)
    initial_segment_bounds = sliding_window(image)
    
    camera_name = []
    image_time = []
    segment_number = []
    minimum_row = []
    minimum_column = []
    maximum_row = []
    maximum_column = []
    smoke_scores = []
    camera_name += ['Camera_Name']
    image_time += ['Date_and_Time']
    segment_number += ['Segment_Number']
    minimum_row += ['Top_Edge']
    minimum_column += ['Left_Edge']
    maximum_row += ['Bottom_Edge']
    maximum_column += ['Right_Edge']
    smoke_scores += ['Smoke_Score']
    
    camera_dir = out_dir + image_name + '/'
    time_dir = str('_'.join(ntime.split('.'))) + '/'
    segments_dir = 'Segments/'
    if not os.path.exists(camera_dir):
        os.makedirs(camera_dir)
    os.makedirs(camera_dir+time_dir)
    os.makedirs(camera_dir+time_dir + segments_dir)
    if len(initial_segment_bounds) == 4 and initial_segment_bounds[1] == 0:
        print("uh oh")
        segment_bounds = initial_segment_bounds
        scores = categorizer("retrained_graph_2018_08_21_newcat.pb", image, segment_bounds, url, config, MOTION_OR_COLOR = False, ONE_SEG = True)
        if scores[smoke_index] > 0:
            filename = str(image_name)
            img_filename = camera_dir + time_dir + filename +'.jpg'
            rag_filename = camera_dir + time_dir + filename + '_difference.jpg'
            io.imsave(img_filename, image)
            cc = str(0)
            seg_file_loc2 = '/home/fuego/Desktop/live_segs/' + filename + '_segment' + cc + '.jpg'
            io.imsave(filename, image)
            io.imsave(seg_file_loc2, image)
            camera_name += [image_name]
            image_time += [str(ntime)]
            segment_number += [cc]
            minimum_row += [str(0)]
            minimum_column += [str(0)]
            maximum_row += [str(segment_bounds[3])]
            maximum_column += [str(segment_bounds[4])]
            smoke_scores += [str(scores[smoke_index])]
            
        if scores[smoke_index] >= .5:
            try:
                warning_manager.send_email(emails, scores[smoke_index], image_name, img_filename, rag_filename, img_filename)
                print("Email Sent")
            except:
                print("Overflow")
    else:
        segment_bounds, segment_labels = segment_check(old_image, image, initial_segment_bounds, COLOR = False, UNIVERSAL_THRESHOLD = False, uni_thresh = 0.1, LIVE_RUN = True)
        scores = categorizer("retrained_graph_2018_08_21_newcat.pb", image, segment_bounds, url, config, MOTION_OR_COLOR = False)
        for seg_num in range(len(scores)):
            smokefound = scores[seg_num][smoke_index]
            if smokefound > 0:
                #print("FOUND POTENTIAL FIRE at {name} with probability of {prob} at {time}".format(name=image_name, prob=smokefound, time=ntime))
                #for i in range(len(label_lines)):
                #    print(label_lines[i], scores[seg_num][i])
                min_row = segment_bounds[seg_num][0]
                max_row = segment_bounds[seg_num][2]
                min_col = segment_bounds[seg_num][1]
                max_col = segment_bounds[seg_num][3]
                if max_col >= len(image[0]):
                    max_col = len(image[0])-1
                if max_row >= len(image):
                    max_row = len(image)-1
                cropped_image = image[min_row:max_row, min_col:max_col]
                img_w_box = np.array(image)[:,:,0:3]
                img_w_box[min_row, min_col:max_col] = boxcolor_r
                img_w_box[max_row, min_col:max_col] = boxcolor_r
                img_w_box[min_row:max_row, min_col] = boxcolor_r
                img_w_box[min_row:max_row, max_col] = boxcolor_r

                filename = str(image_name)
                img_filename = camera_dir + time_dir + filename +'.jpg'
                rag_filename = camera_dir + time_dir + filename + '_difference.jpg'
                io.imsave(img_filename, image)
                io.imsave(rag_filename, segment_labels)

                cc = str(seg_num)
                seg_filename = camera_dir + time_dir + segments_dir + filename + '_segment' + cc + '.jpg'
                seg_file_loc2 = '/home/fuego/Desktop/live_segs/' + filename + '_segment' + cc + '.jpg'
                box_filename = camera_dir + time_dir + segments_dir + filename + '_displaying_seg' + cc + '.jpg'
                io.imsave(seg_filename, cropped_image)
                io.imsave(seg_file_loc2, cropped_image)
                io.imsave(box_filename, img_w_box)
                camera_name += [image_name]
                image_time += [str(ntime)]
                segment_number += [cc]
                minimum_row += [str(min_row)]
                minimum_column += [str(min_col)]
                maximum_row += [str(max_row)]
                maximum_column += [str(max_col)]
                smoke_scores += [str(smokefound)]
                #fff = open(camera_dir+ time_dir + 'detection_scores.txt','a+')
                #fff.write(image_url+' '+str(ntime)+' segment'+ cc +' '+ min_row + min_col + max_row+max_col + str(smokefound)+'\r\n')
                #fff.close()
                #Wait For Google to Reopen Account
            if smokefound >= .5:
                try:
                    warning_manager.send_email(emails, smokefound, image_name, img_filename, rag_filename, box_filename)
                    print("Email Sent")
                except:
                    print("Overflow")
                    #    print("Email Warning System Failed")
                    #    print("Emails ", emails)
                    #    print("Smokefound ", smokefound)
                    #    print("Image Name ", image_name)
                    #    print("File Name ", img_filename)
                    #    print("Difference File Name ", rag_filename)
                    #    print("Box File Name ", box_filename)
                    #    break
            file_input = np.transpose(np.array([camera_name, image_time, segment_number, minimum_row, minimum_column, maximum_row, maximum_column, smoke_scores]))
            np.savetxt(camera_dir + time_dir + filename + '_detection_scores.txt', file_input, fmt='%s')
    return (url, image_name, ntime, image)
    
    
if __name__=="__main__":
    t = time.time()
    while True:
        list_of_urls = grab_some_urls(1)
        #pool = Pool()
        list_outputs = parallel_run(list_of_urls[0])#pool.map(parallel_run, list_of_urls)
        images_processed_this_run+=1#len(list_outputs)  
        #pool.close()
        #pool.join()
        #for line in list_outputs:
        #    if line is None:
        #        continue
        o_url, o_image_name, o_time, o_image = list_outputs#line
        camdat[o_url] = [o_image_name, o_time, o_image]
        print("Images Processed: " + str(images_processed_this_run))
        elapsed = time.time() - t
        print(elapsed)
        if images_processed_this_run > 0:
            print(elapsed/images_processed_this_run)