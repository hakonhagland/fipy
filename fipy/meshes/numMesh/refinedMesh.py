#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  FiPy - Python-based finite volume PDE solver
 # 
 #  FILE: "refinedMesh.py"
 #                                    created: 11/10/03 {3:15:38 PM} 
 #                                last update: 9/16/05 {12:36:04 PM} 
 #  Author: Jonathan Guyer <guyer@nist.gov>
 #  Author: Daniel Wheeler <daniel.wheeler@nist.gov>
 #  Author: James Warren   <jwarren@nist.gov>
 #    mail: NIST
 #     www: http://www.ctcms.nist.gov/fipy/
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  FiPy is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  
 #  Description: 
 # 
 #  History
 # 
 #  modified   by  rev reason
 #  ---------- --- --- -----------
 #  2003-11-10 JEG 1.0 original
 # ###################################################################
 ##

""" 
The `_RefinedMesh` class provides an alternative way to adapt a mesh without
using the `_AdaptiveMesh` class.  The `_RefinedMesh` contructor takes as
input an old mesh (baseMesh) as well as a list of cells to refine
(nodeList).  The cells are refined by putting an additional vertex in the
center of the cell and dividng up the cell by drawing lines from the center
to each vertex.  After creating the new mesh, you can convert variables to
use the new mesh by creating a `_RefinedMeshCellVariable` (defined in this
module) with the old variable and the new `_RefinedMesh` as arguments.  Note
that if the mesh of the variable passed to `_RefinedMeshCellVariable` is not
the same as the old mesh used to generate the `_RefinedMesh`, the results
will be erroneous.

.. note:: 
    
   This currently only works with triangular meshes.

Test case:

   >>> from fipy.meshes.numMesh.tri2D import Tri2D
   >>> baseMesh = Tri2D(dx = 6., dy = 6., nx = 1, ny = 1)
   >>> baseVar = CellVariable(value = [0., 1., 2., 3.], mesh = baseMesh)
   >>> refinedMesh = _RefinedMesh2D(baseMesh, [1, 3])
   >>> refinedVar = _RefinedMeshCellVariable(baseVar, refinedMesh)
   >>> print refinedMesh.getVertexCoords()
   [[ 0.  0.]
    [ 6.  0.]
    [ 0.  6.]
    [ 6.  6.]
    [ 3.  3.]
    [ 3.  5.]
    [ 3.  1.]]
   >>> print refinedVar()
   [ 0.  2.  1.  1.  1.  3.  3.  3.]
   
"""
__docformat__ = 'restructuredtext'

from fipy.tools import numerix
from fipy.variables.cellVariable import CellVariable
from fipy.meshes.numMesh.mesh2D import Mesh2D

class _RefinedMesh2D(Mesh2D):
    def __init__(self, baseMesh, nodeList):
        ## calculate new vertex coords
        baseNumVertices = baseMesh.getVertexCoords().shape[0]
        baseNumCells = baseMesh._getCellFaceIDs().shape[0]
        newNumVertices = baseNumVertices + len(nodeList)
        newVertexCoords = numerix.concatenate((baseMesh.getVertexCoords(), numerix.take(baseMesh.getCellCenters(), nodeList)))
        ## calculate new face vertex IDs
        cellVertexIDs = baseMesh._getOrderedCellVertexIDs()
        maxVerticesPerCell = cellVertexIDs.shape[1]
        refinedCellVertexIDs = numerix.take(cellVertexIDs, nodeList)
        firstVerticesInAddedFaces = numerix.repeat(numerix.arange(baseNumVertices, newNumVertices), maxVerticesPerCell * numerix.ones(len(nodeList), 'l'))
        secondVerticesInAddedFaces = numerix.ravel(refinedCellVertexIDs)
        facesToAdd = numerix.transpose([firstVerticesInAddedFaces, secondVerticesInAddedFaces])
        newFaceVertexIDs = numerix.concatenate((baseMesh.faceVertexIDs, facesToAdd))
        ## calc face string to face IDs
        faceVertexToFaceIDs = {}
        currIndex = 0
        for i in newFaceVertexIDs:
            faceVertexToFaceIDs[' '.join([str(j) for j in numerix.sort(i)])] = currIndex
            currIndex = currIndex + 1
        ## calculate new cell face IDs
        cellIDsToKeep = numerix.ones(baseNumCells, 'l')
        numerix.put(cellIDsToKeep, nodeList, 0)
        cellFaceIDsToKeep = numerix.compress(cellIDsToKeep, baseMesh.cellFaceIDs, 0)
        refinedCellFaceIDs = numerix.take(baseMesh.cellFaceIDs, nodeList)
        middleIndex = baseNumVertices
        newCellFaceIDs = cellFaceIDsToKeep
        for i in refinedCellVertexIDs:
            outsideFaceVertexList = [[i[x], i[x+1]] for x in range(-1, len(i) - 1)]
            outsideFaceList = [faceVertexToFaceIDs[' '.join([str(id) for id in numerix.sort(face)])] for face in outsideFaceVertexList]
            rightFaceVertexList = [[middleIndex, i[x]] for x in range(-1, len(i) - 1)]
            rightFaceList = [faceVertexToFaceIDs[' '.join([str(id) for id in numerix.sort(face)])] for face in rightFaceVertexList]
            leftFaceVertexList = [[middleIndex, i[x+1]] for x in range(-1, len(i) - 1)]
            leftFaceList = [faceVertexToFaceIDs[' '.join([str(id) for id in numerix.sort(face)])] for face in leftFaceVertexList]
            faceArray = numerix.transpose(numerix.array([outsideFaceList, rightFaceList, leftFaceList]))
            newCellFaceIDs = numerix.concatenate((newCellFaceIDs, faceArray))
            middleIndex = middleIndex + 1
        newNumCells = len(newCellFaceIDs)
        ## calculate newToOldCellIDs. Used for changing variables.
        self.newToOldCellIDs = numerix.compress(cellIDsToKeep, numerix.arange(baseNumCells))
        for i in nodeList:
            self.newToOldCellIDs = numerix.concatenate((self.newToOldCellIDs, [i, i, i]))
        Mesh2D.__init__(self, newVertexCoords, newFaceVertexIDs, newCellFaceIDs)

class _RefinedMeshCellVariable(CellVariable):
    def __init__(self, oldVar, newMesh):
        newValues = numerix.take(numerix.array(oldVar), newMesh.newToOldCellIDs)
        CellVariable.__init__(self, newMesh, name = oldVar.name, value = newValues, unit = oldVar.getUnit())

def _test():
    import doctest
    return doctest.testmod()


if __name__ == "__main__":
    _test()