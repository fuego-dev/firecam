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
import logging
import OCR

assert os.path.isfile('./test_OCR1.jpg')
assert os.path.isfile('./test_OCR2.jpg')

path = tempfile.TemporaryDirectory()
temporaryDir.name
	assert os.path.isfile(imgPath)
	shutil.rmtree(temporaryDir.name)

def test_load_image():
    #load_image( infilename )
    testdata = OCR.load_image('test_OCR1.jpg')
    assert type(metadatastrip) == type(np.array([]))

def test_save_image():
    #save_image( npdata, outfilename )
    testdata = OCR.load_image('test_OCR1.jpg')
    OCR.save_image( testdata, path+'test.jpg' )
    assert os.path.isfile(path+'/test.jpg')
    os.remove(path+'/test.jpg')
    assert not os.path.isfile(path+'/test.jpg')

def test_ocr_crop():
    #ocr_crop(image,outputname = None,maxHeight=60)
    metadatastrip, metabottom, metatop = OCR.ocr_crop('test_OCR1.jpg', outputname = path+'test.jpg',maxHeight=60)
    assert type(metadatastrip)==type(np.array([]))
    assert type(metabottom)==type(1)
    assert type(metatop)==type(1)
    assert metatop-metabottom<20
    assert os.path.isfile(path+'/test.jpg')   

def test_cut_metadata():
    #cut_metadata(im, camera_type)
    metadata = OCR.cut_metadata('test_OCR1.jpg', 'Axis')
    assert metadata.shape[0]<20
    metadata = OCR.cut_metadata('test_OCR2.jpg', 'hpwren')
    assert metadata.shape[0]<20

def test_iden(filename,cam_type):
    """test function to assess the capability of the metadata location and cropping
    Args:
        filename (str) : filepath
        camera_type (str): {'hpwren','Axis','unknown'} defined type of image to remove metadata from.
    Returns:
        saved_file_name (str): name of cropped image
        toc (flt): time taken to perform metadatacrop
    """
    tic=time.time()
    metadata = OCR.cut_metadata(filename,cam_type)
    toc = time.time()-tic
    saved_file_name = filename[:-4]+"_cutout"+filename[-4:]
    OCR.save_image(metadata,saved_file_name)
    
    
    logging.warning('time taken to cut metadata %s',toc)
    return saved_file_name, toc

def test_ocr_core():
    #ocr_core(filename=None, data=None)
    testdata = OCR.load_image(path+'test.jpg')
    testfile = path+'/test.jpg'
    OCR.save_image( testdata, testfile)
    text = OCR.ocr_core( data=testdata )
    assert type(text )==type('')
    text = OCR.ocr_core(filename=testfile)
    assert type(text )==type('')
    os.remove(path+'/test.jpg')
    assert not os.path.isfile(path+'/test.jpg')

def test_pull_metadata():
    #pull_metadata(camera_type,filename = None, save_location=False)
    testfile = 'test_OCR1.jpg'
    vals = OCR.pull_metadata('Axis',filename = testfile, save_location=False)
    assert type(vals)==type('')



