# Used to compile rleEncode.pyx
#   sudo apt-get install python3-dev
#   python3 compileRLE.py build_ext --inplace

from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    name="Fast 1-bit RLE encoding of 1440x2560x8 images.",
    ext_modules=cythonize("rleEncode.pyx"),
    include_dirs=[numpy.get_include()]
)