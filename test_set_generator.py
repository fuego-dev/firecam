# -*- coding: utf-8 -*-
"""
Created on Tue Mar 19 11:39:22 2019

@author: fuego
"""

import sys
import settings
import os
settings.fuegoRoot = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(settings.fuegoRoot, 'lib'))
from img_archive import parseFilename

import numpy as np

#Reads the csv. Creates to lists, a list of rows in the csv and a list of dictionaries based on the camera name.
def image_library(input_csv):
    cropped_image_list = np.loadtxt(input_csv, delimiter = ',', dtype = str)
    image_name_list = []
    for image_name in cropped_image_list:
        image_name_list += [parseFilename(image_name[0])]
    return cropped_image_list, image_name_list

#Generates test set and new training set
#The input variable 'n' sets the neighborhood of images to be removed around the drawn test image. 2*n minutes before to n//2 minutes after
def test_set_generator(cropped_image_list, image_name_list, test_size, n = 5):
    #Create a list of indices the length of the cropped images csv
    #These indices correspond to a cropped image in the training set
    #Each loop an image is removed from the training set and added to the test set. Neighboring images (of the drawn image) are also removed from the training set. 
    library_length = len(cropped_image_list)
    training_indices = list(np.arange(library_length, dtype = int))
    test_indices = np.zeros(test_size, dtype = int)
    
    for i in range(test_size):
        #draw an index from the list of remaining indices and add it to the test_indices array
        drawn_index = np.random.choice(training_indices)
        test_indices[i] = int(drawn_index)
        
        #Determine the name, date, and time of the drawn image
        drawn_name = image_name_list[drawn_index]['cameraID']
        drawn_date = image_name_list[drawn_index]['date']
        drawn_hours = image_name_list[drawn_index]['hours']
        drawn_minutes = image_name_list[drawn_index]['minutes']
        minute_time = float(drawn_hours)*60 + float(drawn_minutes)
        
        #Determine which images need to be removed based on the draw
        neighbors = [index for index, image in enumerate(image_name_list) if image["cameraID"] == drawn_name and image["date"] == drawn_date and float(image["hours"])*60 + float(image["minutes"]) >= minute_time - 2*n and float(image["hours"])*60 + float(image["minutes"]) <= minute_time + n//2]
        
        #Remove the neighboring images from the training set
        for neighbor in neighbors:
            if neighbor in training_indices:
                training_indices.remove(neighbor)
    
    #Generate the new sets based on the new indices
    training_set = cropped_image_list[np.array(training_indices)]
    test_set = cropped_image_list[test_indices]
    
    return training_set, test_set

#Saves new sets to csvs
def save_new_sets(training_set, test_set, output_dir):
    np.savetxt(output_dir + 'training_set.csv', training_set, delimiter = ',', fmt = '%s')
    np.savetxt(output_dir + 'test_set.csv', test_set, delimiter = ',', fmt = '%s')
    
#For Testing
def main():
    input_csv = '/home/fuego/Desktop/Cropped_Images.csv' #Replace with path to your csv
    cropped_image_list, image_name_list = image_library(input_csv)
    training_set, test_set = test_set_generator(cropped_image_list, image_name_list, 100) #adjust value for desired test set size
    save_new_sets(training_set, test_set, '/home/fuego/Desktop/') #change output directory to your desired location
    print(len(training_set), len(test_set), len(cropped_image_list)) #debugging output
if __name__=="__main__":
    main()
