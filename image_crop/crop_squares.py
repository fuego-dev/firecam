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
@author: Jean-Gabriel JOLLY

Now generating text file with coordinates (by Lucas)

Now showing how the rectangle may potentially be split into squares (Kinshuk)

"""

#===============
#Importing modules
#===============

#modules for GUI
#from tkinter import *
import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showwarning

#modules for image processing
from PIL import Image, ImageTk

#module for Manage files and use system commands
import os
import glob

import math

#===============
#variables declaration
#===============


#List of rectangles displays on screen
global rectangleList
rectangleList=[[],[],[],[],[],[],[],[],[],[]]

#Counters for managing rectangles and pictures
global numberImage, numberRectangle,totalRectangle,numberPicture
numberImage, numberRectangle,totalRectangle,numberPicture = 0,0,0,0

global numberTotalImagePerLabel
numberTotalImagePerLabel = [0,0,0,0,0,0,0,0,0,0]

global numberImagePerLabel
numberImagePerLabel = [0,0,0,0,0,0,0,0,0,0]

#Square position
global x1,x2,y1,y2
x1,x2,y1,y2=0,0,0,0

# for select the folder
global selectFolder
selectFolder = 0

global listFolder
listFolder = ["nope","nope","nope","nope","nope","nope","nope","nope","nope","nope"]

global listLabel
listLabel = ["nope","nope","nope","nope","nope","nope","nope","nope","nope","nope"]

global labelDisplay
labelDisplay = "txt"

#===============
#===============
#===============

MIN_SIZE = 150

def rect_to_squares(selectionX0, selectionY0, selectionX1, selectionY1, limitX, limitY):
    """
    Convert the given rectangle into a series of squares if the aspect ratio is not
    close enough to a square.  Also, squares must meet minimium size requiremet of
    MIN_SIZE and must be centered around the selected rectangle.  All squares must fit
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
    if (diffMax/numSquares < MIN_SIZE):
        numSquares = max(math.floor(diffMax/MIN_SIZE), 1)

    offset = diffMax/numSquares
    squareSize = max(diffMax/numSquares, MIN_SIZE)
    squareCoords = []
    for i in range(numSquares):
        squareCentroidX = centroidX
        squareCentroidY = centroidY

        if (flip):
            squareCentroidY += offset*i - offset*(numSquares-1)/2
        else:
            squareCentroidX += offset*i - offset*(numSquares-1)/2

        sx0 = max(squareCentroidX - squareSize/2, 0)
        sy0 = max(squareCentroidY - squareSize/2, 0)
        sx1 = min(squareCentroidX + squareSize/2, limitX)
        sy1 = min(squareCentroidY + squareSize/2, limitY)
        # print("Square: " + str((sx0, sy0, sx1, sy1)))
        squareCoords.append((sx0, sy0, sx1, sy1))

    return squareCoords

#Square position

global squares
squares = []

def leftClick(event):
    chaine.configure(text = str(event.x)+" "+str(event.y))
    global x1,y1
    x1=cadre.canvasx(event.x)
    y1=cadre.canvasy(event.y)

def holdLeftClick(event):
    chaine.configure(text = str(cadre.canvasx(event.x))+" "+str(cadre.canvasy(event.y))+"Frame object number "+str(numberRectangle))
    cadre.coords(rectangle, x1,y1,cadre.canvasx(event.x),cadre.canvasy(event.y))
    #cadre.coords(oval,x1+90,y1+90, event.x-90, event.y-90)

    x2=cadre.canvasx(event.x)
    y2=cadre.canvasy(event.y)

    # delete old squares
    for square in squares:
        cadre.delete(square)

    # make new squares
    squareCoords = rect_to_squares(x1, y1, x2, y2, img.size[0], img.size[1])
    for coords in squareCoords:
        (sx0, sy0, sx1, sy1) = coords
        square = cadre.create_rectangle(sx0, sy0, sx1, sy1, outline='red', width=2)
        squares.append(square)

    
