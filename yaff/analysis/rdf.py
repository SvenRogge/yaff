# YAFF is yet another force-field code
# Copyright (C) 2008 - 2011 Toon Verstraelen <Toon.Verstraelen@UGent.be>, Center
# for Molecular Modeling (CMM), Ghent University, Ghent, Belgium; all rights
# reserved unless otherwise stated.
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
# --


import numpy as np

from yaff.log import log
from yaff.analysis.utils import get_slice
from yaff.sampling.iterative import Hook
from yaff.pes.ext import Cell


__all__ = ['RDF']


class RDF(Hook):
    label = 'rdf'

    def __init__(self, f, rcut, rspacing, start=0, end=-1, max_sample=None,
                 step=None, select0=None, select1=None, path='trajectory/pos',
                 key='pos', outpath=None):
        """Computes a radial distribution function (RDF)

           **Argument:**

           f
                An h5py.File instance containing the trajectory data. If ``f``
                is not given, or it does not contain the dataset referred to
                with the ``path`` argument, an on-line analysis is carried out.

           rcut
                The cutoff for the RDF analysis. This should be lower than the
                spacing between the primitive cell planes.

           rspacing
                The width of the bins to build up the RDF.

           **Optional arguments:**

           start, end, max_sample, step
                arguments to setup the selection of time slices. See
                ``get_slice`` for more information.

           select0
                A list of atom indexes that are considered for the computation
                of the ref data. If not given, all atoms are used.

           select1
                A list of atom indexes that are needed to compute an RDF between
                two disjoint sets of atoms. (If there is some overlap between
                select0 and select1, an error will be raised.) If this is None,
                an 'internal' RDF will be computed for the atoms specified in
                select0.

           path
                The path of the dataset that contains the time dependent data in
                the HDF5 file. The first axis of the array must be the time
                axis.

           key
                In case of an on-line analysis, this is the key of the state
                item that contains the data from which the RDF is derived.

           outpath
                The output path for the frequency computation in the HDF5 file.
                If not given, it defaults to '%s_rdf' % path. If this path
                already exists, it will be removed first.

           When f is None, or when the path does not exist in the HDF5 file, the
           class can be used as an on-line analysis hook for the iterative
           algorithms in yaff.sampling package. This means that the RDF
           is built up as the itertive algorithm progresses. The end option is
           ignored and max_sample is not applicable to an on-line analysis.
        """
        self.f = f
        self.rcut = rcut
        self.rspacing = rspacing
        self.start, self.end, self.step = get_slice(self.f, start, end, max_sample, step)
        self.select0 = select0
        self.select1 = select1
        self.path = path
        self.key = key
        if outpath is None:
            self.outpath = '%s_rdf' % path
        else:
            self.outpath = outpath

        if self.select0 is not None and len(self.select0) != len(set(self.select0)):
            raise ValueError('No duplicates are allowed in select0')
        if self.select1 is not None and len(self.select1) != len(set(self.select1)):
            raise ValueError('No duplicates are allowed in select1')
        if self.select0 is not None and self.select1 is not None and len(self.select0) + len(select1) != len(set(select0) | set(self.select1)):
            raise ValueError('No overlap is allowed between select0 and select1')
        if self.select0 is None and self.select1 is not None:
            raise ValueError('select1 can not be given without select0.')

        self.nbin = int(self.rcut/self.rspacing)
        self.bins = np.arange(self.nbin+1)*self.rspacing
        self.counts = np.zeros(self.nbin, int)
        self.nsample = 0

        self.online = self.f is None or path not in self.f
        if not self.online:
            self.compute_offline()
        else:
            # this is used to check if the hook is called for the first time.
            self.natom0 = None

    def prepare(self, cell, natom):
        self.volume = cell.volume
        # Setup some work arrays
        if self.select0 is None:
            self.natom0 = natom
        else:
            self.natom0 = len(self.select0)
        self.pos0 = np.zeros((self.natom0, 3), float)
        if self.select1 is None:
            self.npair = (self.natom0*(self.natom0-1))/2
            self.pos1 = None
        else:
            self.natom1 = len(self.select1)
            self.pos1 = np.zeros((self.natom1, 3), float)
            self.npair = self.natom0*self.natom1
        self.work = np.zeros(self.npair, float)

    def __call__(self, iterative):
        if self.natom0 is None:
            self.cell = iterative.ff.system.cell
            natom = iterative.ff.system.natom
            self.prepare(self.cell, natom)
        # load data
        pos = iterative.state[self.key].value
        if self.select0 is None:
            self.pos0[:] = pos
        else:
            self.pos0[:] = pos[self.select0]
        if self.select1 is not None:
            self.pos1[:] = pos[self.select1]
        # distances
        self.cell.compute_distances(self.work, self.pos0, self.pos1)
        # compute counts and add to the total
        self.counts += np.histogram(self.work, bins=self.bins)[0]
        self.nsample += 1
        # Compute related arrays
        self.compute_derived()

    def compute_offline(self):
        # Configure the unit cell
        if 'rvecs' in self.f['system']:
            rvecs = self.f['system/rvecs'][:]
            cell = Cell(rvecs)
            if (2*self.rcut > cell.get_rspacings()).any():
                raise ValueError('The 2*rcut argument should not exceed any of the cell spacings.')
        else:
            cell = Cell(None)
        if cell.nvec != 3:
            raise ValueError('RDF can onle be computed for 3D periodic systems.')
        # get the total number of atoms
        natom = self.f['system/numbers'].shape[0]

        self.prepare(cell, natom)

        # Iterate over the dataset
        ds = self.f[self.path]
        for i in xrange(self.start, self.end, self.step):
            # load data
            if self.select0 is None:
                ds.read_direct(self.pos0, (i,))
            else:
                ds.read_direct(self.pos0, (i,self.select0))
            if self.select1 is not None:
                ds.read_direct(self.pos1, (i,self.select1))
            # distances
            cell.compute_distances(self.work, self.pos0, self.pos1)
            # compute counts and add to the total
            self.counts += np.histogram(self.work, bins=self.bins)[0]
            self.nsample += 1

        # Compute related arrays
        self.compute_derived()

    def compute_derived(self):
        # derive the RDF
        self.d = self.bins[:-1] + 0.5*self.rspacing
        ref_count = self.npair/self.volume*4*np.pi*self.d**2*self.rspacing
        self.rdf = self.counts/ref_count/self.nsample
        # derived the cumulative RDF
        self.crdf = self.counts.cumsum()/float(self.nsample*self.natom0)
        # store everything in the h5py file
        if self.f is not None:
            # TODO: avoid recreating group all the time
            if self.outpath in self.f:
                del self.f[self.outpath]
            g = self.f.create_group(self.outpath)
            g['rdf'] = self.rdf
            g['crdf'] = self.crdf
            g['counts'] = self.counts
            g['d'] = self.d

    def plot(self, fn_png='rdf.png'):
        import matplotlib.pyplot as pt
        pt.clf()
        xunit = log.length.conversion
        pt.plot(self.d/xunit, self.rdf, 'k-', drawstyle='steps-mid')
        pt.xlabel('Distance [%s]' % log.length.notation)
        pt.ylabel('RDF')
        pt.xlim(self.bins[0]/xunit, self.bins[-1]/xunit)
        pt.savefig(fn_png)

    def plot_crdf(self, fn_png='crdf.png'):
        import matplotlib.pyplot as pt
        pt.clf()
        xunit = log.length.conversion
        pt.plot(self.d/xunit, self.crdf, 'k-', drawstyle='steps-mid')
        pt.xlabel('Distance [%s]' % log.length.notation)
        pt.ylabel('CRDF')
        pt.xlim(self.bins[0]/xunit, self.bins[-1]/xunit)
        pt.savefig(fn_png)