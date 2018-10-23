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
import numpy as np
import tensorflow as tf
from skimage.measure import regionprops

def categorizer(tensorflow_graph, image, segments, url, config, MOTION_OR_COLOR = False, ONE_SEG = False):
    segment_detection_values = []
    graph_def = tf.GraphDef()
    if ONE_SEG == False:
        cropped_images = []
        if MOTION_OR_COLOR == False:
            mins_and_maxes = segments
            for w_index, coord_pack in enumerate(mins_and_maxes):
                # draw a rectangle around the segmented articles
                # bbox describes: min_row, min_col, max_row, max_col
                min_row, min_column, max_row, max_column = coord_pack
                if max_column >= len(image[0]):
                    max_column = len(image[0])-1
                if max_row >= len(image):
                    max_row = len(image)-1
                    # use those bounding box coordinates to crop the image
                cropped_images.append(image[min_row:max_row, min_column:max_column])
        else:
            mins_and_maxes = []
            for region_index, region in enumerate(regionprops(segments)):
                if region.area >= 7500:
                    # draw a rectangle around the segmented articles
                    # bbox describes: min_row, min_col, max_row, max_col
                    min_row, min_column, max_row, max_column = region.bbox
                    if max_column >= len(image[0]):
                        max_column = len(image[0])-1
                    if max_row >= len(image):
                        max_row = len(image)-1
                    mins_and_maxes.append(region.bbox)
                    # use those bounding box coordinates to crop the image
                    cropped_images.append(image[min_row:max_row, min_column:max_column])
    with tf.gfile.FastGFile(tensorflow_graph, 'rb') as f:
        graph_def.ParseFromString(f.read())
        tf.import_graph_def(graph_def, name='')
    if ONE_SEG == False:        
        for cindex, cropped_image in enumerate(cropped_images):
            image_data = np.array(cropped_image)[:,:,0:3]
            # Unpersists graph from file
            with tf.Session(config=config) as sess:  #config=tf.ConfigProto(log_device_placement=True)
            # Feed the image_data as input to the graph and get first prediction
                softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
                try:
                    predictions = sess.run(softmax_tensor, {'DecodeJpeg:0': image_data})
                except:
                    print("image fault ahhh from url: {url}".format(url=url)) #Caused by image not decoding properly, even though it was a .jpg. Crashed the entire session.
                    print(image_data.shape)
                    continue
            # Sort to show labels of first prediction in order of confidence
            segment_detection_values += [predictions[0]]
    else:
        image_data = image
        with tf.Session(config=config) as sess:  #config=tf.ConfigProto(log_device_placement=True)
        #Feed the image_data as input to the graph and get first prediction
            softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
            try:
                predictions = sess.run(softmax_tensor, {'DecodeJpeg:0': image_data})
            except:
                print("image fault ahhh from url: {url}".format(url=url)) #Caused by image not decoding properly, even though it was a .jpg. Crashed the entire session.
                print(image_data.shape)
            # Sort to show labels of first prediction in order of confidence
        segment_detection_values = predictions[0]
    tf.reset_default_graph()
    return segment_detection_values