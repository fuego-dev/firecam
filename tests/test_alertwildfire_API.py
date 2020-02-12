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

Test alertwildfire_API

"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

fuegoRoot = Path(__file__).parent.parent  # get the firecam directory
sys.path.insert(0, str(fuegoRoot / 'lib'))  # add the lib directory to the path
import alertwildfire_API


def test_get_all_camera_info():
    # get_all_camera_info()
    loc = alertwildfire_API.get_all_camera_info()
    assert type(loc) == type([])
    assert type(loc[0]) == type({})


def test_get_individual_camera_info():
    # get_individual_camera_info(cameraID)
    c = alertwildfire_API.get_individual_camera_info("Axis-UpperBellNorth")
    assert type(c) == type({})
    assert type(c["name"]) == type('')
    assert c["name"] == 'Axis-UpperBellNorth'
    c = alertwildfire_API.get_individual_camera_info("testingfailcase")
    assert type(c) == type(None)


def test_request_current_image():
    # request_current_image(outputDir, cameraID, closestTime = None, display=False)
    temporaryDir = tempfile.TemporaryDirectory()
    imgPath = alertwildfire_API.request_current_image(temporaryDir.name, "Axis-UpperBellNorth")
    assert os.path.isfile(imgPath)
    shutil.rmtree(temporaryDir.name)


"""#time expensive
def test_request_all_current_images():
	#request_all_current_images(outputDir, delay_between_requests=None)
	temporaryDir = tempfile.TemporaryDirectory()
	Paths = alertwildfire_API.request_all_current_images(temporaryDir.name)
	for imgPath in Paths:
		assert os.path.isfile(imgPath)
	shutil.rmtree(temporaryDir.name)
"""


def test_record_camera_info():
    # record_camera_info()
    print("not implemented")
