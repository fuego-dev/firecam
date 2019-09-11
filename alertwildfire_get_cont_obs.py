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

import os
import sys
fuegoRoot = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import alertwildfire_API
import collect_args
import time

def main():
    """requests the continual recording of a a particular alertwildfire camera and saves images to outputDir
    Args:
        -c  cameraID (str): time in hours to store data
        -i  interval (flt): minutes between observations
        -d  duration (flt): duration of observation (minutes)
        -o  outputDir (str): directory to save the output image
    Returns:
        None
    """
    reqArgs = [
        ["c", "cameraID", "ID (code name) of camera"]
    ]
    optArgs = [
        ["i", "interval", "minutes between observations"],
        ["d", "duration", "duration of observation (minutes)"],
        ["o", "outputDir", "directory to save the output image"]
    ]
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs)
    if not args.outputDir:
        args.outputDir = settings.downloadDir
    if not args.duration:
        args.duration = 30
    if not args.interval:
        args.interval = 1

    list_of_downloaded_img_paths = []
    start_time= time.time()
    end_time = start_time+float(args.duration)*60
    next_interval = start_time
    while True:
        path = alertwildfire_API.request_current_image(args.outputDir, args.cameraID)
        list_of_downloaded_img_paths.append(path)
        next_interval +=float(args.interval)*60
        if next_interval> end_time:
            return list_of_downloaded_img_paths
        time.sleep(int(next_interval-time.time()))


if __name__=="__main__":
    main()
