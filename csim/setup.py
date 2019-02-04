from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext as build_pyx
import sys
import numpy
import os

# Jack Tyler 04/02
#
# OMP linking was improperly configured for Darwin machines running gcc-xx, and additional
# rpath to /usr/local/opt/gcc was required to properly link the OMP libraries. I'm assuming
# that this is Darwin-specific, so have therefore added an extra condition to the if-statement
# to only apply this fix to the Darwin architectures.
#

if sys.platform.startswith('darwin'):
    
    os.environ['CC'] = 'gcc-8'      # Replace with version of gcc installed

    # Bugfix 04/02: adjust the rpath .../gcc/8/ to gcc/xx/ as required to be coherent with the version above.
    # May be worth implementing automatic checking for the version of gcc symlinked with the terminal.

    setup(name='AltSim',
          ext_modules=[Extension('AltSim', ['AltSim.pyx'],
                                 include_dirs=[numpy.get_include()],
                                 extra_compile_args=['-O3', '-fopenmp'],
                                 extra_link_args=['-O3', '-fopenmp', '-Wl,-rpath,/usr/local/opt/gcc/lib/gcc/8/'])],
          cmdclass={'build_ext': build_pyx})

else:

    setup(name='AltSim',
          ext_modules=[Extension('AltSim', ['AltSim.pyx'],
                                 include_dirs=[numpy.get_include()],
                                 extra_compile_args=['-O3', '-fopenmp'],
                                 extra_link_args=['-O3', '-fopenmp'])],
          cmdclass={'build_ext': build_pyx})
