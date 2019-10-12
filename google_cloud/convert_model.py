"""
Convert model created by tfslim/tf 1.7 to SavedModel
"""
import tf_helper
import tensorflow as tf
import numpy as np
import pathlib
from PIL import Image
import rect_to_squares


root_dir = '/Users/henrypinkard/Desktop/aug23_model'
export_dir = root_dir + '_SavedModel/'
model_file = root_dir + '/frozen_aug23_223692.pb'
labels_file = root_dir + '/output_labels.txt'

graph = tf_helper.load_graph(model_file)
# labels = tf_helper.load_labels(labels_file)
config = tf.ConfigProto()


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


with tf.Session(graph=graph, config=config) as tfSession:

    with tf.Graph().as_default():
        input_height = 299
        input_width = 299
        # These commented out values are appropriate for tf_retrain
        # https://github.com/tensorflow/hub/raw/master/examples/image_retraining/retrain.py

        # input_mean = 0
        # input_std = 255
        # input_layer = "Placeholder"
        # output_layer = "final_result"

        # These values we're using now are appropriate for the fine-tuning and full training models
        # https://github.com/tensorflow/models/tree/master/research/slim
        input_mean = 128
        input_std = 128
        input_layer = "input"
        output_layer = "InceptionV3/Predictions/Reshape_1"

        input_name = "import/" + input_layer
        output_name = "import/" + output_layer
        input_operation = graph.get_operation_by_name(input_name)
        output_operation = graph.get_operation_by_name(output_name)

        inception_graph_def = graph.as_graph_def()

        with tf.Graph().as_default():
            # input_name = "file_reader"
            # output_name = "normalized"
            # file_name_placeholder = tf.placeholder(tf.string, shape=[])
            # file_reader = tf.read_file(file_name_placeholder, input_name)
            # image_reader = tf.image.decode_jpeg(file_reader, channels=3, name="jpeg_reader", dct_method="INTEGER_ACCURATE")
            # dims_expander = tf.expand_dims(float_caster, 0)

            raw_images_placeholder = tf.placeholder(shape=[None, None, None, 3], dtype=tf.uint8)
            float_caster = tf.cast(raw_images_placeholder, tf.float32)
            resized = tf.image.resize_bilinear(float_caster, [input_height, input_width])
            normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])


            preprocess_graph_def = tf.get_default_graph().as_graph_def()


        with tf.Graph().as_default() as g_combined:
            x = tf.placeholder(shape=[None, None, None, 3], dtype=tf.uint8, name='image_batch')

            # Import gdef_1, which performs f(x).
            # "input:0" and "output:0" are the names of tensors in gdef_1.
            y, = tf.import_graph_def(preprocess_graph_def, input_map={raw_images_placeholder.name: x},
                                     return_elements=[normalized.name])

            # Import gdef_2, which performs g(y)
            z, = tf.import_graph_def(inception_graph_def, input_map={input_operation.name: y},
                                     return_elements=[output_operation.name])


            with tf.Session(graph=g_combined) as sess:
                tf.saved_model.simple_save(sess, export_dir=export_dir,
                                           inputs={x.name: x}, outputs={z.name: z.values()[0]})


            # with tf.Session() as sess:
            #     for segmentInfo in segments:
            #         imgPath = segmentInfo['imgPath']
            #         # print(imgPath)
            #         t = sess.run(normalized, {file_name_placeholder: imgPath})
            #
            #         results = tfSession.run(output_operation.outputs[0], {
            #             input_operation.outputs[0]: t
            #         })
            #         results = np.squeeze(results)
            #
            #         top_k = results.argsort()[-5:][::-1]
            #         # for i in top_k:
            #         #     print(labels[i], results[i])
            #         smokeIndex = labels.index('smoke')
            #         # print(imgPath, results[smokeIndex])
            #         segmentInfo['score'] = results[smokeIndex]




