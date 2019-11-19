import numpy as np
import os
import tensorflow as tf
from tensorflow import keras


def _parse_function(example_proto):
    """
    Function for converting TFRecordDataset to uncompressed image pixels + labels
    :return:
    """
    feature_description = {
    'image/class/label': tf.io.FixedLenFeature([], tf.int64, default_value=0),
    'image/encoded': tf.io.FixedLenFeature([], tf.string, default_value=''),
    'image/format': tf.io.FixedLenFeature([], tf.string, default_value=''),
    'image/height': tf.io.FixedLenFeature([], tf.int64, default_value=0),
    'image/width': tf.io.FixedLenFeature([], tf.int64, default_value=0),
    }

    # Parse the input `tf.Example` proto using the dictionary above.
    example = tf.io.parse_single_example(example_proto, feature_description)
    image = tf.image.decode_image(example['image/encoded'], channels=3)

    #Resizing images in training set because they are apprently rectangular much fo the time
    if example['image/height'] != 299 or example['image/width'] != 299:
        image = tf.image.resize(tf.reshape(image, [example['image/height'], example['image/width'], 3]), [299, 299])
        image = tf.cast(image, tf.uint8)

    image = tf.reshape(image, [299, 299, 3]) #weird workaround because decode image doesnt get shape
    label = tf.one_hot(example['image/class/label'], depth=2)
    return [image, label]





train_filename = '/Users/henrypinkard/Desktop/firecam_train_00000-of-00008.tfrecord'
val_filename = '/home/henry/training_set/firecam_validation_00000-of-00001.tfrecord'
batch_size = 3

raw_dataset_train = tf.data.TFRecordDataset(train_filename).take(20)
raw_dataset_val = tf.data.TFRecordDataset(train_filename).take(20)

dataset_train = raw_dataset_train.map(_parse_function).shuffle(batch_size * 5).batch(batch_size)
dataset_val = raw_dataset_val.map(_parse_function).batch(batch_size)

inception = keras.applications.inception_v3.InceptionV3(weights=None, include_top=True, input_tensor=None, classes=2)
inception.compile(optimizer='adam',
              loss=tf.keras.losses.BinaryCrossentropy(),
              metrics=['accuracy'])

inception.fit(dataset_train, validation_data=dataset_val, epochs=10)
pass
#TODO: export model
#TODO: early stopping
#TODO: checkoiunting




