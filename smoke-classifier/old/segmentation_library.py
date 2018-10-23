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
from skimage import io, segmentation, img_as_ubyte, color
from skimage.measure import label, regionprops
from skimage.future import graph
from skimage.color import label2rgb, rgb2grey
from skimage.filters import threshold_yen
from skimage.morphology import dilation
import datetime
import math as math

##############################################################################################################################################################
##################################################### Multi-Purpose Functions ################################################################################
##############################################################################################################################################################
def segment_check(past_image, current_image, sliding_segments, COLOR = False, UNIVERSAL_THRESHOLD = False, uni_thresh = 0.1, LIVE_RUN = False):
    valid_segments = []
    if COLOR == False:
        motion_segments = []
        motion_segments_unformatted, throwaway_label = check_motion(past_image, current_image, UNIVERSAL_THRESHOLD = False, uni_thresh = 0.1)
        for region_index, region in enumerate(regionprops(motion_segments_unformatted)):
            if region.area >= 7500:
                min_row, min_column, max_row, max_column = region.bbox
                motion_segments += [[min_row, min_column, max_row, max_column]]
        for segment in sliding_segments:
            for motion_segment in motion_segments:
                #See if sliding segment in motion segment
                if segment[0] > motion_segment[0] and segment[0] < motion_segment[2] and segment[1] > motion_segment[1] and segment[1] < motion_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[0] > motion_segment[0] and segment[0] < motion_segment[2] and segment[3] > motion_segment[1] and segment[3] < motion_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[2] > motion_segment[0] and segment[2] < motion_segment[2] and segment[3] > motion_segment[1] and segment[3] < motion_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[2] > motion_segment[0] and segment[2] < motion_segment[2] and segment[1] > motion_segment[1] and segment[1] < motion_segment[3]:
                    valid_segments += [segment]
                    break
                #see if motion segment in sliding segment
                elif motion_segment[0] > segment[0] and motion_segment[0] < segment[2] and motion_segment[1] > segment[1] and motion_segment[1] < segment[3]:
                    valid_segments += [segment]
                    break
                elif motion_segment[0] > segment[0] and motion_segment[0] < segment[2] and motion_segment[3] > segment[1] and motion_segment[3] < segment[3]:
                    valid_segments += [segment]
                    break
                elif motion_segment[2] > segment[0] and motion_segment[2] < segment[2] and motion_segment[3] > segment[1] and motion_segment[3] < segment[3]:
                    valid_segments += [segment]
                    break
                elif motion_segment[2] > segment[0] and motion_segment[2] < segment[2] and motion_segment[1] > segment[1] and motion_segment[1] < segment[3]:
                    valid_segments += [segment]
                    break
    else:
        color_segments = color_segmentation(current_image)
        for segment in sliding_segments:
            for color_segment in color_segments:
                #See if sliding segment in motion segment
                if segment[0] > color_segment[0] and segment[0] < color_segment[2] and segment[1] > color_segment[1] and segment[1] < color_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[0] > color_segment[0] and segment[0] < color_segment[2] and segment[3] > color_segment[1] and segment[3] < color_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[2] > color_segment[0] and segment[2] < color_segment[2] and segment[3] > color_segment[1] and segment[3] < color_segment[3]:
                    valid_segments += [segment]
                    break
                elif segment[2] > color_segment[0] and segment[2] < color_segment[2] and segment[1] > color_segment[1] and segment[1] < color_segment[3]:
                    valid_segments += [segment]
                    break
                #see if motion segment in sliding segment
                elif color_segment[0] > segment[0] and color_segment[0] < segment[2] and color_segment[1] > segment[1] and color_segment[1] < segment[3]:
                    valid_segments += [segment]
                    break
                elif color_segment[0] > segment[0] and color_segment[0] < segment[2] and color_segment[3] > segment[1] and color_segment[3] < segment[3]:
                    valid_segments += [segment]
                    break
                elif color_segment[2] > segment[0] and color_segment[2] < segment[2] and color_segment[3] > segment[1] and color_segment[3] < segment[3]:
                    valid_segments += [segment]
                    break
                elif color_segment[2] > segment[0] and color_segment[2] < segment[2] and color_segment[1] > segment[1] and color_segment[1] < segment[3]:
                    valid_segments += [segment]
                    break
    if LIVE_RUN == True:
        return valid_segments, throwaway_label
    return valid_segments


