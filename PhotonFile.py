"""
Loads/Save .photon files (from the Anycubic Photon Slicer) in memory and allows editing of settings and bitmaps.
"""

__version__ = "alpha"
__author__ = "Nard Janssens, Vinicius Silva, Robert Gowans, Ivan Antalec, Leonardo Marques - See Github PhotonFileUtils"

import os
import copy
import math
import struct
from math import *

#import pygame
#from pygame.locals import *
import concurrent
import time

try:
    import numpy
    numpyAvailable = True
    #print("Numpy library available.")
except ImportError:
    numpyAvailable = False
    #print ("Numpy library not found.")


########################################################################################################################
## Convert byte string to hex string
########################################################################################################################

def hexStr(bytes):
    if isinstance(bytes, bytearray):
        return ' '.join(format(h, '02X') for h in bytes)
    if isinstance(bytes, int):
        return format(bytes, '02X')
    return ("No Byte (string)")


########################################################################################################################
## Class PhotonFile
########################################################################################################################

class PhotonFile:
    isDrawing = False # Navigation can call upon retrieving bitmaps frequently. This var prevents multiple almost parallel loads
    nrLayersString = "# Layers" #String is used in multiple locations and thus can be edited here

    # Data type constants
    tpByte = 0
    tpChar = 1
    tpInt = 2
    tpFloat = 3

    # Clipboard Vars to copy/cut and paste layer settinngs/imagedata
    clipboardDef  = None
    clipboardData = None

    # This is the data structure of photon file. For each variable we need to know
    #   Title string to display user, nr bytes to read/write, type of data stored, editable
    #   Each file consists of
    #     - General info                                            ( pfStruct_Header,      Header)
    #     - Two previews which contain meta-info an raw image data  ( pfStruct_Previews,    Previews)
    #     - For each layer meta-info                                ( pfStruct_LayerDefs,   LayerDefs)
    #     - For each layer raw image data                           ( pfStruct_LayerData,   LayerData)
    pfStruct_Header = [
        ("Header",              8, tpByte,  False, ""),
        ("Bed X (mm)",          4, tpFloat, True,  "Short side of the print bed."),
        ("Bed Y (mm)",          4, tpFloat, True,  "Long side of the print bed."),
        ("Bed Z (mm)",          4, tpFloat, True,  "Maximum height the printer can print."),
        ("padding0",        3 * 4, tpByte,  False, ""), # 3 ints
        ("Layer height (mm)",   4, tpFloat, True,  "Default layer height."),
        ("Exp. time (s)",       4, tpFloat, True,  "Default exposure time."),
        ("Exp. bottom (s)",     4, tpFloat, True,  "Exposure time for bottom layers."),
        ("Off time (s)",        4, tpFloat, True,  "Time UV is turned of between layers. \n Minimum is 6.5 sec, the time to rise the \n build plate and dip back in the resin."),
        ("# Bottom Layers",     4, tpInt,   True,  "Number of bottom layers.\n (These have different exposure time.)"),
        ("Resolution X",        4, tpInt,   True,  "X-Resolution of the screen through \n which the layer image is projected."),
        ("Resolution Y",        4, tpInt,   True,  "Y-Resolution of the screen through \n which the layer image is projected." ),
        ("Preview 0 (addr)",    4, tpInt,   False, "Address where the metadata \n of the High Res preview image can be found."),  # start of preview 0
        ("Layer Defs (addr)",   4, tpInt,   False, "Address where the metadata \n for the layer images can be found."),  # start of layerDefs
        (nrLayersString,        4, tpInt,   False, "Number of layers this file has."),
        ("Preview 1 (addr)",    4, tpInt,   False, "Address where the metadata of the \n Low Res preview image can be found."),  # start of preview 1
        ("unknown6",            4, tpInt,   False, ""),
        ("Proj.type-Cast/Mirror", 4, tpInt, False, "LightCuring/Projection type:\n 1=LCD_X_MIRROR \n 0=CAST"),   #LightCuring/Projection type // (1=LCD_X_MIRROR, 0=CAST)
        ("padding1",        6 * 4, tpByte,  False, "")  # 6 ints
    ]

    pfStruct_Previews = [
        ("Resolution X",        4, tpInt,   False, "X-Resolution of preview pictures."),
        ("Resolution Y",        4, tpInt,   False, "Y-Resolution of preview pictures."),
        ("Image Address",       4, tpInt,   False, "Address where the raw \n image can be found."),  # start of rawData0
        ("Data Length",         4, tpInt,   False, "Size (in bytes) of the \n raw image."),  # size of rawData0
        ("padding",         4 * 4, tpByte,  False, ""),  # 4 ints
        ("Image Data",         -1, tpByte,  False, "The raw image."),
    ]

    # The exposure time and off times are ignored by Photon printer, layerheight not and is cumulative
    pfStruct_LayerDef = [
        ("Layer height (mm)",   4, tpFloat, True,  "Height at which this layer \n should be printed."),
        ("Exp. time (s)",       4, tpFloat, False, "Exposure time for this layer.\n (Based on General Info.)"),
        ("Off time (s)",        4, tpFloat, False, "Off time for this layer.\n (Based on General Info.)"),
        ("Image Address",       4, tpInt,   False, "Address where the raw image \n can be found."),#dataStartPos -> Image Address
        ("Data Length",         4, tpInt,   False, "Size (in bytes) of the raw image."),  #size of rawData+lastByte(1)
        ("padding",         4 * 4, tpByte,  False, "") # 4 ints
    ]

    # pfStruct_LayerData =
    #    rawData  - rle encoded bytes except last one
    #    lastByte - last byte of encoded bitmap data

    Header = {}
    Previews = [{},{}]
    LayerDefs = []
    LayerData = []

    History=[]
    HistoryMaxDepth = 10


    ########################################################################################################################
    ## Methods to convert bytes (strings) to python variables and back again
    ########################################################################################################################

    @staticmethod
    def bytes_to_int(bytes):
        """ Converts list or array of bytes to an int. """
        result = 0
        for b in reversed(bytes):
            result = result * 256 + int(b)
        return result

    @staticmethod
    def bytes_to_float(inbytes):
        """ Converts list or array of bytes to an float. """
        bits = PhotonFile.bytes_to_int(inbytes)
        mantissa = ((bits & 8388607) / 8388608.0)
        exponent = (bits >> 23) & 255
        sign = 1.0 if bits >> 31 == 0 else -1.0
        if exponent != 0:
            mantissa += 1.0
        elif mantissa == 0.0:
            return sign * 0.0
        return sign * pow(2.0, exponent - 127) * mantissa

    @staticmethod
    def bytes_to_hex(bytes):
        """ Converts list or array of bytes to an hex. """
        return ' '.join(format(h, '02X') for h in bytes)

    @staticmethod
    def hex_to_bytes(hexStr):
        """ Converts hex to array of bytes. """
        return bytearray.fromhex(hexStr)

    @staticmethod
    def int_to_bytes(intVal):
        """ Converts POSITIVE int to bytes. """
        return intVal.to_bytes(4, byteorder='little')

    @staticmethod
    def float_to_bytes(floatVal):
        """ Converts POSITIVE floats to bytes.
            Based heavily upon http: //www.simplymodbus.ca/ieeefloats.xls
        """
        # Error when floatVal=0.5
        return struct.pack('f',floatVal)

        if floatVal == 0: return (0).to_bytes(4, byteorder='big')

        sign = -1 if floatVal < 0 else 1
        firstBit = 0 if sign == 1 else 1
        exponent = -127 if abs(floatVal) < 1.1754943E-38 else floor(log(abs(floatVal), 10) / log(2, 10))
        exponent127 = exponent + 127
        mantissa = floatVal / pow(2, exponent) / sign
        substract = mantissa - 1
        multiply = round(substract * 8388608)
        div256_1 = multiply / 256
        divint_1 = int(div256_1)
        rem_1 = int((div256_1 - divint_1) * 256)
        div256_2 = divint_1 / 256
        divint_2 = int(div256_2)
        rem_2 = int((div256_2 - divint_2) * 256)

        bin1 = (exponent127 & 0b11111110) >> 1 | firstBit << 7
        bin2 = (exponent127 & 0b00000001) << 7 | divint_2
        bin3 = rem_2
        bin4 = rem_1
        # print ("ALT: ",bin(bin1_new), bin(bin2_new),bin(bin3_new),bin(bin4_new))
        bin1234 = bin1 | bin2 << 8 | bin3 << 16 | bin4 << 24
        return bin1234.to_bytes(4, byteorder='big')

    @staticmethod
    def convBytes(bytes, bType):
        """ Converts all photonfile types to bytes. """
        nr = None
        if bType == PhotonFile.tpInt:
            nr = PhotonFile.bytes_to_int(bytes)
        if bType == PhotonFile.tpFloat:
            nr = PhotonFile.bytes_to_float(bytes)
        if bType == PhotonFile.tpByte:
            nr = PhotonFile.bytes_to_hex(bytes)
        return nr


    ########################################################################################################################
    ## History methods
    ########################################################################################################################


    def realDeepCopy(self,dictionary):
        return #probable not needed
        """ Makes a real copy of a dictionary consisting of bytes strings
        """
        hC = copy.deepcopy(self.Header)
        for key,byteString in dictionary.items():
            dictionary[key]=(byteString+b'\x00')[:-1] # Force to make a real copy


    def saveToHistory(self, action, layerNr):
        """ Makes a copy of current /Layer Data to memory
            Since all are bytearrays no Copy.Deepcopy is needed.
        """

        # Copy LayerDefs and LayerData
        layerDef=copy.deepcopy(self.LayerDefs[layerNr])
        layerData=copy.deepcopy(self.LayerData[layerNr])
        self.realDeepCopy(layerDef)
        self.realDeepCopy(layerData)

        # Append to history stack/array
        newH = {"Action":action,"LayerNr":layerNr,"LayerDef":layerDef,"LayerData":layerData}
        print("Stored:",newH,id(layerDef),id(layerData))
        self.History.append(newH)
        if len(self.History)>self.HistoryMaxDepth:
            self.History.remove(self.History[0])


    def loadFromHistory(self):
        """ Load a copy of current Header/Preview/Layer Data to memory
            We copy by reference and remove item from history stack.
        """

        if len(self.History)==0:
            raise Exception("You have reached the maximum depth to undo.")

        # Find last item added to History
        idxLastAdded=len(self.History)-1
        lastItemAdded=self.History[idxLastAdded]
        action=lastItemAdded["Action"]
        layerNr =lastItemAdded["LayerNr"]
        layerDef = lastItemAdded["LayerDef"]
        layerData = lastItemAdded["LayerData"]
        print("Found:", self.History[idxLastAdded])

        # Reverse the actions
        if action=="insert":
            self.deleteLayer(layerNr, saveToHistory=False)
        elif action=="delete":
            self.clipboardDef=layerDef
            self.clipboardData=layerData
            self.insertLayerBefore(layerNr,fromClipboard=True, saveToHistory=False)
        elif action=="replace":
            self.clipboardDef=layerDef
            self.clipboardData=layerData
            self.deleteLayer(layerNr)
            self.insertLayerBefore(layerNr,fromClipboard=True, saveToHistory=False)

        # Remove this item
        self.History.remove(lastItemAdded)

    #Make alias for loadFromHistory
    undo = loadFromHistory

    ########################################################################################################################
    ## Class methods
    ########################################################################################################################

    def __init__(self, photonfilename):
        """ Just stores photon filename. """
        self.filename = photonfilename


    def nrLayers(self):
        """ Returns 4 bytes for number of layers as int. """
        return  PhotonFile.bytes_to_int(self.Header[self.nrLayersString])


    def readFile(self):
        """ Reads the photofile from disk to memory. """

        with open(self.filename, "rb") as binary_file:

            # Start at beginning
            binary_file.seek(0)

            # Read HEADER / General settings
            for bTitle, bNr, bType, bEditable,bHint in self.pfStruct_Header:
                self.Header[bTitle] = binary_file.read(bNr)

            # Read PREVIEWS settings and raw image data
            for previewNr in (0,1):
                for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_Previews:
                    # if rawData0 or rawData1 the number bytes to read is given bij dataSize0 and dataSize1
                    if bTitle == "Image Data": bNr = dataSize
                    self.Previews[previewNr][bTitle] = binary_file.read(bNr)
                    if bTitle == "Data Length": dataSize = PhotonFile.bytes_to_int(self.Previews[previewNr][bTitle])

            # Read LAYERDEFS settings
            nLayers = PhotonFile.bytes_to_int(self.Header[self.nrLayersString])
            self.LayerDefs = [dict() for x in range(nLayers)]
            # print("nLayers:", nLayers)
            # print("  hex:", ' '.join(format(x, '02X') for x in self.Header[self.nrLayersString]))
            # print("  dec:", nLayers)
            # print("Reading layer meta-info")
            for lNr in range(0, nLayers):
                # print("  layer: ", lNr)
                for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_LayerDef:
                    self.LayerDefs[lNr][bTitle] = binary_file.read(bNr)

            # Read LAYERRAWDATA image data
            # print("Reading layer image-info")
            self.LayerData = [dict() for x in range(nLayers)]
            for lNr in range(0, nLayers):
                rawDataSize = PhotonFile.bytes_to_int(self.LayerDefs[lNr]["Data Length"])
                # print("  layer: ", lNr, " size: ",rawDataSize)
                self.LayerData[lNr]["Raw"] = binary_file.read(rawDataSize - 1) # b'}}}}}}}}}}
                # -1 because we don count byte for endOfLayer
                self.LayerData[lNr]["EndOfLayer"] = binary_file.read(1)

            # print (' '.join(format(x, '02X') for x in header))

            # Clear History for this new file
            self.History = []


    def writeFile(self, newfilename=None):
        """ Writes the photofile from memory to disk. """

        # Check if other filename is given to save to, otherwise use filename used to load file.
        if newfilename == None: newfilename = self.filename


        with open(newfilename, "wb") as binary_file:

            # Start at beginning
            binary_file.seek(0)

            # Write HEADER / General settings
            for bTitle, bNr, bType, bEditable,bHint in self.pfStruct_Header:
                binary_file.write(self.Header[bTitle])

            # Write PREVIEWS settings and raw image data
            for previewNr in (0, 1):
                for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_Previews:
                    #print ("Save: ",bTitle)
                    binary_file.write(self.Previews[previewNr][bTitle])

            # Read LAYERDEFS settings
            nLayers = PhotonFile.bytes_to_int(self.Header[self.nrLayersString])
            for lNr in range(0, nLayers):
                #print("  layer: ", lNr)
                #print("    def: ", self.LayerDefs[lNr])
                for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_LayerDef:
                    binary_file.write(self.LayerDefs[lNr][bTitle])

            # Read LAYERRAWDATA image data
            # print("Reading layer image-info")
            for lNr in range(0, nLayers):
                binary_file.write(self.LayerData[lNr]["Raw"])
                binary_file.write(self.LayerData[lNr]["EndOfLayer"])


    ########################################################################################################################
    ## Encoding
    ########################################################################################################################
    def encodedBitmap_Bytes_withnumpy(image):
        """ Converts image (filename/pygame.surface/numpy.array2d) to RLE encoded byte string.
            Uses Numpy library - Fast
            Based on https://gist.github.com/itdaniher/3f57be9f95fce8daaa5a56e44dd13de5
            Encoding scheme:
                Highest bit of each byte is color (black or white)
                Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        """
        imgarr=None

        # Check if we got a string and if so load image
        #if isinstance(image, str): # received name of file to load
        #    imgsurf = pygame.image.load(image)
        #    (width, height) = imgsurf.get_size()
        #elif isinstance(image,pygame.Surface):
        #    imgsurf = image  # reveived pygame.surface
        #    (width, height) = imgsurf.get_size()
        #el
        if isinstance(image, (numpy.ndarray, numpy.generic)): # received opencv / numpy image array
            #print ("shape",image.shape)
            (width, height)=image.shape
            imgarr=image
        else:
            raise Exception("Only image filename, pygame.Surface or numpy.array (2D) are excepted")

        # Check if size is correct size (1440 x 2560)
        if not (width, height) == (1440, 2560):
            raise Exception("Your image dimensions are off and should be 1440x2560")

        #t0=time.time()

        # Convert image data to Numpy 1-dimensional array
        #if not isinstance(image, (numpy.ndarray, numpy.generic)): # Not needed if we got an numpy array as input
        #    imgarr = pygame.surfarray.array2d(imgsurf)

        #t1 = time.time()

        # Rotate,flip image and flatten array
        imgarr = numpy.rot90(imgarr,axes=(1,0))
        imgarr = numpy.fliplr(imgarr)  # reverse/mirror array
        x = numpy.asarray(imgarr).flatten(0)

        #t2 = time.time()
        #print ("rotate/flip/flatten:",(t2-t1))

        # Encoding magic
        where = numpy.flatnonzero
        x = numpy.asarray(x)
        n = len(x)
        if n == 0:
            return numpy.array([], dtype=numpy.int)
        starts = numpy.r_[0, where(~numpy.isclose(x[1:], x[:-1], equal_nan=True)) + 1]
        lengths = numpy.diff(numpy.r_[starts, n])
        values = x[starts]
        #ret=np.dstack((lengths, values))[0]

        #t3 = time.time()
        #print ("encoding magic:",(t3-t2))

        # Reduce repetitions of color to max 0x7D/125 and store in bytearray
        rleData = bytearray()
        for (nr, col) in zip(lengths,values):
            #color = (abs(col)>1) # slow
            color=1 if col else 0 # fast
            while nr > 0x7D:
                encValue = (color << 7) | 0x7D
                rleData.append(encValue)
                nr = nr - 0x7D
            encValue = (color << 7) | nr
            rleData.append(encValue)

        #t4 = time.time()
        #print ("max rep 0x7D:",(t4-t3))
        #quit()

        # Needed is an byte string, so convert
        return bytes(rleData)


    def encodedBitmap_Bytes_nonumpy(surfOrFile):
        """ Converts image data from file on disk to RLE encoded byte string.
            Processes pixels one at a time (pygame.get_at) - Slow
            Encoding scheme:
                Highest bit of each byte is color (black or white)
                Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        """

        # Check if we got a string and if so load image
        if isinstance(surfOrFile, str):
            imgsurf = pygame.image.load(surfOrFile)
        else:
            imgsurf = surfOrFile

        # Check if size is correct size (1440 x 2560)
        #bitDepth = imgsurf.get_bitsize()
        #bytePerPixel = imgsurf.get_bytesize()
        (width, height) = imgsurf.get_size()
        if not (width, height) == (1440,2560):
            raise Exception("Your image dimensions are off and should be 1440x2560")

        # Count number of pixels with same color up until 0x7D/125 repetitions
        rleData = bytearray()
        color = 0
        black = 0
        white = 1
        nrOfColor = 0
        prevColor=None
        for y in range(height):
            for x in range(width):
                # print (imgsurf.get_at((x, y)))
                (r, g, b, a) = imgsurf.get_at((x, y))
                if ((r + g + b) // 3) < 128:
                    color = black
                else:
                    color = white
                if prevColor == None: prevColor = color
                isLastPixel = (x == (width - 1) and y == (height - 1))
                if color == prevColor and nrOfColor < 0x7D and not isLastPixel:
                    nrOfColor = nrOfColor + 1
                else:
                    #print (color,nrOfColor,nrOfColor<<1)
                    encValue = (prevColor << 7) | nrOfColor # push color (B/W) to highest bit and repetitions to lowest 7 bits.
                    rleData.append(encValue)
                    prevColor = color
                    nrOfColor = 1
        return bytes(rleData)


    def encodedBitmap_Bytes(surfOrFile):
        """ Depening on availability of Numpy, calls upon correct Encoding method."""
        if numpyAvailable:
            return PhotonFile.encodedBitmap_Bytes_withnumpy(surfOrFile)
        else:
            return PhotonFile.encodedBitmap_Bytes_nonumpy(surfOrFile)


    def encodedPreviewBitmap_Bytes_nonumpy(filename,checkSizeForNr=0):
        """ Converts image data from file on disk to RLE encoded byte string.
            Processes pixels one at a time (pygame.get_at) - Slow
            Encoding scheme:
                The color (R,G,B) of a pixel spans 2 bytes (little endian) and each color component is 5 bits: RRRRR GGG GG X BBBBB
                If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
        """

        imgsurf = pygame.image.load(filename)
        # bitDepth = imgsurf.get_bitsize()
        # bytePerPixel = imgsurf.get_bytesize()
        (width, height) = imgsurf.get_size()
        print ("Size:", width, height)

        #Preview images tend to have different sizes. Check on size is thus not possible.
        #if checkSizeForNr==0 and not (width, height) == (360,186):
        #    raise Exception("Your image dimensions are off and should be 360x186 for the 1st preview.")
        #if checkSizeForNr==1 and not (width, height) == (198,101):
        #    raise Exception("Your image dimensions are off and should be 198x101 for the 1st preview.")

        # Count number of pixels with same color up until 0x7D/125 repetitions
        rleData = bytearray()
        color = 0
        black = 0
        white = 1
        nrOfColor = 0
        prevColor = None
        for y in range(height):
            for x in range(width):
                #print (x,y)
                # print (imgsurf.get_at((x, y)))
                color = imgsurf.get_at((x, y)) # (r, g, b, a)
                if prevColor == None: prevColor = color
                isLastPixel = (x == (width - 1) and y == (height - 1))
                if color == prevColor and nrOfColor < 0x0FFF and not isLastPixel:
                    nrOfColor = nrOfColor + 1
                else:
                    # print (color,nrOfColor,nrOfColor<<1)
                    R=prevColor[0]
                    G=prevColor[1]
                    B=prevColor[2]
                    if nrOfColor>1:
                        X=1
                    else:
                        X=0
                    # build 2 or 4 bytes (depending on X
                    # The color (R,G,B) of a pixel spans 2 bytes (little endian) and
                    # each color component is 5 bits: RRRRR GGG GG X BBBBB
                    R = round(R / 255 * 31)
                    G = round(G / 255 * 31)
                    B = round(B / 255 * 31)
                    encValue0=R<<3 | G>>2
                    encValue1=(((G & 0b00000011)<<6) | X<<5 | B)
                    if X==1:
                        nrOfColor=nrOfColor-1 # write one less than nr of pixels
                        encValue2=nrOfColor>>8
                        encValue3=nrOfColor & 0b000000011111111
                        #seems like nr bytes pixels have 0011 as start
                        encValue2=encValue2 | 0b00110000

                    # save bytes
                    rleData.append(encValue1)
                    rleData.append(encValue0)
                    if X==1:
                        rleData.append(encValue3)
                        rleData.append(encValue2)

                    # search next color
                    prevColor = color
                    nrOfColor = 1
        #print ("len",len(rleData))
        return (width,height,bytes(rleData))


    ########################################################################################################################
    ## Decoding
    ########################################################################################################################
    def getBitmap_withnumpy(self, layerNr, forecolor=(128,255,128), backcolor=(0,0,0),scale=(0.25,0.25),retNumpyArray=False):
        """ Decodes a RLE byte array from PhotonFile object to a pygame surface.
            Based on: https://gist.github.com/itdaniher/3f57be9f95fce8daaa5a56e44dd13de5
            Encoding scheme:
                Highest bit of each byte is color (black or white)
                Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        """
        #tStart=pygame.time.get_ticks()

        # Colors are stored reversed and we count on alpha bit (size of int does not matter for numpy speed)
        isAlpha=False
        if   len(forecolor) == 4 or len(backcolor) == 4: isAlpha = True
        if   len(forecolor) == 3:forecolor = (255,forecolor[0], forecolor[1], forecolor[2])
        elif len(forecolor) == 4:forecolor = (forecolor[3], forecolor[0], forecolor[1],forecolor[2])
        if   len(backcolor) == 3:backcolor = (255,backcolor[0], backcolor[1], backcolor[2])
        elif len(backcolor) == 4:backcolor=(backcolor[3], backcolor[0], backcolor[1],backcolor[2])

        # If no layers return
        if self.nrLayers()==0:#could occur if loading new file
            memory=pygame.Surface((int(1440 * scale[0]), int(2560 * scale[1])),24)
            return memory

        # Tell PhotonFile we are drawing so GUI can prevent too many calls on getBitmap
        self.isDrawing = True

        # Retrieve raw image data and add last byte to complete the byte array
        bA = self.LayerData[layerNr]["Raw"]
        # add endOfLayer Byte
        bA = bA + self.LayerData[layerNr]["EndOfLayer"]

        # Convert bytes to numpy 1 dimensional array
        bN =numpy.fromstring(bA,dtype=numpy.uint8)


        # Extract color value (highest bit) and nr of repetitions (lowest 7 bits)
        valbin = bN >> 7  # only read 1st bit
        nr = bN & ~(1 << 7)  # turn highest bit of

        # Replace 0's en 1's with correct colors
        forecolor_int = (forecolor[0] << 24) + (forecolor[1] << 16) + (forecolor[2] << 8) + forecolor[3]
        backcolor_int = (backcolor[0] << 24) + (backcolor[1] << 16) + (backcolor[2] << 8) + backcolor[3]
        val = numpy.array([{0: backcolor_int, 1: forecolor_int}[x] for x in valbin])

        # Make a 2d array like [ [3,0] [2,1], [nr_i,val_i]...] using the colorvalues (val) and repetitions(nr)
        runs = numpy.column_stack((nr, val))

        # Decoding magic
        runs_t = numpy.transpose(runs)
        lengths = runs_t[0].astype(int)
        values = runs_t[1].astype(int)
        starts = numpy.concatenate(([0], numpy.cumsum(lengths)[:-1]))
        starts, lengths, values = map(numpy.asarray, (starts, lengths, values))
        ends = starts + lengths
        n = ends[-1]
        x = numpy.full(n, 0)
        for lo, hi, val in zip(starts, ends, values):
            x[lo:hi] = val

        # Make sure we have a bitmap of the correct size and if not pad with black pixels
        if not len(x) == 3686400: print ("Warning: The file decoded with less bytes than needed. Will pad the file with zero bytes.")
        while not len(x)==3686400:
            x=numpy.append(x,(0,))

        # Convert 1-dim array to matrix
        rgb2d = x.reshape((2560,1440))              # data is stored in rows of 2560
        if retNumpyArray:return rgb2d               # if numpy array is returned, rotation not needed
        rgb2d = numpy.rot90(rgb2d, axes=(1, 0))     # we need 1440x2560
        rgb2d = numpy.fliplr(rgb2d)                 # however data is mirrored along x axis

        #picture=pygame.surfarray.make_surface(rgb2d)# convert numpy array to pygame surface
        #memory=pygame.transform.scale(picture, (int(1440*scale[0]), int(2560*scale[1]))) # rescale for display in window
        if isAlpha:
            temp = pygame.Surface((1440, 2560), depth=32,flags=pygame.SRCALPHA)
        else:
            temp = pygame.Surface((1440, 2560), depth=24)
        pygame.surfarray.blit_array(temp,rgb2d)
        memory=pygame.transform.scale(temp, (int(1440*scale[0]), int(2560*scale[1]))) # rescale for display in window
        # Done drawing so next caller knows that next call can be made.
        self.isDrawing = False

        #tDelta = pygame.time.get_ticks()-tStart
        #print ("elaps:",tDelta)
        return memory


    def getBitmap_nonumpy(self, layerNr, forecolor=(128,255,128), backcolor=(0,0,0),scale=(0.25,0.25)):
        """ Decodes a RLE byte array from PhotonFile object to a pygame surface.
            Based on: https://gist.github.com/itdaniher/3f57be9f95fce8daaa5a56e44dd13de5
            Encoding scheme:
                Highest bit of each byte is color (black or white)
                Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        """

        # Tell PhotonFile we are drawing so GUI can prevent too many calls on getBitmap
        memory = pygame.Surface((int(1440 * scale[0]), int(2560 * scale[1])))
        if self.nrLayers()==0: return memory #could occur if loading new file
        self.isDrawing = True

        # Retrieve raw image data and add last byte to complete the byte array
        bA = self.LayerData[layerNr]["Raw"]
        # add endOfLayer Byte
        bA = bA + self.LayerData[layerNr]["EndOfLayer"]

        # Decode bytes to colors and draw lines of that color on the pygame surface
        x = 0
        y = 0
        for idx, b in enumerate(bA):
            # From each byte retrieve color (highest bit) and number of pixels of that color (lowest 7 bits)
            nr = b & ~(1 << 7)  # turn highest bit of
            val = b >> 7  # only read 1st bit

            # The surface to draw on is smaller (scale) than the file (1440x2560 pixels)
            x1 = int(x *scale[0])
            y1 = int(y *scale[1])
            x2 = int((x + nr) *scale[0])
            y2 = y1
            if val==0:
                col= backcolor
            else:
                col=forecolor
            # Bytes and repetions of pixels with same color can span muliple lines (y-values)
            if x2 > int(1440 *scale[0]): x2 = int(1440 *scale[1])
            pygame.draw.line(memory, col, (x1, y1), (x2, y2))
            # debug nr2=nr-(x+nr-1440) if (x+nr)>=1440 else nr
            # debug print("draw line: ", x, y, " - ", nr2)
            x = x + nr
            if x >= 1440:
                nr = x - 1440
                x = 0
                y = y + 1
                x1 = int(x *scale[0])
                y1 = int(y *scale[1])
                x2 = int((x + nr) *scale[0])
                y2 = y1
                pygame.draw.line(memory, col, (x1, y1), (x2, y2))
                # debug print ("draw line: ",x,y," - ",nr)
                x = x + nr
        #print("Screen Drawn")
        # debug print ("layer: ", layerNr)
        # debug print ("lastByte:", self.LayerData[layerNr]["EndOfLayer"])

        # Done drawing so next caller knows that next call can be made.
        self.isDrawing = False
        return memory


    def getBitmap(self, layerNr, forecolor=(128, 255, 128), backcolor=(0, 0, 0), scale=(1, 1)):
        """ Depending on availability of Numpy, calls upon correct Decoding method."""
        if numpyAvailable:
            return self.getBitmap_withnumpy(layerNr,forecolor,backcolor,scale)
        else:
            return self.getBitmap_nonumpy(layerNr,forecolor,backcolor,scale)

    def volume(self,progressDialog=None):
        nLayers=self.nrLayers()
        nrPixels=0
        #numpyAvailable=False
        for layerNr in range(0,nLayers):
            img=self.getBitmap(layerNr,forecolor=(255,255,255,255),backcolor=(0,0,0,0),scale=(1,1))
            pixarray = pygame.surfarray.pixels2d(img)
            pixelsInLayer=0

            if numpyAvailable:
                pixelsInLayer=((pixarray>0).sum())
            else:
                for row in pixarray:
                    for color in row:
                        if color>0:pixelsInLayer+=1

            nrPixels=nrPixels+pixelsInLayer

            # Check if user canceled
            if not progressDialog==None:
                progressDialog.setProgress(100*layerNr/nLayers)
                progressDialog.setProgressLabel(str(layerNr)+"/"+str(nLayers))
                progressDialog.handleEvents()
                if progressDialog.cancel: return False

        #pixel is 0.047mm x 0.047mm x layer height
        print (nrPixels)
        pixVolume=0.047*0.047*self.bytes_to_float(self.Header["Layer height (mm)"])
        volume=pixVolume*nrPixels
        return volume


    def getPreviewBitmap(self, prevNr, scaleToWidth=1440/4):
        """ Decodes a RLE byte array from PhotonFile object to a pygame surface.
            Based on https://github.com/Reonarudo/pcb2photon/issues/2
            Encoding scheme:
                The color (R,G,B) of a pixel spans 2 bytes (little endian) and each color component is 5 bits: RRRRR GGG GG X BBBBB
                If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
        """

        # Tell PhotonFile we are drawing so GUI can prevent too many calls on getBitmap
        self.isDrawing = True

        # Retrieve resolution of preview image and set pygame surface to that size.
        w = PhotonFile.bytes_to_int(self.Previews[prevNr]["Resolution X"])
        h = PhotonFile.bytes_to_int(self.Previews[prevNr]["Resolution Y"])
        s = PhotonFile.bytes_to_int(self.Previews[prevNr]["Data Length"])

        if scaleToWidth==0:
            scale=(1,1)
        else:
            scale = (scaleToWidth / w, scaleToWidth / w)

        memory = pygame.Surface((int(w), int(h)))
        if w == 0 or h == 0: return memory # if size is (0,0) we return empty surface

        # Retrieve raw image data and add last byte to complete the byte array
        bA = self.Previews[prevNr]["Image Data"]

        # Decode bytes to colors and draw lines of that color on the pygame surface
        idx = 0
        pixelIdx = 0
        while idx < len(bA):
            # Combine 2 bytes Little Endian so we get RRRRR GGG GG X BBBBB (and advance read byte counter)
            b12 = bA[idx + 1] << 8 | bA[idx + 0]
            idx += 2
            # Retrieve colr components and make pygame color tuple
            #red = round(((b12 >> 11) & 0x1F) / 31 * 255)
            red = round(((b12 >> 11) & 0x1F) << 3 )
            #green = round(((b12 >> 6) & 0x1F) / 31 * 255)
            green = round(((b12 >> 6) & 0x1F) << 3 )
            #blue = round(((b12 >> 0) & 0x1F) / 31 * 255)
            blue = round((b12 & 0x1F) << 3 )
            col = (red, green, blue)

            # If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
            nr = 1
            if b12 & 0x20:
                nr12 = bA[idx + 1] << 8 | bA[idx + 0]
                idx += 2
                nr += nr12 & 0x0FFF

            # Draw (nr) many pixels of the color
            for i in range(0, nr, 1):
                x = int((pixelIdx % w))
                y = int((pixelIdx / w))
                memory.set_at((x, y), col)
                pixelIdx += 1

        # Scale the surface to the wanted resolution
        memory = pygame.transform.scale(memory, (int(w * scale[0]), int(h * scale[1])))

        # Done drawing so next caller knows that next call can be made.
        self.isDrawing = False
        return memory


    ########################################################################################################################
    ## Layer (Image) Operations
    ########################################################################################################################

    def layerHeight(self,layerNr):
        """ Return height between two layers
        """
        # We retrieve layer height from previous layer
        if layerNr>0:
            curLayerHeight = self.bytes_to_float(self.LayerDefs[layerNr]["Layer height (mm)"])
            prevLayerHeight = self.bytes_to_float(self.LayerDefs[layerNr-1]["Layer height (mm)"])
        else:
            if self.nrLayers()>1:
                curLayerHeight = self.bytes_to_float(self.LayerDefs[layerNr+1]["Layer height (mm)"])
                prevLayerHeight=0
            else:
                curLayerHeight=self.bytes_to_float(self.Header["Layer height (mm)"])
                prevLayerHeight = 0
        return curLayerHeight-prevLayerHeight
        #print ("Delta:", deltaHeight)


    def deleteLayer(self, layerNr, saveToHistory=True):
        """ Deletes layer and its image data in the PhotonFile object, but store in clipboard for paste. """

        # Store all data to history
        if saveToHistory: self.saveToHistory("delete",layerNr)

        #deltaHeight=self.bytes_to_float(self.LayerDefs[layerNr]["Layer height (mm)"])
        deltaHeight =self.layerHeight(layerNr)
        print ("deltaHeight:",deltaHeight)

        # Update start addresses of RawData of before deletion with size of one extra layerdef (36 bytes)
        for rLayerNr in range(0,layerNr):
            # Adjust image address for removal of image raw data and end byte
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr-36 # size of layerdef
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)

        # Update start addresses of RawData of after deletion with size of image and layerdef
        deltaLength = self.bytes_to_int(self.LayerDefs[layerNr]["Data Length"]) + 36  # +1 for len(EndOfLayer)
        nLayers=self.nrLayers()
        for rLayerNr in range(layerNr+1,nLayers):
            # Adjust image address for removal of image raw data and end byte
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr-deltaLength
            #print ("layer, cur, new: ",rLayerNr,curAddr,newAddr)
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)

            # Adjust layer starting height for removal of layer
            curHeight=self.bytes_to_float(self.LayerDefs[rLayerNr]["Layer height (mm)"])
            newHeight=curHeight-deltaHeight
            self.LayerDefs[rLayerNr]["Layer height (mm)"] =self.float_to_bytes(newHeight)

        # Store deleted layer in clipboard
        self.clipboardDef=self.LayerDefs[layerNr].copy()
        self.clipboardData=self.LayerData[layerNr].copy()

        # Delete layer settings and data and reduce number of layers in header
        self.LayerDefs.remove(self.LayerDefs[layerNr])
        self.LayerData.remove(self.LayerData[layerNr])
        self.Header[self.nrLayersString]=self.int_to_bytes(self.nrLayers()-1)

    def insertLayerBefore(self, layerNr, fromClipboard=False, saveToHistory=True):
        """ Inserts layer copying data of the previous layer or the clipboard. """
        if fromClipboard and self.clipboardDef==None: raise Exception("Clipboard is empty!")

        # Store all data to history
        if saveToHistory: self.saveToHistory("insert",layerNr)

        # Check if layerNr in range, could occur on undo after deleting last layer
        #   print(layerNr, "/", self.nrLayers())
        insertLast=False
        if layerNr>self.nrLayers(): layerNr=self.nrLayers()
        if layerNr == self.nrLayers():
            layerNr=layerNr-1 # temporary reduce layerNr
            insertLast=True

        # Check deltaHeight
        deltaHeight = self.layerHeight(layerNr)

        # Make duplicate of layerDef and layerData if not pasting from clipboard
        if fromClipboard == False:
            self.clipboardDef=self.LayerDefs[layerNr].copy()
            self.clipboardData=self.LayerData[layerNr].copy()

        # Set layerheight correctly
        if layerNr==0: # if first layer than the height should start at 0
            self.clipboardDef["Layer height (mm)"] = self.float_to_bytes(0)
        else:          # start at layer height of layer at which we insert
            curLayerHeight = self.bytes_to_float(self.LayerDefs[layerNr]["Layer height (mm)"])
            self.clipboardDef["Layer height (mm)"]=self.float_to_bytes(curLayerHeight)

        # Set start addresses of layer in clipboard, we add 1 layer(def) so add 36 bytes
        lA=self.bytes_to_int(self.LayerDefs[layerNr]["Image Address"])+36
        #   if lastlayer we need to add last image length
        if insertLast: lA=lA+self.bytes_to_int(self.LayerDefs[layerNr]["Data Length"])
        self.clipboardDef["Image Address"]=self.int_to_bytes(lA)

        # If we inserting last layer, we correct layerNr
        if insertLast: layerNr = layerNr + 1  # fix temporary reduced layerNr

        # Update start addresses of RawData of before insertion with size of one extra layerdef (36 bytes)
        for rLayerNr in range(0,layerNr):
            # Adjust image address for removal of image raw data and end byte
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr+36 # size of layerdef
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)

        # Update start addresses of RawData of after insertion with size of image and layerdef
        #   Calculate how much room we need in between. We insert an extra layerdef (36 bytes) and a extra image
        deltaLayerImgAddress = self.bytes_to_int(self.clipboardDef["Data Length"]) + 36
        nLayers=self.nrLayers()
        #   remove
        for rLayerNr in range(layerNr,nLayers):
            # Adjust image address for removal of image raw data and end byte
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr+deltaLayerImgAddress
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)

            # Adjust layer starting height for removal of layer
            curHeight=self.bytes_to_float(self.LayerDefs[rLayerNr]["Layer height (mm)"])
            newHeight=curHeight+deltaHeight
            self.LayerDefs[rLayerNr]["Layer height (mm)"] =self.float_to_bytes(newHeight)
            #print ("layer, cur, new: ",rLayerNr,curAddr,newAddr, "|", curHeight,newHeight ,">",self.bytes_to_float(self.LayerDefs[rLayerNr]["Layer height (mm)"]))

        # Insert layer settings and data and reduce number of layers in header
        self.LayerDefs.insert(layerNr, self.clipboardDef)
        self.LayerData.insert(layerNr, self.clipboardData)

        self.Header[self.nrLayersString]=self.int_to_bytes(self.nrLayers()+1)

        # Make new copy so second paste will not reference this inserted objects
        self.clipboardDef = self.LayerDefs[layerNr].copy()
        self.clipboardData = self.LayerData[layerNr].copy()


    def copyLayer(self,layerNr):
        # Make duplicate of layerDef and layerData
        self.clipboardDef=self.LayerDefs[layerNr].copy()
        self.clipboardData=self.LayerData[layerNr].copy()



    def replaceBitmap(self, layerNr,filePath, saveToHistory=True):
        """ Replace image data in PhotonFile object with new (encoded data of) image on disk."""

        print("  ", layerNr, "/", filePath)

        # Store all data to history
        if saveToHistory: self.saveToHistory("replace",layerNr)

        # Get/encode raw data
        rawData = PhotonFile.encodedBitmap_Bytes(filePath)

        # Last byte is stored seperately
        rawDataTrunc = rawData[:-1]
        rawDataLastByte = rawData[-1:]

        # Get change in image rawData size so we can correct starting addresses of higher layer images
        oldLength=self.bytes_to_int(self.LayerDefs[layerNr]["Data Length"]) #"Data Length" = len(rawData)+len(EndOfLayer)
        newLength=len(rawData)
        deltaLength=newLength-oldLength
        #print ("old, new, delta:",oldLength,newLength,deltaLength)

        # Update image settings and raw data of layer to be replaced
        self.LayerDefs[layerNr]["Data Length"] = self.int_to_bytes(len(rawData))
        self.LayerData[layerNr]["Raw"] = rawDataTrunc
        self.LayerData[layerNr]["EndOfLayer"] = rawDataLastByte

        # Update start addresses of RawData of all following images
        nLayers=self.nrLayers()
        for rLayerNr in range(layerNr+1,nLayers):
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr+deltaLength
            #print ("layer, cur, new: ",rLayerNr,curAddr,newAddr)
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)


    cancelReplace=False
    def par_encodedBitmap_Bytes(self,layerNr,filename):
        # Helper for procespoolexecutor in replaceBitmaps to call 
        if self.cancelReplace: return None
        return [layerNr,PhotonFile.encodedBitmap_Bytes(surfOrFile=filename)]

    def replaceBitmaps(self, bitmaps, progressDialog=None):
        """ Delete all images in PhotonFile object and add images in directory."""

        # Check if bitmaps is a string with dirpath
        rlestack=None
        if isinstance(bitmaps, list):
            rlestack = bitmaps
            #print ("replaceBitmap - got image data")
        elif isinstance(bitmaps,str):
            dirPath=bitmaps
            #print("replaceBitmap - got image directory")
        else:
            raise Exception("replaceBitmaps excepts a directorypath string or an array of rle encoded slices.")

        # If bitmaps was directory string we need to encode all files in directory
        if isinstance(bitmaps,str):
            # Get all files, filter png-files and sort them alphabetically
            direntries = os.listdir(dirPath)
            files = []
            for entry in direntries:
                fullpath = os.path.join(dirPath, entry)
                if entry.endswith("png"):
                    if not entry.startswith("_"): # on a export of images from a photon file, the preview image starts with _
                        files.append(fullpath)
            files.sort()

            # Check if there are files available and if so check first file for correct dimensions
            if len(files) == 0: raise Exception("No files of type png are found!")

            # Read all files in parallel and wait for result
            res=[]
            nLayers=len(files)
            rlestack = nLayers * [None]
            self.cancelReplace=False
            tstart=time.time()
            with concurrent.futures.ProcessPoolExecutor() as executor: # In this case ProcessPoolExecutor is 2.5 x faster then ThreadPoolExecutor
                # Submit all jobs to ProcessPoolExecutor
                for layerNr,filename in enumerate(files):
                    job = executor.submit(self.par_encodedBitmap_Bytes, layerNr=layerNr, filename=filename)
                    res.append(job)
                    if not progressDialog==None:
                        perc = 50 * layerNr / nLayers
                        if perc > 50: perc = 50
                        progressDialog.setProgress(perc)
                        #progressDialog.setProgressLabel(str(layerNr) + "/" + str(nLayers))
                        progressDialog.handleEvents()
                        if progressDialog.cancel:
                            #  Reset total number of layers to last layer we processes
                            self.cancelReplace=True
                            print ("Abort.")
                            return

                # Handle all results as they come available
                nrLayersDone = 0
                for ret in concurrent.futures.as_completed(res):
                    layerNr,rawData=ret.result()
                    rlestack[layerNr] = rawData
                    nrLayersDone+=1
                    if not progressDialog==None:
                        perc = 50+50 * nrLayersDone / nLayers
                        if perc > 100: perc = 100
                        progressDialog.setProgress(perc)
                        #progressDialog.setProgressLabel(str(nrLayersDone) + "/" + str(nLayers))
                        progressDialog.handleEvents()
                        if progressDialog.cancel:
                            #  Reset total number of layers to last layer we processes
                            self.cancelReplace=True
                            print ("Abort.")
                            return
            print ("Import images in %0.2f msec." % (int(1000*(time.time()-tstart))))

        # Remove old data in PhotonFile object
        nLayers = len(rlestack)
        self.LayerData = [dict() for x in range(nLayers)] # make room for all images

        # Put rlestack in LayerData
        nrL=0
        for layerNr,rawData in enumerate(rlestack):
            if not rawData == None:
                rawDataTrunc = rawData[:-1]
                rawDataLastByte = rawData[-1:]
                self.LayerData[layerNr]["Raw"] = rawDataTrunc
                self.LayerData[layerNr]["EndOfLayer"] = rawDataLastByte
                nrL+=1

        # Resize depending on number of layers imported (abort could have deminished nr of layers)
        nLayers=nrL # if cancel this nr can differ from nr of images
        self.Header[self.nrLayersString] = self.int_to_bytes(nLayers)
        self.LayerDefs = [dict() for x in range(nLayers)]
        self.LayerData = self.LayerData[:nLayers]

        # Depending on nr of new images, set nr of bottom layers and total layers in Header
        #   If only one image is supplied the file should be set as 0 base layers and 1 normal layer
        if nLayers == 1:
            self.Header["# Bottom Layers"] = self.int_to_bytes(0)
        #   We can't have more bottom layers than total nr of layers
        nrBottomLayers=self.bytes_to_int(self.Header["# Bottom Layers"])
        if nrBottomLayers>nLayers: nrBottomLayers=nLayers-1
        self.Header["# Bottom Layers"] = self.int_to_bytes(nrBottomLayers)
        #   Set total number of layers
        self.Header["# Layers"] = self.int_to_bytes(nLayers)

        # Calculate the start position of raw imagedata of the FIRST layer
        rawDataStartPos = 0
        for bTitle, bNr, bType, bEditable,bHint in self.pfStruct_Header:
            rawDataStartPos = rawDataStartPos + bNr
        for previewNr in (0,1):
            for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_Previews:
                if bTitle == "Image Data": bNr = dataSize
                rawDataStartPos = rawDataStartPos + bNr
                if bTitle == "Data Length": dataSize = PhotonFile.bytes_to_int(self.Previews[previewNr][bTitle])
        for bTitle, bNr, bType, bEditable, bHint in self.pfStruct_LayerDef:
            rawDataStartPos = rawDataStartPos + bNr * nLayers

        # For each layer copying layer settings from Header/General settings.
        deltaLayerHeight=self.bytes_to_float(self.Header["Layer height (mm)"])
        #print("Processing:")
        for layerNr in range(nLayers):
            #print("  ", layerNr,"/",nLayers, file)
            # Get rawdata to determine size
            rawDataTrunc = self.LayerData[layerNr]["Raw"]
            rawDataLastByte = self.LayerData[layerNr]["EndOfLayer"]
            rawDataLen=len(rawDataTrunc)+len(rawDataLastByte)

            # Update layer settings (LayerDef)
            # todo: following should be better coded
            curLayerHeight = layerNr * deltaLayerHeight
            self.LayerDefs[layerNr]["Layer height (mm)"] = self.float_to_bytes(curLayerHeight)
            if layerNr<nrBottomLayers:
                self.LayerDefs[layerNr]["Exp. time (s)"] = self.Header["Exp. bottom (s)"]
            else:
                self.LayerDefs[layerNr]["Exp. time (s)"] = self.Header["Exp. time (s)"]
            self.LayerDefs[layerNr]["Off time (s)"] = self.Header["Off time (s)"]
            self.LayerDefs[layerNr]["Image Address"] = self.int_to_bytes(rawDataStartPos)
            self.LayerDefs[layerNr]["Data Length"] = self.int_to_bytes(rawDataLen)
            self.LayerDefs[layerNr]["padding"] = self.hex_to_bytes("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00") # 4 *4bytes

            # Keep track of address of raw imagedata
            #print ("Layer, DataPos, DataLength ",layerNr,rawDataStartPos,len(rawData))

            # Get encoded raw data
            rawDataStartPos = rawDataStartPos + rawDataLen
            #print("New DataPos", rawDataStartPos)

        return True


    def exportBitmap(self,dirPath,filepre,layerNr):
        """ Saves specified images in PhotonFile object as (decoded) png files in specified directory and with file precursor"""

        # Make filename
        nrStr="%04d" % layerNr
        filename=filepre+"_"+ nrStr+".png"
        #print ("filename: ",filename)
        fullfilename=os.path.join(dirPath,filename)
        # Retrieve decode pygame image surface
        imgSurf=self.getBitmap(layerNr, (255, 255, 255), (0, 0, 0), (1, 1))
        # Save layer image to disk
        pygame.image.save(imgSurf,fullfilename)

        print ("Exported slice ",layerNr)
        # Check if user canceled

        return


    def exportPreviewBitmap(self, dirPath, previewNr):
        """ Saves specified preview image in PhotonFile object as (decoded) png files in specified directory and with file precursor"""

        #   Make filename beginning with _ so PhotonFile.importBitmaps will skip this on import layer images.
        barefilename = (os.path.basename(self.filename))
        barefilename=barefilename.split(sep=".")[0]
        filename = "_"+barefilename + "_preview_"+str(previewNr)+".png"
        fullfilename = os.path.join(dirPath, filename)

        #  Get the preview images
        prevSurf = self.getPreviewBitmap(previewNr, 0)  # 0 is don't scale
        #  Save preview image to disk
        pygame.image.save(prevSurf, fullfilename)
        return

    cancelReplace=False
    def par_getBitmap(self,layerNr,forecolor,backcolor,scale,fullfilename):
        # Helper for procespoolexecutor in replaceBitmaps to call
        if self.cancelReplace: return None
        imgSurf=self.getBitmap(layerNr,forecolor,backcolor,scale)
        pygame.image.save(imgSurf, fullfilename)
        #print (layerNr,imgsurf)
        #return [layerNr,imgsurf]
        return layerNr

    def exportBitmaps(self,dirPath,filepre,progressDialog=None):
        """ Save all images in PhotonFile object as (decoded) png files in specified directory and with file precursor"""

        nLayers=self.nrLayers()

        # Traverse all layers
        self.cancelReplace=False
        res = []
        tstart=time.time()
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # Submit all jobs to ProcessPoolExecutor
            for layerNr in range(0,nLayers):
                # Retrieve decode pygame image surface
                #imgSurf=self.getBitmap(layerNr, (255, 255, 255), (0, 0, 0), (1, 1))
                # Make filename
                nrStr = "%04d" % layerNr
                filename = filepre + "_" + nrStr + ".png"
                # print ("filename: ",filename)
                fullfilename = os.path.join(dirPath, filename)

                job = executor.submit(self.par_getBitmap, layerNr=layerNr, forecolor=(255,255,255),backcolor=(0,0,0),scale=(1,1),fullfilename=fullfilename)
                res.append(job)
                # Check if user canceled
                if not progressDialog == None:
                    perc = 50 * layerNr / nLayers
                    if perc > 50: perc = 50
                    progressDialog.setProgress(perc)
                    # progressDialog.setProgressLabel(str(layerNr) + "/" + str(nLayers))
                    progressDialog.handleEvents()
                    if progressDialog.cancel:
                        #  Reset total number of layers to last layer we processes
                        self.cancelReplace = True
                        print("Abort.")
                        return

            # Handle all results as they come available
            #   We can't store pygame.Surface in ret, they will come up as dead surface
            #   So saving images to files is also done in par_getBitmap
            nrLayersDone=0
            for ret in concurrent.futures.as_completed(res):
                layerNr=ret.result()
                nrLayersDone+=1
                if not progressDialog == None:
                    perc = 50 + 50 * nrLayersDone / nLayers
                    if perc > 100: perc = 100
                    progressDialog.setProgress(perc)
                    # progressDialog.setProgressLabel(str(layerNr) + "/" + str(nLayers))
                    progressDialog.handleEvents()
                    if progressDialog.cancel:
                        #  Reset total number of layers to last layer we processes
                        self.cancelReplace = True
                        print("Abort.")
                        return
            print("Export images in %0.2f msec." % (int(1000 * (time.time() - tstart))))

        # Also save the preview images
        for i in range (0,2):
            prevSurf=self.getPreviewBitmap(i,0) # 0 is don't scale
            #   Make filename beginning with _ so PhotonFile.importBitmaps will skip this on import layer images.
            barefilename = (os.path.basename(self.filename))
            barefilename=barefilename.split(sep=".")[0]
            filename = "_"+barefilename + "_preview_"+str(i)+".png"
            fullfilename = os.path.join(dirPath, filename)
            #   Save preview image to disk
            pygame.image.save(prevSurf, fullfilename)

        return True

    def replacePreview(self, previewNr,filePath, saveToHistory=True):
        """ Replace image data in PhotonFile object with new (encoded data of) image on disk."""

        print("Replace Preview", previewNr, " - ", filePath)

        # Store all data to history
        # *** not yet implemented for preview images ***
        # if saveToHistory: self.saveToHistory("replace prev",previewNr)

        # Get/encode raw data
        (width,height,rawData) = PhotonFile.encodedPreviewBitmap_Bytes_nonumpy(filePath)
        if len(rawData)==0:
            raise Exception ("Could not import Preview image.")
            return

        # Get change in image rawData size so we can correct starting addresses of higher layer images
        oldLength=self.bytes_to_int(self.Previews[previewNr]["Data Length"]) #"Data Length" = len(rawData)+len(EndOfLayer)
        newLength=len(rawData)
        deltaLength=newLength-oldLength
        #print ("old, new, delta:",oldLength,newLength,deltaLength)

        # Update image settings and raw data of layer to be replaced
        self.Previews[previewNr]["Resolution X"]= self.int_to_bytes(width)
        self.Previews[previewNr]["Resolution Y"]= self.int_to_bytes(height)

        self.Previews[previewNr]["Data Length"] = self.int_to_bytes(len(rawData))
        self.Previews[previewNr]["Image Data"] = rawData

        # Update Header info about "Preview 1 (addr)"
        if previewNr==0: # then the "Preview 1 (addr)" shifts
            curAddr=self.bytes_to_int(self.Header["Preview 1 (addr)"])
            newAddr = curAddr + deltaLength
            self.Header["Preview 1 (addr)"]=self.int_to_bytes(newAddr)
        # Update Preview[1] info about "Preview 1 (addr)"
            curAddr=self.bytes_to_int(self.Previews[1]["Image Address"])
            newAddr = curAddr + deltaLength
            self.Previews[1]["Image Address"]=self.int_to_bytes(newAddr)

        #Always Header info about layerdefs shifts
        curAddr = self.bytes_to_int(self.Header["Layer Defs (addr)"])
        newAddr = curAddr + deltaLength
        self.Header["Layer Defs (addr)"] = self.int_to_bytes(newAddr)

        # Update start addresses of RawData of all following images
        nLayers=self.nrLayers()
        for rLayerNr in range(0,nLayers):
            curAddr=self.bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr+deltaLength
            self.LayerDefs[rLayerNr]["Image Address"]= self.int_to_bytes(newAddr)




