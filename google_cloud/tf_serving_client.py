"""
tmp scratch file for messing around and debugging
"""

import rect_to_squares
from PIL import Image
import pathlib
import numpy as np
import os

from gcp_helper import connect_to_prediction_service, predict_batch

def segmentImage(imgPath):
    """Segment the given image into sections to for smoke classificaiton

    Args:
        imgPath (str): filepath of the image

    Returns:
        List of dictionary containing information on each segment
    """
    img = Image.open(imgPath)
    ppath = pathlib.PurePath(imgPath)
    segments = rect_to_squares.cutBoxes(img, str(ppath.parent), imgPath)
    img.close()
    return segments


def load_crops(crop_root):
    crops = []
    for file in os.listdir(crop_root):
        if 'Crop' in file:
            array = np.asarray(Image.open(crop_root + file))
            crops.append(array)
    return np.stack(crops)




# server_ip_and_port = '34.82.71.243:8500'
server_ip_and_port = 'localhost:8500'


#crop image into sqaures
# test_path = '/Users/henrypinkard/Desktop/fuego_smoke_img/test_smoke_2.jpg'
# segments = segmentImage(test_path)

#load all crops
# crop_root = '/Users/henrypinkard/Desktop/fuego_test_img/'
# crop_root = '/home/henry/fuego_smoke_img/'
crop_root = '/Users/henrypinkard/Desktop/fuego_smoke_img/'

crops = load_crops(crop_root)

prediction_service = connect_to_prediction_service(server_ip_and_port)

result = predict_batch(prediction_service, crops, timing=True)

#do again now that memory allocated
result = predict_batch(prediction_service, crops, timing=True)
result = predict_batch(prediction_service, crops, timing=True)



pass


