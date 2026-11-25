# Environment painting and distribution

Environment Layers keeps sculpting, material painting and object placement
independently editable. Masks, seeds, rules, palettes and corrections are saved
with the blend. Instances are evaluated results, not the source of truth.

## Start with the Estuary example

Open `build/privateer-complete/Privateer-Estuary-Editable.blend` in the release
checkout. It contains a real approximately 127 m Estuary patch, three tree
variants, rocks, a clearing and retained corrections. Select the terrain in the
Wavelength workspace and open **N → wavelength → Environment Layers**.

Choose a layer and **Paint Mask**. Native Weight Paint controls radius, strength
and falloff; weight 1 covers and 0 removes. Material painting updates shading
through live attributes. Distribution painting takes effect after returning to
Object Mode and choosing **Refresh Distribution**. Sculpt in native Sculpt Mode
independently. Save normally. Fill and Clear affect only the selected mask.

Privateer's separate `development/environment/maps/wavelength-estuary-edit-test/Privateer-Wavelength-Review.tscn`
loads the exported example. The normal Estuary scene and streaming configuration
are unchanged.

## Palettes and generated coverage

Add a Distribution layer and choose a collection of static mesh prototypes as
Asset Palette. Prototypes need identity transforms and an origin at the desired
contact point; prepare normalized copies rather than changing shared source
assets. Hide the source objects individually. Collection members are variants;
Palette Weight controls their relative probability. Reuse palettes across modules.

Density is instances per square meter. Candidate Cell sets a fixed physical
sampling grid independently of movement snapping. A cell can contain several
candidate slots. Seed, slope limit, scale range and surface alignment are saved.
Lower density removes candidates without moving survivors; changing seed or cell
size changes the pattern. Preview Fraction thins the shared Geometry Nodes preview
only. Export resolves the complete set. Refresh is explicit and terrain-scoped,
not an automatic whole-world rescat after every brush movement.

Masks are native vertex groups. Detail depends on cage resolution; subdivision
interpolates them. Destructive topology changes may need weight transfer or
repainting. Use single-user mesh data for independent masks.

## Adopt existing point layouts

Select point meshes, then select the terrain last so it is active. Choose **Adopt
Selected Point Sets**. Supported native layouts have one Object Info prototype and
point vector attributes `instance_rotation` and `instance_scale`, matching Estuary.

Adoption preserves transforms in independent placement data, creates an unchanged
outside remainder and hides the original as a backup. It does not flatten trees.
For the next patch, select the visible remainder, not the original hidden backup.
Work on one terrain module per adoption. Native undo reverses the operation.

Adopted layers expose Retained Fraction, scale variation and Follow Sculpted
Terrain. They preserve existing positions instead of resampling them. Ground
height changes move uncorrected placements by the height delta, retaining their
original offsets. Add a generated layer to paint more objects. Disable adopted
layers to suppress their patch contents; removing provenance is refused.

Photographic emission/transparent canopy cards receive local PBR palette copies
with their atlas and UVs retained. Original prototypes/textures remain unchanged.
Other unsupported shaders require compatible copies or native Godot references.

## Clearings and corrections

Add an Exclusion layer, paint a clearing, then refresh. It reduces adopted and
generated coverage without changing elevation, materials or explicit corrections.

Choose a Manual Prototype, position the 3D Cursor and use Add Manual at Cursor.
Move, rotate or scale the correction, then Keep or Discard. Edit Nearest to Cursor
selects a generated or adopted placement for the same correction workflow.
Remove Placement records a deletion. Kept overrides survive regeneration and
save/reopen, including inside clearings. Missing prototypes cause an error instead
of losing corrections. Finish corrections before export.

Overrides are stored in an object-owned authored map keyed by layer and placement
identity. Earlier per-layer JSON remains readable. Terrain checkpoint copies get
independent masks, layer identities and disposable previews; prototype/material
references retain the existing shared-resource contract.

## Live material painting

Material layers compose native shaders through live named attributes. Use Refresh
Material Preview after changing layer definitions. The original base material is
retained. The native attribute modifier retains viewport/render switches.

Choose Privateer Biomes, set Godot Base Material to
`res://development/environment/maps/city-design/iteration-11/runtime/materials/Terrain.res`,
and choose a Paint Surface biome. Blender previews use one representative textured
surface per biome to avoid the original graph's GPU sampler limit. They approximate
the full three-surface mixtures. Godot export retains the original shader, texture
arrays, normals, lighting and seasonal inputs, inserting painted weights before
native biome selection. Unsupported shader revisions are refused.

The PBR adapter supports base-color textures/tints and scalar roughness. Linked
normal/roughness inputs in custom paint materials require baking or a native
adapter. Composition currently requires one base material slot. Material masks
export as evaluated vertex data and sampled PNGs. Mask Export Resolution controls
raster detail independently of sculpt resolution. Arbitrary shader baking and
rewriting unrelated custom ShaderMaterials are outside this workflow.

## Godot handoff

Select terrain modules with layers in Object Mode and choose Export Environment
to Godot. Choose a new bundle directory inside the game project or a previous
generated bundle. Inclusion checks apply independently of viewport visibility.

Bundles contain modular evaluated terrain GLBs, shared prototype GLBs or explicit
res:// scene references, mask data, rules, palette weights, stable IDs, overrides
and complete instance matrices. Batches group records by terrain, layer, prototype
and 128 m Godot X/Z cell. Blender `(x,y,z)` becomes Godot `(x,z,-y)`, in meters.
Preview thinning never removes exported placements.

After Godot imports the GLBs, attach the bundled environment_loader.gd to an empty
Node3D and set Manifest Path, or call load_bundle(path) and check its boolean result.
Reimport after regenerating. The example reader loads the small bundle into
MultiMeshes; the game owns streaming, collisions, lighting, seasons and gameplay.
Windows may retain old generated files after a successful swap; export reports
that cleanup warning rather than claiming the committed new bundle failed.

Animated prototypes, overhang-aware projection, minimum-distance spacing,
image-mask import and automatic cross-module brush strokes remain future work.
Work on selected modules; this acceptance does not certify whole-world frame rate
or regeneration latency. Existing point-set remainders let unedited regions remain
native instances without mandatory migration of the entire world.

## Verification

The real source is iteration-10/blender/estuary-nature-rev010.blend behind the
streamed iteration 011 scene. Its source SHA-256 is unchanged. Adoption accounts
for all 103,047 original tree points across patch data and preserved remainders.
The artist example includes a native UI-painted material stroke, saved/reopened
corrections and a successful textured viewport preview.

The focused tests are tests/blender_environment_layers.py,
tests/blender_environment_adoption.py and tests/blender_privateer_environment.py.
They cover masks, deterministic rules, retained outside points, exact transforms,
sculpt following, live attributes, checkpoint isolation, save/reopen and failure
preservation. The Godot counterpart tests/godot_privateer_environment.gd checks
native biome resources, mask values, all transforms and physical scale in the
real Compatibility renderer. Headless dummy-renderer transform readback is
unsuitable. The installed Godot build retains its previously documented shutdown
access violation after the successful test marker; this is not a clean engine
exit and is not fixed by the addon.
