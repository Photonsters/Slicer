# This script is working but needs a major overhaulling
# Check https://github.com/makewitharduino/Scratio/blob/master/setup.py for inspiration
# X3msnake 180726
#
################################
#
# just build	    	python guisetup.py build -b ..\				            #Builds on the folder above
# build installer    python guisetup.py build -b ..\  bdist_msi -d ..\		#Builds on the folder above
#
# OR make exe directory to zip
#
# 1) python guisetup.py build -b ..\PhotonSlicer.build  install_exe -d ..\PhotonSlicer.install
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
# 4) 7-Zip file - Resulting .7Z is 64MB
#
################################

import os
import sys
from cx_Freeze import setup, Executable
import numpy
import tkinter
import OpenGL.platform.win32
import OpenGL.arrays.ctypesarrays
import OpenGL.arrays.ctypesparameters
import OpenGL.arrays.ctypespointers
import OpenGL.arrays.lists
import OpenGL.arrays.nones
import OpenGL.arrays.numbers
import OpenGL.arrays.strings
import OpenGL.platform.win32
import OpenGL.raw.GL
import OpenGL.GL
import OpenGL.GLU
import OpenGL.GLUT

shortcut_table = [
    ("DesktopShortcut",			# Shortcut
     "DesktopFolder",			# Directory_
     "PhotonSlicer",			# Name
     "TARGETDIR",				# Component_
     "[TARGETDIR]\PhotonSlicer.exe",  	# Target
     None,				# Arguments
     None,				# Description
     None,				# Hotkey
     "",				# Icon
     0,					# IconIndex
     None,				# ShowCmd
     "TARGETDIR",              		# WkDir
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
					"packages": ["os", "numpy","OpenGL.arrays"],
					"include_msvcr" : True,
					"excludes":["email","html","https","json","urllib","xmlrpc","setuptools","pydoc_data"],
                    "includes":["OpenGL.platform.win32","OpenGL.GLU.glustruct","numpy"],
					"include_files":[
									os.path.join(PYTHON_INSTALL_DIR,'DLLs','tcl86t.dll'),
									os.path.join(PYTHON_INSTALL_DIR,'DLLs','tk86t.dll'),
									"PhotonSlicer.gif",
									"newfile.photon",
                                    "base.vert",
                                    "mesh.vert",
                                    "quad.vert",
                                    "slice.vert",
                                    "base.frag",
                                    "mesh.frag",
                                    "quad.frag",
                                    "slice.frag",
									"STLs/"
								    ]
					}

os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

if 'bdist_msi' in sys.argv:
    sys.argv += ['--initial-target-dir', 'c:\PhotonSlicer']

setup(  name = "PhotonSlicer_GUI",
        version = "0.1",
	    author= "Photonsters",
	    url="https://github.com/Photonsters",
        description = "Converts STL (binary) files to Images or PhotonFile.",
        options = {"build_exe": build_exe_options,"bdist_msi": bdist_msi_options},
        executables = [Executable(script="PhotonSlicer.py", base=base,icon="PhotonSlicer.ico",)]
)
