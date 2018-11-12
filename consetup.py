# This script is working but needs a major overhaulling
# Check https://github.com/makewitharduino/Scratio/blob/master/setup.py for inspiration
# X3msnake 180726
#
################################
#
# just build	    	python consetup.py build -b ..\				#Builds on the folder above
# build installer    python consetup.py build -b ..\  bdist_msi -d ..\		#Builds on the folder above
#  
# OR make exe directory to zip
#
# 1) python consetup.py build -b ..\PhotonSlicer.buildcon  install_exe -d ..\PhotonSlicer.installcon
# 
# 2) in .build move all dlls (tcl86t.dll,tk86t.dll,VCRUNTIME140.dll,python36.dll) from install rootdir to libs folder
#
# 3) following files (in order of size) are large and not necessary:
#           [
#            "numpy.core.mkl_avx512_mic.dll",
#            "numpy.core.mkl_avx512.dll",
#            "numpy.core.mkl_avx2.dll",
#            "numpy/core/mkl_avx.dll",
#            "numpy.core.libopenblas.dll",
#            "numpy.core.mkl_mc3.dll",
#            "numpy.core.mkl_mc.dll",
#
#            "numpy.core.svml_dispmd.dll"
#            "numpy.core.mkl_sequential.dll",
#
#            "numpy.core.vml_avx512.dll",
#            "numpy.core.vml_avx.dll",
#            "numpy.core.vml_avx2.dll",
#            "numpy.core.vml_avx512_mic.dll",
#            "numpy.core.mkl_vml_mc.dll",
#            "numpy.core.mkl_vml_mc3.dll",
#            "numpy.core.mkl_vml_mc2.dll",
#            "numpy.core.mkl_vml_def.dll"
#            ]
#
# 4) Remove all stl's except bunny.stl and cog.stl
#            
# 5) 7-Zip file - Resulting .7Z is 53MB
#
# Diff between Con and GUI is PhotonSlicer.exe and lib/library.zip 
#
#################################

import os
import sys
from cx_Freeze import setup, Executable
import numpy
import tkinter

shortcut_table = [
    ("DesktopShortcut",			# Shortcut
     "DesktopFolder",			# Directory_
     "PhotonSlicer",	# Name
     "TARGETDIR",				# Component_
     "[TARGETDIR]\PhotonSlicer.exe",  	# Target
     None,				# Arguments
     None,				# Description
     None,				# Hotkey
     "",				# Icon
     0,					# IconIndex
     None,				# ShowCmd
     "TARGETDIR",       # WkDir
     )
    ]

	
# Now create the table dictionary
msi_data = {"Shortcut": shortcut_table}

# Change some default MSI options and specify the use of the above defined tables
bdist_msi_options = {'data': msi_data}

# Dependencies are automatically detected, but it might need fine tuning.
# build_exe_options = {"packages": ["os", "numpy"],"include_files": [""], "include_msvcr" : True}
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))

build_exe_options = {
					"packages": ["os", "numpy"],
					"include_msvcr" : True,
					"excludes":["email","html","https","json","urllib","xml","xmlrpc","setuptools","pydoc_data"],
					"include_files":[
									#os.path.join(PYTHON_INSTALL_DIR,'DLLs','tcl86t.dll'), 
									#os.path.join(PYTHON_INSTALL_DIR,'DLLs','tk86t.dll'),
									"PhotonSlicer.gif",
									"newfile.photon",
									"STLs/"
								    ]
					}

os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Console" 
	
if 'bdist_msi' in sys.argv:
    sys.argv += ['--initial-target-dir', 'c:\PhotonSlicer']
	
setup(  name = "PhotonSlicer_Console",
        version = "0.1",
	    author= "Photonsters",
	    url="https://github.com/Photonsters",
        description = "Converts STL (binary) files to Images or PhotonFile.",
        options = {"build_exe": build_exe_options,"bdist_msi": bdist_msi_options},
        executables = [Executable(script="PhotonSlicer.py", base=base,icon="PhotonSlicer.ico",)]
)



