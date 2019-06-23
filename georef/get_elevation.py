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

"""

import os
import sys
fuegoRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot
import collect_args
import goog_helper
import logging
import gdal

def get_pix(metadata, latitude, longtitude):  
    pixX = int((longtitude - metadata[0])*metadata[1])
    pixY = int((latitude - metadata[3])*metadata[5])
    logging.warning('pix: (%d, %d)', pixX, pixY)
    return [pixX,pixY]


# def get_data():
# if cord[0] < tiffData.RasterXSize and cord[1] < tiffData.RasterYSize:
#         val = specs[cord[0], cord[1]]
#         print(val)
# else:
#         logging.warning("sorry coordinate not in data (%d < %d) and (%d < %d)", cord[0], tiffData.RasterXSize, cord[1], tiffData.RasterYSize)

def main():
    reqArgs = [
        ["g", "geoTiffName", "File name of geotiff"],
        ["a", "lat", "latitude of desired point"],
        ["o", "long", "longtitude of desired point"],
    ]
    args = collect_args.collectArgs(reqArgs, optionalArgs=[], parentParsers=[goog_helper.getParentParser()])
    latitude = float(args.lat)
    longtitude = float(args.long)
    tiffData = gdal.Open(args.geoTiffName)
    logging.warning('x: %d, y: %d', tiffData.RasterXSize, tiffData.RasterYSize)
    metadata = tiffData.GetGeoTransform()
    logging.warning('metadata: %s', metadata)
    specs =  tiffData.ReadAsArray(xoff=0, yoff=0)
    logging.warning('specs: %s', specs)

    cord = get_pix(metadata, latitude, longtitude)
    if cord[0] < tiffData.RasterXSize and cord[1] < tiffData.RasterYSize:
        val = specs[cord[0], cord[1]]
        print(val)
    else:
        logging.warning("sorry coordinate not in data (%d < %d) and (%d < %d)", cord[0], tiffData.RasterXSize, cord[1], tiffData.RasterYSize)
    

if __name__=="__main__":
    main()