########################################################################################################################
## Testing
########################################################################################################################

'''
   def float_to_bytes_old(self,floatVal):
        #http: //www.simplymodbus.ca/ieeefloats.xls
        #todo: remove binary string steps
        sign     =-1 if floatVal<0  else 1
        firstBit = 0 if sign==1     else 1
        exponent=-127 if abs(floatVal)<1.1754943E-38 else floor(log(abs(floatVal),10)/log(2,10))
        print ("abs          ", abs(floatVal))
        print ("logabs       ", log(abs(floatVal),10))
        print ("log2         ", log(2,10))
        print ("logabs/log2= ", log(abs(floatVal),10)/log(2,10))
        print ("int        = ", floor(log(abs(floatVal),10)/log(2,10)))
        exponent127=exponent+127
        next8Bits=format(exponent127,'#010b')
        mantissa=floatVal/pow(2,exponent)/sign
        substract=mantissa-1
        multiply=round(substract*8388608)
        div256_1=multiply/256
        divint_1=int(div256_1)
        rem_1=int((div256_1-divint_1)*256)
        div256_2=divint_1/256
        divint_2=int(div256_2)
        rem_2=int((div256_2-divint_2)*256)

        print (sign,firstBit,exponent,exponent127)
        print (next8Bits,mantissa,substract,multiply)
        print (div256_1,divint_1,rem_1)
        print (div256_2, divint_2, rem_2)

        bin1=str(firstBit)+next8Bits[2:9]
        bin2_=format(divint_2,'#010b')[-7:]#last 7 bits
        bin2=next8Bits[-1:]+bin2_
        bin3=format(rem_2,'#010b')[-8:]
        bin4=format(rem_1,'#010b')[-8:]
        bin1234=bin4+bin3+bin2+bin1

        #print(bin4, bin3, bin2, bin1)
        return int(bin1234, 2).to_bytes(len(bin1234) // 8, byteorder='big')
'''


