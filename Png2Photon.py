import time
import os
import sys # for stdout

import cv2

from PhotonFile import *
import rleEncode

# python PhotonSlicer.py -s D:\NardJ\PhotonSlicer\STLs\legocog\*.png -p D:\NardJ\PhotonSlicer\STLs\test.photon -v true -g False

class Png2Photon:

	def __init__(self, pngfolder,
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
		if photonfilename==None:return

        # Get input files
		files=os.listdir(pngfolder[:-5])
		files.sort(key=str.lower)

		rlestack=[]

        # draw layer for layer
		sliceNr=0
		nrSlices=len(files)
		for file in files:
            # Read image
			filepath=os.path.join(pngfolder[:-5],file)
			img = cv2.imread(filepath)
			# print (sliceNr,file,filepath)
			# print (img.shape)

            # Check if 8 image-depth
			"""
			imgDepth = img.shape[3]
			if not imgDepth==8:
			    print ("Only 8 bit png images are allowed.")
			    sys.exit()
			"""

			#Encode image
			imgarr8=img[:,:,1]
			img1D=imgarr8.flatten(0)
			rlestack.append(rleEncode.encodedBitmap_Bytes_numpy1DBlock(img1D))

			# Show progress in terminal
			if not self.gui:
				msg="Reading ... "+str(sliceNr)+" / " + str(nrSlices)
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
