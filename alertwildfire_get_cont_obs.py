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
    reqArgs = [
        ["c", "cameraID", "ID (code name) of camera"],
        ["f", "frequency", "minutes between observations"],
        ["d", "duration", "duration of observation (minutes)"]
    ]
    optArgs = [
        ["o", "outputDir", "directory to save the output image"]
    ]
    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs)
    if not args.outputDir:
        args.outputDir = settings.downloadDir
    list_of_downloaded_img_paths = []
    current_durration = 0#mins
    while True:
        camera_info = alertwildfire_API.get_individual_camera_info(args.cameraID)
        if camera_info["position"]["time"]:
            timeStamp = camera["position"]["time"]###need to convert their format
        elif camera_info["image"]["time"]:
            timeStamp = camera["image"]["time"]###need to convert their format
        else:
            timeStamp = None
        path = alertwildfire_API.request_current_image(args.outputDir, args.cameraID, timeStamp)
        list_of_downloaded_img_paths.append(path)
        current_durration += int(args.frequency)
        time.sleep(int(args.frequency)*60)
        if current_durration>int(args.duration):
            break
    return list_of_downloaded_img_paths


if __name__=="__main__":
    main()
