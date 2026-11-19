# System Tree

The wavelength workspace places the **System Tree** between the Outliner and
Properties editor. It groups objects by their engine purpose without changing
Blender Collections.

Click the **eye beside Props** to hide or reveal all prop entities and their
attached model previews. The triangle expands a category so individual objects
can be selected or hidden. Other categories include structural/detail brushes,
displacements, sky, utility geometry, point entities, brush entities and model
references. Visibility is an editor control; it does not exclude objects from
map export.

## Export and compilation checkboxes

The checkbox beside each engine category or object controls inclusion in game
export and compilation. Uncheck a category to exclude its current members; check
it to include them. A dash means the category contains a mixture of included and
excluded objects. The eye beside it controls viewport visibility independently.

The native Outliner includes a checkbox on each object row in the same column as
collection checkboxes, including parented child rows. The native Outliner and
System Tree share the same restrictions. Disabling an
object's render/camera toggle, a collection's render toggle, or a collection's
view-layer checkbox excludes that content from wavelength output too. The System
Tree reflects those changes immediately; its own checkboxes update native object
render restrictions. Enabling an object beneath an excluded collection restores
one collection membership path. Objects linked through another enabled collection
remain included unless their own render toggle is disabled.

This policy applies to brush maps, entities, displacements, mesh handoffs, custom
model sources and model compilation. Excluded geometry does not block export
validation. A custom prop with no enabled render meshes is omitted from both map
export and compilation. An unchecked collision source is not compiled; physics
props still require an enabled collision source or automatic collision.

The standard Blender OBJ, STL, PLY, FBX, glTF, USD and Alembic exporters also
honor these restrictions. Selection-only export remains an additional filter;
exporting does not change object selection, viewport hiding or transforms.

These restrictions are saved with the blend file. Temporary helper hiding during
clean renders does not change the saved export selection.

Existing layouts with two stacked Outliners reuse the lower slot. Layouts with
one Outliner take space from the top of Properties. Regular Blender workspaces
are left intact.

> Screenshot placeholder: Outliner, System Tree with Props expanded, Properties.

Use **Reload Asset Previews** to retry missing map textures and models.