def releaseLeftClick(event):
    cadre.coords(rectangle, 0, 0, 0, 0)
    cadre.coords(oval, 0, 0, 0, 0)
    global x2,y2,numberRectangle,rectangleList,totalRectangle,hpercent,numberImagePerLabel,numberTotalImagePerLabel
    chaine.configure(text = "Number of frames:" + str(numberRectangle+1)+" Selected folder: "+listLabel[int(selectFolder)])
    x2=cadre.canvasx(event.x)
    y2=cadre.canvasy(event.y)
    rectangleList[int(selectFolder)].append(cadre.create_rectangle(x1,y1,x2,y2))
    numberRectangle += 1
    numberImagePerLabel[int(selectFolder)] = numberImagePerLabel[int(selectFolder)]+1
    totalRectangle += 1
    numberTotalImagePerLabel[int(selectFolder)] = numberTotalImagePerLabel[int(selectFolder)]+1
    



    
    ####Selection orientation management PART#####
    if x1 < x2 and y1 < y2:
        area = (int(x1), int(y1), int(x2), int(y2))
    elif x2 < x1 and y2 < y1:
        area = (int(x2), int(y2), int(x1), int(y1))
    elif x2 < x1 and y1 < y2:
        area = (int(x2), int(y1), int(x1),int(y2))
    elif x1 < x2 and y2 < y1:
        area = (int(x1), int(y2), int(x2), int(y1))
        
    centroidX = (area[0]+area[2])/2
    centroidY = (area[1]+area[3])/2
    lengthX = area[2]-area[0]
    lengthY = area[3]-area[1]
    if lengthX > lengthY:
        longer = 'X'
    elif lengthY > lengthX:
        longer = 'Y'
    else:
        longer = '='
    
    print('coords:'+str(area),'centroid X:'+str(centroidX),'centroidY:'+str(centroidY),'lengthX:'+str(lengthX),'lengthY:'+str(lengthY),'longer:'+str(longer))
    f = open(listFolder[int(selectFolder)]+"/" + 'coords.txt','a+')
    f.write(listLabel[int(selectFolder)]+ str(numberTotalImagePerLabel[int(selectFolder)]) + ' ' + name +', '+str(area[0])+', '+str(area[1])+', '
        +str(area[0])+', '+str(area[3])+', '
        +str(area[2])+', '+str(area[3])+', '
        +str(area[2])+', '+str(area[1])+', '
        +str(centroidX)+', '+str(centroidY)+', '+str(lengthX)+', '+str(lengthY)+', '+str(longer) + ' CR LF\r\n')
    f.close()
    ####CROPPING PART#####
    cropped_img = img.crop(area)
    cropped_img.save(listFolder[int(selectFolder)]+"/"+ justname +listLabel[int(selectFolder)]+ str(numberTotalImagePerLabel[int(selectFolder)]) + '.tif') #test bug here
    ######################
    
def middleClick(event):
    global numberPicture,photo,photo2,img,rectangle,numberRectangle,numberImagePerLabel
    numberPicture += 1
    if numberPicture < len(listPictures):

        imageDisplay()

        cadre.delete(aff)
        cadre.create_image(0, 0, anchor='nw', image=photo2)
        rectangle=cadre.create_rectangle(0,0,0,0)
        numberRectangle = 0
        numberImagePerLabel = [0,0,0,0,0,0,0,0,0,0]
        
        #Removing old rectangles
        for j in range(0,8,1):
            for i in rectangleList[j]:
                cadre.delete(i)
        ########################

    else:
        chaine.configure(text = "No More pictures")
        showwarning('Warning', 'No More pictures')
        
        

##########################
##########################
##########################
def rightClick(event):
    global rectangleList, numberRectangle, totalRectangle
    if numberImagePerLabel[int(selectFolder)] > 0:
        chaine.configure(text = "Erasing frame number ="+str(numberRectangle))
        cadre.delete(rectangleList[int(selectFolder)][len(rectangleList[int(selectFolder)])-1])
        del rectangleList[int(selectFolder)][len(rectangleList[int(selectFolder)])-1]
        os.remove(listFolder[int(selectFolder)]+"/"+ justname +listLabel[int(selectFolder)]+ str(numberTotalImagePerLabel[int(selectFolder)]) + '.tif')
        numberRectangle -= 1
        totalRectangle -= 1
        numberImagePerLabel[int(selectFolder)] = numberImagePerLabel[int(selectFolder)]-1
        numberTotalImagePerLabel[int(selectFolder)] = numberTotalImagePerLabel[int(selectFolder)]-1
        
        rf = open(listFolder[int(selectFolder)]+"/" + 'coords.txt', 'r')
        lines = rf.readlines()
        rf.close()
        wf = open(listFolder[int(selectFolder)]+"/" + 'coords.txt', 'w')
        wf.writelines([item for item in lines[:-1]])
        wf.close()
        
    else:
        chaine.configure(text = "Nothing to erase")

def imageDisplay():
    global numberPicture,photo,photo2,img,rectangle,hpercent,name,justname
    
    #photo = PhotoImage(file=listPictures[numberPicture])
    im=Image.open(listPictures[numberPicture]) #test test test
    photo = tk.PhotoImage(im)
    
    ###DISPLAY RESIZE MODULE###
    baseheight = (int(fen.winfo_screenheight()*0.85))#size of the height of the screen
    ############ A MOFIFIER PLUS TARD  ^^^^^^^^
    img = Image.open(listPictures[numberPicture])
    name = listPictures[numberPicture]
    base = os.path.basename(name)
    justname = str(os.path.splitext(base)[0])
    print(name)
    print(justname)
    print("Dimensions: " + str((img.size[0], img.size[1])))
    hpercent = ((baseheight / float(img.size[1])))
    wsize = int((float(img.size[0]) * float(hpercent)))
    img2 = img
    #img2 = img.resize((wsize, baseheight), PIL.Image.ANTIALIAS)     #try and make this something along the lines of img2 = img, so no loss of resolution
    ###########################
    
    ############ A MOFIFIER PLUS TARD
    img2.save("temporaryFile.png")
    image_replacement = Image.open("temporaryFile.png")
    photo2 = ImageTk.PhotoImage(image_replacement)
    ############ A MOFIFIER PLUS TARD
    
    
    
    
