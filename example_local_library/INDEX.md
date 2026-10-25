# Library Index

## Topics

_No topic folders yet. Documents start flat, directly in this directory. Create
a topic folder (and list it here) when it's useful, not before - see CLAUDE.md._

## Top-level documents

### kernkamp2011_flexible_mesh — Efficient scheme for the shallow water equations on unstructured grids with application to the Continental Shelf

**Summary:** Presents a finite-volume shallow-water flow solver on unstructured grids, suitable for 1D (rivers, sewers), 2D (shallow seas, overland flow), and 3D (estuaries, lakes, shelf breaks) applications. This is the numerical method underlying D-Flow Flexible Mesh.
**Keywords:** unstructured grids, finite volume, shallow water equations, hydrodynamics, computational efficiency, Continental Shelf, tidal propagation
**Key results:** three 2D test cases plus a Continental Shelf tidal-propagation application; computational speed compared favorably with the structured-grid solvers WAQUA/TRIWAQ and Delft3D.
**Files:** [PDF](kernkamp2011_flexible_mesh.pdf) · [markdown](kernkamp2011_flexible_mesh/kernkamp2011_flexible_mesh.md)

### deltares2026_dflowfm_user_manual — D-Flow Flexible Mesh, Computational Cores and User Interface — User Manual

**Summary:** Deltares' user manual for D-Flow Flexible Mesh (part of the Delft3D FM Suite 2D3D, release 2027.01 draft) — the software implementation of the unstructured-grid shallow-water method in `kernkamp2011_flexible_mesh`. Covers model setup, computational cores, and the graphical user interface.
**Keywords:** D-Flow Flexible Mesh, Delft3D FM Suite, Deltares, unstructured grid, user manual, computational core, GUI
**Key results:** reference manual, not a results paper — the thing worth knowing without opening it is which release/version it documents (2D3D 2027.01, draft) and that it's the practical setup/usage counterpart to `kernkamp2011_flexible_mesh`'s method paper.
**Files:** [PDF](deltares2026_dflowfm_user_manual.pdf) · [markdown](deltares2026_dflowfm_user_manual/deltares2026_dflowfm_user_manual.md)