def testDataConversions():
    print("Testing Data Type Conversions")
    print("-----------")
    floatVal = 9999.9999563227
    print("float:", floatVal)
    bytes = (PhotonFile.float_to_bytes(floatVal))
    print("raw bytes: ", bytes, len(bytes))
    hexs = ' '.join(format(h, '02X') for h in bytes)
    print("bytes in hex:", hexs)
    f = PhotonFile.bytes_to_float(bytes)
    print("want :", floatVal)
    print("float:", f)
    if not floatVal == 0: print("diff :", 100 * (floatVal - f) / floatVal, "%")
    quit()
    print("-----------")
    intVal = 313
    print("int:", intVal)
    bytes = (PhotonFile.int_to_bytes(intVal))
    print("raw bytes: ", bytes)
    hexs = ' '.join(format(h, '02X') for h in bytes)
    print("bytes in hex:", hexs)
    i = PhotonFile.bytes_to_int(bytes)
    print("int:", i)
    print("-----------")
    hexStr = '00 A1 7D DF'
    print("hex:", hexStr)
    bytes = (PhotonFile.hex_to_bytes(hexStr))
    print("raw bytes: ", bytes)
    h = PhotonFile.bytes_to_hex(bytes)
    print("hex:", h)
    print("-----------")
    quit()