def folderSelectKey(event):
    global selectFolder, listFolder, listLabel, labelDisplay
    
    key = event.keysym
    selectFolder=int(key)

    if key == "1" or key == "2" or key == "3" or key == "4" or key == "5" or key == "6" or key == "7" or key == "8" or  key == "9" or key == "0":
        selectFolder = event.keysym
        if listFolder[int(key)] == "nope":
            toDo="Select the destination folder of label number "+str(selectFolder)
            listFolder[int(key)] = askdirectory(title=toDo, initialdir='C:/Users/%s')
            listLabel[int(key)] = os.path.basename(listFolder[int(key)])
            labelDisplay = labelDisplay+" Key"+key+"= "+listLabel[int(key)]+" ;"
            chaineLabels.configure(text = labelDisplay)

    chaine.configure(text = "Number of frames:" + str(numberRectangle+1)+" Selected folder: "+listLabel[int(selectFolder)])
            
##########################
##########################
##########################
##########################
##########################
##########################
    



fen = tk.Tk()
fen.title('Very Fast Multiple Cropping Tool')

#Ask for directory
showwarning('Instructions', 'Enter the image folder')
inputDirectory = askdirectory(initialdir='C:/Users/%s')
showwarning('Instructions', 'Enter the destination folder')
outputDirectory = askdirectory(initialdir='C:/Users/%s')


#Set Directory list and display
listFolder[0] = outputDirectory
listLabel[0] = os.path.basename(listFolder[0])
labelDisplay = "Key0= "+listLabel[0]+" ;"


#=================

#list images in the forlder
listPictures = sorted(glob.glob(inputDirectory + '/*.png'))
listPictures2 = sorted(glob.glob(inputDirectory + '/*.jpg'))
listPictures3 = sorted(glob.glob(inputDirectory + '/*.tif'))
listPictures4 = sorted(glob.glob(inputDirectory + '/*.PNG'))
listPictures5 = sorted(glob.glob(inputDirectory + '/*.JPG'))
listPictures6 = sorted(glob.glob(inputDirectory + '/*.TIF'))
listPictures6 = listPictures6 + sorted(glob.glob(inputDirectory + '/*.tiff'))
listpictures6 = listPictures6 + sorted(glob.glob(inputDirectory + '/*.TIFF'))

listPictures = listPictures+listPictures2+listPictures3+listPictures4+listPictures5+listPictures6


###
if len(listPictures)>0:
    imageDisplay()
    cadre = tk.Canvas(fen, width=photo2.width(), height=photo2.height(), bg="light yellow")
    
    cadre.config(highlightthickness=0)
    
    sbarV = tk.Scrollbar(fen, orient='vertical')
    sbarH = tk.Scrollbar(fen, orient='horizontal')
    
    sbarV.config(command=cadre.yview)
    sbarH.config(command=cadre.xview)
    
    cadre.config(yscrollcommand=sbarV.set)
    cadre.config(xscrollcommand=sbarH.set)
    
    
    
    width=photo2.width()
    height=photo2.height()
    cadre.config(scrollregion=(0,0,width,height))
    
    aff=cadre.create_image(0, 0, anchor='nw', image=photo2) #BUG
    cadre.bind("<Button-1>", leftClick)
    cadre.bind("<B1-Motion>", holdLeftClick)
    cadre.bind("<ButtonRelease-1>", releaseLeftClick)
    cadre.bind("<Button-2>", middleClick)
    cadre.bind("<ButtonRelease-3> ", rightClick)
    cadre.focus_set()
    cadre.bind("<Key>", folderSelectKey)
    
    #cadre.pack(side="left", fill="both", expand=True)   
    #cadre.pack()
    chaineLabels = tk.Label(fen)
    chaine = tk.Label(fen)
    chaineLabels.configure(text = labelDisplay)
    chaineLabels.pack(side='bottom')
    chaine.pack()
    
    sbarV.pack(side='right', fill='y')
    sbarH.pack(side='bottom', fill='x')
    cadre.pack(side='left', expand='yes', fill='both')
    
    rectangle=cadre.create_rectangle(0,0,0,0)
    oval=cadre.create_oval(0,0,0,0)
    fen.mainloop()
    os.remove("temporaryFile.png")
else:
    showwarning('Error', 'There are no images in the folder')
    fen.destroy()
