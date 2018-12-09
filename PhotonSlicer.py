# Todo/Bugs
#  if force GPU is default....why than console mode?
#  keep opengl center in viewport.updateScale?

"""
Needed (external) packages by other modules
 Cython
 numpy
 opencv-python
 PyOpenGL
 PyOpenGL-accelerate

Usage: use --help argument
       
       safe mode - command line only, CPU slicing, sliceheight 0.05mm:
            PhotonSlicer.py -s STLs/3dBenchy.stl

       gui mode - dialog to select stl file and photon file, GPU slicing, sliceheight 0.05mm:
            PhotonSlicer.py -s dialog -p dialog -f False -g True
            
"""

# import the necessary packages
import argparse
from argparse import RawTextHelpFormatter
import os
import ntpath   # to extract filename on all OS'es
import re       # needed for case insentive replace

from Stl2Slices import *
from Svg2Slices import *
from GL_Stl2Slices import *

filename=None
outputpath=None
outputfile=None
gui=False

# If cx_Freeze, check if we are in console or gui model
"""
try:
	gui=True
	sys.stdout.write("\n")
	sys.stdout.flush()
except IOError:
	gui=False
"""
def is_bool_gui(arg):
    global gui
    if arg.lower() in ('yes', 'true', 't', 'y', '1'):
        gui = True
        return True
    elif arg.lower() in ('no', 'false', 'f', 'n', '0'):
        gui = False
        return False
    else:
        raise argparse.ArgumentTypeError('boolean value expected.')

def is_bool(arg):
    if arg.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif arg.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('boolean value expected.')

def is_valid_file(arg):
    global filename
    global gui
    global args
    if arg=="dialog":
        if gui:
            import tkinter
            from tkinter.filedialog import askopenfilename
            root=tkinter.Tk() # define root (which is opened by askopenfilename anyway) so we can destroy it afterwards
            root.withdraw()   # hide root
            filename=askopenfilename(initialdir = ".",title = "Open file",filetypes = (("stl files","*.stl"),("svg files","*.svg")))
            root.destroy()    # destroy root
            if not (filename):
                print ("Abort, no file selected.")
                sys.exit() 
            args["filename"]=filename
            return filename
        else:
            raise argparse.ArgumentTypeError('filedialog only available in GUI mode.')            

    arg=os.path.normpath(arg) # convert all / to \ for windows and vv for linux
    if not os.path.isfile(arg):
        raise argparse.ArgumentTypeError("filename argument ('"+arg+"') does not point to valid STL/SVG file")
    elif not (arg[-4:].lower()==".stl" or arg[-4:].lower()==".svg"):
	    raise argparse.ArgumentTypeError("filename argument ('"+arg+"') does not point to valid STL/SVG file")
    else:
        filename = arg
        return arg

