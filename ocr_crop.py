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

Crop given mage to get just the metadata line

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
import img_archive

import logging
from PIL import Image
import numpy as np

def main():
    reqArgs = [
        ["i", "image", "image to crop"],
        ["o", "output", "output cropped image"],
    ]
    optArgs = [
        ["m", "maxHeight", "max height of the metadata line"],
    ]

    args = collect_args.collectArgs(reqArgs, optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    maxHeight = args.maxHeight if args.maxHeight else 50
    cushionRows = 4
    minLetterBrightness = int(.9*255) # 90% of max value of 255
    minLetterSize = 12

    img = Image.open(args.image)
    assert maxHeight < img.size[1]
    try:
        imgCroppedGray = img.crop((0, img.size[1] - maxHeight, minLetterSize, img.size[1])).convert('L')
        croppedArray = np.array(imgCroppedGray)
    except Exception as e:
        logging.error('Error processing image: %s', str(e))
        return

    top = 0
    bottom = 0
    mode = 'find_dark_below_bottom'
    for i in range(maxHeight):
        row = maxHeight - i - 1
        maxVal = croppedArray[row].max()
        # logging.warning('Mode = %s: Top %d, Bottom %d, Max val for row %d is %d', mode, top, bottom, row, maxVal)
        if mode == 'find_dark_below_bottom':
            if maxVal < minLetterBrightness:
                mode = 'find_bottom'
        elif mode == 'find_bottom':
            if maxVal >= minLetterBrightness:
                mode = 'find_top'
                bottom = row
        elif mode == 'find_top':
            if maxVal < minLetterBrightness:
                possibleTop = row
                if bottom - possibleTop > minLetterSize:
                    top = possibleTop
                    break

    if not top or not bottom:
        logging.error('Unable to locate metadata')
        return

    # row is last row with letters, so row +1 is first without letters, and add cushionRows
    bottom = min(img.size[1] - maxHeight + bottom + 1 + cushionRows, img.size[1])
    # row is first row without letters, so subtract cushionRows
    top = max(img.size[1] - maxHeight + top - cushionRows, img.size[1] - maxHeight)

    logging.warning('Top = %d, bottom = %d', top, bottom)
    imgOut = img.crop((0, top, img.size[0], bottom))
    imgOut.save(args.output, format='JPEG')


if __name__=="__main__":
    main()