def live_reader(camera_dictionary, url, out_dir, images_processed_this_run):
    url = str(url)
    try:
        old_time = camera_dictionary[url][1]
    except:
        print("#############################################################################")
        print("Key Error: URL NOT FOUND FOR PREVIOUS IMAGE")
        try:
            image_url = str(url)
            image = io.imread(image_url, plugin='matplotlib')
            ntime = datetime.datetime.now().isoformat()
            print("Successfully Read In Replacement")
            print("#############################################################################")            
            return (url, image, ntime, url)
        except:
            print("CATASTROPHIC FAILURE - WILL CRASH")
            print("#############################################################################") 
            return
    old_image = camera_dictionary[url][2]
    image_url = str(url)
    image_name = camera_dictionary[url][0]
    print("Processing image from: "+image_url)
    ntime = datetime.datetime.now().isoformat()
    ff = open(out_dir+'urls_ran.txt','a+')
    ff.write(image_url+' '+str(images_processed_this_run)+' '+str(ntime)+'\r\n')
    ff.close()
    try:
        image = io.imread(image_url, plugin='matplotlib')
        print("Successfully read in: "+url)
    except:
        print("Oops, looks like we cant get "+url+" right now. Skipping...")
        return (url, old_image, old_time, image_name)
    return image, old_image, ntime, image_name
    

##############################################################################################################################################################
##################################################### Color Segmentation Functions ###########################################################################
##############################################################################################################################################################

def _weight_mean_color(graph, src, dst, n):
    """Callback to handle merging nodes by recomputing mean color.

    The method expects that the mean color of `dst` is already computed.

    Parameters
    ----------
    graph : RAG
        The graph under consideration.
    src, dst : int
        The vertices in `graph` to be merged.
    n : int
        A neighbor of `src` or `dst` or both.

    Returns
    -------
    data : dict
        A dictionary with the `"weight"` attribute set as the absolute
        difference of the mean color between node `dst` and `n`.
    """

    diff = graph.node[dst]['mean color'] - graph.node[n]['mean color']
    diff = np.linalg.norm(diff)
    return {'weight': diff}

def merge_mean_color(graph, src, dst):
    """Callback called before merging two nodes of a mean color distance graph.

    This method computes the mean color of `dst`.

    Parameters
    ----------
    graph : RAG
        The graph under consideration.
    src, dst : int
        The vertices in `graph` to be merged.
    """
    graph.node[dst]['total color'] += graph.node[src]['total color']
    graph.node[dst]['pixel count'] += graph.node[src]['pixel count']
    graph.node[dst]['mean color'] = (graph.node[dst]['total color'] / graph.node[dst]['pixel count'])

def color_segmentation(image, GRAY_CHECK = True):
        if GRAY_CHECK == True:
            try: 
                labels = segmentation.slic(image, compactness=3, n_segments=200, spacing=[1, .1, 1]) # or (img, compactness=30, n_segments=200)
            except Exception:
                return
            try:
                g = graph.rag_mean_color(image, labels)
            except:
                return
            labels2 = graph.merge_hierarchical(labels, g, thresh=35, rag_copy=False, in_place_merge=True, merge_func=merge_mean_color, weight_func=_weight_mean_color)
            if len(regionprops(labels2)) < 15:
                labels2 = segmentation.slic(image,compactness=3, n_segments=40, spacing=[1, .1, 1])
            out = color.label2rgb(labels2, image, kind='avg')
            out = segmentation.mark_boundaries(out, labels2, (0, 0, 0))
            color_segments = []
            unfiltered_color_segments = []
            for region_index, region in enumerate(regionprops(labels2)):
                if region.area >= 7500:
                    min_row, min_column, max_row, max_column = region.bbox
                    unfiltered_color_segments += [[min_row, min_column, max_row, max_column]]
            for seg in unfiltered_color_segments:
                rgb = out[seg[0]+1][seg[1] + 1]
                grayness = np.var(rgb)
                white_or_black = math.fsum(rgb)
                if grayness < .1 and white_or_black > 0.05 and white_or_black < 2.95:
                    color_segments += [seg]
            return color_segments
            
        else:
            try: 
                labels = segmentation.slic(image, compactness=3, n_segments=200, spacing=[1, .1, 1]) # or (img, compactness=30, n_segments=200)
            except Exception:
                return
            try:
                g = graph.rag_mean_color(image, labels)
            except:
                return
                labels2 = graph.merge_hierarchical(labels, g, thresh=35, rag_copy=False, in_place_merge=True, merge_func=merge_mean_color, weight_func=_weight_mean_color)
            if len(regionprops(labels2)) < 15:
                labels2 = segmentation.slic(image,compactness=3, n_segments=40, spacing=[1, .1, 1])
            out = color.label2rgb(labels2, image, kind='avg')
            out = segmentation.mark_boundaries(out, labels2, (0, 0, 0))
            return labels2, out