def is_valid_output(arg):
    global filename
    global outputpath
    global outputfile
    if arg=="dialog":
        if gui:
            import tkinter
            from tkinter.filedialog import asksaveasfilename
            root=tkinter.Tk() # define root (which is opened by askopenfilename anyway) so we can destroy it afterwards
            root.withdraw()   # hide root
            outputfile=asksaveasfilename(initialdir = ".",title = "Save to file",filetypes = (("photon files","*.photon"),))
            root.destroy()    # destroy root
            if not (outputfile):
                print ("Abort, no file selected.")
                sys.exit() 
            args["photonfilename"]=outputfile
            return outputfile
        else:
            raise argparse.ArgumentTypeError('filedialog only available in GUI mode.')            

    if arg=="dialogdir":
        if gui:
            import tkinter
            from tkinter.filedialog import askdirectory
            root=tkinter.Tk() # define root (which is opened by askopenfilename anyway) so we can destroy it afterwards
            root.withdraw()   # hide root
            outputpath=askdirectory(initialdir = ".",title = "Save to directory")
            root.destroy()    # destroy root
            if not (outputpath):
                print ("Abort, no file selected.")
                sys.exit() 
            outputpath=outputpath+os.path.sep                 
            args["photonfilename"]=outputpath
            return outputpath
        else:
            raise argparse.ArgumentTypeError('filedialog only available in GUI mode.')            

    if arg=="photon": #1 output to same dir and use same name but end with .photon
        # filename is checked to end with '.stl' so replace last 4 with '.photon'
        outputfile=filename[:-4]+'.photon'  
        return outputfile
    elif arg.endswith(".photon"): #2 output to current working dir but  use same name but end with .photon
        arg=os.path.normpath(arg) # make sure the slashes are correct for os
        # if not starts with slash we have relative path so we append current path
        if not arg.startswith('/') and not arg.startswith('\\'):
           arg=os.path.join(os.getcwd(),arg)           
        #check if parent directory exists
        pardir=os.path.dirname(arg)
        if os.path.isdir(pardir):
            outputfile = arg
            return outputfile 
        else:
            raise argparse.ArgumentTypeError("photonfilename path does not exist")
        return outputfile
    elif arg.endswith("/photon") or arg.endswith("\\photon") : #3 use same name as stl but output to given dir
        # make sure the slashes are correct for os
        arg=os.path.normpath(arg)
        # if not starts with slash we have relative path so we append current path
        if not arg.startswith('/') and not arg.startswith('\\'):
           arg=os.path.join(os.getcwd(),arg)           
        # filename is checked to end with '.stl' so remove last 6 to get new dir
        bare_filename=os.path.basename(filename)[:-4]      
        outputfile=os.path.join(arg[:-6],bare_filename+".photon")
        #check if parent directory exists
        pardir=os.path.dirname(arg)
        if os.path.isdir(pardir):
            return outputfile 
        else:
            raise argparse.ArgumentTypeError("photonfilename path does not exist")     
        return outputfile
    elif arg=="images": #4 output to same dir under new subdir with name of stl
        # filename is checked to end with '.stl'
        outputpath=filename[:-4]+os.path.sep
        return outputpath
    elif arg.endswith("/") or arg.endswith("\\") : #5 output to user defined path
        # make sure the slashes are correct for os
        arg=os.path.normpath(arg)+os.path.sep 
        # if not starts with slash we have relative path so we append current path
        if not arg.startswith('/') and not arg.startswith('\\'):
           arg=os.path.join(os.getcwd(),arg)           
        #check if parent directory exists
        pardir=os.path.dirname(arg) #just removes last '/'
        pardir=os.path.dirname(pardir)
        if os.path.isdir(pardir):
            outputpath = arg
            return outputpath
        else:
            raise argparse.ArgumentTypeError("photonfilename argument contains more than 1 new dir level")
    elif arg.endswith("/images") or arg.endswith("\\images") : #6
        # make sure the slashes are correct for os
        arg=os.path.normpath(arg)
        # if not starts with slash we have relative path so we append current path
        if not arg.startswith('/') and not arg.startswith('\\'):
           arg=os.path.join(os.getcwd(),arg)           
        # filename is checked to end with '.stl'
        bare_filename=os.path.basename(filename)[:-4]      
        # make new path
        outputpath=os.path.join(arg[:-6],bare_filename+os.path.sep)
        #check if parent directory exists
        pardir=os.path.dirname(outputpath) #just removes last '/'
        pardir=os.path.dirname(pardir)
        if os.path.isdir(pardir):
            return outputpath
        else:
            raise argparse.ArgumentTypeError("photonfilename argument contains more than 1 new dir level")
    else:
        raise argparse.ArgumentTypeError("photonfilename argument not valid")

# Rewrite argparse _print_message to it prints using the print command
sys.tracebacklimit = 0
class argparse_logger(argparse.ArgumentParser):
    def _print_message(self,message,stderr):        
        print (message)
        #raise Exception(message)
        #pass         

