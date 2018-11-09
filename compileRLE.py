# Used to compile rleEncode.pyx
# Linux Mint
#   sudo apt-get install python3-dev
#   python3 compileRLE.py build_ext --inplace
#
# Windows 10 (64)
# "C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
#   python compileRLE.py build_ext --inplace

from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    name="Fast 1-bit RLE encoding of 1440x2560x8 images.",
    ext_modules=cythonize("rleEncode.pyx"),
    include_dirs=[numpy.get_include()]
)