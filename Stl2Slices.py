# internal
import struct
import math
import time
import os
import sys # for stdout

# external
import cv2
import numpy

# user
from PhotonFile import *
import pyximport; pyximport.install()
import rleEncode
import triInSlice

#todo: Can we recalc/unify normals using numpy?
#todo: Parallel processing of slices?
#todo: Simplify args. If photonfile arg without name we output to same filename but with photon extension

"""
class TriBucket:
    childs = []
    tris = None
    minY=0
    maxY=0
    dY=0
    level=0
    id=""
    def __init__(self, minY,maxY, smallestHeight=2,level=0,id="0"):
        self.minY=minY
        self.maxY=maxY
        #make 3 childs, where one overlaps with other two
        dY=maxY-minY
        self.dY=dY
        self.level=level
        self.id=id
        self.tris = []
        print ("create:",level,">", id,":",minY,maxY)
        if dY>smallestHeight:
            midY=minY+dY/2
            y14=minY+dY/4
            y34=midY+dY/4
            t1 = TriBucket(minY,midY,smallestHeight,level+1,id+".1")
            t2 = TriBucket(y14, y34,smallestHeight,level+1,id+".2")
            t3 = TriBucket(midY, maxY,smallestHeight,level+1,id+".3")
            self.childs=[t1,t2,t3]

    def put(self,tri):
        (p1, p2, p3)=tri
        y=1
        bottom = min(p1[y],p2[y],p3[y])
        top = max(p1[y], p2[y], p3[y])

        # Check if belongs in this bucket
        if bottom<self.minY or top>self.maxY:
            return

        print ("Check bucket:",self.level,self.id,self.minY,self.maxY)

        # Check if small enough for child
        height=top-bottom
        childHeight=self.dY/2
        # since we have 1/2 child overlap, if smaller than 1/2 a child we can put in child
        if height<childHeight/2:
            for child in self.childs:
                child.put(tri)
                return

        # If too large or no childs
        self.tris.append(tri)
        print ("Found bucket:",self.level,self.id,self.minY,self.maxY)

    def get(self,fromY, toY):
        #Returns self and child buckets where minY-maxY is between fromY-toY
        #do

    def tostr(self,head=""):
        print (head,self.id,self.minY,self.maxY,len(self.tris))
        for child in self.childs:
            child.tostr(head+"")

#tb=TriBucket(0,10)
#tri=([0,1,0],[0,1.2,1],[0,1.1,2])
#tb.put(tri)
#print(tb.tostr())
#quit()
"""