# If we are in GUI we want to output all prints to log.txt
import sys
import datetime
import time
if gui:
    # Get path of script/exe for local resources like iconpath and newfile.photon
    if getattr(sys, 'frozen', False):# frozen
        installpath = os.path.dirname(sys.executable)
    else: # unfrozen
        installpath = os.path.dirname(os.path.realpath(__file__))
    logfilename=os.path.join(installpath,"log.txt")
    sys.stdout = open(logfilename, 'a+')  
    sys.stderr = open(logfilename, 'a')  
    ts = time.time()
    print ("")
    print ("---------------------------")
    print (datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

# construct the argument parse and parse the arguments
ap = argparse_logger(description=
#ap = argparse.ArgumentParser(description=
                             "version    : December 2, 2018 \n" +
                             #"0123456789001234567890012345678900123456789001234567890012345678900123456789001234567890\n"+
                             "description: Slices a STL (binary) or Slic3r SVG file to images or a photon file.\n"
                             "\n"+
                             "examples: PhotonSlicer.exe -s ./STLs/Cube.stl                         -> ./STLs/Cube.photon\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.svg                         -> ./STLs/Cube.photon\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.stl -p photon -l 0.05       -> ./STLs/Cube.photon\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.stl -p /home/photon -l 0.05 -> /home/Cube.photon\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.stl -p /Sqrs.photon -l 0.05 -> /Sqrs.photon\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.stl -p images -l 0.05    -> ./STLs/Cube/0001.png,..\n"
                             "          PhotonSlicer.exe -s ./STLs/Cube.stl -p ./sliced/ -l 0.05 -> ./sliced/0001.png,..\n"
                             "          PhotonSlicer.exe -s dialog -p dialog -g True -f False    -> full GUI is used\n"
                             ,formatter_class=argparse.RawTextHelpFormatter)

ap.add_argument("-s","--filename",
                required=True,
                help="name of (binary) stl or svg file to import\n"+
                     "'dialog' for dialog to select stl file (only in GUI mode) OR\n")
ap.add_argument("-p","--photonfilename",
                #type=str,
                help="photon file name (ends with '.photon') OR \n"+
                     "output directory (ends with '/') for images OR \n"+
                     "'dialog' to select photon file (only in GUI mode) OR\n"+
                     "'dialogdir' to select dir to save images (only in GUI mode) OR\n"+
                     "'photon' as argument to generate photon file with same name OR \n"+
                     "'images' to generate images in directory with same name as stl\n"+
                     "these can be combined e.g. './subdir/photon'")
ap.add_argument("-l","--layerheight",
                default=0.05,type=float,
                help="layer height in mm")
ap.add_argument("-r", "--rescale", type=float, required=False,
                help="scales model and offset")
ap.add_argument("-t", "--exposure", required=False,
                default=8.0,type=float,
                help="normal exposure time (sec)")
ap.add_argument("-be", "--bottomexposure", required=False,
                default=90,type=float,
                help="exposure time for bottom layers")
ap.add_argument("-bl", "--bottomlayers", required=False,
                default=8,type=int,
                help="nr of layers with exposure for bottom")
ap.add_argument("-o", "--offtime", required=False,
                default=6.5,type=float,
                help="off time between layers (sec)")
ap.add_argument("-g", "--gui", required=False,
                default=True,type=is_bool_gui,
                help="show progress in popup window")
ap.add_argument("-f", "--forceCPU", required=False,
                default=True,type=is_bool,
                help="force slicing with CPU instead of GPU/OpenGL")
ap.add_argument("-e", "--execute", required=False,
                help="execute command when done \n"+
                     "'photon' will be replace with output filename \n"+
                     "if argument is 'folder' a file browser will open")
args = vars(ap.parse_args())


# Check photonfilename is valid only now (that we have filename)
sf=(args["filename"])
is_valid_file(sf)
filetype = args["filename"][-4:].lower()

pf=(args["photonfilename"])
if pf==None: pf="photon"
is_valid_output(pf)
#print ("pf",pf, outputpath, outputfile)
#quit()

# No raised errors, so we have a valid stl file, a valid output dir or output file (photon)

# set values for optional arguments
scale = float(args["rescale"]) if args["rescale"] else 1.0
if scale==0.0: scale=1.0
layerheight = float(args["layerheight"])
normalexposure = float(args["exposure"])
bottomexposure = float(args["bottomexposure"])
bottomlayers = int(args["bottomlayers"])
offtime = float(args["offtime"])
linkedcmd = args["execute"]
forceCPU = args["forceCPU"]

# Some arguments do not work together
if not forceCPU and not gui: #default is false, so user explicitly set it to True
    print ("You cannot use opengl without gui.")
    sys.exit()

if filetype == ".svg":
    S2I=Svg2Slices(svgfilename=filename,
                   outputpath=outputpath,
                   photonfilename=outputfile,
                   layerheight=layerheight,
                   scale=scale,
                   normalexposure=normalexposure,
                   bottomexposure=bottomexposure,
                   bottomlayers=bottomlayers,
                   offtime=offtime,
                   gui=gui
                   )
elif filetype == ".stl":
    if forceCPU:
        S2I=Stl2Slices(stlfilename=filename,
                   outputpath=outputpath,
                   photonfilename=outputfile,
                   layerheight=layerheight,
                   scale=scale,
                   normalexposure=normalexposure,
                   bottomexposure=bottomexposure,
                   bottomlayers=bottomlayers,
                   offtime=offtime,
                   gui=gui
                   )

    else: #use GPU/OpenGL
        S2I=GL_Stl2Slices(stlfilename=filename,
                   outputpath=outputpath,
                   photonfilename=outputfile,
                   layerheight=layerheight,
                   scale=scale,
                   normalexposure=normalexposure,
                   bottomexposure=bottomexposure,
                   bottomlayers=bottomlayers,
                   offtime=offtime
                   )

import subprocess
import platform
import os
def open_folder(path):
    if platform.system() == 'Darwin':
        subprocess.Popen(['open', path])
        #os.startfile(path)
    elif platform.system() == 'Linux':
        subprocess.Popen(['xdg-open', path])
        #os.startfile(path)
    else: #platform.system() == 'Windows':
        os.startfile(path)
        #os.startfile(path)

if not linkedcmd==None:
    linkedcmd=linkedcmd.replace("photon",outputfile)
    os.system(linkedcmd)

    if linkedcmd=="folder":
        folderpath=os.path.dirname(outputfile)
        open_folder(path=folderpath)  # open current directory