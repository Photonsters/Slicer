# Used to compile triInSlice.pyx
# Linux Mint
#   sudo apt-get install python3-dev
#   python3 compileTIS.py build_ext --inplace
#
# Windows 10 (64)
# "C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
#   python compileTIS.py build_ext --inplace

from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    name="Fast check if tri between two heights (in slice).",
    ext_modules=cythonize("triInSlice.pyx"),
    include_dirs=[numpy.get_include()]
)