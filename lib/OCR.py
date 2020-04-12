
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


import sys
import os
fuegoRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.image import imread
from PIL import Image
import tempfile
import math
import logging
import string
import pytesseract
import time

#generalized OCR will attempt to compare img against all characters inclusive of
#UTF-8,etc. As both camera networks restrict their outputs to ASCII this improves the
#efficiency and accuracy of the OCR script by defining expected allowed characters 
char_whitelist = string.digits
char_whitelist += string.ascii_lowercase
char_whitelist += string.ascii_uppercase
char_whitelist += string.punctuation.replace("'","").replace('"','')

 
def load_image( infilename ) :
    """loads an image file to an array
    Args:
        infilename: file path
    Returns:
        numpy array of image data
    """
    im = imread(infilename)
    return np.array(im)

def save_image( npdata, outfilename ) :
    """saves an image file from an array
    Args:
        npdata: (array) numpy array of image data
        outfilename: (str)strfile path
    Returns:
        None
    """
    outimg = Image.fromarray( npdata, "RGB" )
    outimg.save( outfilename, format='JPEG' )


def ocr_crop(image,outputname = None,maxHeight=60):
    """saves an image file from an array
    Args:
        image (str): image path
        opt outputname (str): save crop to address
        opt maxHeight (int): maximum height to search for metadata else default 60
    Returns:
        npdata (array): numpy array of cropped image data
        bottom (int): height of bottom of metadata from image bottom
        top (int):height of top of metadata from image bottom
    """

    cushionRows = 4
    minLetterBrightness = int(.8*255) # % of max value of 255
    minLetterSize = 12

    img = Image.open(image)
    assert maxHeight < img.size[1]
    try:
        imgCroppedGray = img.crop((1, img.size[1] - maxHeight, 2*minLetterSize, img.size[1])).convert('L')#possibility to apply to hprwen under simuliar parameters
        croppedArray = np.array(imgCroppedGray)

    except Exception as e:
        logging.error('Error processing image: %s', str(e))
        return

    top = 0
    bottom = 0
    mode = 'find_dark_below_bottom'
    for i in range(maxHeight):
        row = maxHeight - i - 1
        maxVal = croppedArray[row].max()
        # logging.warning('Mode = %s: Top %d, Bottom %d, Max val for row %d is %d', mode, top, bottom, row, maxVal)
        if mode == 'find_dark_below_bottom':
            if maxVal < minLetterBrightness:
                mode = 'find_bottom'
        elif mode == 'find_bottom':
            if maxVal >= minLetterBrightness:
                mode = 'find_top'
                bottom = row
        elif mode == 'find_top':
            if maxVal < minLetterBrightness:
                possibleTop = row
                if bottom - possibleTop > minLetterSize:
                    top = possibleTop
                    break

    if not top or not bottom:
        logging.error('Unable to locate metadata')
        return

    # row is last row with letters, so row +1 is first without letters, and add cushionRows
    bottom = min(img.size[1] - maxHeight + bottom + 1 + cushionRows, img.size[1])
    # row is first row without letters, so subtract cushionRows
    top = max(img.size[1] - maxHeight + top - cushionRows, img.size[1] - maxHeight)

    logging.warning('Top = %d, bottom = %d', top, bottom)
    imgOut = img.crop((0, top, img.size[0], bottom))
    img.close()
    if outputname:
        imgOut.save(outputname, format='JPEG')
    npdata = np.array(imgOut)
    return npdata, bottom, top


def cut_metadata(im, camera_type):
    """locates and cuts the metadata tag from image
    Args:
        im (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        metadatastrip (array): numpy array containing only the presumed metadata line
    """
    
    if camera_type == 'unknown':#needs update
        logging.warning('unkown has not been implemented yet')
        return 

    if camera_type == 'Axis':
        #output = im[:-4]+"_cutout"+im[-4:]
        maxHeight=60
        metadatastrip, metabottom, metatop = ocr_crop(im,maxHeight=maxHeight)


        return metadatastrip
    if camera_type == 'hpwren':#uses first order central difference gradient in 1-D to determine edges of text
        im = load_image( im )
        index = 10
        xview =10
        
        while 30>index:
            pt1up = np.sum(im[index-1,:xview,:])
            pt1down =np.sum(im[index+1,:xview,:]) 
            if np.abs(.5*pt1down-.5*pt1up)>160*xview:#(np.sum(im[index,:xview,:]) <1000) and (np.sum(im[index+1,:xview,:]) <1000):
                index=math.ceil(index*1.5)#index+=3#add a buffer for lower than average chars like g,j,q,p...
                break
            index+=1
        metadatastrip = im[:index,:,:]
        return metadatastrip
    return None
   










def ocr_core(filename=None, data=None):
    """
    This function will handle the core OCR processing of images.
    Args:
        opt filename (str) : filepath
        opt data (array): data
    Returns:
        text (str): string of OCR recognized data
    """
    if filename:
        text = pytesseract.image_to_string(load_image( filename ),config="-c tessedit_char_whitelist=%s_-." % char_whitelist)
    elif type(data) == np.ndarray:
        text = pytesseract.image_to_string(data,config="-c tessedit_char_whitelist=%s_-." % char_whitelist)
    else:
        logging.warning('Please feed in processable data to ocr_core of type filename or data')
        return
    return text



def pull_metadata(camera_type,filename = None, save_location=False):
    """ function to separate metadata from image
    Args:
        opt filename (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
        opt save_location (str): filepath to save metadata strip to
    Returns:
        vals (list): list of OCR recognized data
    """
    if not filename:
        logging.warning('specify data location of data itself')
        return
    tic=time.time()
    metadata = cut_metadata(filename,camera_type)
    logging.warning('time to complete cropping: %s',time.time()-tic)
    try:
        tic=time.time()
        vals = ocr_core(data = metadata)
        logging.warning('time to complete OCR: %s',time.time()-tic)
    except Exception as e:
        vals = ''
    if save_location:
        save_image(metadata,save_location)
        logging.warning('metadata strip saved to location, %s',save_location)
    return vals





