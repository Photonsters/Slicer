import time
import os
import sys # for stdout

from xml.dom import minidom
import cv2

from PhotonFile import *
import rleEncode


class Svg2Slices:
	cmin = [100, 100]
	cmax = [-100, -100]
	modelheight = 0

	def __init__(self, svgfilename, scale=1,
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

		# read and parse svg file
		xmldoc = minidom.parse(svgfilename)
		layers = xmldoc.getElementsByTagName('g')

		#contourColor = (255, 255, 255)  # alpha 255 is NOT transparent
		#contourColor = (255)  # alpha 255 is NOT transparent
		# innerColor = (0, 0, 255)
		innerColor = (128)

		scale=scale/0.047

		# draw layer for layer
		sliceNr=0
		nrSlices=len(layers)
		pLayers=[]
		for layer in layers:
			layer_id = layer.attributes['id'].value
			layer_z  = layer.attributes['slic3r:z'].value
			layer_polygons =layer.getElementsByTagName('polygon')
			img = numpy.zeros((2560, 1440, 1), numpy.uint8)
			pPolys=[]
			for layer_polygon in layer_polygons:
				layer_polygon_points = layer_polygon.attributes['points'].value
				pointString=layer_polygon_points.replace(',',' ')
				np_points = numpy.fromstring(pointString,dtype=float,sep=' ')
				np_points = np_points * scale
				nr_points = np_points.size
				nr_coords = nr_points//2
				np_coords = np_points.reshape(nr_coords,2)
				pPolys.append(np_coords)

				x = np_coords[:, 0]
				z = np_coords[:, 1]
				self.cmin = (min(self.cmin[0],x.min()), min(self.cmin[1],z.min()))
				self.cmax = (max(self.cmax[0],x.max()), max(self.cmax[1],z.max()))

			pLayers.append(pPolys)
			sliceNr=sliceNr+1

			# Show progress in terminal
			if not self.gui:
				msg="Reading ... "+str(sliceNr)+" / " + str(nrSlices)
				sys.stdout.write (msg)
				sys.stdout.write('\r')
				sys.stdout.flush()

		print("")

		# Center model and put on base
		trans    =  [0, 0]
		trans[0] = -(self.cmax[0] - self.cmin[0]) / 2 - self.cmin[0]
		trans[1] = -(self.cmax[1] - self.cmin[1]) / 2 - self.cmin[1]

		# We want the model centered in 2560x1440
		# 2560x1440 pixels equals 120x67
		trans[0] = trans[0] + 1440 / 2
		trans[1] = trans[1] + 2560 / 2

		sliceNr=0
		nrSlices=len(layers)
		for pLayer in pLayers:
			img = numpy.zeros((2560, 1440, 1), numpy.uint8)

			for pPoly in pLayer:
				# Center numpy array of points which is returned for fast OGL model loading
				pPoly = pPoly + trans
				# Fill poly
				cv2.fillPoly(img, numpy.array([pPoly],dtype='int32'), color=innerColor)                    

			if photonfilename==None:
				cv2.imwrite(filename, img)
			else:
				imgarr8 = img
				img1D=imgarr8.flatten(0)
				rlestack.append(rleEncode.encodedBitmap_Bytes_numpy1DBlock(img1D))    

			# Show progress in terminal
			if not self.gui:
				msg="Saving ... "+str(sliceNr)+" / " + str(nrSlices)
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

			sliceNr += 1


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


#test =  Svg2Slices(
#		svgfilename='STLs/pikachu_repaired.svg',
#		photonfilename="STLs/pikachu_svg.photon",
#		gui=False
#		)