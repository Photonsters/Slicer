# Used to compile rleEncode.pyx
#   sudo apt-get install python3-dev
#   python3 compileRLE.py build_ext --inplace

from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    name="Fast check if tri between two heights (in slice).",
    ext_modules=cythonize("triInSlice.pyx"),
    include_dirs=[numpy.get_include()]
)