##############################################################################################################################################################
##################################################### Sliding Window Segmentation Functions ##################################################################
##############################################################################################################################################################

def sliding_window(image, overlap=True, fractional_overlap = 0.5, window_size_factor = 1):
    print('Generating window size...')
    image_height, image_width = image.shape[0:2]
    print(image_height, image_width)
    if image_height < 2000:
        window_height= int(256*window_size_factor)
        window_width= int(256*window_size_factor)
    elif image_height >= 2000:
        window_height = int(384*window_size_factor)
        window_width = int(384*window_size_factor)
    if image_height <= 256 or image_width <= 256:
        return [0, 0, image_height-1, image_width-1]
    coordlist = []

    if overlap==False:
        for min_height in np.arange(0, image_height, window_height):
            for min_width in np.arange(0, image_width, window_width):
                max_height = min_height + window_height
                if max_height >= image_height:
                    max_height = image_height-1
                max_width = min_width + window_width
                if max_width >= image_width:
                    max_width = image_width-1
                coordlist += [[min_height, min_width, max_height, max_width]]

    elif overlap == True:
        pixel_step_height = int(np.ceil(window_height - fractional_overlap*window_height))
        pixel_step_width = int(np.ceil(window_width - fractional_overlap*window_width))
        height_dist = int(image_height - window_height)
        
        if np.mod(height_dist, pixel_step_height) != 0:
            for i in range(1, window_height):
                if np.mod(height_dist, pixel_step_height - i) == 0:
                    pixel_step_height =  pixel_step_height - i
                    break
                elif np.mod(height_dist, pixel_step_height + i) == 0:
                    pixel_step_height =  pixel_step_height + i
                    break
        width_dist = int(image_width - window_width)
        
        if np.mod(width_dist, pixel_step_width) != 0:
            for i in range(1, window_width):
                if np.mod(width_dist, pixel_step_width - i) == 0:
                    pixel_step_width =  pixel_step_width - i
                    break
                elif np.mod(width_dist, pixel_step_width + i) == 0:
                    pixel_step_width =  pixel_step_width + i
                    break
                    
        for height in np.arange(0, height_dist + pixel_step_height, pixel_step_height):
            for width in np.arange(0, width_dist + pixel_step_width, pixel_step_width):
                coordlist += [[height, width, height + window_height, width + window_width]]
    print('Generated '+str(len(coordlist))+' windows.')
    return coordlist

##############################################################################################################################################################
##################################################### Motion Detection Segmentation Functions ##################################################################
##############################################################################################################################################################

def reduce_res(channel, dtype = int):  #np.float64 for greyscale
    height = channel.shape[0]
    width = channel.shape[1]
    if np.mod(height,2) > 0 or np.mod(width,2) > 0:
        print("ODD!")
    h = 16
    if height < 1080:
        h = 12
    while np.mod(height,h) > 0 or np.mod(width,h) > 0:
        h -= 4
        if h == 0:
            h = 2
            break
    w = h
    c = np.arange(0,channel.shape[0], h)
    d = np.arange(0,channel.shape[1], w)
    hs = np.full_like(c, h)
    ws = np.full_like(d, w)
    list_avgs = [np.mean(channel[i:i+w,j:j+h]) for i in c for j in d]
    array_avgs =  np.array(list_avgs, dtype=dtype).reshape(len(c),len(d))
    A = array_avgs.repeat(hs, axis=0)
    A = A.repeat(ws, axis=1)
    return A

def check_motion(previous_image, current_image, UNIVERSAL_THRESHOLD = False, uni_thresh = .1):

    previous_grey = rgb2grey(previous_image)
    current_grey = rgb2grey(current_image)

    diff = reduce_res(current_grey, dtype=np.float64)-reduce_res(previous_grey, dtype=np.float64)
    abdiff = abs(diff)
    nabdiff = abdiff**.5
    
    if UNIVERSAL_THRESHOLD == True:
        thresh = uni_thresh
    else:
        thresh = threshold_yen(nabdiff)
    
    binary = nabdiff > thresh
    selem = np.ones([32,32],dtype=np.uint8)
    smallselem = np.ones([4,4], dtype=np.uint8)

    dilated = dilation(binary, selem)
    ddilated = dilation(dilated, smallselem)

    segments = label(ddilated, connectivity=2)
    try:
        image_label_overlay = img_as_ubyte(label2rgb(segments, image=current_grey, colors=['red'], bg_label=0,bg_color=(0,0,0)))
    except:
        print("Label Shape", np.shape(segments))
        print("Image Shape", np.shape(current_grey))

    return segments, image_label_overlay