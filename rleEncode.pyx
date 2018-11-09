#!python
#cython: language_level=3, boundscheck=False, wraparound=False, nonecheck=False, initializedcheck=False

cimport cython
import numpy as numpy
cimport numpy as numpy
DTYPE = numpy.uint8
ctypedef numpy.uint8_t DTYPE_t
#!python
@cython.wraparound (False) # turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def encodedBitmap_Bytes_numpy1DBlock(numpy.ndarray[DTYPE_t,ndim=1] surfOrFile):
    """ Converts image data from file on disk to RLE encoded byte string.
        Encoding scheme:
            Highest bit of each byte is color (black or white)
            Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        Credits for speed to:
            https://kogs-www.informatik.uni-hamburg.de/~seppke/content/teaching/wise1314/20131128_letsch-gries-boomgarten-cython.pdf
            https://stackoverflow.com/questions/53135050/why-is-cython-only-20-faster-on-runlengthencode-b-w-image
    """
    # Make room for rleData
    cdef numpy.ndarray [DTYPE_t,ndim=1] rleData = numpy.zeros((3686400),dtype=DTYPE)

    # Some constants for nr of pixels and last pixelnr
    cdef unsigned int nrPixels = 3686400 #(width, height) = (1440, 2560)
    cdef unsigned int lastPixel = nrPixels - 1

    # Count number of pixels with same color up until 0x7D/125 repetitions
    cdef unsigned char color = 0
    cdef unsigned char prevColor = 0
    cdef unsigned char r
    cdef unsigned char nrOfColor = 0
    cdef unsigned char encValue = 0
    cdef unsigned int pixelNr
    cdef unsigned int nrBytes=0
    prevColor = surfOrFile[0] >> 7 #prevColor = nocolor
    for pixelNr in range(nrPixels):
        r = surfOrFile[pixelNr]
        color = r >> 7 #if (r<128) color = 1 else: color = 0
        if color == prevColor and nrOfColor < 0x7D:# and not isLastPixel:
            nrOfColor = nrOfColor + 1
        else:
            encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
            rleData[nrBytes]=encValue
            nrBytes = nrBytes+1
            prevColor = color
            nrOfColor = 1
    # Handle lastpixel, we did nrOfColor++ once too many
    nrOfColor=nrOfColor-1
    encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
    rleData[nrBytes] = encValue
    nrBytes = nrBytes + 1

    # Remove excess bytes and return rleData
    rleData=rleData[:nrBytes]
    return bytes(rleData)

