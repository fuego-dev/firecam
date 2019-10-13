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
"""

Helper functions for Google Cloud Platform

"""

import grpc
import tensorflow as tf
import time

from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc
from tensorflow.python.framework import tensor_util

def connect_to_prediction_service(server_ip_and_port):
    """
    Connect to a an inference server at given ip address and port. Server could be
    a single machine or a Kubernetes cluster
    :param server_ip_and_port: string with ip address followed by port (e.g. '34.82.71.243:8500')
    :return: PredicitonServiceStub object
    """
    tf.app.flags.DEFINE_string('server', server_ip_and_port, 'PredictionService host:port')
    channel = grpc.insecure_channel(tf.app.flags.FLAGS.server)
    # grpc.secure_channel()
    return prediction_service_pb2_grpc.PredictionServiceStub(channel)

def predict_batch(prediction_service, crops, timing=False):
    """
    Run inference on a batch of predicitons
    :param crops: N x H x W x 3 uint8 numpy array (e.g. set of crops for a single camera)
    :return: N x 2 numpy array of smoke/nonsmoke probabilities
    """

    # Send request
    # See prediction_service.proto for gRPC request/response details.
    request = predict_pb2.PredictRequest()
    request.model_spec.name = 'inception'
    request.model_spec.signature_name = 'serving_default'
    request.inputs['image_batch:0'].CopyFrom(tf.contrib.util.make_tensor_proto(crops, shape=crops.shape))

    start = time.time()
    result = prediction_service.Predict(request, 1000.0)  # 1000 secs timeout
    if timing:
        print('Inference time {}'.format(time.time() - start))
    #convert to numpy
    numpy_result = tensor_util.MakeNdarray(result.outputs["import_1/import/InceptionV3/Predictions/Reshape_1"])
    return numpy_result
