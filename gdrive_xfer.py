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

Simple wrapper to download or upload files from google drive using stored credentials

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import collect_args
import goog_helper

import logging

def main():
    reqArgs = [
        ["d", "dirID", "ID of google drive directory"],
        ["f", "fileName", "fileName of google drive file"],
    ]
    optArgs = [
        ["u", "upload", "(optional) performs upload vs. download"]
    ]
    
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    if (args.upload):
        goog_helper.uploadFile(googleServices['drive'], args.dirID, args.fileName)
    else:
        goog_helper.downloadFile(googleServices['drive'], args.dirID, args.fileName, args.fileName)

if __name__=="__main__":
    main()