# testDataConversions()
#c=0.0000001
'''
c=0.44999998807907104 #0.4999999888241291 > 0.25
for i in range (0,20):
    bA=PhotonFile.float_to_bytes(c)
    bHA=PhotonFile.bytes_to_hex(bA)
    bB=PhotonFile.bytes_to_float(bA)
    print (i,bA,bHA, bB)
    c = c + 0.05
#quit()
'''
'''
files=("SamplePhotonFiles/Debug/debug 0.05mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.07mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.08mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.09mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.10mm.photon",
        "SamplePhotonFiles/Debug/debug 0.11mm.photon",
        "SamplePhotonFiles/Debug/debug 0.12mm.photon",
        "SamplePhotonFiles/Debug/debug 0.13mm.photon",
        "SamplePhotonFiles/Debug/debug 0.14mm.photon",
        "SamplePhotonFiles/Debug/debug 0.15mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.20mm.photon",
        "SamplePhotonFiles/Debug/debug 0.25mm.photon",
        "SamplePhotonFiles/Debug/debug 0.30mm.photon",
        "SamplePhotonFiles/Debug/debug 0.35mm.photon",
        "SamplePhotonFiles/Debug/debug 0.40mm.photon",
        "SamplePhotonFiles/Debug/debug 0.45mm.photon",
        "SamplePhotonFiles/Debug/debug 0.50mm.photon",
        "SamplePhotonFiles/Debug/debug 0.55mm (err).photon",
        "SamplePhotonFiles/Debug/debug 0.60mm.photon",
        "SamplePhotonFiles/Debug/debug 0.65mm.photon",
        "SamplePhotonFiles/Debug/debug 0.70mm.photon",
        "SamplePhotonFiles/Debug/debug 0.75mm.photon",
        "SamplePhotonFiles/Debug/debug 0.80mm.photon",
       )
'''
'''
files=("SamplePhotonFiles/Debug/debug 0.65mm test.photon",)
for file in files:
    ph=PhotonFile(file)
    ph.readFile()
    print ( file[30:34],':',
            PhotonFile.bytes_to_int(ph.Header["# Layers"]),
            PhotonFile.bytes_to_int(ph.Header["Preview 0 (addr)"]),
            PhotonFile.bytes_to_int(ph.Header["Preview 1 (addr)"]),
            PhotonFile.bytes_to_int(ph.Previews[0]["Image Address"]),
            PhotonFile.bytes_to_int(ph.Previews[0]["Data Length"]),
            PhotonFile.bytes_to_int(ph.Previews[1]["Image Address"]),
            PhotonFile.bytes_to_int(ph.Previews[1]["Data Length"]),
            PhotonFile.bytes_to_int(ph.Header["Layer Defs (addr)"]),
            )
'''

