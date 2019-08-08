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
    response = requests.get(url, headers=headers)
    return response.content


def main():
    reqArgs = [
    ]
    optArgs = [
    ]
    
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleCreds = goog_helper.getCreds(settings, args)

    url = 'https://us-central1-dkgu-dev.cloudfunctions.net/fuego-test1'
    respData = callGCF(url, googleCreds)
    logging.warning('Result: %s', respData)


if __name__=="__main__":
    main()
