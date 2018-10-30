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
Automated Scoring of old detections for analysis purposes
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import pathlib
import subprocess
import re
import numpy as np
import tensorflow as tf
import math
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import rect_to_squares
import tf_helper


# alternate version that uses in-memory image segments without persisting to disk
from skimage import io
import numpy as np

def read_tensor_from_array(data,
                            input_height=299,
                            input_width=299,
                            input_mean=0,
                            input_std=255):
  float_caster = data
  dims_expander = tf.expand_dims(float_caster, 0)
  resized = tf.image.resize_bilinear(dims_expander, [input_height, input_width])
  normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
  sess = tf.Session()
  result = sess.run(normalized)

  return result

# use multiple colors to make it slightly easier to see the overlapping boxes
colors = [(255, 0, 0), (0, 0, 255)]
white = (255, 255, 255, 0)
def imageWithScores(imageName, imgPath, segments, output):
    image = Image.open(imgPath).convert('RGBA')

    boxes_and_scores = Image.new('RGBA', image.size, white)
    draw = ImageDraw.Draw(boxes_and_scores)
    for counter, segmentInfo in enumerate(segments):
        offset = ((counter%2) - 0.5)*2
        x0 = segmentInfo['MinX'] + offset
        y0 = segmentInfo['MinY'] + offset
        x1 = segmentInfo['MaxX'] + offset
        y1 = segmentInfo['MaxY'] + offset
        centerX = (x0 + x1)/2
        centerY = (y0 + y1)/2
        color = colors[counter % len(colors)]
        scoreStr = '%.2f' % segmentInfo['score']
        draw.text((centerX,centerY), scoreStr, fill = color)
        draw.rectangle([x0, y0, x1, y1], outline = color)
    scoredImage = Image.alpha_composite(image, boxes_and_scores)
    scoredImage.save(output + 'Scored_' + imageName[:-4] + '.png')
    boxes_and_scores.close()
    image.close()
    
def deleteImageFiles(segments):
    for segmentInfo in segments:
        os.remove(segmentInfo['imgPath'])

def check_image(imageName, output, in_dir, seg_dump):
    
    
    """
    reqArgs = [
        ["i", "image", "filename of the image"],
        ["o", "output", "output directory name"],
        ["l", "labels", "labels file generated during retraining"],
        ["m", "model", "model file generated during retraining"],
    ]
    optArgs = [
        ["d", "display", "(optional) specify any value to display image and boxes"]
    ]
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs)
    """
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    graph = tf_helper.load_graph(settings.model_file)
    labels = tf_helper.load_labels(settings.labels_file)
    segments = []
    imgPath = in_dir + '/' + imageName
    with tf.Session(graph=graph) as tfSession:
        # chops image in segment files and classifies each segment
        imgOrig = Image.open(imgPath)
        segments = rect_to_squares.cutBoxes(imgOrig, seg_dump, imgPath)
        imgOrig.close()
        tf_helper.classifySegments(tfSession, graph, labels, segments)        
        imageWithScores(imageName, imgPath, segments, output)
    deleteImageFiles(segments)
            
def main():
    out_dir = settings.fuegoRoot + 'images_scored/'
    in_dir = settings.fuegoRoot + 'detections'
    detection_directory = os.walk(in_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    seg_dump = settings.fuegoRoot + 'segment_dump/'
    if not os.path.exists(seg_dump):
        os.makedirs(seg_dump)
        
    detection_files = []
    detection_image_list = []
    
    for lists in detection_directory:
        detection_files += [lists]
    for x in detection_files[0][2]:
        if x[-4:] == '.jpg':
            detection_image_list += [x]

    for image in detection_image_list[471:]:
        print(image)
        check_image(image, out_dir, in_dir, seg_dump)

# for testing
if __name__=="__main__":
    main()
 