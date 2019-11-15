# Used to compile triInSlice.pyx
# Linux Mint
#   sudo apt-get install python3-dev
#   python3 compileTIS.py build_ext --inplace
#
# Windows 10 (64)
# "C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
#   python compileTIS.py build_ext --inplace

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy


setup(
    ext_modules=[
        Extension("triInSlice", ["triInSlice.c"],
                  include_dirs=[numpy.get_include()]),
    ],
)