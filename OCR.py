import numpy as np
import matplotlib.pyplot as plt
from matplotlib.image import imread
from PIL import Image
import tempfile
import math
import logging
import string
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
    outimg.save( outfilename )


def cut_metadata(im, camera_type):
    """locates and cuts the metadata tag from image
    Args:
        im (array) : numpy array of image data
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        metadatastrip (array): numpy array containing only the presumed metadata line
    """
    #uses first order central difference gradient in 1-D to determine edges of text
    if camera_type == 'unknown':
        index = im.shape[1]//2
        if np.sum(im[im.shape[0]-1,im.shape[1]//2,:]) < 80:#check if metadata bar is present on bottom
            camera_type = 'Axis'
        else:
            camera_type = 'hpwren'

    if camera_type == 'Axis':
        index = im.shape[0]-2
        

        while index>0:
            pt1down = np.sum(im[index+1,0,:])
            pt1up = np.sum(im[index-1,0,:])
            if np.abs(.5*pt1down-.5*pt1up)>50:#(np.sum(im[index,0,:]) > 80) and (np.sum(im[index-1,0,:]) > 80):
                #index+=1
                break
            index-=1
            
        metadatastrip = im[index:,:,:]
        return metadatastrip
    if camera_type == 'hpwren':
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
  
def test_iden(filename,cam_type):
    """test function to assess the capability of the metadata location and cropping
    Args:
        filename (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        None
    """
    img = load_image( filename )
    metadata = cut_metadata(img,cam_type)
    save_image(metadata,"test4.jpg")
    tic=time.time()
    logging.warning('time taken to cut metadata %s',time.time()-tic)











import pytesseract
import time
def ocr_core(filename=None, data=None):
    """
    This function will handle the core OCR processing of images.
    Args:
        opt filename (str) : filepath
        opt data (array): data
    Returns:
        list of OCR recognized data
    """
    if filename:
        text = pytesseract.image_to_string(load_image( filename ),config="-c tessedit_char_whitelist=%s_-." % char_whitelist)
    if type(data) == np.ndarray:
        text = pytesseract.image_to_string(data,config="-c tessedit_char_whitelist=%s_-." % char_whitelist)
    else:
        logging.warning('Please feed in processable data to ocr_core of type filename or data')
        return
    return text.split(' ')



def pull_metadata(camera_type,filename = None, data = None, save_location=False):
    """test function to assess the capability of the OCR
    Args:
        opt filename (str) : filepath
        opt data (array): data
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
        opt save_location (str): filepath to save metadata strip to
    Returns:
        vals (list): list of OCR recognized data
    """
    if filename:
        img = load_image( filename )
    elif type(data) == np.ndarray:
        img = data
    else:
        logging.warning('specify data location or data itself')
    metadata = cut_metadata(img,camera_type)
    tic=time.time()#####################
    vals = ocr_core(data = metadata)
    logging.warning('time to complete OCR: %s',time.time()-tic)##################
    if save_location:
        save_image(metadata,save_location)
        logging.warning('metadata strip saved to location, %s',save_location)
    return vals


#script to run over all of the alert archive
#open the postgress/cloud platform
#read all uploaded images
#download image? 
#perform OCR
#update name in GCP and POSTGRES



