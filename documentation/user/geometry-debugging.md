# Visual geometry debugging

Open the viewport sidebar (**N**) → **wavelength** → **Geometry Problems**.
Choose **Check Geometry** to scan exported brushes. **Validate Map**, **Map
Problems**, and **Diagnostics → Show Geometry Problems** also populate the display.
A structured geometry failure during export/build queues its offending object
automatically, without moving the viewport or altering its mesh.

```{screenshot} geometry-problem-markers
:alt: Coincident vertex marker and Geometry Problems list with Select Geometry and Frame
Capture a coincident-vertex error with its pink marker, readable label, issue list and repair hint visible.
```

Coincident vertices have pink markers. Other localized geometry problems show
red/orange vertices or wire outlines. Markers remain visible through surfaces.
The issue list identifies the object, reason, affected element counts and a repair
hint. **Select Geometry** activates the object, enters Edit Mode and selects the
problem vertices; **Frame** also focuses the viewport on them.

For an accidental duplicate, inspect the selected vertices and use Blender's
**Merge by Distance**. Coincident coordinates can also indicate touching solids
in one object: separating those solids may be the correct repair. No geometry is
merged or deleted automatically.

**Refresh After Edits** rechecks objects already in the issue list after geometry
or transform changes. Once a problem is fixed, it disappears; another underlying
geometry failure on that object can then be reported. **Check Geometry** discovers
new failures across the scene. **Clear** removes the current markers/list.

For procedural/evaluated output, the display marks the evaluated result but selects
only the object. Use **Finalize Geometry** before selecting individual elements;
evaluated indices must not be applied to unrelated control-mesh vertices.

The initial system covers BSP brush geometry: exact coincident vertices, loose
vertices, nonmanifold edges, degenerate/nonplanar faces, nonconvex solids, duplicate
planes and thin/zero-volume solids. It follows profile constraints, so unrestricted
Blender meshes are not incorrectly required to be convex. Material, compiler and
entity errors still use their existing diagnostics. Run full map validation after
repairing geometry to check face metadata, materials and other export requirements.

Overlays belong to the wavelength editing context and originating scene/view
layer. Hidden objects stay unmarked; leaving wavelength, Clean Preview, rendering
or disabling viewport overlays hides the markers. No debug mesh objects are added
to the map.
