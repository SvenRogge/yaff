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
cimport numpy as np
cimport nlists
cimport pair_pot


__all__ = [
    'nlist_status_init', 'nlist_update', 'nlist_status_finish',
    'PairPot', 'PairPotLJ', 'PairPotEI',
]

#
# Neighbor lists
#

def nlist_status_init(center_index, rmax):
    # five integer status fields:
    # * r0
    # * r1
    # * r2
    # * other_index
    # * number of rows consumed
    result = np.array([0, 0, 0, center_index, 0], int)
    for i in xrange(len(rmax)):
        if len(rmax) > 0:
            result[i] = -rmax[i]
    return result


def nlist_update(np.ndarray[np.float64_t, ndim=2] pos, center_index, cutoff,
                 np.ndarray[np.long_t, ndim=1] rmax,
                 np.ndarray[np.float64_t, ndim=2] rvecs,
                 np.ndarray[np.float64_t, ndim=2] gvecs,
                 np.ndarray[np.long_t, ndim=1] nlist_status,
                 np.ndarray[nlists.nlist_row_type, ndim=1] nlist):
    assert pos.shape[1] == 3
    assert pos.flags['C_CONTIGUOUS']
    assert rmax.shape[0] <= 3
    assert rmax.flags['C_CONTIGUOUS']
    assert rvecs.shape[0] <= 3
    assert rvecs.shape[1] == 3
    assert rvecs.flags['C_CONTIGUOUS']
    assert gvecs.shape[0] <= 3
    assert gvecs.shape[1] == 3
    assert gvecs.flags['C_CONTIGUOUS']
    assert nlist_status.shape[0] == 5
    assert nlist_status.flags['C_CONTIGUOUS']
    assert nlist.flags['C_CONTIGUOUS']
    assert rmax.shape[0] == rvecs.shape[0]
    assert rmax.shape[0] == gvecs.shape[0]
    return nlists.nlist_update_low(
        <double*>pos.data, center_index, cutoff, <long*>rmax.data,
        <double*>rvecs.data, <double*>gvecs.data, <long*>nlist_status.data,
        <nlists.nlist_row_type*>nlist.data, len(pos), len(nlist), rvecs.shape[0]
    )


def nlist_status_finish(nlist_status):
    return nlist_status[4]


#
# Pair potentials
#

cdef class PairPot:
    cdef pair_pot.pair_pot_type* _c_pair_pot

    def __cinit__(self, *args, **kwargs):
        self._c_pair_pot = pair_pot.pair_pot_new()
        if self._c_pair_pot is NULL:
            raise MemoryError()

    def __dealloc__(self):
        if pair_pot.pair_pot_ready(self._c_pair_pot):
            pair_pot.pair_data_free(self._c_pair_pot)
        if self._c_pair_pot is not NULL:
            pair_pot.pair_pot_free(self._c_pair_pot)

    def get_cutoff(self):
        return pair_pot.pair_pot_get_cutoff(self._c_pair_pot)

    cutoff = property(get_cutoff)

    def energy(self, long center_index,
               np.ndarray[nlists.nlist_row_type, ndim=1] nlist,
               np.ndarray[pair_pot.scaling_row_type, ndim=1] scaling):
        assert pair_pot.pair_pot_ready(self._c_pair_pot)
        assert nlist.flags['C_CONTIGUOUS']
        assert scaling.flags['C_CONTIGUOUS']
        return pair_pot.pair_pot_energy(
            center_index, <nlists.nlist_row_type*>nlist.data, len(nlist),
            <pair_pot.scaling_row_type*>scaling.data, len(scaling),
            self._c_pair_pot
        )


cdef class PairPotLJ(PairPot):
    def __cinit__(self, np.ndarray[np.float64_t, ndim=1] sigmas, np.ndarray[np.float64_t, ndim=1] epsilons, double cutoff):
        assert sigmas.flags['C_CONTIGUOUS']
        assert epsilons.flags['C_CONTIGUOUS']
        assert sigmas.shape[0] == epsilons.shape[0]
        pair_pot.pair_pot_set_cutoff(self._c_pair_pot, cutoff)
        pair_pot.pair_data_lj_init(self._c_pair_pot, <double*>sigmas.data, <double*>epsilons.data)
        if not pair_pot.pair_pot_ready(self._c_pair_pot):
            raise MemoryError()


cdef class PairPotEI(PairPot):
    def __cinit__(self, np.ndarray[np.float64_t, ndim=1] charges, double alpha, double cutoff):
        assert charges.flags['C_CONTIGUOUS']
        pair_pot.pair_pot_set_cutoff(self._c_pair_pot, cutoff)
        pair_pot.pair_data_ei_init(self._c_pair_pot, <double*>charges.data, alpha)
        if not pair_pot.pair_pot_ready(self._c_pair_pot):
            raise MemoryError()