"""
("Header", 8, tpByte, False),
("Bed X (mm)", 4, tpFloat, True),
("Bed Y (mm)", 4, tpFloat, True),
("Bed Z (mm)", 4, tpFloat, True),
("padding0", 3 * 4, tpByte, False),  # 3 ints
("Layer height (mm)", 4, tpFloat, True),
("Exp. time (s)", 4, tpFloat, True),
("Exp. bottom (s)", 4, tpFloat, True),
("Off time (s)", 4, tpFloat, True),
("# Bottom Layers", 4, tpInt, True),
("Resolution X", 4, tpInt, True),
("Resolution Y", 4, tpInt, True),
("Preview 0 (addr)", 4, tpInt, False),  # start of preview 0
("Layer Defs (addr)", 4, tpInt, False),  # start of layerDefs
(nrLayersString, 4, tpInt, False),
("Preview 1 (addr)", 4, tpInt, False),  # start of preview 1
("unknown6", 4, tpInt, False),
("Proj.type-Cast/Mirror", 4, tpInt, False),  # LightCuring/Projection type // (1=LCD_X_MIRROR, 0=CAST)
("padding1", 6 * 4, tpByte, False)  # 6 ints
]

pfStruct_Previews = [
("Resolution X", 4, tpInt, False),
("Resolution Y", 4, tpInt, False),
("Image Address", 4, tpInt, False),  # start of rawData0
("Data Length", 4, tpInt, False),  # size of rawData0
("padding", 4 * 4, tpByte, False),  # 4 ints
("Image Data", -1, tpByte, False),
]

pfStruct_LayerDef = [
("Layer height (mm)", 4, tpFloat, True),
("Exp. time (s)", 4, tpFloat, True),
("Off time (s)", 4, tpFloat, True),
("Image Address", 4, tpInt, False),  # dataStartPos -> Image Address
("Data Length", 4, tpInt, False),  # size of rawData+lastByte(1)
("padding", 4 * 4, tpByte, False)  # 4 ints
"""

#quit()
#PhotonFile.encodedBitmap_Bytes_withnumpy("SamplePhotonFiles/Smilie.bitmaps/slice__0005.png")
#quit()