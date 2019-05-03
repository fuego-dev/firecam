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
Created on Wed Oct 17 14:33:16 2018

@author: fuego
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
"""
@author: John Soltis

This code scores the already cropped images in our data set and saves those scores to a google sheet

"""

import os
import sys
import settings
settings.fuegoRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(settings.fuegoRoot, 'lib'))
import collect_args
import rect_to_squares
import goog_helper
import tf_helper
import db_manager

import numpy as np
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
import csv

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.1

def segmentImage(imgPath):
    img = Image.open(imgPath)
    ppath = pathlib.PurePath(imgPath)    
    return rect_to_squares.cutBoxes(img, str(ppath.parent), imgPath)
    
    
def smoke_check(tfSession, graph, labels, imgPath):
    input_height = 299
    input_width = 299
    input_mean = 0
    input_std = 255
    input_layer = "Placeholder"
    output_layer = "final_result"
    input_name = "import/" + input_layer
    output_name = "import/" + output_layer
    input_operation = graph.get_operation_by_name(input_name)
    output_operation = graph.get_operation_by_name(output_name)
    
    t = tf_helper.read_tensor_from_image_file(imgPath, input_height=input_height, input_width=input_width, input_mean=input_mean, input_std=input_std)
    
    results = tfSession.run(output_operation.outputs[0], {input_operation.outputs[0]: t})
    return results[0][1]
    
def deleteImageFiles(imgPath, segments):
    for segmentInfo in segments:
        os.remove(segmentInfo['imgPath'])

def main():
    #header = np.array(['Filename','Score','Class'])
    #with open('/home/fuego/Desktop/training_set_scores.csv', 'w', newline = '') as f:
    #    writer = csv.writer(f)
    #    writer.writerow(header)
        
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # quiet down tensorflow logging
    graph = tf_helper.load_graph(settings.model_file)
    labels = tf_helper.load_labels(settings.labels_file)
    
    smoke_directory = os.walk('/home/fuego/Desktop/training_set_smoke')
    smoke_files = []
    smoke_image_list = []
    
    for lists in smoke_directory:
        smoke_files += [lists]
    for x in smoke_files[0][2]:
        if x[-4:] == '.jpg':
            smoke_image_list += ['/home/fuego/Desktop/training_set_smoke/' + x]
     
    other_directory = os.walk('/home/fuego/Desktop/training_set_other')
    other_files = []
    other_image_list = []
    
    for other_lists in other_directory:
        other_files += [other_lists]
    for other_x in other_files[0][2]:
        if other_x[-4:] == '.jpg':
            other_image_list += ['/home/fuego/Desktop/training_set_other/' + other_x]

    with open('/home/fuego/Desktop/training_set_scores.csv', 'a', newline = '') as fd:
        writer = csv.writer(fd)
        with tf.Session(graph=graph) as tfSession:
            for smoke_image in smoke_image_list:
                smoke_score = smoke_check(tfSession, graph, labels, smoke_image)
                writer.writerow([smoke_image[39:], smoke_score, 'smoke'])
                
            for other_image in other_image_list:
                segments = segmentImage(other_image)
                tf_helper.classifySegments(tfSession, graph, labels, segments)
                for i in range(len(segments)):
                    writer.writerow([segments[i]['imgPath'][39:],segments[i]['score'],'other'])
                deleteImageFiles(other_image, segments)
                    
    print("DONE")
if __name__=="__main__":
    main()