class Stl2Slices:
    cmin = [100, 100, 100]
    cmax = [-100, -100, -100]
    modelheight = 0
    points = []
    normals = []
    gui=False

    def clearModel(self):
        self.points = []
        self.normals = []
        self.cmin = []
        self.cmax = []

    def load_binary_stl(self,filename, scale=1):
        if not self.gui: print("Reading binary")
        # filebytes = os.path.getsize(filename)

        fp = open(filename, 'rb')

        h = fp.read(80)
        l = struct.unpack('I', fp.read(4))[0]
        count = 0

        t0 = time.time()

        self.clearModel()
        points = []
        normals = []
        filepos = 0
        while True:
            try:
                p = fp.read(12)
                if len(p) == 12:
                    n = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p1 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p2 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p3 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                if len(p) == 12:
                    # switch coordinates to OpenGL
                    a = 0
                    b = 2
                    c = 1
                    n = [n[a], n[b], n[c]]
                    p1 = [p1[a], p1[b], p1[c]]
                    p2 = [p2[a], p2[b], p2[c]]
                    p3 = [p3[a], p3[b], p3[c]]

                    # add points to array
                    points.append(p1)
                    points.append(p2)
                    points.append(p3)
                    normals.append(n)

                count += 1
                fp.read(2)

                # Check if we reached end of file
                if len(p) == 0:
                    break
            except EOFError:
                break
        fp.close()

        # t1=time.time()
        # print ("t1-t0",t1-t0)

        # use numpy for easy and fast center and scale model
        np_points = numpy.array(points)
        np_normals = numpy.array(normals)

        # scale model, 1mm should be 1/0,047 pixels
        scale=scale/0.047
        np_points = np_points * scale

        # find max and min of x, y and z
        x = np_points[:, 0]
        y = np_points[:, 1]
        z = np_points[:, 2]
        self.cmin = (x.min(), y.min(), z.min())
        self.cmax = (x.max(), y.max(), z.max())
        self.modelheight = self.cmax[1] - self.cmin[1]

        # Center model and put on base
        trans = [0, 0, 0]
        trans[0] = -(self.cmax[0] - self.cmin[0]) / 2 - self.cmin[0]
        trans[2] = -(self.cmax[2] - self.cmin[2]) / 2 - self.cmin[2]
        trans[1] = -self.cmin[1]

        # We want the model centered in 2560x1440
        # 2560x1440 pixels equals 120x67
        trans[0] = trans[0] +1440 / 2
        trans[2] = trans[2] +2560 / 2

        # Center numpy array of points which is returned for fast OGL model loading
        np_points = np_points + trans

        # Find bounding box again
        x = np_points[:, 0]
        y = np_points[:, 1]
        z = np_points[:, 2]
        self.cmin = (x.min(), y.min(), z.min())
        self.cmax = (x.max(), y.max(), z.max())

        # align coordinates on grid
        # this will reduce number of points and speed up loading
        # with benchy grid-screenres/1:  total time 28 sec, nr points remain 63k , but large artifacts
        # with benchy grid-screenres/50: total time 39 sec, nr points remain 112k, no artifacts
        # w/o benchy :                   total time 40 sec, nr points remain 113k, no artifacts
        #screenres = 0.047
        #grid = screenres / 50  # we do not want artifacts but reduce rounding errors in the file to cause misconnected triangles
        #np_points = grid * (np_points // grid)


        # return points and normal for OGLEngine to display
        return np_points, np_normals


    def coord2str(self,iterable):
        # [0.124,2.343,6.432] -> "0.12 2.34 6.43"
        s="("
        for c in iterable:
            s=s+"%.2f" %c + " "
        s=s[:-1]+")"
        return s
    def coordlist2str(self,iterable):
        # [a,b,c], [d,e,f],... -> "(a,b,c) (d,e,f) ...
        s=""
        for coord in iterable:
            s=s+self.coord2str(coord)+" "
        s=s[:-1]
        return s

    def PointInTriangle(p,p0,p1,p2):
        x=0
        y=1
        A = 1/2 * (  -p1[y] *   p2[x] +
                      p0[y] * (-p1[x] + p2[x]) +
                      p0[x] * ( p1[y] - p2[y]) +
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


    def __init__(self, stlfilename, scale=1,
                 outputpath=None,       # should end with '/'
                 layerheight=0.05,
                 photonfilename=None,   # keep outputpath=None if output to photonfilename
                 normalexposure=8.0,
                 bottomexposure=90,
                 bottomlayers=8,
                 offtime=6.5,
                 gui=False
                 ):
        # Set Gui
        self.gui=gui
		# Get path of script/exe for local resources like iconpath and newfile.photon
        if getattr(sys, 'frozen', False):# frozen
            self.installpath = os.path.dirname(sys.executable)
        else: # unfrozen
            self.installpath = os.path.dirname(os.path.realpath(__file__))
        if gui:
            import tkinter as tk
            from tkinter import ttk
            # Construct window            
            self.popup = tk.Tk()#tk.Toplevel()
            self.popup.geometry('240x32')
            # Set window icon
            img=tk.PhotoImage(file=os.path.join(self.installpath,'PhotonSlicer.gif'))
            self.popup.tk.call('wm','iconphoto',self.popup._w,img)
            #tk.Label(self.popup, text="Slicing...").grid(row=0, column=0)
            self.popup.title("Slicing...")
            self.progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(self.popup, variable=self.progress_var, maximum=100, length=240)
            progress_bar.pack(fill=tk.Y, expand=1, side=tk.BOTTOM)

        # Measure how long it takes
        t1 = time.time()

        # Setup output path
        if outputpath==None and photonfilename==None:return

        #create path if not exists
        if not outputpath==None:
            if not os.path.exists(outputpath):
                os.makedirs(outputpath)

        # if we output to PhotonFile we need a place to store RunLengthEncoded images
        if not photonfilename==None:
            rlestack=[]

        # Load 3d Model in memory
        points, normals = self.load_binary_stl(stlfilename, scale=scale)
        # Check if inside build area
        if (self.cmin[0]<0 or self.cmin[2]<0 or self.cmin[1]<0 or
           self.cmax[0]>1440 or self.cmax[2]>2560 ):
           size=(self.cmax[0]-self.cmin[0],self.cmax[1]-self.cmin[1],self.cmax[2]-self.cmin[2])
           sizestr="("+str(int(size[0]*0.047))+"x"+str(int(size[2]*0.047))+")"
           areastr="(65x115)"
           errmsg="Model is too big "+sizestr+"for build area "+areastr+". Maybe try another orientation, use the scale argument (-s or --scale) or cut up the model."
           if not self.gui: 
              print (errmsg)
           else:
              sys.tracebacklimit = None
              raise Exception(errmsg)
              sys.tracebacklimit = 0
           sys.exit() # quit() does not work if we make this an exe with cx_Freeze
        # extract x and z to make 2d normals and normalize these
        normals2D=numpy.delete(normals,1,1)
        l = numpy.sqrt(numpy.power(normals, 2).sum(-1))[..., numpy.newaxis]
        normals2D = 2*normals2D / l

        # Slice settings
        #   model dimensions are in pixels/voxels of size 0.047mm,
        #   so we need to recalc layerheight in mm to voxelheight of 0.047mm
        layerHeight = layerheight / 0.047   # recalc to 0.047mm units
        maxHeight = self.modelheight        # modelheight is in 0.047mm units
        nrSlices = 1 + int(maxHeight / layerHeight)

        # Determine which triangles are in which slices
        slicepointindices = []
        # construct layers
        for sliceNr in range(nrSlices+1):
            l=[]
            slicepointindices.append ( l )

        # map tris to layer
        # all coordinates are now in 0.047 size voxels
        # aso layerHeight is in 0.047 steps
        y=1
        #print ("modelHeight,layerheight,nrSlices",maxHeight,layerheight,nrSlices)
        pointsAppended=0
        for i in range(0,len(points), 3):
            p0 = points[i + 0]
            p1 = points[i + 1]
            p2 = points[i + 2]
            minY = min(p0[y], p1[y], p2[y])
            maxY = max(p0[y], p1[y], p2[y])
            minSlice = int(minY / layerHeight)
            maxSlice = int(maxY / layerHeight) + 1
            #print ("Tri:",i,minY,maxY,minSlice,maxSlice)
            for sliceNr in range(minSlice, maxSlice+1):
                slicepointindices[sliceNr].append(i)
                #print ("append to",sliceNr)
            pointsAppended=pointsAppended+1
        if (len(points)//3!=pointsAppended):
            raise Exception ("Bug found. Not all triangles are stored in layers!")
        #print (len(points)//3,pointsAppended)
        #show layers
        #for sliceNr in range(nrSlices+1):
        #    print (sliceNr,len(slicepointindices[sliceNr]))

        # Slice model
        #contourColor = (255, 255, 255)  # alpha 255 is NOT transparent
        contourColor = (255)  # alpha 255 is NOT transparent
        # innerColor = (0, 0, 255)
        innerColor = (128)

        for sliceNr in range(0, nrSlices):
            # Filename for new slice
            sliceBottom = sliceNr * layerHeight
            sliceTop = sliceBottom + layerHeight
            if not outputpath == None:
                Sstr = "%04d" % sliceNr
                filename = outputpath+Sstr + ".png"

            # Start with empty image for slice (3 bytes depth is 2.5x slower than 1 byte depth)
            #img = numpy.zeros((2560, 1440, 3), numpy.uint8)
            img = numpy.zeros((2560, 1440, 1), numpy.uint8)

            # Clear fillpoints
            fillpoints = []
            """
            lines=[]
            nors=[]
            ps=[]
            """

            # Traverse all triangles
            for pidx in slicepointindices[sliceNr]:                
                p0 = points[pidx + 0]
                p1 = points[pidx + 1]
                p2 = points[pidx + 2]
                n2d= normals2D[pidx//3]
                # Check which part of triangle is inside slice
                polypoints = triInSlice.triInSlice(p0, p1, p2, sliceBottom, sliceTop)
                # Draw filled poly, fillConvexPoly is much faster than fillPoly, but poly should be convex...
                if polypoints:
                    # if we do fill on all lines, do we need fillConvexPoly?
                    cv2.fillConvexPoly(img, numpy.array([polypoints], dtype='int32'), color=contourColor)                    
                    # Add points for which to floodfillpoints using normal but only if normal not along y
                    if not (n2d[0] == 0 and n2d[1] == 0):
                        nrpoints = len(polypoints)
                        for idx in range(nrpoints):
                            pfrom = polypoints[idx]
                            pto = polypoints[(idx + 1) % nrpoints]                            
                            pmid = ((pfrom[0] + pto[0]) / 2, (pfrom[1] + pto[1]) / 2)
                            pfill = (int((pmid[0] - n2d[0])), int((pmid[1] - n2d[1])))
                            # Check if point inside triangle(s) - https://stackoverflow.com/questions/2049582/how-to-determine-if-a-point-is-in-a-2d-triangle
                            # Pikachu_repaired.STL with check 9-11sec, without 10-12sec
                            #"""
                            #inTri1=False
                            #inTri2=False
                            """
                            inTri1=Stl2Slices.PointInTriangle(pfill,
                            #inTri1=triInSlice.PointInTriangle(pfill,
                                                              polypoints[(idx+0) % nrpoints],
                                                              polypoints[(idx+1) % nrpoints],
                                                              polypoints[(idx+2) % nrpoints])
                            if nrpoints>3:
                                inTri2=Stl2Slices.PointInTriangle(pfill,
                                #inTri2=triInSlice.PointInTriangle(pfill,
                                                                  polypoints[(idx+0) % nrpoints],
                                                                  polypoints[(idx+1) % nrpoints],
                                                                  polypoints[(idx-1) % nrpoints])
                            else:
                                inTri2=inTri1
                            if not inTri1 and not inTri2:
                                fillpoints.append(pfill)
                            """
                            fillpoints.append(pfill)
                            """
                            pfrom = polypoints[idx % nrpoints]#(int(pfrom[0]),int(pfrom[1]))
                            pto   = polypoints[(idx+1) % nrpoints] #(int(pto[0]), int(pto[1]))
                            lines.append((pfrom,pto))
                            nors.append(n2d)
                            ps.append([p0,p1,p2])
                            """
                            
            # Floodfill all points
            tester = img.copy()
            nrTests = 0
            nrFills = 0
            nrRedos = 0
            nr = 0

            #fillPoint=(100,30)
            #cv2.circle(img,fillPoint,10,192,1)
            #cv2.floodFill(img, mask=None, seedPoint=fillPoint, newVal=100)  # 80% of time
            #cv2.floodFill(img, mask=None, seedPoint=fillPoint, newVal=100)  # 80% of time
            #cv2.imwrite("STLs/legocog/_test.png", img)
            #quit()

            #for idx,fillPoint in enumerate(fillpoints):
            """
            for y in range(0,2560):            
                oldcol=0
                inShape=False
                for x in range (0,1440):
                    col=1#img[y,x]
                    if oldcol!=col: 
                        inShape!=inShape
                        col=oldcol    
                    if inShape:
                        img[y,x]=innerColor
            """

            for fillPoint in fillpoints:
                # Check if fill is necessary at fillpoint (if fillpoint still has background color = 0,0,0)) and not fill color (=innerColor)
                pxColor = (img[fillPoint[1], fillPoint[0], 0]#,
                           #img[fillPoint[1], fillPoint[0], 1],
                           #img[fillPoint[1], fillPoint[0], 2]
                           )
                #if pxColor == (0, 0, 0):
                if pxColor == (0):
                    # Do a testfill on tester
                    cv2.floodFill(tester, mask=None, seedPoint=fillPoint, newVal=innerColor) # 80% of time
                    nrTests += 1
                    # And check if fill (on tester) reaches (0,0) and thus we are filling outside of model contour
                    #outerColor = (tester[0, 0, 0], tester[0, 0, 1], tester[0, 0, 2])
                    outerColor = (tester[0, 0, 0])
                    # If fill was necessary and fill in tester stayed inside model, then we apply fill on img
                    #if outerColor == (0, 0, 0):
                    if outerColor == (0):
                        cv2.floodFill(img, mask=None, seedPoint=fillPoint, newVal=innerColor)
                        nrFills += 1
                    else:  # we destroyed tester and have to repair it by making a copy of img
                        """
                        fname=("STLs/3DBenchy/%04d" % sliceNr) +"-"+("%04d" % nrTests)+".png"
                        print (fname)
                        print ("fillPoint,oldColor: ",fillPoint,pxColor)
                        print ("line,normal       : ",lines[idx],nors[idx])
                        print ("(0,0):",outerColor)
                        print ("3D Tri:")
                        q0=(0,0,0)
                        q1 = (ps[idx][1][0]-ps[idx][0][0],ps[idx][1][1]-ps[idx][0][1],ps[idx][1][2]-ps[idx][0][2])
                        q2 = (ps[idx][2][0] - ps[idx][0][0], ps[idx][2][1] - ps[idx][0][1], ps[idx][2][2] - ps[idx][0][2])
                        print("p0: {:.3f} {:.3f} {:.3f}".format(ps[idx][0][0], ps[idx][0][1], ps[idx][0][2]))
                        print("p1: {:.3f} {:.3f} {:.3f}".format(ps[idx][1][0], ps[idx][1][1], ps[idx][1][2]))
                        print("p2: {:.3f} {:.3f} {:.3f}".format(ps[idx][2][0], ps[idx][2][1], ps[idx][2][2]))
                        print ("q0->1: {:.3f} {:.3f} {:.3f}".format(q1[0],q1[1],q1[2]))
                        print ("q0->2: {:.3f} {:.3f} {:.3f}".format(q2[0], q2[1], q2[2]))

                        #cv2.floodFill(tester, mask=None, seedPoint=fillPoint, newVal=48)  # 80% of time
                        fillPointColor = (128)
                        lines[idx]=((int(lines[idx][0][0]),int(lines[idx][0][1])),(int(lines[idx][1][0]), int(lines[idx][1][1])))
                        cv2.line(img, pt1=lines[idx][0], pt2=lines[idx][1], color=48, thickness=1)
                        cv2.line(img, pt1=fillPoint, pt2=fillPoint, color=fillPointColor, thickness=1)
                        cv2.circle(img,fillPoint,20,fillPointColor,1)
                        cv2.imwrite(fname, img)
                        quit()
                        """
                        tester = img.copy()
                        nrRedos += 1
            # Debug: print nr of retries
            #print("sliceNr, nrTests, nrFills, nrRedos", sliceNr,nrTests, nrFills, nrRedos)

            # Debug: mark fill points
            # fillPointColor = (0,255,255)
            """
            fillPointColor = (128)
            for fillpoint in fillpoints:
                # Debug
                cv2.line(img, pt1=fillpoint, pt2=fillpoint, color=fillPointColor, thickness=1)
            """

            # Save image
            #if (img[0, 0, 0], img[0, 0, 1], img[0, 0, 2]) == (0, 0, 0):
            if (img[0,0]) == (0):
                if photonfilename==None:
                    #print("Saved ",sliceNr, "/", nrSlices, "->", filename)
                    cv2.imwrite(filename, img)
                else:
                    #print("Encoded", sliceNr, "/", nrSlices, "->", filename)
                    # Convert slice to 1 color component (keep white and red)
                    #imgarr8 = img[:, :, 2]
                    imgarr8 = img
                    # we need to rotate img 90 degrees
                    #imgarr8 = numpy.rot90(imgarr8, axes=(1, 0))  # we need 1440x2560
                    # encode bitmap numpy array to rle
                    img1D=imgarr8.flatten(0)
                    rlestack.append(rleEncode.encodedBitmap_Bytes_numpy1DBlock(img1D))
                    #rlestack.append(bytes([0x00]))
            else:
                if not self.gui: print("Slice Error: ", filename)

            # Show progress in terminal
            if not self.gui:
                msg="Slicing ... "+str(sliceNr)+" / " + str(nrSlices)
                sys.stdout.write (msg)
                sys.stdout.write('\r')
                sys.stdout.flush()

            # Update GUI progress bar if gui active
            if self.gui:
                try: # Check if user aborted/closed window
                    self.popup.update()
                    progress=100*sliceNr/nrSlices
                    self.progress_var.set(progress)
                except Exception:
                    sys.exit() # quit() does not work if we make this an exe with cx_Freeze

        if not self.gui: print () # close progress stdout and go to new line

        if not photonfilename==None:
            tempfilename=os.path.join(self.installpath,"newfile.photon")
            photonfile=PhotonFile(tempfilename)
            photonfile.readFile()
            photonfile.Header["Layer height (mm)"]= PhotonFile.float_to_bytes(layerheight)
            photonfile.Header["Exp. time (s)"]    = PhotonFile.float_to_bytes(normalexposure)
            photonfile.Header["Exp. bottom (s)"]  = PhotonFile.float_to_bytes(bottomexposure)
            photonfile.Header["# Bottom Layers"]  = PhotonFile.int_to_bytes(bottomlayers)
            photonfile.Header["Off time (s)"]     = PhotonFile.float_to_bytes(offtime)
            photonfile.replaceBitmaps(rlestack)
            photonfile.writeFile(photonfilename)

        if not self.gui: print("Elapsed: ", "%.2f" % (time.time() - t1), "secs")


