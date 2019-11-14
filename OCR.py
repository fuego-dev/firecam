import numpy as np
import matplotlib.pyplot as plt
from matplotlib.image import imread
from PIL import Image
import tempfile
import math
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

#im[:,100,0] = 0`
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
    print(time.time()-tic)











import pytesseract
import time
def ocr_core(filename):
    """
    This function will handle the core OCR processing of images.
    Args:
        filename (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        list of OCR recognized data
    """
    text = pytesseract.image_to_string(load_image( filename ))
    return text.split(' ')



def pull_metadata(filename):
    """test function to assess the capability of the OCR
    Args:
        filename (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        vals (list): list of OCR recognized data
    """
    tempfilepath = tempfile.TemporaryFile(suffix=".jpg")
    img = load_image( filename )
    metadata = cut_metadata(img,"Axis")#for now its hardcoded
    save_image(metadata,"test4.jpg")#tempfilepath.name
    tic=time.time()
    vals = ocr_core('./test4.jpg')#tempfilepath.name
    print(time.time()-tic)
    return vals


"""
name = vals[0]
date = [elem for elem in vals if elem.count("/") == 2][0]
time = [elem for elem in vals if elem.count(":") == 2][0]
P = 1
T = 1
Z = 1"""

"""
#script to run over all of the alert archive
#open the postgress/cloud platform
#read all uploaded images
#download image? 
#perform OCR
#update name in GCP and POSTGRES
"""


