"""
Needed (external) packages by other modules
 cython
 numpy
 opencv-python

Usage
1) PhotonSlicer bunny.stl photon 0.05
Slices ./bunny.stl to ./bunny.photon with sliceheight 0.05

2) PhotonSlicer STLs/bunny.stl hare.photon 0.05
     Slices ./STLs/bunny.stl to ./hare.photon with sliceheight 0.05
   PhotonSlicer STLs/bunny.stl  subdir/hare.photon 0.05
     Slices ./STLs/bunny.stl to ./subdir/hare.photon with sliceheight 0.05
   PhotonSlicer STLs/bunny.stl  /subdir/hare.photon 0.05
     Slices ./STLs/bunny.stl to /subdir/hare.photon with sliceheight 0.05
    
3) PhotonSlicer bunny.stl ./animals/photon 0.05
Slices ./bunny.stl to ./animals/bunny.photon with sliceheight 0.05

4) PhotonSlicer bunny.stl images 0.05
Slices ./bunny.stl to ./bunny/0001.png , ./bunny/0002.png , ... with sliceheight 0.05

5) PhotonSlicer bunny.stl userdir/ 0.05
Slices ./bunny.stl to ./userdir/001.png , ./userdir/0002.png , ... with sliceheight 0.05

For 1,2,3 you can add optional arguments for the resin exposure type etc.
For 5 only last directory level may be new

"""

# import the necessary packages
import argparse
from argparse import RawTextHelpFormatter
import os
import ntpath   # to extract filename on all OS'es
import re       # needed for case insentive replace

from Stl2Slices import *

stlfilename=None
outputpath=None
outputfile=None
gui=False

# If cx_Freeze, check if we are in console or gui model
if sys.stdout==None:
    gui=True
else:
    gui=False	
"""
try:
	gui=True
	sys.stdout.write("\n")
	sys.stdout.flush()
except IOError:
	gui=False
"""
def is_bool(arg):
    global gui
    if arg.lower() in ('yes', 'true', 't', 'y', '1'):
        gui = True
        return True
    elif arg.lower() in ('no', 'false', 'f', 'n', '0'):
        gui = False
        return False
    else:
        raise argparse.ArgumentTypeError('boolean value expected.')

def is_valid_file(arg):
    global stlfilename
    arg=os.path.normpath(arg) # convert all / to \ for windows and vv for linux
    if not os.path.isfile(arg):
        raise argparse.ArgumentTypeError("stlfilename argument ('"+arg+"') does not point to valid STL file")
    elif not arg[-4:].lower()==".stl":
	    raise argparse.ArgumentTypeError("stlfilename argument ('"+arg+"') does not point to valid STL file")
    else:
        stlfilename = arg
        return arg

def is_valid_output(arg):
    global stlfilename
    global outputpath
    global outputfile
    if arg=="photon": #1 output to same dir and use same name but end with .photon
        # stlfilename is checked to end with '.stl' so replace last 4 with '.photon'
        outputfile=stlfilename[:-4]+'.photon'  
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
        # stlfilename is checked to end with '.stl' so remove last 6 to get new dir
        bare_stlfilename=os.path.basename(stlfilename)[:-4]      
        outputfile=os.path.join(arg[:-6],bare_stlfilename+".photon")
        #check if parent directory exists
        pardir=os.path.dirname(arg)
        if os.path.isdir(pardir):
            return outputfile 
        else:
            raise argparse.ArgumentTypeError("photonfilename path does not exist")     
        return outputfile
    elif arg=="images": #4 output to same dir under new subdir with name of stl
        # stlfilename is checked to end with '.stl'
        outputpath=stlfilename[:-4]+os.path.sep
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
        # stlfilename is checked to end with '.stl'
        bare_stlfilename=os.path.basename(stlfilename)[:-4]      
        # make new path
        outputpath=os.path.join(arg[:-6],bare_stlfilename+os.path.sep)
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
class argparse_logger(argparse.ArgumentParser):
    def _print_message(self,message,stderr):
        print (message)
        sys.tracebacklimit = None
        raise Exception(message)
        sys.tracebacklimit = 0

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
                             "version    : October 28, 2018 \n" +
                             #"0123456789001234567890012345678900123456789001234567890012345678900123456789001234567890\n"+
                             "description: Slices a STL (binary file) to images or a photon file.\n"
                             "\n"+
                             "examples: PhotonSlicer.cmd -s ./STLs/Cube.stl                         -> ./STLs/Cube.photon\n"
                             "          PhotonSlicer.cmd -s ./STLs/Cube.stl -p photon -l 0.05       -> ./STLs/Cube.photon\n"
                             "          PhotonSlicer.cmd -s ./STLs/Cube.stl -p /home/photon -l 0.05 -> /home/Cube.photon\n"
                             "          PhotonSlicer.cmd -s ./STLs/Cube.stl -p /Sqrs.photon -l 0.05 -> /Sqrs.photon\n"
                             "          PhotonSlicer.cmd -s ./STLs/Cube.stl -p images -l 0.05    -> ./STLs/Cube/0001.png,..\n"
                             "          PhotonSlicer.cmd -s ./STLs/Cube.stl -p ./sliced/ -l 0.05 -> ./sliced/0001.png,..\n"
                             ,formatter_class=argparse.RawTextHelpFormatter)

ap.add_argument("-s","--stlfilename",
                required=True,
                help="name of (binary) stl file to import")
ap.add_argument("-p","--photonfilename",
                #type=str,
                help="photon file name (ends with '.photon') OR \n"+
                     "output directory (ends with '/') for images OR \n"+
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
                default=6.5,type=is_bool,
                help="show progress in popup window")
    
args = vars(ap.parse_args())

# Check photonfilename is valid only now (that we have stlfilename)
sf=(args["stlfilename"])
type = is_valid_file(sf)
#print ("sf",sf, stlfilename)

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

S2I=Stl2Slices(stlfilename=stlfilename,
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
