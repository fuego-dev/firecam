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

Test Google cloud function for ffmpeg

"""

import sys
import os
fuegoRoot = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import collect_args
import goog_helper
import requests

import logging

def callGCF(url, creds):
    headers = {'Authorization': f'bearer {creds.id_token_jwt}'}
    data = {
        'hostName': 'c1',
        'cameraID': 'rm-w-mobo-c',
        'yearDir': 2017,
        'dateDir': 20170613,
        'qName': 'Q3.mp4',
        'uploadDir': '1KCdRENKi_b9HgiZ9nzq05P5rTuRH71q2',
    }
    response = requests.post(url, headers=headers, data=data)
    return response.content


def main():
    reqArgs = [
    ]
    optArgs = [
        ["l", "localhost", "localhost for testing"],
    ]
    
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleCreds = goog_helper.getCreds(settings, args)

    url = 'https://us-central1-dkgu-dev.cloudfunctions.net/fuego-ffmpeg1'
    if args.localhost:
        url = 'http://localhost:8080'
    respData = callGCF(url, googleCreds)
    logging.warning('Result: %s', respData)


if __name__=="__main__":
    main()
