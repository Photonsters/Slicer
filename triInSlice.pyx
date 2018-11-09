cimport cython

from cpython cimport array
import array
import numpy as numpy
cimport numpy as numpy
DTYPE = numpy.float64
ctypedef numpy.float64_t DTYPE_t

cpdef enum:
    x = 0
    y = 1
    z = 2

#!python
@cython.wraparound (False) # turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def triInSlice( numpy.ndarray[DTYPE_t, ndim = 1] p0 ,
                numpy.ndarray[DTYPE_t, ndim = 1] p1 ,
                numpy.ndarray[DTYPE_t, ndim = 1] p2 ,
                yBottom not None,
                yTop not None):

    cdef numpy.ndarray[DTYPE_t, ndim = 1] q0,q1,q2
    cdef float s01, s02, s01Bottom, s01Top, s02Bottom, s02Top, s12Top
    cdef (float,float) q01Bottom, q01Top, q02Bottom, q02Top, q12Top, q01, q02

    # Debug
    #if debug:
    #    print()
    #    print("p0:    ", p0)
    #    print("p1:    ", p1)
    #    print("p2:    ", p2)
    #    print("slice: ", yBottom, " to ", yTop)

    # To prevent points on yFrom and yTo, we add a small offset
    cdef float offset = 0.0001
    if p0[y] == yBottom or p0[y] == yTop: p0[y] = p0[y] + offset
    if p1[y] == yBottom or p1[y] == yTop: p1[y] = p1[y] + offset
    if p2[y] == yBottom or p2[y] == yTop: p2[y] = p2[y] + offset

    # Triangles could be oriented in several ways relative to the layer bottom and top:
    #             (1)        (2)          (3)     (4)     (5)   (6)     (7)       (8)       (9)         (10)
    #            Above      Below       Between    Intersect     Intersect          Intersect
    #
    #              *
    #             * *
    #            *****                             *     *****                     *  *************  *
    # yTo    -------------------------------------* *-----* *---------------------* *--*         *---* *------
    #                                    *       *****     *                     *   *  *       *    *   *
    #                                   * *                                     *     *  *     *     *     *
    #                                  *****                     *     *****   *       *  *   *      *   *
    # yFrom  ---------------------------------------------------* *-----* *---*         *  * *-------*  *-----
    #                          *                               *****     *   *************  *        *
    #                         * *
    #                        *****

    # Determine position of points relative to slice
    cdef unsigned char d0F = (p0[y] > yBottom)
    cdef unsigned char d1F = (p1[y] > yBottom)
    cdef unsigned char d2F = (p2[y] > yBottom)
    cdef unsigned char d0T = (p0[y] > yTop)
    cdef unsigned char d1T = (p1[y] > yTop)
    cdef unsigned char d2T = (p2[y] > yTop)
    cdef unsigned char nrAbove = d0T + d1T+ d2T
    cdef unsigned char nrBelow = (not d0F) + (not d1F) + (not d2F)
    cdef unsigned char nrBetween = (d0F and not d0T) + (d1F and not d1T) + (d2F and not d2T)
    if (nrAbove + nrBelow + nrBetween) != 3: raise Exception("Coding error in triInSlice!")

    # (1) Check all Above slice
    if nrAbove == 3:
        #if debug: return ("(1) All points above! ", [])
        return []

    # (2) Check all Below slice
    if nrBelow == 3:
        #if debug: return ("(2) All points below! ", [])
        return []

    # (3) Check all in Between slice
    if nrBetween == 3:
        #if debug: return (
        #"(3) All points within slice! ", coordlist2str([(p0[x], p0[z]), (p1[x], p1[z]), (p2[x], p2[z])]))
        return [(p0[x], p0[z]), (p1[x], p1[z]), (p2[x], p2[z])]

    # (4) Check for 2 points in Between and 1 Above slice
    if nrBetween == 2 and nrAbove == 1:
        # Make the above point #0 and the between points #1 and #2
        if p0[y] > yTop: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] > yTop: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] > yTop: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01 = (yTop - q1[y]) / (q0[y] - q1[y])
        s02 = (yTop - q2[y]) / (q0[y] - q2[y])
        # Create intersection points
        q01 = (s01 * (q0[x] - q1[x]) + q1[x],
               s01 * (q0[z] - q1[z]) + q1[z])
        q02 = (s02 * (q0[x] - q2[x]) + q2[x],
               s02 * (q0[z] - q2[z]) + q2[z])
        #if debug: return (
        #"(4) 2 points in Between and 1 Above slice! ", coordlist2str([(q1[x], q1[z]), q01, q02, (q2[x], q2[z])]))
        return [(q1[x], q1[z]), q01, q02, (q2[x], q2[z])]

    # (5) Check for 1 points in Between and 2 Above slice
    if nrBetween == 1 and nrAbove == 2:
        # Make the between point #0 and the above points #1 and #2
        if p0[y] < yTop: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] < yTop: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] < yTop: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01 = (yTop - q0[y]) / (q1[y] - q0[y])
        s02 = (yTop - q0[y]) / (q2[y] - q0[y])
        # Create intersection points
        q01 = (s01 * (q1[x] - q0[x]) + q0[x],
               s01 * (q1[z] - q0[z]) + q0[z])
        q02 = (s02 * (q2[x] - q0[x]) + q0[x],
               s02 * (q2[z] - q0[z]) + q0[z])
        #if debug: return ("(5) 1 points in Between and 2 Above slice! ", coordlist2str([(q0[x], q0[z]), q01, q02]))
        return [(q0[x], q0[z]), q01, q02]

    # (6) Check for 1 points in Between and 2 Below slice
    if nrBetween == 1 and nrBelow == 2:
        # Make the between point #0 and the below points #1 and #2
        if p0[y] > yBottom: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] > yBottom: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] > yBottom: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01 = (yBottom - q1[y]) / (q0[y] - q1[y])
        s02 = (yBottom - q2[y]) / (q0[y] - q2[y])
        # Create intersection points
        q01 = (s01 * (q0[x] - q1[x]) + q1[x],
               s01 * (q0[z] - q1[z]) + q1[z])
        q02 = (s02 * (q0[x] - q2[x]) + q2[x],
               s02 * (q0[z] - q2[z]) + q2[z])
        #if debug: return ("(6) 1 point in Between and 2 Below slice! ", coordlist2str([q01, (q0[x], q0[z]), q02]))
        return [q01, (q0[x], q0[z]), q02]

    # (7) Check for 2 points in Between and 1 Below slice
    if nrBetween == 2 and nrBelow == 1:
        # Make the below point #0 and the between points #1 and #2
        if p0[y] < yBottom: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] < yBottom: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] < yBottom: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01 = (yBottom - q0[y]) / (q1[y] - q0[y])
        s02 = (yBottom - q0[y]) / (q2[y] - q0[y])
        # Create intersection points
        q01 = (s01 * (q1[x] - q0[x]) + q0[x],
               s01 * (q1[z] - q0[z]) + q0[z])
        q02 = (s02 * (q2[x] - q0[x]) + q0[x],
               s02 * (q2[z] - q0[z]) + q0[z])
        #if debug: return (
        #"(7) 2 points in Between and 1 Below slice! ", coordlist2str([q01, (q1[x], q1[z]), (q2[x], q2[z]), q02]))
        return [q01, (q1[x], q1[z]), (q2[x], q2[z]), q02]

    # (8) Check for 1 point Above and 2 Below slice
    if nrAbove == 1 and nrBelow == 2:
        # Make the above point #0 and the below points #1 and #2
        if p0[y] > yTop: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] > yTop: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] > yTop: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01Bottom = (yBottom - q1[y]) / (q0[y] - q1[y])
        s02Bottom = (yBottom - q2[y]) / (q0[y] - q2[y])
        s01Top = (yTop - q1[y]) / (q0[y] - q1[y])
        s02Top = (yTop - q2[y]) / (q0[y] - q2[y])
        # Create intersection points
        q01Bottom = (s01Bottom * (q0[x] - q1[x]) + q1[x],
                     s01Bottom * (q0[z] - q1[z]) + q1[z])
        q02Bottom = (s02Bottom * (q0[x] - q2[x]) + q2[x],
                     s02Bottom * (q0[z] - q2[z]) + q2[z])
        q01Top = (s01Top * (q0[x] - q1[x]) + q1[x],
                  s01Top * (q0[z] - q1[z]) + q1[z])
        q02Top = (s02Top * (q0[x] - q2[x]) + q2[x],
                  s02Top * (q0[z] - q2[z]) + q2[z])
        #if debug: return (
        #"(8) 1 point Above and 2 Below slice! ", coordlist2str([q01Top, q01Bottom, q02Bottom, q02Top]))
        return [q01Top, q01Bottom, q02Bottom, q02Top]

    # (9) Check for 2 points Above and 1 Below slice
    if nrAbove == 2 and nrBelow == 1:
        # Make the below point #0 and the above points #1 and #2
        if p0[y] < yBottom: (q0, q1, q2) = (p0, p1, p2)
        if p1[y] < yBottom: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] < yBottom: (q0, q1, q2) = (p2, p0, p1)
        # Find intersection between 0-1 and 0-2
        s01Bottom = (yBottom - q0[y]) / (q1[y] - q0[y])
        s02Bottom = (yBottom - q0[y]) / (q2[y] - q0[y])
        s01Top = (yTop - q0[y]) / (q1[y] - q0[y])
        s02Top = (yTop - q0[y]) / (q2[y] - q0[y])
        # Create intersection points
        q01Bottom = (s01Bottom * (q1[x] - q0[x]) + q0[x],
                     s01Bottom * (q1[z] - q0[z]) + q0[z])
        q02Bottom = (s02Bottom * (q2[x] - q0[x]) + q0[x],
                     s02Bottom * (q2[z] - q0[z]) + q0[z])
        q01Top = (s01Top * (q1[x] - q0[x]) + q0[x],
                  s01Top * (q1[z] - q0[z]) + q0[z])
        q02Top = (s02Top * (q2[x] - q0[x]) + q0[x],
                  s02Top * (q2[z] - q0[z]) + q0[z])
        #if debug: return (
        #"(9) 2 points Above and 1 Below slice! ", coordlist2str([q01Top, q01Bottom, q02Bottom, q02Top]))
        return [q01Top, q01Bottom, q02Bottom, q02Top]

    # (10) Check for 1 point Above,1 point Between and 1 Below slice
    if nrAbove == 1 and nrBetween == 1 and nrBelow == 1:
        # Make below point as #0, between point as #1, above point as #2
        if p0[y] < yBottom and p2[y] > yTop: (q0, q1, q2) = (p0, p1, p2)
        if p0[y] < yBottom and p1[y] > yTop: (q0, q1, q2) = (p0, p2, p1)
        if p1[y] < yBottom and p2[y] > yTop: (q0, q1, q2) = (p1, p0, p2)
        if p1[y] < yBottom and p0[y] > yTop: (q0, q1, q2) = (p1, p2, p0)
        if p2[y] < yBottom and p1[y] > yTop: (q0, q1, q2) = (p2, p0, p1)
        if p2[y] < yBottom and p0[y] > yTop: (q0, q1, q2) = (p2, p1, p0)
        # Find intersection between 0-1 and 0-2
        s01Bottom = (yBottom - q0[y]) / (q1[y] - q0[y])
        s02Bottom = (yBottom - q0[y]) / (q2[y] - q0[y])
        s12Top = (yTop - q1[y]) / (q2[y] - q1[y])
        s02Top = (yTop - q0[y]) / (q2[y] - q0[y])
        # Create intersection points
        q01Bottom = (s01Bottom * (q1[x] - q0[x]) + q0[x],
                     s01Bottom * (q1[z] - q0[z]) + q0[z])
        q02Bottom = (s02Bottom * (q2[x] - q0[x]) + q0[x],
                     s02Bottom * (q2[z] - q0[z]) + q0[z])
        q12Top = (s12Top * (q2[x] - q1[x]) + q1[x],
                  s12Top * (q2[z] - q1[z]) + q1[z])
        q02Top = (s02Top * (q2[x] - q0[x]) + q0[x],
                  s02Top * (q2[z] - q0[z]) + q0[z])
        #if debug: return ("(10) 1 point Below, 1 Between and 1 Above slice! ",
        #                  coordlist2str([q01Bottom, (q1[x], q1[z]), q12Top, q02Top, q02Bottom]))
        return [q01Bottom, (q1[x], q1[z]), q12Top, q02Top, q02Bottom]

    # if we come here something in this method is wrong
    #if debug:
    #    print("Encountered error, debug info")
    #    print("sliceBottom, sliceTop        : ", yBottom, yTop)
    #    print("Triangle                     : ", coordlist2str([p0, p1, p2]))
    #    print("nrBelow, nrBetween, nrAbove  : ", nrBelow, nrBetween, nrAbove)
    #    raise Exception("Coding error in Triangle.splitOnPlaneY")

"""
def coordlist2str(self,iterable):
    # [a,b,c], [d,e,f],... -> "(a,b,c) (d,e,f) ...
    s=""
    for coord in iterable:
        s=s+self.coord2str(coord)+" "
    s=s[:-1]
    return s
"""

#!python
@cython.wraparound (False) # turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def PointInTriangle(
                (float,float) p ,
                (float,float) p0 ,
                (float, float) p1 ,
                (float, float) p2
                ):

    cdef float A
    cdef float sign
    cdef float s
    cdef float t
    cdef float half=0.5

    A = half * (-p1[y] * p2[x] +
                 p0[y] * (-p1[x] + p2[x]) +
                 p0[x] * (p1[y] - p2[y]) +
                 p1[x] * p2[y])

    sign = -1 if A < 0 else 1
    s = (p0[y] * p2[x] -
         p0[x] * p2[y] +
         (p2[y] - p0[y]) * p[x] +
         (p0[x] - p2[x]) * p[y]) * sign

    t = (p0[x] * p1[y] -
         p0[y] * p1[x] +
         (p0[y] - p1[y]) * p[x] +
         (p1[x] - p0[x]) * p[y]) * sign

    return s > 0 and t > 0 and (s + t) < 2 * A * sign

