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

import sys
sys.path.insert(0, '/home/fuego/firecam/')
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import rect_to_squares
import tf_helper
import numpy as np
import os
import pathlib
import tensorflow as tf
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

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
    
def deleteImageFiles(segments):
    for segmentInfo in segments:
        os.remove(segmentInfo['imgPath'])

def main():
    test_data = []
    
    image_name = []
    crop_name = []
    score_name = []
    class_name = []
    
    image_name += ["Image"]
    crop_name += ["Crop"]
    score_name += ["Score"]
    class_name += ["Class"]
    
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # quiet down tensorflow logging
    graph = tf_helper.load_graph('/home/fuego/Desktop/output_graph_Oct23.pb')#settings.model_file)
    labels = tf_helper.load_labels(settings.labels_file)
    
    smoke_directory = os.walk('/home/fuego/Desktop/test_set_smoke')
    smoke_files = []
    smoke_image_list = []
    
    for lists in smoke_directory:
        smoke_files += [lists]
    for x in smoke_files[0][2]:
        if x[-4:] == '.jpg':
            smoke_image_list += ['/home/fuego/Desktop/test_set_smoke/' + x]
     
    other_directory = os.walk('/home/fuego/Desktop/test_set_other')
    other_files = []
    other_image_list = []
    
    for other_lists in other_directory:
        other_files += [other_lists]
    for other_x in other_files[0][2]:
        if other_x[-4:] == '.jpg':
            other_image_list += ['/home/fuego/Desktop/test_set_other/' + other_x]
            
    np.savetxt('/home/fuego/Desktop/test_smoke.txt', smoke_image_list, fmt = "%s")
    np.savetxt('/home/fuego/Desktop/test_other.txt', other_image_list, fmt = "%s")
    
    with tf.Session(graph=graph) as tfSession:
        for smoke_image in smoke_image_list:
            segments = segmentImage(smoke_image)
            tf_helper.classifySegments(tfSession, graph, labels, segments)
            for i in range(len(segments)):
                image_name += [smoke_image[35:]]
                crop_name += [segments[i]['imgPath'][35:]]
                score_name += [segments[i]['score']]
                class_name += ['smoke']
            deleteImageFiles(segments)
                
        for other_image in other_image_list:
            segments = segmentImage(other_image)
            tf_helper.classifySegments(tfSession, graph, labels, segments)
            for i in range(len(segments)):
                image_name += [other_image[35:]]
                crop_name += [segments[i]['imgPath'][35:]]
                score_name += [segments[i]['score']]
                class_name += ['other']            
            deleteImageFiles(segments)

    test_data = [image_name, crop_name, score_name, class_name]
    np.savetxt('/home/fuego/Desktop/test_scores_Oct23.txt', np.transpose(test_data), fmt = "%s")             
    print("DONE")
if __name__=="__main__":
    main()
