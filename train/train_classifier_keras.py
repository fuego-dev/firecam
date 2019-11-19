import glob
import tensorflow as tf
from tensorflow import keras
import collect_args
import goog_helper

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

    image = (tf.cast(image, tf.float32) - 128) / 128.0
    return [image, label]


def main():
    reqArgs = [
        ["i", "inputDir", "local directory containing both smoke and nonSmoke images"],
        ["o", "outputDir", "local directory to write out TFRecords files"],
    ]
    optArgs = [
        ["t", "trainPercentage", "percentage of data to use for training vs. validation (default 90)"]
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])

    batch_size = 32
    max_epochs = 1000
    steps_per_epoch=250
    overshoot_epochs=200 #number of epochs over which validation loss hasnt decreased to stop training at
    val_steps = 100 #only needed for now because of a bug in tf2.0, which should be fixed in next version
    #TODO: either set this to # of validation examples /batch size (i.e. figure out num validation examples)
    #or upgrade to 2.1 when its ready and automatically go thorugh the whole set

    train_filenames = glob.glob(args.inputDir + 'firecam_train_*.tfrecord')
    val_filenames = glob.glob(args.inputDir + 'firecam_validation_*.tfrecord')

    raw_dataset_train = tf.data.TFRecordDataset(train_filenames)
    raw_dataset_val = tf.data.TFRecordDataset(val_filenames)

    dataset_train = raw_dataset_train.map(_parse_function).shuffle(batch_size * 5).batch(batch_size)
    dataset_val = raw_dataset_val.map(_parse_function).batch(batch_size)

    inception = keras.applications.inception_v3.InceptionV3(weights=None, include_top=True, input_tensor=None,
                                                            classes=2)
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.001, beta_1=0.9, beta_2=0.999, amsgrad=False)
    inception.compile(optimizer=optimizer, loss=tf.keras.losses.BinaryCrossentropy(), metrics=['accuracy'])

    callbacks = [keras.callbacks.EarlyStopping(monitor='val_loss', patience=overshoot_epochs),
                 keras.callbacks.ModelCheckpoint(filepath=args.outputDir + 'best_model',
                                                 monitor='val_loss', save_best_only=True)]

    inception.fit(dataset_train, validation_data=dataset_val, epochs=max_epochs, steps_per_epoch=steps_per_epoch, validation_steps=val_steps,callbacks=callbacks)


if __name__ == "__main__":
    main()