""" 
#OLD CALLS Stl2Slices.py

                    #rlestack.append (PhotonFile.encodedBitmap_Bytes_withnumpy(imgarr8))
                    #rlestack.append(rleEncode.encodedBitmap_Bytes_nonumpy(imgarr8.tolist()))
                    #rlestack.append(rleEncode.encodedBitmap_Bytes_nonumpy1D(img1D.tolist()))
                    #rlestack.append(rleEncode.encodedBitmap_Bytes_nonumpy1DBlock(img1D.tolist()))
                    #rlestack.append(rleEncode.encodedBitmap_Bytes_withnumpy(img1D))
                    #rlestack.append(rleEncode.encodedBitmap_Bytes_withnumpy2(img1D))

#OLD DEFS

#!python
cimport cython

#!python
@cython.wraparound (False) #turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
def encodedBitmap_Bytes_nonumpy(list surfOrFile not None):

    #(width, height) = (1440, 2560)
    cdef unsigned int width = 1440
    cdef unsigned int height= 2560
    cdef unsigned int lastX = width - 1
    cdef unsigned int lastY = height - 1

    # Count number of pixels with same color up until 0x7D/125 repetitions
    rleData = bytearray() # convert bytearray to cdef array has no speed benefit
    cdef unsigned char color = 0
    cdef unsigned char prevColor = 0
    cdef unsigned char black = 0
    cdef unsigned char white = 1
    cdef unsigned char nocolor=3
    cdef unsigned char r
    cdef unsigned char nrOfColor = 0
    cdef unsigned char encValue = 0
    cdef unsigned int x
    cdef unsigned int y
    cdef unsigned int lastLine =  False
    cdef unsigned int isLastPixel = False
    prevColor = nocolor

    for y in range(height):
        lastLine = (y==lastY)
        for x in range(width):
            # print (x,y,(surfOrFile[y][x]))
            r = surfOrFile[y][x]
            if (r and 0b10000000): #if (r<128)
                color = white
            else:
                color = black
            if prevColor == nocolor: prevColor = color
            isLastPixel = (x == lastX and lastLine)
            if color == prevColor and nrOfColor < 0x7D and not isLastPixel:
                nrOfColor = nrOfColor + 1
            else:
                # print (color,nrOfColor,nrOfColor<<1)
                encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
                rleData.append(encValue)
                prevColor = color
                nrOfColor = 1

    return bytes(rleData)

#!python
@cython.wraparound (False) #turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def encodedBitmap_Bytes_nonumpy1D(list surfOrFile not None):
    #(width, height) = (1440, 2560)
    cdef unsigned int nrPixels = 3686400
    cdef unsigned int lastPixel = nrPixels - 1

    # Count number of pixels with same color up until 0x7D/125 repetitions
    rleData = bytearray() # convert bytearray to cdef array has no speed benefit
    cdef unsigned char color = 0
    cdef unsigned char prevColor = 0
    cdef unsigned char black = 0
    cdef unsigned char white = 1
    cdef unsigned char nocolor=3
    cdef unsigned char r
    cdef unsigned char nrOfColor = 0
    cdef unsigned char encValue = 0
    cdef unsigned int pixelNr
    cdef unsigned int isLastPixel = False
    prevColor = nocolor

    for pixelNr in range(nrPixels):
        r = surfOrFile[pixelNr]
        if (r and 0b10000000): #if (r<128)
            color = white
        else:
            color = black
        if prevColor == nocolor: prevColor = color
        isLastPixel = (pixelNr == lastPixel)
        if color == prevColor and nrOfColor < 0x7D and not isLastPixel:
            nrOfColor = nrOfColor + 1
        else:
            # print (color,nrOfColor,nrOfColor<<1)
            encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
            rleData.append(encValue)
            prevColor = color
            nrOfColor = 1

    return bytes(rleData)

from cpython cimport array
#!python
@cython.wraparound (False) # turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def encodedBitmap_Bytes_nonumpy1DBlock(list surfOrFile not None):

    # Make room for rleData
    cdef templatemv = array.array('B')
    cdef rleData = array.array('B')
    rleData = array.clone(templatemv, 3686400, zero=False)

    # Some constants for nr of pixels and last pixelnr
    cdef unsigned int nrPixels = 3686400 #(width, height) = (1440, 2560)
    cdef unsigned int lastPixel = nrPixels - 1

    # Count number of pixels with same color up until 0x7D/125 repetitions
    cdef unsigned char color = 0
    cdef unsigned char prevColor = 0
    cdef unsigned char black = 0
    cdef unsigned char white = 1
    cdef unsigned char nocolor=3
    cdef unsigned char r
    cdef unsigned char nrOfColor = 0
    cdef unsigned char encValue = 0
    cdef unsigned int pixelNr
    cdef unsigned int isLastPixel = False
    cdef unsigned int nrBytes=0
    prevColor = nocolor
    for pixelNr in range(nrPixels):
        r = surfOrFile[pixelNr]
        if (r and 0b10000000): #if (r<128)
            color = white
        else:
            color = black
        if prevColor == nocolor: prevColor = color
        isLastPixel = (pixelNr == lastPixel)
        if color == prevColor and nrOfColor < 0x7D and not isLastPixel:
            nrOfColor = nrOfColor + 1
        else:
            # print (color,nrOfColor,nrOfColor<<1)
            encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
            rleData[nrBytes]=encValue
            nrBytes = nrBytes+1
            prevColor = color
            nrOfColor = 1

    # Remove excess bytes and return rleData
    array.resize(rleData,nrBytes)
    return bytes(rleData)




import numpy
cimport numpy
#ctypedef numpy.npy_float FLOAT
#ctypedef numpy.npy_intp INTP

#!python
@cython.boundscheck(False) # turn off bounds-checking
@cython.wraparound(False) # turn off bounds-checking
def encodedBitmap_Bytes_withnumpy(numpy.ndarray[numpy.npy_uint8,ndim=1] x):

    # Encoding magic
    cdef unsigned int n=0
    cdef numpy.ndarray[numpy.npy_int64, ndim = 1] starts # npy_int64
    cdef numpy.ndarray[numpy.npy_int64, ndim = 1] lengths# npy_int64
    cdef numpy.ndarray[numpy.npy_uint8, ndim = 1] values # npy_uint8

    where = numpy.flatnonzero
    n = len(x)
    starts = numpy.r_[0, where(~numpy.isclose(x[1:], x[:-1], equal_nan=True)) + 1]
    lengths = numpy.diff(numpy.r_[starts, n])
    values = x[starts]

    # Reduce repetitions of color to max 0x7D/125 and store in bytearray
    rleData = bytearray()
    cdef unsigned int nr=0
    cdef unsigned int col=0
    cdef unsigned char color=0
    cdef unsigned char encValue = 0

    cdef unsigned int l=len(lengths)
    cdef unsigned int i=0
    for i in range (0,l):
        nr=lengths[i]
        col=values[i]
        # color = (abs(col)>1) # slow
        color = 1 if col else 0  # fast
        while nr > 0x7D:
            encValue = (color << 7) | 0x7D
            rleData.append(encValue)
            nr = nr - 0x7D
        encValue = (color << 7) | nr
        rleData.append(encValue)

    # Needed is an byte string, so convert
    return bytes(rleData)

#import numpy as numpy
#cimport numpy as numpy
#DTYPE = numpy.uint8
#ctypedef numpy.uint8_t DTYPE_t
#!python
@cython.boundscheck(False) # turn off bounds-checking
@cython.wraparound(False) # turn off bounds-checking
def encodedBitmap_Bytes_withnumpy2(numpy.ndarray[DTYPE_t,ndim=1] x):

    # Encoding magic
    cdef unsigned int n=0
    cdef numpy.ndarray[numpy.npy_int64, ndim = 1] starts # npy_int64
    cdef numpy.ndarray[numpy.npy_int64, ndim = 1] lengths# npy_int64
    cdef numpy.ndarray[numpy.npy_uint8, ndim = 1] values # npy_uint8

    where = numpy.flatnonzero
    n = len(x)
    starts = numpy.r_[0, where(~numpy.isclose(x[1:], x[:-1], equal_nan=True)) + 1]
    lengths = numpy.diff(numpy.r_[starts, n])
    values = x[starts]

    # Reduce repetitions of color to max 0x7D/125 and store in bytearray
    cdef numpy.ndarray[DTYPE_t, ndim = 1] rleData = numpy.zeros((3686400), dtype=DTYPE)
    cdef unsigned int nr=0
    cdef unsigned int col=0
    cdef unsigned char color=0
    cdef unsigned char encValue = 0

    cdef unsigned int l=len(lengths)
    cdef unsigned int i=0
    cdef unsigned int nrBytes = 0

    for i in range (0,l):
        nr=lengths[i]
        col=values[i]
        # color = (abs(col)>1) # slow
        color = 1 if col else 0  # fast
        while nr > 0x7D:
            encValue = (color << 7) | 0x7D
            rleData[nrBytes] = encValue
            nrBytes = nrBytes + 1
            nr = nr - 0x7D
        encValue = (color << 7) | nr
        rleData[nrBytes] = encValue
        nrBytes = nrBytes + 1

    # Needed is an byte string, so convert
    rleData = rleData[:nrBytes]
    return bytes(rleData)
    
"""