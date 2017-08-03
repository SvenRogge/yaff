#!/usr/bin/env python
# -*- coding: utf-8 -*-
# YAFF is yet another force-field code
# Copyright (C) 2011 - 2013 Toon Verstraelen <Toon.Verstraelen@UGent.be>,
# Louis Vanduyfhuys <Louis.Vanduyfhuys@UGent.be>, Center for Molecular Modeling
# (CMM), Ghent University, Ghent, Belgium; all rights reserved unless otherwise
# stated.
#
# This file is part of YAFF.
#
# YAFF is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# YAFF is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
#--


import os
import subprocess
import sys
from glob import glob

import numpy as np
from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import build_ext


# Try to get the version from git describe
__version__ = None
try:
    git_describe = subprocess.check_output(["git", "describe", "--tags"])
    version_words = git_describe.decode('utf-8').strip().split('-')
    __version__ = version_words[0]
    if len(version_words) > 1:
        __version__ += '.dev' + version_words[1]
except subprocess.CalledProcessError:
    pass

# Interact with version.py
fn_version = os.path.join(os.path.dirname(__file__), 'yaff', 'version.py')
version_template = """\
\"""Do not edit this file, versioning is governed by ``git describe --tags`` and ``setup.py``.\"""
__version__ = '{}'
"""
if __version__ is None:
    # Try to load the git version tag from version.py
    try:
        with open(fn_version, 'r') as fh:
            __version__ = fh.read().split('=')[-1].replace('\'', '').strip()
    except IOError:
        print('Could not determine version. Giving up.')
        sys.exit(1)
else:
    # Store the git version tag in version.py
    with open(fn_version, 'w') as fh:
        fh.write(version_template.format(__version__))


setup(
    name='yaff',
    version=__version__,
    description='YAFF is yet another force-field code.',
    author='Toon Verstraelen',
    author_email='Toon.Verstraelen@UGent.be',
    url='http://molmod.ugent.be/code/',
    scripts=glob("scripts/yaff-*"),
    package_dir = {'yaff': 'yaff'},
    packages=['yaff', 'yaff/test', 'yaff/pes', 'yaff/pes/test', 'yaff/sampling',
              'yaff/sampling/test', 'yaff/analysis', 'yaff/analysis/test',
              'yaff/tune', 'yaff/tune/test', 'yaff/conversion',
              'yaff/conversion/test'],
    cmdclass = {'build_ext': build_ext},
    include_package_data=True,
    install_requires=['numpy>=1.0', 'nose>=0.11', 'cython>=0.24.1', 'matplotlib>1.0.0',
                      'h5py>=2.0.0', 'molmod>1.3.1', 'scipy>=0.17.1'],
    ext_modules=[
        Extension("yaff.pes.ext",
            sources=['yaff/pes/ext.pyx', 'yaff/pes/nlist.c',
                     'yaff/pes/pair_pot.c', 'yaff/pes/ewald.c',
                     'yaff/pes/dlist.c', 'yaff/pes/grid.c', 'yaff/pes/iclist.c',
                     'yaff/pes/vlist.c', 'yaff/pes/cell.c',
                     'yaff/pes/truncation.c', 'yaff/pes/slater.c'],
            depends=['yaff/pes/nlist.h', 'yaff/pes/nlist.pxd',
                     'yaff/pes/pair_pot.h', 'yaff/pes/pair_pot.pxd',
                     'yaff/pes/ewald.h', 'yaff/pes/ewald.pxd',
                     'yaff/pes/dlist.h', 'yaff/pes/dlist.pxd',
                     'yaff/pes/grid.h', 'yaff/pes/grid.pxd',
                     'yaff/pes/iclist.h', 'yaff/pes/iclist.pxd',
                     'yaff/pes/vlist.h', 'yaff/pes/vlist.pxd',
                     'yaff/pes/cell.h', 'yaff/pes/cell.pxd',
                     'yaff/pes/truncation.h', 'yaff/pes/truncation.pxd',
                     'yaff/pes/slater.h', 'yaff/pes/slater.pxd',
                     'yaff/pes/constants.h'],
            include_dirs=[np.get_include()],
        ),
    ],
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Intended Audience :: Science/Research',
    ],
)
