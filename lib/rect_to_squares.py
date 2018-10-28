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
@author: Kinshuk Govil

Simple utility to break up rectangle into squares

"""

import os
import pathlib
import math
import collect_args

MIN_SQUARE_SIZE = 150

def rect_to_squares(selectionX0, selectionY0, selectionX1, selectionY1, limitX, limitY, minSize):
    """
    Convert the given rectangle into a series of squares if the aspect ratio is not
    close enough to a square.  Also, squares must meet minimium size requiremet of
    minSize and must be centered around the selected rectangle.  All squares must fit
    between (0,0) and (limitX, limitY)

    Returns array/list of coordinates for the squares.  The coordinates are represented
    by 4-tuples (x0,y0,x1,y1)
    """

    minX = min(selectionX0, selectionX1)
    maxX = max(selectionX0, selectionX1)
    minY = min(selectionY0, selectionY1)
    maxY = max(selectionY0, selectionY1)
    centroidX = (minX + maxX)/2
    centroidY = (minY + maxY)/2

    diffX = maxX - minX
    diffY = maxY - minY
    diffMin = min(diffX, diffY)
    diffMax = max(diffX, diffY)
    if (diffMin < 1): # must be at least 1 pixel in each dimension to avoid div by zero
        return []

    aspectRatio = diffX/diffY
    flip = False
    if (aspectRatio < 1):  # vertical rectangle
        flip = True
        aspectRatio = 1./aspectRatio
    # print("Rect: " + str((minX, minY, maxX, maxY, diffX, diffY, flip, aspectRatio)))

    # number of squares is simply the rounded aspect ratio with contraint of minimimum size
    numSquares = max(round(aspectRatio), 1)
    if (diffMax/numSquares < minSize):
        numSquares = max(math.floor(diffMax/minSize), 1)

    offset = diffMax/numSquares
    squareSize = max(diffMax/numSquares, minSize)
    squareSize = squareSize * 1.1 # give them 10% overlap
    squareCoords = []
    for i in range(numSquares):
        squareCentroidX = centroidX
        squareCentroidY = centroidY

        if (flip):
            squareCentroidY += offset*i - offset*(numSquares-1)/2
        else:
            squareCentroidX += offset*i - offset*(numSquares-1)/2

        sx0 = int(max(squareCentroidX - squareSize/2, 0))
        sy0 = int(max(squareCentroidY - squareSize/2, 0))
        sx1 = int(min(squareCentroidX + squareSize/2, limitX))
        sy1 = int(min(squareCentroidY + squareSize/2, limitY))
        # print("Square: ", (sx0, sy0, sx1, sy1))
        squareCoords.append((sx0, sy0, sx1, sy1))

    return squareCoords

# Divide large picture into ~50 boxes, so sqrt(50) =~ 7
MAX_ROWS=7
# Also want to maintain approximate minimum of 300 pixels to match inception v3 299 size
MIN_ROW_HEIGHT=300

def cutBoxes(imgOrig, outputDirectory, imageFileName, callBackFn=None):
    segments = []
    imgName = pathlib.PurePath(imageFileName).name
    imgNameNoExt = str(os.path.splitext(imgName)[0])
    if imgOrig.size[1] > MIN_ROW_HEIGHT * MAX_ROWS:
        approxSize = imgOrig.size[1] / MAX_ROWS
    else:
        approxSize = MIN_ROW_HEIGHT

    level = max(int(imgOrig.size[1]/approxSize),1)
    offsetY = imgOrig.size[1] / level
    # print('Sizes', imgOrig.size[0], imgOrig.size[1], approxSize, level, offsetY)
    for i in range(level):
        minY = max(i * offsetY, 0)
        maxY = min((i+1) * offsetY, imgOrig.size[1])
        # print(i, minY, maxY)
        squares = rect_to_squares(0, minY, imgOrig.size[0], maxY, imgOrig.size[0], imgOrig.size[1], MIN_SQUARE_SIZE)
        # print(squares)
        for coords in squares:
            if callBackFn != None:
                callBackFn(coords)
            # output cropped image
            cropImgName = imgNameNoExt + '_Crop_' + 'x'.join(list(map(lambda x: str(x), coords))) + '.jpg'
            cropImgPath = os.path.join(outputDirectory, cropImgName)
            cropped_img = imgOrig.crop(coords)
            cropped_img.save(cropImgPath, format='JPEG')
            cropped_img.close()
            segments.append({
                'imgPath': cropImgPath,
                'MinX': coords[0],
                'MinY': coords[1],
                'MaxX': coords[2],
                'MaxY': coords[3]
            })
    return segments


def test():
    argDefs = [
        ["a", "X0", "X coord of first corner", int],
        ["b", "Y0", "Y coord of first corner", int],
        ["c", "X1", "X coord of opposite corner", int],
        ["d", "Y1", "Y coord of opposite corner", int],
    ]
    args = collect_args.collectArgs(argDefs)
    print('Rect:', (args.X0, args.Y0, args.X1, args.Y1))
    coords = rect_to_squares(args.X0, args.Y0, args.X1, args.Y1, 1000, 1000, MIN_SQUARE_SIZE)
    print('Squares:', coords)


# for testing
if __name__=="__main__":
    test()