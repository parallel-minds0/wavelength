# Feature change record

Append-only review history. A recorded change is not proof of passing behavior.

## 2026-11-02T21:50:40+00:00

Features: WL-DIST-005

Initial preservation baseline: catalogued existing profile, geometry, texture, entity/model, terrain, IO, cross-compiler, renderer/cache and distribution behavior. Recorded explicit limits and stubs, not new behavioral assurances. Static checks fingerprint implementation and regression entrypoints; verification will exercise the guard and existing unit suite.

added: 3109; removed: 0; changed: 0

Initial reviewed surface; the complete initial inventory is in the reference snapshot.

## 2026-11-02T21:55:24+00:00

Features: WL-DIST-005

Corrected discovery of Blender RNA settings stored as annotation calls, exposed by the new fixture test. Added explicit declaration coverage to the ledger. No product behavior removed or changed; guard fixtures and the full suite will verify this reviewed surface.

added: 329; removed: 0; changed: 4

### Added

- `setting|addon/wavelength/source/asset_browser.py|WL_OT_assets.category`
- `setting|addon/wavelength/source/asset_browser.py|WL_OT_assets.limit`
- `setting|addon/wavelength/source/asset_browser.py|WL_OT_assets.search`
- `setting|addon/wavelength/source/asset_browser.py|WL_OT_use_asset.effect_name`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.data`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.face`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.location`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.object_name`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.scope`
- `setting|addon/wavelength/source/asset_placement.py|WL_OT_stamp.selected_faces`
- `setting|addon/wavelength/source/asset_search.py|WLAssetSearch.area_key`
- `setting|addon/wavelength/source/asset_search.py|WLAssetSearch.query`
- `setting|addon/wavelength/source/authoring.py|WL_OT_asset_entity.kind`
- `setting|addon/wavelength/source/authoring.py|WL_OT_asset_entity.path`
- `setting|addon/wavelength/source/authoring.py|WL_OT_choice_set.field_index`
- `setting|addon/wavelength/source/authoring.py|WL_OT_choice_set.value`
- `setting|addon/wavelength/source/authoring.py|WL_OT_flag_toggle.field_index`
- `setting|addon/wavelength/source/authoring.py|WL_OT_flag_toggle.mask`
- `setting|addon/wavelength/source/authoring.py|WL_OT_path_chain.loop`
- `setting|addon/wavelength/source/authoring.py|WL_OT_path_chain.prefix`
- `setting|addon/wavelength/source/authoring.py|WL_OT_special_brush.classname`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.elevation`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.feature`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.field`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.mode`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.resource`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.resource_amount`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.river_east`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.river_southeast`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.river_southwest`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.terrain`
- `setting|addon/wavelength/source/civ5_cells.py|WLCiv5Settings.wonder`
- `setting|addon/wavelength/source/context_state.py|WLContext.editing`
- `setting|addon/wavelength/source/context_state.py|WLContext.helpers`
- `setting|addon/wavelength/source/context_state.py|WLContext.mode`
- `setting|addon/wavelength/source/context_state.py|WLContext.overlays`
- `setting|addon/wavelength/source/context_state.py|WLContext.preparation`
- `setting|addon/wavelength/source/context_state.py|WLContext.render_helpers`
- `setting|addon/wavelength/source/context_state.py|WL_OT_context.mode`
- `setting|addon/wavelength/source/csg.py|WL_OT_csg.operation`
- `setting|addon/wavelength/source/csg.py|WL_OT_csg_finish.cancel`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.activity`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.end`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.fps`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.loop`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.name`
- `setting|addon/wavelength/source/custom_models.py|WLModelClip.start`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.clips`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.collision`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.collision_mode`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.deployment`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.mass`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.origin`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.prop_data`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.status`
- `setting|addon/wavelength/source/custom_models.py|WLModelDefinition.surface_prop`
- `setting|addon/wavelength/source/custom_models.py|WL_OT_custom_clip.remove`
- `setting|addon/wavelength/source/diagnostics_ui.py|WL_OT_export_log.filter_glob`
- `setting|addon/wavelength/source/engine_tools.py|WL_OT_engine_transform.axis`
- `setting|addon/wavelength/source/engine_tools.py|WL_OT_engine_transform.kind`
- `setting|addon/wavelength/source/engine_tools.py|WL_OT_engine_transform.release_confirm`
- `setting|addon/wavelength/source/entity/browser.py|WL_OT_entity_browser.section`
- `setting|addon/wavelength/source/export_scope.py|WL_OT_export_inclusion.category`
- `setting|addon/wavelength/source/export_scope.py|WL_OT_export_inclusion.object_name`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryDebug.active`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryDebug.engine`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryDebug.issues`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryDebug.live`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryDebug.overlay`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.code`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.details`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.evaluated`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.hint`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.message`
- `setting|addon/wavelength/source/geometry_debug.py|WLGeometryIssue.target`
- `setting|addon/wavelength/source/geometry_debug.py|WL_OT_select_geometry_problem.frame`
- `setting|addon/wavelength/source/mesh_assets.py|WL_OT_source2_library.action`
- `setting|addon/wavelength/source/model_import.py|WL_OT_add_source_model.model`
- `setting|addon/wavelength/source/model_import.py|WL_OT_import_source_model.body`
- `setting|addon/wavelength/source/model_import.py|WL_OT_import_source_model.filter_glob`
- `setting|addon/wavelength/source/model_import.py|WL_OT_import_source_model.skin`
- `setting|addon/wavelength/source/model_io.py|WL_OT_build_model_asset.source_name`
- `setting|addon/wavelength/source/model_io.py|WL_OT_import_model_asset.body`
- `setting|addon/wavelength/source/model_io.py|WL_OT_import_model_asset.filter_glob`
- `setting|addon/wavelength/source/model_io.py|WL_OT_import_model_asset.skin`
- `setting|addon/wavelength/source/model_io.py|WL_OT_publish_model_drop.source_name`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.cut_through`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.depth`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.direction`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.geometry`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.height`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.keep`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.operation`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.separate_objects`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.target`
- `setting|addon/wavelength/source/pencil.py|WLCutterGuide.through`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.auto_extrude`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.depth`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.direction`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.guide`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.keep`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.operation`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.resolution`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.separate_objects`
- `setting|addon/wavelength/source/pencil.py|WLDrawSettings.through`
- `setting|addon/wavelength/source/precision_move.py|WL_OT_precision_move.axis`
- `setting|addon/wavelength/source/precision_move.py|WL_OT_precision_move.release_confirm`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.angle`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.curve_angle`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.curved`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.depth`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.direction`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.edit`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.fill_center`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.inner_radius`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.kind`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.landing`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.radius`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.rings`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.rise`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.run`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.segments`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.sphere_type`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.steps`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.subdivisions`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.thickness`
- `setting|addon/wavelength/source/primitive_ui.py|WL_OT_primitive.width`
- `setting|addon/wavelength/source/profile_setup.py|WL_OT_library_setup.action`
- `setting|addon/wavelength/source/profile_ui.py|WL_OT_profile.action`
- `setting|addon/wavelength/source/profile_ui.py|WL_OT_profile.name`
- `setting|addon/wavelength/source/profile_ui.py|WL_OT_profile.parent`
- `setting|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement.action`
- `setting|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement.power`
- `setting|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement.tags`
- `setting|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement_paint.mode`
- `setting|addon/wavelength/source/sun.py|WLSunControls.elevation`
- `setting|addon/wavelength/source/sun.py|WLSunControls.heading`
- `setting|addon/wavelength/source/surface_tools.py|WL_OT_align.action`
- `setting|addon/wavelength/source/surface_tools.py|WL_OT_pick.kind`
- `setting|addon/wavelength/source/system_tree_view.py|WL_OT_system_tree_expand.category`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.amplitude`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.blend_base`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.elevation`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.flat_preview`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.frequency`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.length`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.paint_material`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.paint_mode`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.paint_opacity`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.paint_radius`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.paint_strength`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.power`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.resolution`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.seed`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.surface_source`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.tiles_x`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.tiles_y`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.width`
- `setting|addon/wavelength/source/terrain_face.py|WL_OT_displacement_from_face.independent`
- `setting|addon/wavelength/source/terrain_face.py|WL_OT_displacement_from_face.native`
- `setting|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.mode`
- `setting|addon/wavelength/source/terrain_sew.py|WL_OT_terrain_sew.smooth`
- `setting|addon/wavelength/source/transform_bridge.py|WL_OT_transform_route.kind`
- `setting|addon/wavelength/source/ui.py|WLKey.choice`
- `setting|addon/wavelength/source/ui.py|WLKey.choices`
- `setting|addon/wavelength/source/ui.py|WLKey.integer`
- `setting|addon/wavelength/source/ui.py|WLKey.key`
- `setting|addon/wavelength/source/ui.py|WLKey.kind`
- `setting|addon/wavelength/source/ui.py|WLKey.label`
- `setting|addon/wavelength/source/ui.py|WLKey.number`
- `setting|addon/wavelength/source/ui.py|WLKey.value`
- `setting|addon/wavelength/source/ui.py|WLSettings.arch_angle`
- `setting|addon/wavelength/source/ui.py|WLSettings.arch_segments`
- `setting|addon/wavelength/source/ui.py|WLSettings.arch_thickness_steps`
- `setting|addon/wavelength/source/ui.py|WLSettings.asset_browser_section`
- `setting|addon/wavelength/source/ui.py|WLSettings.asset_paths`
- `setting|addon/wavelength/source/ui.py|WLSettings.auto_prepare_assets`
- `setting|addon/wavelength/source/ui.py|WLSettings.brush_height_steps`
- `setting|addon/wavelength/source/ui.py|WLSettings.brush_rings`
- `setting|addon/wavelength/source/ui.py|WLSettings.brush_sides`
- `setting|addon/wavelength/source/ui.py|WLSettings.brush_size`
- `setting|addon/wavelength/source/ui.py|WLSettings.brush_type`
- `setting|addon/wavelength/source/ui.py|WLSettings.build_error`
- `setting|addon/wavelength/source/ui.py|WLSettings.build_log_dir`
- `setting|addon/wavelength/source/ui.py|WLSettings.build_output`
- `setting|addon/wavelength/source/ui.py|WLSettings.clip_axis`
- `setting|addon/wavelength/source/ui.py|WLSettings.clip_distance`
- `setting|addon/wavelength/source/ui.py|WLSettings.clip_flip`
- `setting|addon/wavelength/source/ui.py|WLSettings.compiler_dir`
- `setting|addon/wavelength/source/ui.py|WLSettings.custom_model_deployment`
- `setting|addon/wavelength/source/ui.py|WLSettings.custom_model_directory`
- `setting|addon/wavelength/source/ui.py|WLSettings.diagnostics`
- `setting|addon/wavelength/source/ui.py|WLSettings.effective_grid_subdivisions`
- `setting|addon/wavelength/source/ui.py|WLSettings.engine`
- `setting|addon/wavelength/source/ui.py|WLSettings.entity_add_key`
- `setting|addon/wavelength/source/ui.py|WLSettings.entity_choice`
- `setting|addon/wavelength/source/ui.py|WLSettings.entity_class`
- `setting|addon/wavelength/source/ui.py|WLSettings.entity_editor_binding`
- `setting|addon/wavelength/source/ui.py|WLSettings.entity_json`
- `setting|addon/wavelength/source/ui.py|WLSettings.environment`
- `setting|addon/wavelength/source/ui.py|WLSettings.fgd_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.field_index`
- `setting|addon/wavelength/source/ui.py|WLSettings.fields`
- `setting|addon/wavelength/source/ui.py|WLSettings.game_dir`
- `setting|addon/wavelength/source/ui.py|WLSettings.game_executable`
- `setting|addon/wavelength/source/ui.py|WLSettings.grid_mode`
- `setting|addon/wavelength/source/ui.py|WLSettings.grid_step`
- `setting|addon/wavelength/source/ui.py|WLSettings.grid_subdivisions`
- `setting|addon/wavelength/source/ui.py|WLSettings.hollow_thickness`
- `setting|addon/wavelength/source/ui.py|WLSettings.last_build`
- `setting|addon/wavelength/source/ui.py|WLSettings.launch_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.light_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.light_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.live_texture_reproject`
- `setting|addon/wavelength/source/ui.py|WLSettings.log_filter`
- `setting|addon/wavelength/source/ui.py|WLSettings.map_name`
- `setting|addon/wavelength/source/ui.py|WLSettings.map_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.mesh_export_directory`
- `setting|addon/wavelength/source/ui.py|WLSettings.mesh_export_selected`
- `setting|addon/wavelength/source/ui.py|WLSettings.metric_grid_step`
- `setting|addon/wavelength/source/ui.py|WLSettings.model_browser_field`
- `setting|addon/wavelength/source/ui.py|WLSettings.palette_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.profile_grid_spacing`
- `setting|addon/wavelength/source/ui.py|WLSettings.profile_id`
- `setting|addon/wavelength/source/ui.py|WLSettings.profile_name`
- `setting|addon/wavelength/source/ui.py|WLSettings.project_dir`
- `setting|addon/wavelength/source/ui.py|WLSettings.qbsp_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.qbsp_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.quake_pak_dir`
- `setting|addon/wavelength/source/ui.py|WLSettings.saved_profile`
- `setting|addon/wavelength/source/ui.py|WLSettings.shift_u`
- `setting|addon/wavelength/source/ui.py|WLSettings.shift_v`
- `setting|addon/wavelength/source/ui.py|WLSettings.show_edge_measurements`
- `setting|addon/wavelength/source/ui.py|WLSettings.snap_to_grid`
- `setting|addon/wavelength/source/ui.py|WLSettings.source_vbsp_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.source_vrad_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.source_vvis_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.sphere_subdivisions`
- `setting|addon/wavelength/source/ui.py|WLSettings.sphere_type`
- `setting|addon/wavelength/source/ui.py|WLSettings.stair_angle`
- `setting|addon/wavelength/source/ui.py|WLSettings.stair_curved`
- `setting|addon/wavelength/source/ui.py|WLSettings.stair_inner_radius`
- `setting|addon/wavelength/source/ui.py|WLSettings.stair_landing`
- `setting|addon/wavelength/source/ui.py|WLSettings.stair_steps`
- `setting|addon/wavelength/source/ui.py|WLSettings.status`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_alignment`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_choice`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_count`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_lightmap`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_page`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_rotation`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_scale_u`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_scale_v`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_search`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_wads`
- `setting|addon/wavelength/source/ui.py|WLSettings.timeout`
- `setting|addon/wavelength/source/ui.py|WLSettings.unit_scale`
- `setting|addon/wavelength/source/ui.py|WLSettings.vis_args`
- `setting|addon/wavelength/source/ui.py|WLSettings.vis_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.wad_path`
- `setting|addon/wavelength/source/ui.py|WLSettings.worldspawn_json`
- `setting|addon/wavelength/source/ui.py|WLSettings.wrapper`
- `setting|addon/wavelength/source/ui.py|WLTextureBrowserItem.name`
- `setting|addon/wavelength/source/ui.py|WLTextureGalleryRow.name0`
- `setting|addon/wavelength/source/ui.py|WLTextureGalleryRow.name1`
- `setting|addon/wavelength/source/ui.py|WLTextureGalleryRow.name2`
- `setting|addon/wavelength/source/ui.py|WL_OT_add_wad.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_brush.kind`
- `setting|addon/wavelength/source/ui.py|WL_OT_build.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_convert_source2_materials.assign_materials`
- `setting|addon/wavelength/source/ui.py|WL_OT_convert_source2_materials.directory`
- `setting|addon/wavelength/source/ui.py|WL_OT_convert_source2_materials.selected_only`
- `setting|addon/wavelength/source/ui.py|WL_OT_convert_source2_materials.source_directory`
- `setting|addon/wavelength/source/ui.py|WL_OT_convert_source2_materials.use_loaded_textures`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.package_project`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.selected_only`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.source_profile`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.target_compiler_dir`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.target_game_dir`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.target_profile`
- `setting|addon/wavelength/source/ui.py|WL_OT_entity_browse.classname`
- `setting|addon/wavelength/source/ui.py|WL_OT_entity_search.classname`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.convert_entities`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.export_format`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.filename_ext`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.ignore_material_errors`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.package_project`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.selected_only`
- `setting|addon/wavelength/source/ui.py|WL_OT_export.visibility_quality`
- `setting|addon/wavelength/source/ui.py|WL_OT_grid_step.direction`
- `setting|addon/wavelength/source/ui.py|WL_OT_import.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_import.import_format`
- `setting|addon/wavelength/source/ui.py|WL_OT_properties.apply`
- `setting|addon/wavelength/source/ui.py|WL_OT_property_add.property_key`
- `setting|addon/wavelength/source/ui.py|WL_OT_property_custom_add.key`
- `setting|addon/wavelength/source/ui.py|WL_OT_property_remove.index`
- `setting|addon/wavelength/source/ui.py|WL_OT_remove_wad.filepath`
- `setting|addon/wavelength/source/ui.py|WL_OT_select_problem.object_name`
- `setting|addon/wavelength/source/ui.py|WL_OT_select_target.direction`
- `setting|addon/wavelength/source/ui.py|WL_OT_select_wad.filepath`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_material.choice`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.delay`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.event`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.index`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.input_name`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.once`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.parameter`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.remove`
- `setting|addon/wavelength/source/ui.py|WL_OT_source_output.target`
- `setting|addon/wavelength/source/ui.py|WL_OT_system_category_visibility.category`
- `setting|addon/wavelength/source/ui.py|WL_OT_system_select.extend`
- `setting|addon/wavelength/source/ui.py|WL_OT_system_select.object_name`
- `setting|addon/wavelength/source/ui.py|WL_OT_system_select_category.category`
- `setting|addon/wavelength/source/ui.py|WL_OT_system_visibility.object_name`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.material_only`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.active_index`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.gallery_row_index`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.gallery_rows`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.items`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.search`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser.view_mode`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_browser_pick.texture_name`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_nudge.action`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture_page.direction`
- `setting|addon/wavelength/source/workspace.py|WL_OT_workspace.reset`
- `setting|addon/wavelength/source/workspace.py|WL_OT_workspace_toggle.feature`

### Changed

- `function|tools/feature_inventory.py|capture`
- `function|tools/feature_inventory.py|capture.walk`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|tools/feature_inventory.py|feature_inventory`

## 2026-11-02T21:57:41+00:00

Features: WL-DIST-003, WL-DIST-005

Package the reviewed JSON baseline with the Markdown handbook so it survives documentation sync and distribution. Added a focused sync regression; retained unmanaged-file behavior and the existing screenshot/Markdown outputs. No runtime product behavior changed.

added: 0; removed: 0; changed: 4

### Changed

- `function|tools/docs.py|sync`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|tools/docs.py|docs`
- `test|tests/test_docs.py|test_docs`

## 2026-11-02T22:01:32+00:00

Features: WL-DIST-005

Strengthened the guard fixture to reject a changed function body even when all interface names remain unchanged, before testing operator removal. Retained the same product contracts; the initial 256-test suite and docs sync passed, with this added assertion verified in the final checks.

added: 0; removed: 0; changed: 2

### Changed

- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `test|tests/test_feature_inventory.py|test_feature_inventory`

## 2026-11-02T22:03:57+00:00

Features: WL-DIST-003, WL-DIST-005

Keep generated feature identifiers literal during handbook preparation instead of applying prose branding replacements to code names. Added a focused preparation regression. Normal prose branding, source mirrors and existing source-view generation remain intact; the full regression and documentation checks verify the final state.

added: 0; removed: 0; changed: 4

### Changed

- `function|tools/docs.py|prepare`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|tools/docs.py|docs`
- `test|tests/test_docs.py|test_docs`

## Verification — 2026-11-03

Features: WL-DIST-003, WL-DIST-005

- 122 behavioral contracts and 3,438 reviewed implementation surface entries,
  including 329 annotated Blender settings.
- Full Python suite: 257 tests passed.
- Inventory guard and documentation checks/sync passed.
- Fixtures verify same-interface body changes and removed operators are rejected
  until reviewed; feature IDs cannot be deleted; literal identifiers and the
  JSON baseline survive handbook generation/packaging.
- Canonical, checkout and packaged feature documents match byte-for-byte.
- No Blender executable or runtime addon behavior changed for this documentation
  task. These checks do not substitute for subsystem Blender/native regressions.

## 2026-11-02T22:08:48+00:00

Features: WL-DIST-005

Protect the accepted review-history prefix against deletion, truncation or rewriting, while allowing new verification and decisions to be appended. Added a destructive-history fixture. Existing 257 tests passed before this final guard extension; the next verification checks its final state.

added: 1; removed: 0; changed: 5

### Added

- `function|tools/feature_inventory.py|verify_history`

### Changed

- `function|tools/feature_inventory.py|check`
- `function|tools/feature_inventory.py|update`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|tools/feature_inventory.py|feature_inventory`
- `test|tests/test_feature_inventory.py|test_feature_inventory`

## 2026-11-02T22:21:40+00:00

Features: WL-XCOMP-002, WL-XCOMP-006, WL-XCOMP-007, WL-XCOMP-008, WL-XCOMP-009, WL-XCOMP-010

User-requested consolidation: replace separate conversion/repair panel buttons with Cross-Compile Level; retain legacy operators and assignment features for compatibility. Resolve Source 1 materials through source-profile paths rather than CS2 target settings, expose fallback/error policies in the unified dialog, and recover legacy brush projection in export memory without source mutation. Real-map source-recovery and projection assertions passed; final regression/docs checks follow.

added: 4; removed: 0; changed: 15

### Added

- `function|addon/wavelength/source/source2_port_materials.py|recover_export_projection`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.ignore_material_errors`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.source_game_dir`
- `setting|addon/wavelength/source/ui.py|WL_OT_cross_compile.use_loaded_textures`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_cross_compile`
- `class|addon/wavelength/source/ui.py|WL_PT_project`
- `function|addon/wavelength/source/cross_compile.py|_source1_level`
- `function|addon/wavelength/source/source2_map.py|export`
- `function|addon/wavelength/source/source2_map.py|export.material`
- `function|addon/wavelength/source/ui.py|WL_OT_cross_compile.draw`
- `function|addon/wavelength/source/ui.py|WL_OT_cross_compile.run`
- `function|addon/wavelength/source/ui.py|WL_PT_project.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/cross_compile.py|cross_compile`
- `module|addon/wavelength/source/source2_map.py|source2_map`
- `module|addon/wavelength/source/source2_port_materials.py|source2_port_materials`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_cross_compile.py|blender_cross_compile`
- `test|tests/blender_source2_projection.py|blender_source2_projection`

## 2026-11-02T22:25:07+00:00

Features: WL-XCOMP-002, WL-XCOMP-008, WL-XCOMP-010

Added final UI and unified-fallback regressions: the project panel exposes one Cross-Compile Level action, optional loaded pixels work through that action, strict mode still reports missing games, and automatic projection repair preserves source UVs. These Blender assertions passed on the real map and loaded-texture fixtures; legacy standalone operators remain registered.

added: 0; removed: 0; changed: 2

### Changed

- `test|tests/blender_cross_compile.py|blender_cross_compile`
- `test|tests/blender_source2_port_materials.py|blender_source2_port_materials`

## 2026-11-02T23:27:33+00:00

Features: WL-PROF-008, WL-PROF-001, WL-PROF-005, WL-TEX-009

Add the installed CS:GO Legacy Windows Source 1 profile as an appended enum entry, separate from CS2, retaining all previous enum numbers. Discover legacy csgo/gameinfo.txt and csgo.exe, fall back to the installed Source 1 importer FGD, and mount implicit directory VPKs with loose override precedence. Actual installation discovery/material indexing passed. BSP21 compilation remains explicitly unsupported; focused and full regressions verify the final changes.

added: 1; removed: 0; changed: 9

### Added

- `test|tests/test_csgo_legacy_profile.py|test_csgo_legacy_profile`

### Changed

- `class|addon/wavelength/source/source_assets.py|Assets`
- `configuration|addon/wavelength/environment/profiles/templates.json|templates.json`
- `function|addon/wavelength/source/source_assets.py|Assets.__init__`
- `function|addon/wavelength/source/source_assets.py|Assets.__init__.mount`
- `function|addon/wavelength/source/source_tools.py|defaults`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/profiles.py|profiles`
- `module|addon/wavelength/source/source_assets.py|source_assets`
- `module|addon/wavelength/source/source_tools.py|source_tools`

## 2026-11-02T23:28:50+00:00

Features: WL-PROF-008

Keep the new legacy profile row inside the existing profile preservation table; documentation formatting only, with no runtime or profile-enum changes.

added: 0; removed: 0; changed: 1

### Changed

- `ledger|documentation/FEATURES.md|behavioral-contracts`

## 2026-11-03T00:08:12+00:00

Features: WL-IO-010, WL-TEX-009, WL-PERF-004, WL-XCOMP-006

Fix de_dorms_d.vmf scene placeholders: retry materials without prior cache keys on load/profile changes, retain missing-source provenance, clear stale errors, and refresh affected live UVs once after dimensions recover. Map verified Source 1 clip surface variants and 2D sky to native CS2 tool equivalents with warnings. Exact-map tests recovered all 63 bindings, checked image nodes and projection, exercised profile/load recovery, and exported with explicit placeholders for the four unsupported blends. No claim of automatic blended-shader conversion.

added: 3; removed: 0; changed: 17

### Added

- `function|addon/wavelength/source/native_source.py|_refresh_recovered_uvs`
- `function|addon/wavelength/source/native_source.py|recover_missing_materials`
- `test|tests/blender_dorms_material_recovery.py|blender_dorms_material_recovery`

### Changed

- `class|addon/wavelength/source/asset_loading.py|WL_OT_reload_map_assets`
- `function|addon/wavelength/source/asset_loading.py|WL_OT_reload_map_assets.execute`
- `function|addon/wavelength/source/native_source.py|bind_material`
- `function|addon/wavelength/source/native_source.py|migrate`
- `function|addon/wavelength/source/profile_ui.py|apply`
- `function|addon/wavelength/source/scene.py|import_map_iter`
- `function|addon/wavelength/source/source2_map.py|export`
- `function|addon/wavelength/source/source2_map.py|export.material`
- `function|addon/wavelength/source/source2_port_materials.py|deploy`
- `function|addon/wavelength/source/source2_port_materials.py|tool_material`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/asset_loading.py|asset_loading`
- `module|addon/wavelength/source/native_source.py|native_source`
- `module|addon/wavelength/source/profile_ui.py|profile_ui`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/source2_map.py|source2_map`
- `module|addon/wavelength/source/source2_port_materials.py|source2_port_materials`

## 2026-11-03T00:51:23+00:00

Features: WL-XCOMP-006, WL-XCOMP-014

Reviewed two-layer terrain conversion, blend weights and packaging. Blender blend roundtrip and strict dorms export pass; native visual parity remains unverified.

added: 2; removed: 0; changed: 11

### Added

- `function|addon/wavelength/source/source2_dmx.py|corner_blend_weights`
- `test|tests/blender_source2_blends.py|blender_source2_blends`

### Changed

- `function|addon/wavelength/source/source2_dmx.py|polygon_mesh`
- `function|addon/wavelength/source/source2_map.py|export`
- `function|addon/wavelength/source/source2_map.py|import_map`
- `function|addon/wavelength/source/source2_port_materials.py|deploy`
- `function|addon/wavelength/source/source2_port_materials.py|deploy.image`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/source2_dmx.py|source2_dmx`
- `module|addon/wavelength/source/source2_map.py|source2_map`
- `module|addon/wavelength/source/source2_port_materials.py|source2_port_materials`
- `test|tests/blender_dorms_material_recovery.py|blender_dorms_material_recovery`
- `test|tests/test_source2_dmx.py|test_source2_dmx`

## 2026-11-03T00:55:21+00:00

Features: WL-XCOMP-014

Corrected regression fixture to serialize a valid VMAP root; Blender full document roundtrip already passed.

added: 0; removed: 0; changed: 1

### Changed

- `test|tests/test_source2_dmx.py|test_source2_dmx`

## 2026-11-03T01:38:32+00:00

Features: WL-XCOMP-015, WL-XCOMP-010, WL-IO-009

Reviewed detail-to-visexclude mapping, utility map brushes, native face projections and unbound UV streams. Preserves explicit export scope and manual dynamic entities. Dorms now exports 580 meshes with all 3505 world/detail UV faces checked; projection repair and native compiler UV probe pass. Hammer visual parity remains unverified.

added: 1; removed: 0; changed: 14

### Added

- `function|addon/wavelength/source/source2_port_materials.py|export_brush_projections`

### Changed

- `function|addon/wavelength/source/cross_compile.py|source1_to_source2`
- `function|addon/wavelength/source/mesh_assets.py|candidates`
- `function|addon/wavelength/source/source2_dmx.py|polygon_mesh`
- `function|addon/wavelength/source/source2_dmx.py|stream`
- `function|addon/wavelength/source/source2_map.py|export`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/cross_compile.py|cross_compile`
- `module|addon/wavelength/source/mesh_assets.py|mesh_assets`
- `module|addon/wavelength/source/source2_dmx.py|source2_dmx`
- `module|addon/wavelength/source/source2_map.py|source2_map`
- `module|addon/wavelength/source/source2_port_materials.py|source2_port_materials`
- `test|tests/blender_dorms_material_recovery.py|blender_dorms_material_recovery`
- `test|tests/test_cross_compile.py|test_cross_compile`
- `test|tests/test_source2_dmx.py|test_source2_dmx`

## 2026-11-03T19:05:12+00:00

Features: WL-MODEL-007, WL-MODEL-013, WL-MODEL-015, WL-MODEL-016, WL-MODEL-017, WL-MODEL-018

Reviewed phase-one persistent model assets and Source 1 mounted editing. Detach copies independent data without altering placements; Make Unique/Attach explicitly replace or link instances. Preserve legacy unmanaged detach, world units/poses, images across saves, rigs/actions, private compile origins, native duplication and existing compiler/collision behavior. New lifecycle/rig tests plus native StudioMDL regressions pass; cross-engine model conversion and full material compilation remain later phases.

added: 59; removed: 0; changed: 24

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_attach_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_OT_detach_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_OT_edit_model`
- `class|addon/wavelength/source/model_io.py|WL_OT_make_model_unique`
- `class|addon/wavelength/source/model_io.py|_ModelEditAction`
- `function|addon/wavelength/source/model_backend_source1.py|Source1._editable`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.bind_asset`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.import_reference`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.model_path`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.validate_placement`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.validate_placement.style`
- `function|addon/wavelength/source/model_io.py|WL_OT_attach_model_asset.run`
- `function|addon/wavelength/source/model_io.py|WL_OT_detach_model_asset.run`
- `function|addon/wavelength/source/model_io.py|WL_OT_edit_model.run`
- `function|addon/wavelength/source/model_io.py|WL_OT_make_model_unique.run`
- `function|addon/wavelength/source/model_io.py|_ModelEditAction.execute`
- `function|addon/wavelength/source/model_io.py|_ModelEditAction.poll`
- `function|addon/wavelength/source/model_io.py|object_menu`
- `function|addon/wavelength/source/model_io.py|selected_assets`
- `function|addon/wavelength/source/model_lifecycle.py|_adopt`
- `function|addon/wavelength/source/model_lifecycle.py|_anchor`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique.independent`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique.own_tree`
- `function|addon/wavelength/source/model_lifecycle.py|_owned_image`
- `function|addon/wavelength/source/model_lifecycle.py|_pack_image`
- `function|addon/wavelength/source/model_lifecycle.py|_parent`
- `function|addon/wavelength/source/model_lifecycle.py|_reference`
- `function|addon/wavelength/source/model_lifecycle.py|_release`
- `function|addon/wavelength/source/model_lifecycle.py|_validate`
- `function|addon/wavelength/source/model_lifecycle.py|asset_for`
- `function|addon/wavelength/source/model_lifecycle.py|attach`
- `function|addon/wavelength/source/model_lifecycle.py|bindings`
- `function|addon/wavelength/source/model_lifecycle.py|detach`
- `function|addon/wavelength/source/model_lifecycle.py|edit`
- `function|addon/wavelength/source/model_lifecycle.py|edit_dependencies`
- `function|addon/wavelength/source/model_lifecycle.py|ensure`
- `function|addon/wavelength/source/model_lifecycle.py|entity_for`
- `function|addon/wavelength/source/model_lifecycle.py|make_unique`
- `function|addon/wavelength/source/model_lifecycle.py|save_owned_images`
- `function|addon/wavelength/source/model_lifecycle.py|select_sources`
- `function|addon/wavelength/source/model_lifecycle.py|selection`
- `function|addon/wavelength/source/model_lifecycle.py|sources`
- `function|addon/wavelength/source/model_lifecycle.py|sync_placements`
- `hook|addon/wavelength/source/model_io.py|bpy.app.handlers.depsgraph_update_post.append(sync_placements)`
- `hook|addon/wavelength/source/model_io.py|bpy.app.handlers.depsgraph_update_post.remove(sync_placements)`
- `hook|addon/wavelength/source/model_io.py|bpy.app.handlers.save_pre.append(save_owned_images)`
- `hook|addon/wavelength/source/model_io.py|bpy.app.handlers.save_pre.remove(save_owned_images)`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`
- `test|tests/blender_model_asset_lifecycle.py|blender_model_asset_lifecycle`
- `test|tests/blender_model_asset_rigs.py|blender_model_asset_rigs`
- `ui|addon/wavelength/source/model_io.py|WL_OT_attach_model_asset.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_attach_model_asset.bl_label`
- `ui|addon/wavelength/source/model_io.py|WL_OT_detach_model_asset.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_detach_model_asset.bl_label`
- `ui|addon/wavelength/source/model_io.py|WL_OT_edit_model.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_edit_model.bl_label`
- `ui|addon/wavelength/source/model_io.py|WL_OT_make_model_unique.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_make_model_unique.bl_label`

### Changed

- `class|addon/wavelength/source/custom_models.py|WL_OT_detach_custom_model`
- `class|addon/wavelength/source/custom_models.py|WL_PT_custom_model`
- `class|addon/wavelength/source/model_backend_source1.py|Source1`
- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `class|addon/wavelength/source/model_io.py|_ModelBuildJob`
- `function|addon/wavelength/source/custom_models.py|WL_OT_detach_custom_model.execute`
- `function|addon/wavelength/source/custom_models.py|WL_PT_custom_model.draw`
- `function|addon/wavelength/source/custom_models.py|assign`
- `function|addon/wavelength/source/entity/models.py|copy_references`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.import_model`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.prepare`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.poll`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob.execute`
- `function|addon/wavelength/source/model_io.py|asset_for_object`
- `function|addon/wavelength/source/model_io.py|import_asset`
- `function|addon/wavelength/source/model_io.py|register`
- `function|addon/wavelength/source/model_io.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/entity/models.py|models`
- `module|addon/wavelength/source/model_backend_source1.py|model_backend_source1`
- `module|addon/wavelength/source/model_io.py|model_io`
- `test|tests/blender_model_pipeline.py|blender_model_pipeline`

## 2026-11-03T19:14:04+00:00

Features: WL-MODEL-017

Reviewed native modifier isolation: copy owned Geometry Nodes groups and remap object inputs/Mirror targets while preserving Blender tools. Independent rig/native modifier regression passes; no custom curving UI added.

added: 0; removed: 0; changed: 3

### Changed

- `function|addon/wavelength/source/model_lifecycle.py|_make_unique`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`
- `test|tests/blender_model_asset_rigs.py|blender_model_asset_rigs`

## 2026-11-03T20:43:18+00:00

Features: WL-MODEL-019, WL-MODEL-020, WL-MODEL-021, WL-MODEL-017, WL-MODEL-018

Add owned editable Source model textures, isolated target compiler snapshots, Source/Godot/CS2 conversion routes and verified portable packages. Preserve copy-out detach, native controls, placement identity and inclusion. Real Source1/CS2 compilation, Godot import, rig/clip timing, independent collision, transactional rollback and lifecycle tests exercised; CS2 animation/collision and Godot collision remain explicit stubs, native shader approximation requires opt-in. Existing saved-user-map shared-collision fixture has changed preconditions; deterministic shared-collision coverage added.

added: 69; removed: 0; changed: 30

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_asset_clip`
- `class|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_OT_package_model_asset`
- `class|addon/wavelength/source/model_transfer.py|Job`
- `class|addon/wavelength/source/model_transfer.py|Snapshot`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.editable_materials`
- `function|addon/wavelength/source/model_bundle.py|extract`
- `function|addon/wavelength/source/model_bundle.py|import_asset`
- `function|addon/wavelength/source/model_bundle.py|safe_path`
- `function|addon/wavelength/source/model_bundle.py|write`
- `function|addon/wavelength/source/model_io.py|WL_OT_asset_clip.execute`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.invoke`
- `function|addon/wavelength/source/model_io.py|WL_OT_package_model_asset.execute`
- `function|addon/wavelength/source/model_io.py|WL_OT_package_model_asset.poll`
- `function|addon/wavelength/source/model_io.py|_targets`
- `function|addon/wavelength/source/model_materials.py|_convert_basic`
- `function|addon/wavelength/source/model_materials.py|_source`
- `function|addon/wavelength/source/model_materials.py|realize`
- `function|addon/wavelength/source/model_pipeline.py|register_route`
- `function|addon/wavelength/source/model_pipeline.py|route`
- `function|addon/wavelength/source/model_transfer.py|Job.__init__`
- `function|addon/wavelength/source/model_transfer.py|Job._capture_editable`
- `function|addon/wavelength/source/model_transfer.py|Job._finish_source2`
- `function|addon/wavelength/source/model_transfer.py|Job.close`
- `function|addon/wavelength/source/model_transfer.py|Job.finish`
- `function|addon/wavelength/source/model_transfer.py|Job.omitted`
- `function|addon/wavelength/source/model_transfer.py|Job.write_package`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.__init__`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.__init__.tree`
- `function|addon/wavelength/source/model_transfer.py|Snapshot._dependency`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.activate`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.close`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.freeze`
- `function|addon/wavelength/source/model_transfer.py|Snapshot.restore_selection`
- `function|addon/wavelength/source/model_transfer.py|_clips_for_gltf`
- `function|addon/wavelength/source/model_transfer.py|_commit`
- `function|addon/wavelength/source/model_transfer.py|_commit_many`
- `function|addon/wavelength/source/model_transfer.py|_pbr_limits`
- `function|addon/wavelength/source/model_transfer.py|_source2_material`
- `function|addon/wavelength/source/model_transfer.py|_source2_material.image_input`
- `function|addon/wavelength/source/model_transfer.py|export_package`
- `function|addon/wavelength/source/model_transfer.py|godot`
- `function|addon/wavelength/source/model_transfer.py|prepare`
- `function|addon/wavelength/source/model_transfer.py|source1`
- `function|addon/wavelength/source/model_transfer.py|source2`
- `function|addon/wavelength/source/model_transfer.py|target_settings`
- `module|addon/wavelength/source/model_bundle.py|model_bundle`
- `module|addon/wavelength/source/model_transfer.py|model_transfer`
- `setting|addon/wavelength/source/model_io.py|WL_OT_asset_clip.remove`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.allow_lossy`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.compiler_directory`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.deploy`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.game_directory`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.output_directory`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.portable`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.source_name`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.target_addon`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.target_profile`
- `setting|addon/wavelength/source/model_io.py|WL_OT_package_model_asset.filter_glob`
- `test|tests/blender_model_transfer.py|blender_model_transfer`
- `test|tests/blender_model_transfer_animation.py|blender_model_transfer_animation`
- `test|tests/test_model_bundle.py|test_model_bundle`
- `ui|addon/wavelength/source/model_io.py|WL_OT_asset_clip.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_asset_clip.bl_label`
- `ui|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.bl_label`
- `ui|addon/wavelength/source/model_io.py|WL_OT_package_model_asset.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_package_model_asset.bl_label`

### Changed

- `class|addon/wavelength/source/model_backend_source1.py|Source1`
- `class|addon/wavelength/source/model_io.py|WL_OT_import_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `class|addon/wavelength/source/model_io.py|_ModelBuildJob`
- `function|addon/wavelength/source/custom_models.py|assign`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.prepare`
- `function|addon/wavelength/source/model_io.py|WL_OT_import_model_asset.invoke`
- `function|addon/wavelength/source/model_io.py|WL_OT_import_model_asset.poll`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob._close`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob.execute`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob.modal`
- `function|addon/wavelength/source/model_io.py|import_asset`
- `function|addon/wavelength/source/model_io.py|register`
- `function|addon/wavelength/source/model_lifecycle.py|_adopt`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique`
- `function|addon/wavelength/source/model_lifecycle.py|edit`
- `function|addon/wavelength/source/model_materials.py|convert`
- `function|addon/wavelength/source/model_smd.py|export`
- `function|addon/wavelength/source/native_source.py|migrate`
- `function|addon/wavelength/source/native_source.py|recover_missing_materials`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/model_backend_source1.py|model_backend_source1`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`
- `module|addon/wavelength/source/model_materials.py|model_materials`
- `module|addon/wavelength/source/model_pipeline.py|model_pipeline`
- `module|addon/wavelength/source/model_smd.py|model_smd`
- `module|addon/wavelength/source/native_source.py|native_source`

## 2026-11-03T20:45:32+00:00

Features: WL-MODEL-020

Correct deterministic cross-profile regression reader to inspect the standalone model output without requiring gameinfo.txt in an export folder. Native Source compilation and target snapshot behavior unchanged.

added: 0; removed: 0; changed: 1

### Changed

- `test|tests/blender_model_transfer_animation.py|blender_model_transfer_animation`

## 2026-11-04T12:58:00+03:00

Features: WL-MODEL-010, WL-TERR-001

Bug fix: custom-model source meshes tagged `wl_custom_model_owner` were silently reachable by the Source-displacement export path, causing Error 67eb3309 (non-affine displacement UV) on map export when stale displacement properties remained on the mesh.

Three complementary guards applied:

1. `source/source_displacement.py` `surfaces()` — added `and not o.get('wl_custom_model_owner')` predicate; model-source meshes are never enumerated as displacement surfaces regardless of property state.
2. `source/scene.py` `export_map()` PROFILE_EXPORT_FORMAT guard (line 145) — added `and not o.get('wl_custom_model_owner')` so model-source meshes do not trigger a spurious "Native displacements require a Source 1 profile" error on non-Source exports.
3. `source/custom_models.py` `assign()` — strips `wl_source_displacement`, `wl_terrain_face_corners`, `wl_terrain_source_corners`, `wl_terrain_face_matrix`, `wl_terrain_face_id`, `wl_displacement`, `wl_terrain`, `wl_terrain_seams`, `wl_terrain_detached` from each mesh at assignment time, preventing future accumulation of stale displacement state.

No displacement behavior removed; the guard is narrowly scoped to objects that are already excluded from BSP brush export by the `wl_custom_model_owner` flag.

Affected: `function|addon/wavelength/source/custom_models.py|assign`, `function|addon/wavelength/source/scene.py|export_map`, `function|addon/wavelength/source/source_displacement.py|surfaces`

added: 0; removed: 0; changed: 6


## 2026-11-04T09:59:14+00:00

Features: WL-MODEL-010, WL-TERR-001

Guard source_displacement.surfaces() against meshes tagged wl_custom_model_owner; strip stale displacement keys in custom_models.assign(); guard scene.py PROFILE_EXPORT_FORMAT check: prevents Error 67eb3309 non-affine displacement UV on model-source meshes

added: 0; removed: 0; changed: 7

### Changed

- `function|addon/wavelength/source/custom_models.py|assign`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/source_displacement.py|surfaces`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/source_displacement.py|source_displacement`

## 2026-11-04T10:07:08+00:00

Features: WL-MODEL-010

Verify and install existing prop-source displacement-tag fix. Added real StudioMDL regression proving assignment strips stale terrain metadata and model-owned children are ignored by displacement surface traversal while normal displacement children remain. No implementation removal or unrelated behavior change.

added: 1; removed: 0; changed: 1

### Added

- `test|tests/blender_model_source_displacement_tags.py|blender_model_source_displacement_tags`

### Changed

- `ledger|documentation/FEATURES.md|behavioral-contracts`

## 2026-11-04T20:32:11+00:00

Features: WL-TEX-003, WL-TEX-006

Route native VMAP/mesh-profile texture application through corner UVs and material slots rather than Source1 BSP face metadata. Preserve imported UVs for material-only painting, selected-face/object scope and Source1 projection behavior; explicit native-mesh mapping uses profile units. Tested exact de_dorms_d Brush.523 with object/edit Apply, drops/stamps and UV preservation; existing texture assignment/drop and surface tests retained.

added: 3; removed: 0; changed: 7

### Added

- `function|addon/wavelength/source/surface_tools.py|project_mesh_uv`
- `function|addon/wavelength/source/surface_tools.py|project_mesh_uv.coordinates`
- `test|tests/blender_source2_texture_assignment.py|blender_source2_texture_assignment`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `function|addon/wavelength/source/asset_placement.py|paint`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/asset_placement.py|asset_placement`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-04T20:35:59+00:00

Features: WL-TEX-003

Keep the VMAP geometry regression placeholder materials isolated from unrelated lazy realization timers. Actual material assignment, selected-face/drop behavior and UV preservation assertions unchanged; installed-module smoke test explicitly pins the installed addon path.

added: 0; removed: 0; changed: 1

### Changed

- `test|tests/blender_source2_texture_assignment.py|blender_source2_texture_assignment`

## 2026-11-04T22:30:40+00:00

Features: WL-XCOMP-002, WL-XCOMP-006

Use the selected source profile before stale material provenance, and verify the requested VMT exists in a candidate game mount before accepting that directory. Preserve material ownership, explicit loaded-pixel/placeholder choices and original source scene. Tested all 53 de_stronghold material names, actual layered concrete_floor_1_blend_1 conversion, source root fallback and existing conversion/blend regressions.

added: 1; removed: 0; changed: 5

### Added

- `test|tests/blender_stronghold_material_source.py|blender_stronghold_material_source`

### Changed

- `function|addon/wavelength/source/cross_compile.py|_source1_level`
- `function|addon/wavelength/source/source2_port_materials.py|source_game`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/cross_compile.py|cross_compile`
- `module|addon/wavelength/source/source2_port_materials.py|source2_port_materials`

## 2026-11-05T19:31:14+00:00

Features: WL-MODEL-020, WL-MODEL-021

Use a short Windows staging root to avoid WinError 206. Add native export names and make editable packages opt-in. Real StudioMDL verified named MDL and collision companions, alongside existing animation and cache regression.

added: 1; removed: 0; changed: 24

### Added

- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.model_name`

### Changed

- `class|addon/wavelength/source/custom_models.py|BuildModels`
- `class|addon/wavelength/source/model_backend_source1.py|Source1`
- `class|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset`
- `class|addon/wavelength/source/model_io.py|_ModelBuildJob`
- `class|addon/wavelength/source/model_transfer.py|Job`
- `function|addon/wavelength/source/custom_models.py|BuildModels.validated`
- `function|addon/wavelength/source/custom_models.py|prepare`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.prepare`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.invoke`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob.execute`
- `function|addon/wavelength/source/model_transfer.py|Job.__init__`
- `function|addon/wavelength/source/model_transfer.py|Job.finish`
- `function|addon/wavelength/source/model_transfer.py|godot`
- `function|addon/wavelength/source/model_transfer.py|prepare`
- `function|addon/wavelength/source/model_transfer.py|source1`
- `function|addon/wavelength/source/model_transfer.py|source2`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/model_backend_source1.py|model_backend_source1`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_transfer.py|model_transfer`
- `setting|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.portable`
- `test|tests/blender_model_transfer_animation.py|blender_model_transfer_animation`

## 2026-11-09T15:20:53+00:00

Features: WL-TERR-002, WL-TERR-004, WL-TERR-005, WL-TERR-007

Add generalized node heightfield controls and image sampling, coordinated network subdivision, shared native brush direction and blend-only sewing. Verified Blender profile heightmap to VMF, mixed-power network subdivision/painting/export and native Source import/export. Existing re-enable assertions encounter duplicate Asset Browser registration after terrain assertions pass.

added: 12; removed: 0; changed: 36

### Added

- `class|addon/wavelength/source/terrain.py|WL_OT_terrain_subdivide`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_subdivide.execute`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_subdivide.poll`
- `function|addon/wavelength/source/terrain.py|supports_terrain`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.heightmap`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.heightmap_midlevel`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.heightmap_scale`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.noise_detail`
- `setting|addon/wavelength/source/terrain.py|WLTerrain.noise_roughness`
- `setting|addon/wavelength/source/terrain.py|WL_OT_terrain_add.paintable_surface`
- `ui|addon/wavelength/source/terrain.py|WL_OT_terrain_subdivide.bl_idname`
- `ui|addon/wavelength/source/terrain.py|WL_OT_terrain_subdivide.bl_label`

### Changed

- `class|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement`
- `class|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement_paint`
- `class|addon/wavelength/source/terrain.py|WLTerrain`
- `class|addon/wavelength/source/terrain.py|WL_OT_terrain_add`
- `class|addon/wavelength/source/terrain.py|WL_OT_terrain_blend`
- `class|addon/wavelength/source/terrain.py|WL_PT_terrain`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement.execute`
- `function|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement_paint.modal`
- `function|addon/wavelength/source/source_displacement.py|paint_stroke`
- `function|addon/wavelength/source/source_displacement.py|sew`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_add.execute`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_add.poll`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.poll`
- `function|addon/wavelength/source/terrain.py|WL_PT_terrain.draw`
- `function|addon/wavelength/source/terrain.py|_update`
- `function|addon/wavelength/source/terrain.py|blend_settings`
- `function|addon/wavelength/source/terrain.py|brushes`
- `function|addon/wavelength/source/terrain.py|create`
- `function|addon/wavelength/source/terrain.py|group`
- `function|addon/wavelength/source/terrain.py|menu`
- `function|addon/wavelength/source/terrain.py|patches`
- `function|addon/wavelength/source/terrain.py|remember`
- `function|addon/wavelength/source/terrain_paint.py|preview_material`
- `function|addon/wavelength/source/terrain_sew.py|knots`
- `function|addon/wavelength/source/terrain_sew.py|patches`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/source_displacement.py|source_displacement`
- `module|addon/wavelength/source/terrain.py|terrain`
- `module|addon/wavelength/source/terrain_paint.py|terrain_paint`
- `module|addon/wavelength/source/terrain_sew.py|terrain_sew`
- `test|tests/blender_source_displacement_authoring.py|blender_source_displacement_authoring`
- `test|tests/blender_terrain.py|blender_terrain`
- `test|tests/blender_terrain_paint.py|blender_terrain_paint`
- `test|tests/blender_terrain_sew.py|blender_terrain_sew`

## 2026-11-09T15:21:23+00:00

Features: WL-TERR-002

Use the active Source unit scale for Blender-authored terrain when converting to editable native grids, matching VMF export. Preserve units on Source-owned grids.

added: 0; removed: 0; changed: 3

### Changed

- `class|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement`
- `function|addon/wavelength/source/source_displacement.py|WL_OT_source_displacement.execute`
- `module|addon/wavelength/source/source_displacement.py|source_displacement`

## 2026-11-09T15:40:36+00:00

Features: WL-TERR-008

Map quads from multi-object Edit Mode to live host Geometry Nodes modifiers with automatic compatible full-edge sewing and patch input controls. Verified multi-host and multi-face mapping, batch settings, viewport switches, actual render switches and Source export. Existing finalized-brush fixture fails before terrain creation in both installed baseline and checkout.

added: 28; removed: 0; changed: 22

### Added

- `class|addon/wavelength/source/terrain_face.py|WL_OT_copy_heightfield_inputs`
- `class|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields`
- `class|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_copy_heightfield_inputs.execute`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields.execute`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields.poll`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.draw`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.poll`
- `function|addon/wavelength/source/terrain_face.py|compose_mapping`
- `function|addon/wavelength/source/terrain_face.py|export_mesh`
- `function|addon/wavelength/source/terrain_face.py|map_selected_faces`
- `function|addon/wavelength/source/terrain_face.py|mapping_modifier`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_copy_heightfield_inputs)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_map_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_PT_face_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_copy_heightfield_inputs)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_map_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_PT_face_heightfields)`
- `setting|addon/wavelength/source/terrain_face.py|WL_OT_copy_heightfield_inputs.patch_name`
- `setting|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields.auto_sew`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_copy_heightfield_inputs.bl_idname`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_copy_heightfield_inputs.bl_label`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields.bl_idname`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_map_heightfields.bl_label`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.bl_context`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.bl_label`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.bl_space_type`

### Changed

- `class|addon/wavelength/source/terrain_face.py|WL_OT_displacement_detach`
- `function|addon/wavelength/source/geometry_debug.py|inspect`
- `function|addon/wavelength/source/mesh_assets.py|export`
- `function|addon/wavelength/source/scene.py|brush_from_object`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/source2_map.py|export`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_displacement_detach.execute`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_displacement_detach.poll`
- `function|addon/wavelength/source/terrain_face.py|apply`
- `function|addon/wavelength/source/terrain_face.py|menu`
- `function|addon/wavelength/source/terrain_face.py|refresh`
- `function|addon/wavelength/source/terrain_face.py|register`
- `function|addon/wavelength/source/terrain_face.py|unregister`
- `function|addon/wavelength/source/terrain_face.py|validate_attachment`
- `function|addon/wavelength/source/terrain_sew.py|sew`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/geometry_debug.py|geometry_debug`
- `module|addon/wavelength/source/mesh_assets.py|mesh_assets`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/source2_map.py|source2_map`
- `module|addon/wavelength/source/terrain_face.py|terrain_face`
- `module|addon/wavelength/source/terrain_sew.py|terrain_sew`

## 2026-11-09T15:49:31+00:00

Features: WL-TERR-004, WL-TERR-008, WL-TERR-009

Expose mapped host painting without applying Geometry Nodes. Reuse existing height, smooth and texture brush paths and stage a shared Source transition material for sewn patches. Verified hidden-target evaluation, painted seam continuity, preserved geometry on blend-only strokes, VMF alpha/offset roundtrip and native VBSP.

added: 3; removed: 0; changed: 14

### Added

- `function|addon/wavelength/source/terrain_paint.py|paint_target`
- `setting|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.patch_name`
- `setting|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.patch_name`

### Changed

- `class|addon/wavelength/source/terrain.py|WL_OT_terrain_blend`
- `class|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields`
- `class|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.execute`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.poll`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.draw`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.invoke`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.modal`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.poll`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain.py|terrain`
- `module|addon/wavelength/source/terrain_face.py|terrain_face`
- `module|addon/wavelength/source/terrain_paint.py|terrain_paint`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`

## 2026-11-09T16:00:24+00:00

Features: WL-TERR-009

Share mapped terrain painting controls and Source blend palette per scene. Verified shared host switching, painted VMF roundtrip and native VBSP.

added: 19; removed: 0; changed: 18

### Added

- `class|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint`
- `class|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint.draw`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint.poll`
- `function|addon/wavelength/source/terrain_paint.py|mapped_paint_members`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_PT_mapped_terrain_paint)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_PT_mapped_terrain_paint)`
- `hook|addon/wavelength/source/terrain_paint.py|bpy.utils.register_class(WLMappedPaintSettings)`
- `hook|addon/wavelength/source/terrain_paint.py|bpy.utils.unregister_class(WLMappedPaintSettings)`
- `setting|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.shared`
- `setting|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings.blend_base`
- `setting|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings.paint_material`
- `setting|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings.paint_opacity`
- `setting|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings.paint_radius`
- `setting|addon/wavelength/source/terrain_paint.py|WLMappedPaintSettings.paint_strength`
- `setting|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.shared`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint.bl_context`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint.bl_label`
- `ui|addon/wavelength/source/terrain_face.py|WL_PT_mapped_terrain_paint.bl_space_type`

### Changed

- `class|addon/wavelength/source/terrain.py|WL_OT_terrain_blend`
- `class|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields`
- `class|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint`
- `function|addon/wavelength/source/terrain.py|WL_OT_terrain_blend.execute`
- `function|addon/wavelength/source/terrain.py|create_blend`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.draw`
- `function|addon/wavelength/source/terrain_face.py|register`
- `function|addon/wavelength/source/terrain_face.py|unregister`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint._draw`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.invoke`
- `function|addon/wavelength/source/terrain_paint.py|WL_OT_terrain_paint.modal`
- `function|addon/wavelength/source/terrain_paint.py|register`
- `function|addon/wavelength/source/terrain_paint.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain.py|terrain`
- `module|addon/wavelength/source/terrain_face.py|terrain_face`
- `module|addon/wavelength/source/terrain_paint.py|terrain_paint`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`

## 2026-11-09T16:03:57+00:00

Features: WL-TERR-008

Consolidate mapped face controls with individual and group scope. Background Blender regression verified group membership, field isolation, retained copy operation and VMF roundtrip.

added: 14; removed: 0; changed: 7

### Added

- `class|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.draw`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.execute`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.invoke`
- `function|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.poll`
- `function|addon/wavelength/source/terrain_face.py|apply_group_inputs`
- `function|addon/wavelength/source/terrain_face.py|draw_inputs`
- `function|addon/wavelength/source/terrain_face.py|heightfield_group`
- `function|addon/wavelength/source/terrain_face.py|heightfield_scopes`
- `function|addon/wavelength/source/terrain_face.py|mapped_patches`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_edit_heightfield_group)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_edit_heightfield_group)`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.bl_idname`
- `ui|addon/wavelength/source/terrain_face.py|WL_OT_edit_heightfield_group.bl_label`

### Changed

- `class|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields`
- `function|addon/wavelength/source/terrain_face.py|WL_PT_face_heightfields.draw`
- `function|addon/wavelength/source/terrain_face.py|register`
- `function|addon/wavelength/source/terrain_face.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain_face.py|terrain_face`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`

## 2026-11-09T16:45:12+00:00

Features: WL-TERR-002, WL-TERR-003, WL-TERR-004, WL-TERR-005, WL-TERR-006, WL-TERR-007, WL-TERR-008, WL-TERR-009

Retire procedural terrain authoring registration, toolbar and menus ahead of the continuous terrain redesign. Retain saved terrain evaluation, Source native controls and export. Blender verified command retirement and mapped/native VMF compatibility.

added: 2; removed: 17; changed: 13

### Added

- `hook|addon/wavelength/source/terrain.py|bpy.utils.register_class(WLTerrain)`
- `hook|addon/wavelength/source/terrain.py|bpy.utils.unregister_class(WLTerrain)`

### Removed

- `function|addon/wavelength/source/terrain.py|menu`
- `hook|addon/wavelength/source/terrain.py|bpy.utils.register_class(cls)`
- `hook|addon/wavelength/source/terrain.py|bpy.utils.unregister_class(cls)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_copy_heightfield_inputs)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_displacement_detach)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_displacement_from_face)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_edit_heightfield_group)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_OT_map_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_PT_face_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.register_class(WL_PT_mapped_terrain_paint)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_copy_heightfield_inputs)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_displacement_detach)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_displacement_from_face)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_edit_heightfield_group)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_OT_map_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_PT_face_heightfields)`
- `hook|addon/wavelength/source/terrain_face.py|bpy.utils.unregister_class(WL_PT_mapped_terrain_paint)`

### Changed

- `function|addon/wavelength/source/engine_tools.py|_draw`
- `function|addon/wavelength/source/source_displacement.py|register`
- `function|addon/wavelength/source/source_displacement.py|unregister`
- `function|addon/wavelength/source/terrain.py|register`
- `function|addon/wavelength/source/terrain.py|unregister`
- `function|addon/wavelength/source/terrain_face.py|register`
- `function|addon/wavelength/source/terrain_face.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/engine_tools.py|engine_tools`
- `module|addon/wavelength/source/source_displacement.py|source_displacement`
- `module|addon/wavelength/source/terrain.py|terrain`
- `module|addon/wavelength/source/terrain_face.py|terrain_face`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`

## 2026-11-09T16:50:13+00:00

Features: WL-TERR-010

Add isolated continuous terrain parameter sampling prototype and fixture. Native subdivision and a cage edit preserve three Source patches, verified with VMF reconstruction and HL2 VBSP. Existing authoring and export paths are unchanged.

added: 5; removed: 0; changed: 1

### Added

- `function|addon/wavelength/source/terrain_surface.py|cage`
- `function|addon/wavelength/source/terrain_surface.py|sample`
- `function|addon/wavelength/source/terrain_surface.py|source_grid`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `test|tests/blender_terrain_surface.py|blender_terrain_surface`

### Changed

- `ledger|documentation/FEATURES.md|behavioral-contracts`

## 2026-11-09T16:56:55+00:00

Features: WL-TERR-011

Add multi-object Edit Mode terrain creation with exact full-edge grouping, persistent host and face bindings, native subdivision and a separate operator ID preserving the terrain plane tool.

added: 13; removed: 0; changed: 5

### Added

- `class|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain.execute`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain.poll`
- `function|addon/wavelength/source/terrain_surface.py|connected_regions`
- `function|addon/wavelength/source/terrain_surface.py|create_selected`
- `function|addon/wavelength/source/terrain_surface.py|menu`
- `function|addon/wavelength/source/terrain_surface.py|register`
- `function|addon/wavelength/source/terrain_surface.py|unregister`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.register_class(WL_OT_create_terrain)`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.unregister_class(WL_OT_create_terrain)`
- `test|tests/blender_create_terrain.py|blender_create_terrain`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain.bl_idname`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain.bl_label`

### Changed

- `function|addon/wavelength/source/terrain.py|register`
- `function|addon/wavelength/source/terrain.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain.py|terrain`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`

## 2026-11-09T16:59:58+00:00

Features: WL-TERR-011

Complete terrain creation entry points with whole-mesh creation and a viewport face picker using the same validated cage builder. Blender verified both mesh entry points, picker registration and existing Source sampling. Interactive overlay verification remains pending.

added: 22; removed: 0; changed: 8

### Added

- `class|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain_from_meshes`
- `class|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain_from_meshes.execute`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain_from_meshes.poll`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.cancel`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.draw_preview`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.finish`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.invoke`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.modal`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.poll`
- `function|addon/wavelength/source/terrain_surface.py|collect_faces`
- `function|addon/wavelength/source/terrain_surface.py|edit_faces`
- `function|addon/wavelength/source/terrain_surface.py|object_faces`
- `function|addon/wavelength/source/terrain_surface.py|object_menu`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.register_class(WL_OT_create_terrain_from_meshes)`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.register_class(WL_OT_pick_terrain_faces)`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.unregister_class(WL_OT_create_terrain_from_meshes)`
- `hook|addon/wavelength/source/terrain_surface.py|bpy.utils.unregister_class(WL_OT_pick_terrain_faces)`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain_from_meshes.bl_idname`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain_from_meshes.bl_label`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.bl_idname`
- `ui|addon/wavelength/source/terrain_surface.py|WL_OT_pick_terrain_faces.bl_label`

### Changed

- `class|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain`
- `function|addon/wavelength/source/terrain_surface.py|WL_OT_create_terrain.poll`
- `function|addon/wavelength/source/terrain_surface.py|create_selected`
- `function|addon/wavelength/source/terrain_surface.py|register`
- `function|addon/wavelength/source/terrain_surface.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `test|tests/blender_create_terrain.py|blender_create_terrain`

## 2026-11-09T17:04:06+00:00

Features: WL-TERR-012, WL-TERR-013

Add native weight painting, Source alpha sampling, optional live detail, and persistent named revision copies. Blender verified seam alpha, geometry evaluation, independent restore and file reopen.

added: 38; removed: 0; changed: 7

### Added

- `class|addon/wavelength/source/terrain_revision.py|TerrainAction`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_add_terrain_detail`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_paint_terrain_blend`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision`
- `class|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain`
- `function|addon/wavelength/source/terrain_detail.py|detail_group`
- `function|addon/wavelength/source/terrain_detail.py|detail_group.math`
- `function|addon/wavelength/source/terrain_detail.py|detail_group.node`
- `function|addon/wavelength/source/terrain_revision.py|TerrainAction.poll`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_add_terrain_detail.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_paint_terrain_blend.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision.invoke`
- `function|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.draw`
- `function|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.poll`
- `function|addon/wavelength/source/terrain_revision.py|copy_surface`
- `function|addon/wavelength/source/terrain_revision.py|register`
- `function|addon/wavelength/source/terrain_revision.py|save_revision`
- `function|addon/wavelength/source/terrain_revision.py|unregister`
- `hook|addon/wavelength/source/terrain_revision.py|bpy.utils.register_class(cls)`
- `hook|addon/wavelength/source/terrain_revision.py|bpy.utils.unregister_class(cls)`
- `module|addon/wavelength/source/terrain_detail.py|terrain_detail`
- `module|addon/wavelength/source/terrain_revision.py|terrain_revision`
- `setting|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision.name`
- `setting|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision.name`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_add_terrain_detail.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_add_terrain_detail.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_paint_terrain_blend.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_paint_terrain_blend.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_save_terrain_revision.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.bl_context`
- `ui|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.bl_space_type`

### Changed

- `function|addon/wavelength/source/terrain_surface.py|register`
- `function|addon/wavelength/source/terrain_surface.py|sample`
- `function|addon/wavelength/source/terrain_surface.py|source_grid`
- `function|addon/wavelength/source/terrain_surface.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `test|tests/blender_create_terrain.py|blender_create_terrain`

## 2026-11-11T14:19:23+00:00

Features: WL-TERR-011, WL-TERR-012, WL-TERR-013, WL-TERR-014, WL-TERR-015

Integrate continuous terrain with normal Source VMF export and shared inspection, add explicit boundary anchors and protect export from duplicate revision claims. Verified deformed VMF parity, VBSP and deleted-target handling.

added: 32; removed: 0; changed: 17

### Added

- `class|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor`
- `class|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_hide_terrain_game_preview`
- `class|addon/wavelength/source/terrain_revision.py|WL_OT_terrain_game_preview`
- `function|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor.execute`
- `function|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor.poll`
- `function|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors.execute`
- `function|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors.poll`
- `function|addon/wavelength/source/terrain_anchors.py|bind`
- `function|addon/wavelength/source/terrain_anchors.py|refresh`
- `function|addon/wavelength/source/terrain_anchors.py|register`
- `function|addon/wavelength/source/terrain_anchors.py|topology_signature`
- `function|addon/wavelength/source/terrain_anchors.py|unregister`
- `function|addon/wavelength/source/terrain_output.py|preview_mesh`
- `function|addon/wavelength/source/terrain_output.py|source_patches`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_hide_terrain_game_preview.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_terrain_game_preview.execute`
- `hook|addon/wavelength/source/terrain_anchors.py|bpy.utils.register_class(cls)`
- `hook|addon/wavelength/source/terrain_anchors.py|bpy.utils.unregister_class(cls)`
- `module|addon/wavelength/source/terrain_anchors.py|terrain_anchors`
- `module|addon/wavelength/source/terrain_output.py|terrain_output`
- `setting|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor.follow`
- `setting|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors.clear`
- `setting|addon/wavelength/source/terrain_revision.py|WL_OT_terrain_game_preview.mode`
- `ui|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor.bl_idname`
- `ui|addon/wavelength/source/terrain_anchors.py|WL_OT_bind_terrain_anchor.bl_label`
- `ui|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors.bl_idname`
- `ui|addon/wavelength/source/terrain_anchors.py|WL_OT_refresh_terrain_anchors.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_hide_terrain_game_preview.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_hide_terrain_game_preview.bl_label`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_terrain_game_preview.bl_idname`
- `ui|addon/wavelength/source/terrain_revision.py|WL_OT_terrain_game_preview.bl_label`

### Changed

- `class|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision`
- `class|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/terrain_revision.py|WL_OT_restore_terrain_revision.execute`
- `function|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.draw`
- `function|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.poll`
- `function|addon/wavelength/source/terrain_revision.py|copy_surface`
- `function|addon/wavelength/source/terrain_revision.py|register`
- `function|addon/wavelength/source/terrain_revision.py|unregister`
- `function|addon/wavelength/source/terrain_surface.py|collect_faces`
- `function|addon/wavelength/source/terrain_surface.py|edit_faces`
- `function|addon/wavelength/source/terrain_surface.py|object_faces`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/terrain_revision.py|terrain_revision`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `test|tests/blender_terrain_surface.py|blender_terrain_surface`

## 2026-11-11T14:23:43+00:00

Features: WL-TERR-002, WL-TERR-003, WL-TERR-004, WL-TERR-005, WL-TERR-006, WL-TERR-007, WL-TERR-008, WL-TERR-009, WL-TERR-014, WL-TERR-016

Add reversible migration for native Source grids and evaluated mesh copies for legacy terrain. Verified native edited VMF with metadata, legacy export compatibility, normal HL2 VBSP and Godot GLB output.

added: 20; removed: 0; changed: 14

### Added

- `class|addon/wavelength/source/terrain_migration.py|WL_OT_migrate_terrain`
- `class|addon/wavelength/source/terrain_migration.py|WL_OT_use_migrated_terrain`
- `function|addon/wavelength/source/terrain_migration.py|WL_OT_migrate_terrain.execute`
- `function|addon/wavelength/source/terrain_migration.py|WL_OT_migrate_terrain.poll`
- `function|addon/wavelength/source/terrain_migration.py|WL_OT_use_migrated_terrain.execute`
- `function|addon/wavelength/source/terrain_migration.py|menu`
- `function|addon/wavelength/source/terrain_migration.py|migrate_legacy`
- `function|addon/wavelength/source/terrain_migration.py|migrate_native`
- `function|addon/wavelength/source/terrain_migration.py|native_mesh`
- `function|addon/wavelength/source/terrain_migration.py|register`
- `function|addon/wavelength/source/terrain_migration.py|unregister`
- `hook|addon/wavelength/source/terrain_migration.py|bpy.utils.register_class(WL_OT_migrate_terrain)`
- `hook|addon/wavelength/source/terrain_migration.py|bpy.utils.register_class(WL_OT_use_migrated_terrain)`
- `hook|addon/wavelength/source/terrain_migration.py|bpy.utils.unregister_class(WL_OT_migrate_terrain)`
- `hook|addon/wavelength/source/terrain_migration.py|bpy.utils.unregister_class(WL_OT_use_migrated_terrain)`
- `module|addon/wavelength/source/terrain_migration.py|terrain_migration`
- `ui|addon/wavelength/source/terrain_migration.py|WL_OT_migrate_terrain.bl_idname`
- `ui|addon/wavelength/source/terrain_migration.py|WL_OT_migrate_terrain.bl_label`
- `ui|addon/wavelength/source/terrain_migration.py|WL_OT_use_migrated_terrain.bl_idname`
- `ui|addon/wavelength/source/terrain_migration.py|WL_OT_use_migrated_terrain.bl_label`

### Changed

- `class|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/terrain_output.py|source_patches`
- `function|addon/wavelength/source/terrain_revision.py|WL_PT_continuous_terrain.draw`
- `function|addon/wavelength/source/terrain_surface.py|register`
- `function|addon/wavelength/source/terrain_surface.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/terrain_output.py|terrain_output`
- `module|addon/wavelength/source/terrain_revision.py|terrain_revision`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `test|tests/blender_source_displacement.py|blender_source_displacement`
- `test|tests/blender_terrain_face_mapping.py|blender_terrain_face_mapping`
- `test|tests/blender_terrain_surface.py|blender_terrain_surface`

## 2026-11-11T15:23:46+00:00

Features: WL-GRID-014, WL-GEO-001

Replace offset footprint motion with pointer ray projection. Consolidate brush snap markers and preserve geometry target priority. Verified perspective accuracy, grid policy and simulated stair cancel, commit and undo.

added: 2; removed: 1; changed: 13

### Added

- `function|addon/wavelength/source/brush_create.py|_draw_snap`
- `test|tests/blender_stair_pointer_ui.py|blender_stair_pointer_ui`

### Removed

- `function|addon/wavelength/source/cutter_snap.py|creation_point`

### Changed

- `class|addon/wavelength/source/brush_create.py|WL_OT_brush_hover`
- `class|addon/wavelength/source/brush_create.py|WL_OT_cube_brush_create`
- `function|addon/wavelength/source/brush_create.py|WL_OT_brush_hover.invoke`
- `function|addon/wavelength/source/brush_create.py|WL_OT_cube_brush_create._draw`
- `function|addon/wavelength/source/brush_create.py|WL_OT_cube_brush_create._footprint_drag_from_mouse`
- `function|addon/wavelength/source/brush_create.py|WL_OT_cube_brush_create.invoke`
- `function|addon/wavelength/source/brush_create.py|WL_OT_cube_brush_create.modal`
- `function|addon/wavelength/source/brush_create.py|_draw_idle_hover`
- `function|addon/wavelength/source/brush_create.py|unregister_tool`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/brush_create.py|brush_create`
- `module|addon/wavelength/source/cutter_snap.py|cutter_snap`
- `test|tests/blender_creation_snap.py|blender_creation_snap`

## 2026-11-11T15:31:40+00:00

Features: WL-PROF-001, WL-PROF-002

Standardize profile display labels while preserving saved names, inherited settings, IDs and enum numbers. Blender registry verified built-in, registered and Steam labels.

added: 1; removed: 0; changed: 7

### Added

- `function|addon/wavelength/source/profile_ui.py|registered_label`

### Changed

- `configuration|addon/wavelength/environment/profiles/templates.json|templates.json`
- `function|addon/wavelength/source/profile_ui.py|draw_registry`
- `function|addon/wavelength/source/profile_ui.py|items`
- `function|addon/wavelength/source/profile_ui.py|parents`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/profile_ui.py|profile_ui`
- `test|tests/blender_profile_registry.py|blender_profile_registry`

## 2026-11-11T15:36:46+00:00

Features: WL-PROF-001, WL-PROF-002

Sort profile labels by engine, game and platform, omit launcher text, and collapse duplicate registered picker labels while preserving stored profiles and enum identities. Verified registry fixtures.

added: 1; removed: 0; changed: 8

### Added

- `function|addon/wavelength/source/profiles.py|profile_sort_key`

### Changed

- `configuration|addon/wavelength/environment/profiles/templates.json|templates.json`
- `function|addon/wavelength/source/profile_ui.py|items`
- `function|addon/wavelength/source/profile_ui.py|parents`
- `function|addon/wavelength/source/profile_ui.py|registered_label`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/profile_ui.py|profile_ui`
- `module|addon/wavelength/source/profiles.py|profiles`
- `test|tests/blender_profile_registry.py|blender_profile_registry`

## 2026-11-11T15:42:49+00:00

Features: WL-GEO-008, WL-GEO-009, WL-GEO-011, WL-GRID-014

Lock cutter drawing to the initial plane in every profile, suppress free-placement markers and preview the retained side on open splits. Verified perspective placement, finite-depth volume, retained side and interactive undo.

added: 1; removed: 0; changed: 15

### Added

- `function|addon/wavelength/source/cutter_solid.py|open_cut_side`

### Changed

- `class|addon/wavelength/source/cutter_snap.py|Targets`
- `class|addon/wavelength/source/pencil.py|WL_OT_draw_path`
- `function|addon/wavelength/source/cutter_snap.py|Targets.resolve`
- `function|addon/wavelength/source/cutter_snap.py|hover`
- `function|addon/wavelength/source/cutter_solid.py|apply`
- `function|addon/wavelength/source/pencil.py|WL_OT_draw_path._begin_extrude`
- `function|addon/wavelength/source/pencil.py|WL_OT_draw_path._draw`
- `function|addon/wavelength/source/pencil.py|WL_OT_draw_path._extrude_modal`
- `function|addon/wavelength/source/pencil.py|WL_OT_draw_path._update`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/cutter_snap.py|cutter_snap`
- `module|addon/wavelength/source/cutter_solid.py|cutter_solid`
- `module|addon/wavelength/source/pencil.py|pencil`
- `test|tests/blender_creation_snap.py|blender_creation_snap`
- `test|tests/blender_cutter_volume_controls.py|blender_cutter_volume_controls`

## 2026-11-11T19:17:39+00:00

Features: WL-GRID-009, WL-GRID-010, WL-GRID-011

Shape handles use the resolved face center and work in Profile and Metric grid modes. The header reports the resulting span during drag. Grid snapping follows the active translation snap target and spacing. Blender background tests cover both grid modes, unsnapped dragging, fixed opposite bounds, face membership, handle size and origin rebasing. Interactive pointer and header rendering require a viewport check.

added: 0; removed: 0; changed: 11

### Changed

- `class|addon/wavelength/source/resize_gizmo.py|WL_GGT_engine_resize`
- `function|addon/wavelength/source/resize_gizmo.py|WL_GGT_engine_resize.poll`
- `function|addon/wavelength/source/resize_gizmo.py|WL_GGT_engine_resize.refresh`
- `function|addon/wavelength/source/resize_gizmo.py|WL_GGT_engine_resize.setup`
- `function|addon/wavelength/source/resize_gizmo.py|WL_GGT_engine_resize.setup.setter`
- `function|addon/wavelength/source/resize_gizmo.py|_boundary_delta`
- `function|addon/wavelength/source/resize_gizmo.py|_brush`
- `function|addon/wavelength/source/resize_gizmo.py|_finish_origins`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/resize_gizmo.py|resize_gizmo`
- `test|tests/blender_procedural_resize.py|blender_procedural_resize`

## 2026-11-11T19:24:55+00:00

Features: WL-GEO-019, WL-GEO-002, WL-GEO-007

Added the opt-in straight-stair landing fit with persistent connection references and preview/apply/discard. Uses the existing generator and ownership, derives exact rise/run, and clears preview on finalization. Verified HL2 convex brush extraction, stale preview rejection, finalization, and standard and legacy stair generation in Blender background mode. Curved stairs are excluded and moving a connection requires a new preview.

added: 26; removed: 0; changed: 8

### Added

- `class|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair`
- `class|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair`
- `function|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair.execute`
- `function|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair.poll`
- `function|addon/wavelength/source/landing_stairs.py|_fit`
- `function|addon/wavelength/source/landing_stairs.py|_preview`
- `function|addon/wavelength/source/landing_stairs.py|_proposal`
- `function|addon/wavelength/source/landing_stairs.py|_straight_root`
- `function|addon/wavelength/source/landing_stairs.py|discard`
- `function|addon/wavelength/source/landing_stairs.py|draw`
- `function|addon/wavelength/source/landing_stairs.py|register`
- `function|addon/wavelength/source/landing_stairs.py|unregister`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.register_class(WL_OT_landing_stair)`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.register_class(WL_PG_landing_stair)`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.unregister_class(WL_OT_landing_stair)`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.unregister_class(WL_PG_landing_stair)`
- `module|addon/wavelength/source/landing_stairs.py|landing_stairs`
- `setting|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair.action`
- `setting|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair.lower`
- `setting|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair.max_rise`
- `setting|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair.min_tread`
- `setting|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair.steps`
- `setting|addon/wavelength/source/landing_stairs.py|WL_PG_landing_stair.upper`
- `test|tests/blender_landing_stairs.py|blender_landing_stairs`
- `ui|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair.bl_idname`
- `ui|addon/wavelength/source/landing_stairs.py|WL_OT_landing_stair.bl_label`

### Changed

- `class|addon/wavelength/source/primitive_ui.py|WL_PT_primitive`
- `function|addon/wavelength/source/primitive_ui.py|WL_PT_primitive.draw`
- `function|addon/wavelength/source/primitive_ui.py|finalize`
- `function|addon/wavelength/source/primitive_ui.py|rebuild`
- `function|addon/wavelength/source/primitive_ui.py|register`
- `function|addon/wavelength/source/primitive_ui.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/primitive_ui.py|primitive_ui`

## 2026-11-11T19:31:07+00:00

Features: WL-GEO-019

Moved the landing fit controls from a nested box into a dedicated Object Properties panel. The same straight-stair context and operator are retained. Background regression verifies panel eligibility and the existing fit lifecycle.

added: 9; removed: 1; changed: 8

### Added

- `class|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair`
- `function|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.draw`
- `function|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.poll`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.register_class(WL_PT_landing_stair)`
- `hook|addon/wavelength/source/landing_stairs.py|bpy.utils.unregister_class(WL_PT_landing_stair)`
- `ui|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.bl_context`
- `ui|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.bl_idname`
- `ui|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.bl_label`
- `ui|addon/wavelength/source/landing_stairs.py|WL_PT_landing_stair.bl_space_type`

### Removed

- `function|addon/wavelength/source/landing_stairs.py|draw`

### Changed

- `class|addon/wavelength/source/primitive_ui.py|WL_PT_primitive`
- `function|addon/wavelength/source/landing_stairs.py|register`
- `function|addon/wavelength/source/landing_stairs.py|unregister`
- `function|addon/wavelength/source/primitive_ui.py|WL_PT_primitive.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/landing_stairs.py|landing_stairs`
- `module|addon/wavelength/source/primitive_ui.py|primitive_ui`
- `test|tests/blender_landing_stairs.py|blender_landing_stairs`

## 2026-11-11T19:40:44+00:00

Features: WL-GEO-019, WL-GEO-020

Registered open Poly fence routes with explicit preview, apply and discard, gate clearance across bends, and normal profile geometry output. Background tests restore undo snapshots and round-trip HL2 VMF for both fence and landing stair. Fence applies replace generated objects, support one open Poly spline and check gate clearance in plan view.

added: 47; removed: 0; changed: 5

### Added

- `class|addon/wavelength/source/fence_route.py|WL_OT_add_fence_route`
- `class|addon/wavelength/source/fence_route.py|WL_OT_fence_route`
- `class|addon/wavelength/source/fence_route.py|WL_PG_fence_route`
- `class|addon/wavelength/source/fence_route.py|WL_PT_fence_route`
- `function|addon/wavelength/source/fence_route.py|WL_OT_add_fence_route.execute`
- `function|addon/wavelength/source/fence_route.py|WL_OT_add_fence_route.poll`
- `function|addon/wavelength/source/fence_route.py|WL_OT_fence_route.execute`
- `function|addon/wavelength/source/fence_route.py|WL_OT_fence_route.poll`
- `function|addon/wavelength/source/fence_route.py|WL_PT_fence_route.draw`
- `function|addon/wavelength/source/fence_route.py|WL_PT_fence_route.poll`
- `function|addon/wavelength/source/fence_route.py|_apply`
- `function|addon/wavelength/source/fence_route.py|_discard`
- `function|addon/wavelength/source/fence_route.py|_draw_add_menu`
- `function|addon/wavelength/source/fence_route.py|_mesh`
- `function|addon/wavelength/source/fence_route.py|_preview`
- `function|addon/wavelength/source/fence_route.py|_proposal`
- `function|addon/wavelength/source/fence_route.py|_remove`
- `function|addon/wavelength/source/fence_route.py|placement`
- `function|addon/wavelength/source/fence_route.py|placement.clears_opening`
- `function|addon/wavelength/source/fence_route.py|placement.point_at`
- `function|addon/wavelength/source/fence_route.py|register`
- `function|addon/wavelength/source/fence_route.py|unregister`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.register_class(WL_OT_add_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.register_class(WL_OT_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.register_class(WL_PG_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.register_class(WL_PT_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.unregister_class(WL_OT_add_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.unregister_class(WL_OT_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.unregister_class(WL_PG_fence_route)`
- `hook|addon/wavelength/source/fence_route.py|bpy.utils.unregister_class(WL_PT_fence_route)`
- `module|addon/wavelength/source/fence_route.py|fence_route`
- `setting|addon/wavelength/source/fence_route.py|WL_OT_fence_route.action`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.gate_center`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.gate_width`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.material`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.post_height`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.post_width`
- `setting|addon/wavelength/source/fence_route.py|WL_PG_fence_route.spacing`
- `test|tests/blender_fence_route.py|blender_fence_route`
- `ui|addon/wavelength/source/fence_route.py|WL_OT_add_fence_route.bl_idname`
- `ui|addon/wavelength/source/fence_route.py|WL_OT_add_fence_route.bl_label`
- `ui|addon/wavelength/source/fence_route.py|WL_OT_fence_route.bl_idname`
- `ui|addon/wavelength/source/fence_route.py|WL_OT_fence_route.bl_label`
- `ui|addon/wavelength/source/fence_route.py|WL_PT_fence_route.bl_context`
- `ui|addon/wavelength/source/fence_route.py|WL_PT_fence_route.bl_idname`
- `ui|addon/wavelength/source/fence_route.py|WL_PT_fence_route.bl_label`
- `ui|addon/wavelength/source/fence_route.py|WL_PT_fence_route.bl_space_type`

### Changed

- `function|addon/wavelength/source/ui.py|register`
- `function|addon/wavelength/source/ui.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_landing_stairs.py|blender_landing_stairs`

## 2026-11-11T19:52:52+00:00

Features: WL-IO-011

Preserve per-polygon material indices when replacing evaluated mesh material slots. Tested a textured second slot in Blender and all 11 compact fixture meshes in Godot, including node-evaluated stairs and terrain. Godot runtime collision was created explicitly from imported meshes.

added: 0; removed: 0; changed: 4

### Changed

- `function|addon/wavelength/source/mesh_assets.py|export`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/mesh_assets.py|mesh_assets`
- `test|tests/blender_mesh_assets.py|blender_mesh_assets`

## 2026-11-11T20:03:10+00:00

Features: WL-DIST-002, WL-DIST-005, WL-PROF-001

Shared add-on archive selection retains the generated handbook manifest and machine-readable feature inventory. Regression verifies these files are included while unapproved metadata stays excluded. Corrected saved profile enum regression to assert each historic key retains its numeric ID regardless of presentation order.

added: 1; removed: 0; changed: 7

### Added

- `function|installer/wavelength_installer/source_bundle.py|addon_files`

### Changed

- `function|installer/wavelength_installer/source_bundle.py|bundle_from_source`
- `function|tools/release.py|package`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|installer/wavelength_installer/source_bundle.py|source_bundle`
- `module|tools/release.py|release`
- `test|tests/test_docs.py|test_docs`
- `test|tests/test_mesh_profiles.py|test_mesh_profiles`

## 2026-11-11T20:04:22+00:00

Features: WL-DIST-002, WL-DIST-005

Include root AGENTS.md in full and source installer archives because its fingerprint is required when source installations synchronize the bundled handbook.

added: 0; removed: 0; changed: 3

### Changed

- `function|tools/build_installer.py|main`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|tools/build_installer.py|build_installer`

## 2026-11-11T20:15:58+00:00

Features: WL-MODEL-019, WL-MODEL-010

Source StudioMDL builds discover materials used by evaluated faces before converting dependencies. A real compiler round trip verifies a Geometry Nodes-only material survives and original slots, modifiers and game files remain unchanged.

added: 0; removed: 0; changed: 6

### Changed

- `function|addon/wavelength/source/custom_models.py|prepare`
- `function|addon/wavelength/source/model_smd.py|export`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/model_smd.py|model_smd`
- `test|tests/blender_model_pipeline.py|blender_model_pipeline`

## 2026-11-12T14:33:33+00:00

Features: WL-TEX-013, WL-TEX-006, WL-TEX-007

Live mapping UI fields apply incremental shift, rotation and scale without painting materials or triggering from sampling. Source brush face metadata and selected live BMesh UVs stay in sync, and native mesh UVs update from Asset Browser context. Verified repeated RNA writes, unselected face isolation, source export axes, native UV shift, and existing vertex reprojection.

added: 9; removed: 0; changed: 11

### Added

- `function|addon/wavelength/source/surface_tools.py|adjust_mapping`
- `function|addon/wavelength/source/surface_tools.py|adjust_native_uv`
- `function|addon/wavelength/source/surface_tools.py|adjust_native_uv.transform`
- `function|addon/wavelength/source/surface_tools.py|draw_mapping`
- `function|addon/wavelength/source/surface_tools.py|mapping_field`
- `function|addon/wavelength/source/surface_tools.py|mapping_field.get`
- `function|addon/wavelength/source/surface_tools.py|mapping_field.set_value`
- `setting|addon/wavelength/source/ui.py|WLSettings.live_mapping_adjustment`
- `test|tests/blender_live_surface_mapping.py|blender_live_surface_mapping`

### Changed

- `class|addon/wavelength/source/surface_tools.py|WL_PT_surface`
- `class|addon/wavelength/source/ui.py|WLSettings`
- `class|addon/wavelength/source/ui.py|WL_PT_texture`
- `function|addon/wavelength/source/editor.py|apply_edit_uv`
- `function|addon/wavelength/source/editor.py|apply_uv`
- `function|addon/wavelength/source/surface_tools.py|WL_PT_surface.draw`
- `function|addon/wavelength/source/ui.py|WL_PT_texture.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/editor.py|editor`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-12T14:41:33+00:00

Features: WL-TEX-013, WL-TEX-006, WL-TEX-007

Activate the named engine UV layer for Workbench, materials and mesh export. Live adjustment handles textured faces without face records. Explicit Apply Mapping preserves assigned materials and no longer needs a held asset. Tested both axes and UV layer selection in Source 1 and Source 2.

added: 2; removed: 0; changed: 18

### Added

- `function|addon/wavelength/source/editor.py|activate_mapping_uv`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.mapping_only`

### Changed

- `class|addon/wavelength/source/surface_tools.py|WL_PT_surface`
- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `class|addon/wavelength/source/ui.py|WL_PT_texture`
- `function|addon/wavelength/source/editor.py|apply_edit_uv`
- `function|addon/wavelength/source/editor.py|apply_uv`
- `function|addon/wavelength/source/surface_tools.py|WL_PT_surface.draw`
- `function|addon/wavelength/source/surface_tools.py|adjust_mapping`
- `function|addon/wavelength/source/surface_tools.py|adjust_native_uv`
- `function|addon/wavelength/source/surface_tools.py|draw_mapping`
- `function|addon/wavelength/source/surface_tools.py|project_mesh_uv`
- `function|addon/wavelength/source/surface_tools.py|project_mesh_uv.coordinates`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `function|addon/wavelength/source/ui.py|WL_PT_texture.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/editor.py|editor`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_live_surface_mapping.py|blender_live_surface_mapping`

## 2026-11-12T14:55:38+00:00

Features: WL-TEX-014, WL-TEX-006

Add viewport U/V, scale and rotation controls, world-space edge continuation and trim-sheet hotspot mapping. Validate all brush projections before commit. Edit Mode face markers keep exported metadata synchronized with Blender undo and redo. Verified viewport drag, cancellation, undo, edge continuity and Source projection reconstruction.

added: 64; removed: 0; changed: 6

### Added

- `class|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles`
- `class|addon/wavelength/source/texture_layout.py|WL_OT_face_layout`
- `class|addon/wavelength/source/texture_layout.py|WL_OT_hotspot_region`
- `class|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle`
- `class|addon/wavelength/source/texture_layout.py|WL_PG_hotspot`
- `class|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout`
- `function|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.draw_prepare`
- `function|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.poll`
- `function|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.setup`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_face_layout.execute`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_face_layout.poll`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_hotspot_region.execute`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.cancel`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.invoke`
- `function|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.modal`
- `function|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout.draw`
- `function|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout.poll`
- `function|addon/wavelength/source/texture_layout.py|active_material`
- `function|addon/wavelength/source/texture_layout.py|affine`
- `function|addon/wavelength/source/texture_layout.py|apply`
- `function|addon/wavelength/source/texture_layout.py|clear_projection_history`
- `function|addon/wavelength/source/texture_layout.py|continue_edge`
- `function|addon/wavelength/source/texture_layout.py|dimensions`
- `function|addon/wavelength/source/texture_layout.py|draw`
- `function|addon/wavelength/source/texture_layout.py|hotspot_uv`
- `function|addon/wavelength/source/texture_layout.py|material`
- `function|addon/wavelength/source/texture_layout.py|register`
- `function|addon/wavelength/source/texture_layout.py|remember_projection`
- `function|addon/wavelength/source/texture_layout.py|restore_projection`
- `function|addon/wavelength/source/texture_layout.py|screen_axes`
- `function|addon/wavelength/source/texture_layout.py|screen_axes.project`
- `function|addon/wavelength/source/texture_layout.py|selection`
- `function|addon/wavelength/source/texture_layout.py|target`
- `function|addon/wavelength/source/texture_layout.py|unregister`
- `gizmo|addon/wavelength/source/texture_layout.py|self.gizmos.new('GIZMO_GT_button_2d')`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.load_post.append(clear_projection_history)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.load_post.remove(clear_projection_history)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.redo_post.append(restore_projection)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.redo_post.remove(restore_projection)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.undo_post.append(restore_projection)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.app.handlers.undo_post.remove(restore_projection)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.utils.register_class(cls)`
- `hook|addon/wavelength/source/texture_layout.py|bpy.utils.unregister_class(cls)`
- `module|addon/wavelength/source/texture_layout.py|texture_layout`
- `setting|addon/wavelength/source/texture_layout.py|WL_OT_face_layout.action`
- `setting|addon/wavelength/source/texture_layout.py|WL_OT_hotspot_region.index`
- `setting|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.action`
- `setting|addon/wavelength/source/texture_layout.py|WL_PG_hotspot.label`
- `setting|addon/wavelength/source/texture_layout.py|WL_PG_hotspot.maximum`
- `setting|addon/wavelength/source/texture_layout.py|WL_PG_hotspot.minimum`
- `test|tests/blender_texture_handles_ui.py|blender_texture_handles_ui`
- `test|tests/blender_texture_layout.py|blender_texture_layout`
- `ui|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.bl_idname`
- `ui|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.bl_label`
- `ui|addon/wavelength/source/texture_layout.py|WL_GGT_texture_handles.bl_space_type`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_face_layout.bl_idname`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_face_layout.bl_label`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_hotspot_region.bl_idname`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_hotspot_region.bl_label`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.bl_idname`
- `ui|addon/wavelength/source/texture_layout.py|WL_OT_texture_handle.bl_label`
- `ui|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout.bl_idname`
- `ui|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout.bl_label`
- `ui|addon/wavelength/source/texture_layout.py|WL_PT_texture_layout.bl_space_type`

### Changed

- `class|addon/wavelength/source/surface_tools.py|WL_PT_surface`
- `function|addon/wavelength/source/surface_tools.py|WL_PT_surface.draw`
- `function|addon/wavelength/source/surface_tools.py|register`
- `function|addon/wavelength/source/surface_tools.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`

## 2026-11-12T15:25:18+00:00

Features: WL-MODEL-014, WL-MODEL-020

Resolve model dialog defaults against the displayed profile identities and stage private Source compiler origins at the scene root. Explicit standalone builds respect editable mesh restrictions while ignoring the synthetic origin restriction. Blender model transfer regression passed for a deduplicated profile and a hidden private origin through native studiomdl.

added: 2; removed: 0; changed: 13

### Added

- `function|addon/wavelength/source/export_scope.py|Scope.includes_model_sources`
- `function|addon/wavelength/source/model_io.py|_default_target`

### Changed

- `class|addon/wavelength/source/export_scope.py|Scope`
- `class|addon/wavelength/source/model_backend_source1.py|Source1`
- `class|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset`
- `function|addon/wavelength/source/custom_models.py|prepare`
- `function|addon/wavelength/source/export_scope.py|Scope.includes`
- `function|addon/wavelength/source/model_backend_source1.py|Source1.prepare`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.invoke`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/export_scope.py|export_scope`
- `module|addon/wavelength/source/model_backend_source1.py|model_backend_source1`
- `module|addon/wavelength/source/model_io.py|model_io`
- `test|tests/blender_model_transfer.py|blender_model_transfer`

## 2026-11-13T15:00:47+00:00

Features: WL-IO-007

Report the compiler name, timeout and log for a timed-out map build, including wrapped compilers. Trainstation reached full VVIS and timed out at 120 seconds, while a separate fast-VIS preview completed VBSP, VVIS and VRAD. Six model format and pipeline tests passed. The configured build settings remain authoritative.

added: 0; removed: 0; changed: 10

### Changed

- `class|addon/wavelength/source/build/pipeline.py|Pipeline`
- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `function|addon/wavelength/source/build/pipeline.py|Pipeline.__init__`
- `function|addon/wavelength/source/build/pipeline.py|Pipeline.poll`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|build_tick`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/build/pipeline.py|pipeline`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/test_model_formats.py|test_model_formats`

## 2026-11-13T15:12:54+00:00

Features: WL-PERF-003

Yield between off-scene model reference staging operations and preserve a single shared-library append and final commit. Blender preload regression passed with forced yields, shared meshes and unchanged mode-switch asset counts. Library append and final commit remain synchronous.

added: 1; removed: 0; changed: 9

### Added

- `function|addon/wavelength/source/render_bundle.py|Request._publish_steps`

### Changed

- `class|addon/wavelength/source/render_bundle.py|Request`
- `function|addon/wavelength/source/render_bundle.py|Request.__init__`
- `function|addon/wavelength/source/render_bundle.py|Request.close`
- `function|addon/wavelength/source/render_bundle.py|Request.publish`
- `function|addon/wavelength/source/render_support.py|step`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/render_bundle.py|render_bundle`
- `module|addon/wavelength/source/render_support.py|render_support`
- `test|tests/blender_render_preload_once.py|blender_render_preload_once`

## 2026-11-13T15:22:12+00:00

Features: WL-PERF-003

Unlink ordinary retired native previews from their collections and free them without the general ID-remap path. Keep the general removal path for references that still have users. Instrumented fork.vmf attributed 24.76 seconds to old preview removal. Blender preload regression passed with an explicit retired-preview cleanup assertion.

added: 0; removed: 0; changed: 5

### Changed

- `class|addon/wavelength/source/render_bundle.py|Request`
- `function|addon/wavelength/source/render_bundle.py|Request._publish_steps`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/render_bundle.py|render_bundle`
- `test|tests/blender_render_preload_once.py|blender_render_preload_once`

## 2026-11-13T15:26:40+00:00

Features: WL-PERF-003

Restore batch removal after the real fork.vmf benchmark measured 47.11 seconds for individual unlink and removal versus 24.76 seconds for batch removal. Keep stage timings and the retired-preview cleanup regression assertion.

added: 0; removed: 0; changed: 4

### Changed

- `class|addon/wavelength/source/render_bundle.py|Request`
- `function|addon/wavelength/source/render_bundle.py|Request._publish_steps`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/render_bundle.py|render_bundle`

## 2026-11-13T15:38:39+00:00

Features: WL-IO-016, WL-IO-004, WL-IO-005, WL-IO-007

Preserve VisGroup definitions and memberships on editable VMF interchange and through the import worker. Keep compiler VMFs free of the new editor metadata. Verify hidden containers and the existing stock Hammer output normalization, and check the real fork.vmf VisGroup round trip. Blender authoring of Hammer groups is outside this feature.

added: 2; removed: 0; changed: 22

### Added

- `function|addon/wavelength/source/vmf.py|visgroup_membership`
- `function|addon/wavelength/source/vmf.py|write.editor_block`

### Changed

- `class|addon/wavelength/source/formats.py|Entity`
- `class|addon/wavelength/source/formats.py|Map`
- `class|addon/wavelength/source/map_import.py|Session`
- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_export`
- `function|addon/wavelength/source/map_import.py|Session.advance`
- `function|addon/wavelength/source/map_import_worker.py|run`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/scene.py|import_map_iter`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_export.run`
- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|parse.solid`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/formats.py|formats`
- `module|addon/wavelength/source/map_import.py|map_import`
- `module|addon/wavelength/source/map_import_worker.py|map_import_worker`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/ui.py|ui`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T15:41:34+00:00

Features: WL-IO-017, WL-IO-016, WL-IO-005

Generalize the prior visgroup_membership helper to editor_membership so both VisGroup and object-group memberships survive. Allocate fresh group IDs and remap nested and member references. Blender background round-trip fixture passed for nested groups and fork.vmf preserved its group-definition count. Compile staging continues to omit editor data.

added: 1; removed: 1; changed: 17

### Added

- `function|addon/wavelength/source/vmf.py|editor_membership`

### Removed

- `function|addon/wavelength/source/vmf.py|visgroup_membership`

### Changed

- `class|addon/wavelength/source/formats.py|Entity`
- `class|addon/wavelength/source/map_import.py|Session`
- `function|addon/wavelength/source/map_import.py|Session.advance`
- `function|addon/wavelength/source/map_import_worker.py|run`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/scene.py|import_map_iter`
- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|parse.solid`
- `function|addon/wavelength/source/vmf.py|write`
- `function|addon/wavelength/source/vmf.py|write.editor_block`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/formats.py|formats`
- `module|addon/wavelength/source/map_import.py|map_import`
- `module|addon/wavelength/source/map_import_worker.py|map_import_worker`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T15:43:24+00:00

Features: WL-IO-018, WL-IO-005

Carry ordered Hammer camera blocks through parsing, worker metadata, Blender scene storage and editable VMF export. Preserve camera coordinates and active index as authored. The Blender fixture checks multiple cameras and omission from the compiler VMF. Bookmark editing stays in Hammer.

added: 0; removed: 0; changed: 15

### Changed

- `class|addon/wavelength/source/formats.py|Map`
- `class|addon/wavelength/source/map_import.py|Session`
- `function|addon/wavelength/source/map_import.py|Session.advance`
- `function|addon/wavelength/source/map_import_worker.py|run`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/scene.py|import_map_iter`
- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/formats.py|formats`
- `module|addon/wavelength/source/map_import.py|map_import`
- `module|addon/wavelength/source/map_import_worker.py|map_import_worker`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T15:45:24+00:00

Features: WL-IO-019, WL-IO-004, WL-IO-005

Carry Hammer view settings and disabled legacy and named cordon regions through the map worker, Blender scene and editable VMF writer. Preserve build staging semantics and continue rejecting active cordons with a specific message. The Blender round-trip fixture passed.

added: 0; removed: 0; changed: 15

### Changed

- `class|addon/wavelength/source/formats.py|Map`
- `class|addon/wavelength/source/map_import.py|Session`
- `function|addon/wavelength/source/map_import.py|Session.advance`
- `function|addon/wavelength/source/map_import_worker.py|run`
- `function|addon/wavelength/source/scene.py|export_map`
- `function|addon/wavelength/source/scene.py|import_map_iter`
- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/formats.py|formats`
- `module|addon/wavelength/source/map_import.py|map_import`
- `module|addon/wavelength/source/map_import_worker.py|map_import_worker`
- `module|addon/wavelength/source/scene.py|scene`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T15:47:26+00:00

Features: WL-IO-020, WL-IO-017

Preserve known Hammer++ editor blocks through existing VMF scene and worker metadata. Restrict group ID rewriting to Hammer object groups and memberships. Blender round trip preserved nested repeated entries and literal group-like keys and omitted the blocks from compiler staging.

added: 0; removed: 0; changed: 6

### Changed

- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|write`
- `function|addon/wavelength/source/vmf.py|write.editor_block`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T15:49:24+00:00

Features: WL-IO-021, WL-IO-019

Carry the original VMF version header and world map revision through the existing scene and worker metadata. Keep the generated compiler and new-map header defaults. The Blender fixture passed with distinct revisions and compiler normalization.

added: 0; removed: 0; changed: 5

### Changed

- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:11:03+00:00

Features: WL-IO-022

Preserve Hammer object editor colors via the existing VMF editor membership path. Blender background import and editable export retain brush, brush-entity and point-entity colors. Compiler staging omits these editor fields. The Blender fixture passed.

added: 0; removed: 0; changed: 3

### Changed

- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:14:29+00:00

Features: WL-IO-023

Sample and apply Source lightmap scale independently through the existing surface selection controls. Blender regression passed for a single selected Edit Mode face, unchanged UV/material records, readback, and emitted VMF scale.

added: 3; removed: 0; changed: 12

### Added

- `function|addon/wavelength/source/surface_tools.py|apply_lightmap_scale`
- `function|addon/wavelength/source/surface_tools.py|draw_lightmap`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.lightmap_only`

### Changed

- `class|addon/wavelength/source/surface_tools.py|WL_PT_surface`
- `class|addon/wavelength/source/ui.py|WL_OT_read_face_texture`
- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `class|addon/wavelength/source/ui.py|WL_PT_texture`
- `function|addon/wavelength/source/surface_tools.py|WL_PT_surface.draw`
- `function|addon/wavelength/source/ui.py|WL_OT_read_face_texture.run`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `function|addon/wavelength/source/ui.py|WL_PT_texture.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:17:09+00:00

Features: WL-IO-024, WL-IO-023

Extend lightmap-only editing into a shared Source face metadata path and add smoothing group sampling and application. Blender regression passed for lightmap editing and a selected-face 32-bit smoothing mask through VMF export, with projection and unrelated fields preserved.

added: 5; removed: 2; changed: 13

### Added

- `function|addon/wavelength/source/surface_tools.py|apply_source_face_setting`
- `function|addon/wavelength/source/surface_tools.py|draw_source_face_settings`
- `function|addon/wavelength/source/surface_tools.py|smoothing_mask`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_smoothing_groups`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.smoothing_only`

### Removed

- `function|addon/wavelength/source/surface_tools.py|apply_lightmap_scale`
- `function|addon/wavelength/source/surface_tools.py|draw_lightmap`

### Changed

- `class|addon/wavelength/source/surface_tools.py|WL_PT_surface`
- `class|addon/wavelength/source/ui.py|WLSettings`
- `class|addon/wavelength/source/ui.py|WL_OT_read_face_texture`
- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `class|addon/wavelength/source/ui.py|WL_PT_texture`
- `function|addon/wavelength/source/surface_tools.py|WL_PT_surface.draw`
- `function|addon/wavelength/source/ui.py|WL_OT_read_face_texture.run`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `function|addon/wavelength/source/ui.py|WL_PT_texture.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:18:43+00:00

Features: WL-IO-025

Carry explicit VMF side contents and flags in existing face metadata and emit them in editable and compiler VMFs. Blender background-import regression passed for explicit values and absent flags.

added: 0; removed: 0; changed: 6

### Changed

- `function|addon/wavelength/source/vmf.py|parse`
- `function|addon/wavelength/source/vmf.py|parse.solid`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:20:43+00:00

Features: WL-IO-026, WL-IO-025, WL-IO-024

Add independent per-face contents and flags editing, readback and blank-field clearing. Generalize the internal smoothing_mask helper to source_mask for all three decimal masks. Blender regression passed for selected-face isolation, readback, clearing, compiler output and existing lightmap and smoothing operations.

added: 4; removed: 1; changed: 11

### Added

- `function|addon/wavelength/source/surface_tools.py|source_mask`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_contents`
- `setting|addon/wavelength/source/ui.py|WLSettings.texture_surface_flags`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.face_flag`

### Removed

- `function|addon/wavelength/source/surface_tools.py|smoothing_mask`

### Changed

- `class|addon/wavelength/source/ui.py|WLSettings`
- `class|addon/wavelength/source/ui.py|WL_OT_read_face_texture`
- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `function|addon/wavelength/source/surface_tools.py|apply_source_face_setting`
- `function|addon/wavelength/source/surface_tools.py|draw_source_face_settings`
- `function|addon/wavelength/source/ui.py|WL_OT_read_face_texture.run`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T16:23:07+00:00

Features: WL-TEX-027, WL-TEX-005, WL-IO-023, WL-IO-024, WL-IO-026

Share Source face setting readback between the viewport eyedropper and Read Face, retaining asset reveal and clearing stale optional masks when the new face has none. Source mapping and VMF face controls passed in background Blender.

added: 1; removed: 0; changed: 7

### Added

- `function|addon/wavelength/source/surface_tools.py|read_source_face_settings`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_read_face_texture`
- `function|addon/wavelength/source/surface_tools.py|sample`
- `function|addon/wavelength/source/ui.py|WL_OT_read_face_texture.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_surface_source_mapping.py|blender_surface_source_mapping`

## 2026-11-13T16:36:45+00:00

Features: WL-IO-027, WL-IO-023, WL-IO-024, WL-IO-026

Add combined Source face settings application through the existing selection and undo operator. Validate all fields before writing and preserve independent controls. Blender regression verified clearing, selected-face isolation, invalid-mask rejection without partial changes and compiler serialization.

added: 1; removed: 0; changed: 9

### Added

- `function|addon/wavelength/source/surface_tools.py|source_face_settings`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_texture`
- `function|addon/wavelength/source/surface_tools.py|apply_source_face_setting`
- `function|addon/wavelength/source/surface_tools.py|draw_source_face_settings`
- `function|addon/wavelength/source/ui.py|WL_OT_texture.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/surface_tools.py|surface_tools`
- `module|addon/wavelength/source/ui.py|ui`
- `setting|addon/wavelength/source/ui.py|WL_OT_texture.face_flag`
- `test|tests/blender_vmf_hidden.py|blender_vmf_hidden`

## 2026-11-13T20:44:06+00:00

Features: WL-IO-028, WL-IO-007

Add isolated Source 1 preview compile and launch actions with VVIS -fast and regular lighting. Preserve configured arguments, map name, output path and previous normal build. The new action completed a real trainstation preview BSP through the standard compiler pipeline.

added: 4; removed: 0; changed: 16

### Added

- `setting|addon/wavelength/source/ui.py|WLSettings.last_preview_build`
- `setting|addon/wavelength/source/ui.py|WL_OT_build.preview`
- `setting|addon/wavelength/source/ui.py|WL_OT_launch.preview`
- `test|tests/blender_build_preview.py|blender_build_preview`

### Changed

- `class|addon/wavelength/source/ui.py|WLSettings`
- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_launch`
- `class|addon/wavelength/source/ui.py|WL_OT_load_project`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/profile_ui.py|apply`
- `function|addon/wavelength/source/ui.py|WL_OT_build.invoke`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_launch.run`
- `function|addon/wavelength/source/ui.py|WL_OT_load_project.run`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|build_tick`
- `function|addon/wavelength/source/ui.py|engine_changed`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/profile_ui.py|profile_ui`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T20:46:17+00:00

Features: WL-IO-029, WL-IO-028, WL-IO-007

Queue the existing preview launcher after validated BSP publication, preserve standalone actions, skip launch when the game profile changes, and retain the preview on launch failure. Real trainstation compile passed with a mocked game launch and verified arguments.

added: 2; removed: 0; changed: 10

### Added

- `function|addon/wavelength/source/ui.py|WL_OT_launch.launch`
- `setting|addon/wavelength/source/ui.py|WL_OT_build.play_after_build`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_launch`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_launch.run`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|build_tick`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T20:47:47+00:00

Features: WL-IO-030, WL-IO-007

Report named running compiler and elapsed stage time while counting completed stages. Limit the progress bar to its owning scene. Seven model format and pipeline tests passed.

added: 1; removed: 0; changed: 8

### Added

- `function|addon/wavelength/source/build/pipeline.py|Pipeline.progress`

### Changed

- `class|addon/wavelength/source/build/pipeline.py|Pipeline`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|build_tick`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/build/pipeline.py|pipeline`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/test_model_formats.py|test_model_formats`

## 2026-11-13T20:49:31+00:00

Features: WL-IO-031, WL-IO-030

Show a bounded active compiler log tail under existing stage progress. Retain the full log operator. Eight model and pipeline tests passed, including missing log and partial progress output.

added: 1; removed: 0; changed: 7

### Added

- `function|addon/wavelength/source/build/pipeline.py|Pipeline.recent_output`

### Changed

- `class|addon/wavelength/source/build/pipeline.py|Pipeline`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/build/pipeline.py|pipeline`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/test_model_formats.py|test_model_formats`

## 2026-11-13T20:50:59+00:00

Features: WL-IO-032, WL-IO-007, WL-IO-030

Reuse stage naming across progress, timeouts and failures. Report named compiler startup and exit failures with log filename and exit code where available. Nine model and pipeline tests passed.

added: 1; removed: 0; changed: 6

### Added

- `function|addon/wavelength/source/build/pipeline.py|Pipeline.stage_name`

### Changed

- `class|addon/wavelength/source/build/pipeline.py|Pipeline`
- `function|addon/wavelength/source/build/pipeline.py|Pipeline.poll`
- `function|addon/wavelength/source/build/pipeline.py|Pipeline.progress`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/build/pipeline.py|pipeline`
- `test|tests/test_model_formats.py|test_model_formats`

## 2026-11-13T20:52:51+00:00

Features: WL-IO-033, WL-IO-007

Keep the last successful BSP pointer until another validated build publishes. Resolve the Source play name from the artifact before validating it. The trainstation Blender regression exercises cancelled and simulated failed rebuilds and verifies the retained artifact and mocked launch arguments.

added: 0; removed: 0; changed: 7

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_launch`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_launch.launch`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T20:54:18+00:00

Features: WL-IO-034, WL-IO-031

Expose the scene build directory through Blender native path_open alongside Load Build Log. Verified the registered Blender operator and panel path wiring in background Blender.

added: 0; removed: 0; changed: 4

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T20:56:09+00:00

Features: WL-IO-035, WL-IO-007

Bind leak diagnostics to the scene build folder, preserve engine scale at staging, and refresh one owned overlay per scene. Blender background check verified named pointfile selection, exact scaled coordinates and repeated refresh.

added: 0; removed: 0; changed: 6

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_leak`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_leak.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T20:57:42+00:00

Features: WL-IO-036, WL-IO-035

Expose clearing of the generated scene-root leak overlay in Build & Validation and Diagnostics. Preserve pointfiles and shared objects. Background Blender verified scene isolation, redisplay and orphaned curve cleanup.

added: 5; removed: 0; changed: 6

### Added

- `class|addon/wavelength/source/ui.py|WL_OT_clear_leak`
- `function|addon/wavelength/source/ui.py|WL_OT_clear_leak.poll`
- `function|addon/wavelength/source/ui.py|WL_OT_clear_leak.run`
- `ui|addon/wavelength/source/ui.py|WL_OT_clear_leak.bl_idname`
- `ui|addon/wavelength/source/ui.py|WL_OT_clear_leak.bl_label`

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `class|addon/wavelength/source/ui.py|WL_PT_diagnostics`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|WL_PT_diagnostics.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T20:59:18+00:00

Features: WL-IO-037, WL-IO-035

Frame the leak overlay in the available 3D viewport without selecting diagnostic objects or changing the authoring selection. Background Blender verified viewport center, distance and selection with the existing show and clear workflow.

added: 5; removed: 0; changed: 6

### Added

- `class|addon/wavelength/source/ui.py|WL_OT_frame_leak`
- `function|addon/wavelength/source/ui.py|WL_OT_frame_leak.poll`
- `function|addon/wavelength/source/ui.py|WL_OT_frame_leak.run`
- `ui|addon/wavelength/source/ui.py|WL_OT_frame_leak.bl_idname`
- `ui|addon/wavelength/source/ui.py|WL_OT_frame_leak.bl_label`

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `class|addon/wavelength/source/ui.py|WL_PT_diagnostics`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|WL_PT_diagnostics.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:00:57+00:00

Features: WL-IO-038, WL-IO-007, WL-IO-029, WL-IO-035

Check for the current staged map pointfile after VBSP and fail before visibility and lighting. Keep the pointfile and last successful artifacts. Regression injects a pointfile at the VBSP boundary and checks that automatic launch is skipped.

added: 1; removed: 0; changed: 5

### Added

- `function|addon/wavelength/source/ui.py|WL_OT_build.run.check_source_leak`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T21:01:39+00:00

Features: WL-IO-038

Use the actual staged map stem for the injected leak pointfile. The previous successful preview can have a different filename after an authoring rename.

added: 0; removed: 0; changed: 1

### Changed

- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T21:03:15+00:00

Features: WL-IO-039, WL-IO-035

Reuse leak overlay validation and replacement for explicitly selected external pointfiles, using current profile units. Blender verified import without a staged build, preserved build metadata, rejected malformed input, and passed existing show/frame/clear checks.

added: 6; removed: 0; changed: 6

### Added

- `class|addon/wavelength/source/ui.py|WL_OT_import_pointfile`
- `function|addon/wavelength/source/ui.py|WL_OT_import_pointfile.run`
- `function|addon/wavelength/source/ui.py|WL_OT_leak.show`
- `setting|addon/wavelength/source/ui.py|WL_OT_import_pointfile.filter_glob`
- `ui|addon/wavelength/source/ui.py|WL_OT_import_pointfile.bl_idname`
- `ui|addon/wavelength/source/ui.py|WL_OT_import_pointfile.bl_label`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_leak`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_OT_leak.run`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:04:45+00:00

Features: WL-IO-040, WL-IO-037

Extend the existing leak framer with first and last point targets in pointfile order. Background Blender verified endpoint coordinates, distance, selection and the existing full path mode.

added: 1; removed: 0; changed: 6

### Added

- `setting|addon/wavelength/source/ui.py|WL_OT_frame_leak.target`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_frame_leak`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_OT_frame_leak.run`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:06:46+00:00

Features: WL-IO-041, WL-IO-028, WL-IO-029

Remember the last queued build mode and destination per scene for Rebuild, using a fresh export and staging directory. Real trainstation regression verified repeat after a leak, fresh staging, preview launch intent and the prior regular destination.

added: 2; removed: 0; changed: 14

### Added

- `setting|addon/wavelength/source/ui.py|WLSettings.last_build_request`
- `setting|addon/wavelength/source/ui.py|WL_OT_build.repeat`

### Changed

- `class|addon/wavelength/source/ui.py|WLSettings`
- `class|addon/wavelength/source/ui.py|WL_OT_build`
- `class|addon/wavelength/source/ui.py|WL_OT_load_project`
- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/profile_ui.py|apply`
- `function|addon/wavelength/source/ui.py|WL_OT_build.invoke`
- `function|addon/wavelength/source/ui.py|WL_OT_build.run`
- `function|addon/wavelength/source/ui.py|WL_OT_load_project.run`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|engine_changed`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/profile_ui.py|profile_ui`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T21:08:16+00:00

Features: WL-IO-033, WL-IO-041

Use the BSP stem for Source launch without mutating the authoring map name. Extend the preview regression to check that a normal Play action preserves an edited authoring name, avoiding preview suffixes leaking into the next build.

added: 0; removed: 0; changed: 5

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_launch`
- `function|addon/wavelength/source/ui.py|WL_OT_launch.launch`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T21:10:18+00:00

Features: WL-IO-033, WL-IO-007

Preserve the authoring map name at regular BSP publication. The compiler still uses the output stem, and Play still uses the successful artifact stem. Verify successful regular publication in the Blender build regression.

added: 0; removed: 0; changed: 4

### Changed

- `function|addon/wavelength/source/ui.py|build_tick`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`

## 2026-11-13T21:11:48+00:00

Features: WL-IO-042, WL-IO-033

Display separate successful BSP filenames for regular and preview playback and disable Play before a successful artifact is recorded. Verified both labels in background Blender.

added: 0; removed: 0; changed: 4

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:13:20+00:00

Features: WL-IO-042, WL-IO-034

Check availability of the last successful BSPs when drawing the build panel and expose their folders through native path_open. Background Blender verified the missing and available cases.

added: 1; removed: 0; changed: 4

### Added

- `function|addon/wavelength/source/ui.py|draw_build_artifact`

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:15:13+00:00

Features: WL-IO-043, WL-IO-042

Relink missing Source 1 regular and preview BSP targets through existing BSP validation. Blender verified independent targets and rejection of a malformed BSP with settings preserved.

added: 6; removed: 0; changed: 5

### Added

- `class|addon/wavelength/source/ui.py|WL_OT_relink_bsp`
- `function|addon/wavelength/source/ui.py|WL_OT_relink_bsp.run`
- `setting|addon/wavelength/source/ui.py|WL_OT_relink_bsp.filter_glob`
- `setting|addon/wavelength/source/ui.py|WL_OT_relink_bsp.preview`
- `ui|addon/wavelength/source/ui.py|WL_OT_relink_bsp.bl_idname`
- `ui|addon/wavelength/source/ui.py|WL_OT_relink_bsp.bl_label`

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `function|addon/wavelength/source/ui.py|draw_build_artifact`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:16:58+00:00

Features: WL-IO-043, WL-IO-042

Expose existing validated regular and preview BSP selection when no output is recorded, leaving missing-file relinking intact. Background Blender verified both chooser targets.

added: 0; removed: 0; changed: 3

### Changed

- `function|addon/wavelength/source/ui.py|draw_build_artifact`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:18:30+00:00

Features: WL-IO-043, WL-IO-042

Allow switching existing Source 1 Play targets through the same validated BSP picker. Preserve both slots, folder shortcuts and missing-file behavior. Blender checks cover replacement wiring and assignment.

added: 0; removed: 0; changed: 3

### Changed

- `function|addon/wavelength/source/ui.py|draw_build_artifact`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`

## 2026-11-13T21:21:07+00:00

Features: WL-IO-007, WL-IO-008

Reuse atomic BSP publication for launch deployment. Background Blender verified normal Steam launch arguments, successful BSP copy, and simulated interrupted transfer with the previous game BSP preserved and no launch.

added: 0; removed: 0; changed: 6

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_launch`
- `function|addon/wavelength/source/ui.py|WL_OT_launch.launch`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_build_preview.py|blender_build_preview`
- `test|tests/blender_steam_launch.py|blender_steam_launch`

## 2026-11-13T21:28:28+00:00

Features: WL-IO-044

Add independent Source 1 BSP deployment actions in Build & Validation, using existing validation and atomic publication. No surfaces removed. Background Blender verified regular and preview slots without launching, plus existing Play and interrupted-copy behavior.

added: 5; removed: 0; changed: 4

### Added

- `class|addon/wavelength/source/ui.py|WL_OT_deploy_bsp`
- `function|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.run`
- `setting|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.preview`
- `ui|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.bl_idname`
- `ui|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.bl_label`

### Changed

- `function|addon/wavelength/source/ui.py|draw_build_artifact`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_steam_launch.py|blender_steam_launch`

## 2026-11-14T01:52:33+00:00

Features: WL-IO-045, WL-IO-044

Add read-only BSP comparison to both Source 1 slots using the deployment path. No removals. Background Blender covered matching, differing and missing copies, no writes during verification, and existing deployment and Play.

added: 1; removed: 0; changed: 6

### Added

- `setting|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.verify`

### Changed

- `class|addon/wavelength/source/ui.py|WL_OT_deploy_bsp`
- `function|addon/wavelength/source/ui.py|WL_OT_deploy_bsp.run`
- `function|addon/wavelength/source/ui.py|draw_build_artifact`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_steam_launch.py|blender_steam_launch`

## 2026-11-14T01:54:27+00:00

Features: WL-IO-046

Expose the runtime game maps folder in Source 1 Build & Validation. No surfaces removed. Background Blender checked HL2 combined path and disabled states for missing folders or settings, alongside deployment and launch regressions.

added: 1; removed: 0; changed: 5

### Added

- `function|addon/wavelength/source/ui.py|draw_game_maps_folder`

### Changed

- `class|addon/wavelength/source/ui.py|WL_PT_build`
- `function|addon/wavelength/source/ui.py|WL_PT_build.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/ui.py|ui`
- `test|tests/blender_steam_launch.py|blender_steam_launch`

## 2026-11-14T01:58:16+00:00

Features: WL-MODEL-022, WL-MODEL-010, WL-MODEL-014

Share Source 1 model input validation and QC generation with an attached-model preflight report. Preserve build and inclusion behavior and reject empty evaluated render output. No surfaces removed. Background Blender checked evaluated counts and named UV errors. Real StudioMDL compiled and cached the static prop.

added: 9; removed: 0; changed: 7

### Added

- `class|addon/wavelength/source/custom_models.py|WL_OT_model_preflight`
- `function|addon/wavelength/source/custom_models.py|WL_OT_model_preflight.execute`
- `function|addon/wavelength/source/custom_models.py|WL_OT_model_preflight.poll`
- `function|addon/wavelength/source/custom_models.py|model_build_policy`
- `function|addon/wavelength/source/custom_models.py|model_inputs`
- `function|addon/wavelength/source/custom_models.py|model_qc`
- `test|tests/blender_model_preflight.py|blender_model_preflight`
- `ui|addon/wavelength/source/custom_models.py|WL_OT_model_preflight.bl_idname`
- `ui|addon/wavelength/source/custom_models.py|WL_OT_model_preflight.bl_label`

### Changed

- `class|addon/wavelength/source/custom_models.py|WL_PT_custom_model`
- `function|addon/wavelength/source/custom_models.py|WL_PT_custom_model.draw`
- `function|addon/wavelength/source/custom_models.py|prepare`
- `function|addon/wavelength/source/model_smd.py|export`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/custom_models.py|custom_models`
- `module|addon/wavelength/source/model_smd.py|model_smd`

## 2026-11-18T19:32:40+00:00

Features: WL-MODEL-016, WL-MODEL-017, WL-MODEL-023

Make linked shared editing explicit and reserve independent variants for Make Unique. Add source selection and common export-inclusion controls with placement count. No surfaces removed. Background Blender lifecycle regression covered identity, pose, texture independence, attachment, variants and save/reopen.

added: 5; removed: 0; changed: 10

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_select_model_sources`
- `function|addon/wavelength/source/model_io.py|WL_OT_select_model_sources.run`
- `setting|addon/wavelength/source/model_io.py|WL_OT_select_model_sources.source_name`
- `ui|addon/wavelength/source/model_io.py|WL_OT_select_model_sources.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_select_model_sources.bl_label`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_OT_edit_model`
- `class|addon/wavelength/source/model_io.py|WL_OT_make_model_unique`
- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_OT_make_model_unique.run`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_lifecycle.py|edit`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`
- `test|tests/blender_model_asset_lifecycle.py|blender_model_asset_lifecycle`

## 2026-11-18T19:36:02+00:00

Features: WL-MODEL-024

Add ordinary-mesh model asset creation via the existing backend lifecycle and Object menu. Preserve source mesh data, world geometry and collection membership. No removed surfaces. Blender tested rotated and scaled meshes, existing ownership rejection and real StudioMDL output validation. Source 1 only.

added: 9; removed: 0; changed: 4

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_create_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.invoke`
- `function|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.poll`
- `function|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.run`
- `function|addon/wavelength/source/model_lifecycle.py|create`
- `setting|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.name`
- `test|tests/blender_model_create.py|blender_model_create`
- `ui|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_create_model_asset.bl_label`

### Changed

- `function|addon/wavelength/source/model_io.py|object_menu`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`

## 2026-11-18T19:39:54+00:00

Features: WL-MODEL-025, WL-MODEL-020, WL-MODEL-017

Consolidate panel publishing in the target/name dialog and remember successful per-asset options. Preserve direct scripted builds and native drop execution. Independent variants omit saved publishing paths. No surfaces removed. Real Blender transfer and lifecycle regressions passed, including removed-profile fallback and independent settings.

added: 1; removed: 0; changed: 14

### Added

- `function|addon/wavelength/source/model_io.py|WL_OT_build_model_asset.invoke`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_OT_build_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset`
- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `class|addon/wavelength/source/model_io.py|_ModelBuildJob`
- `function|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.invoke`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|_ModelBuildJob.modal`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`
- `test|tests/blender_model_asset_lifecycle.py|blender_model_asset_lifecycle`
- `test|tests/blender_model_transfer.py|blender_model_transfer`
- `ui|addon/wavelength/source/model_io.py|WL_OT_convert_model_asset.bl_label`

## 2026-11-18T19:42:56+00:00

Features: WL-MODEL-026, WL-MODEL-011

Expose transient Source collision wire snapshots from the exporter triangle output. Register cleanup on load, undo, redo and unload. No removed surfaces. Background Blender verified box, convex and assigned collision bounds after scale/rotation and state preservation. Visual overlay still requires acceptance.

added: 14; removed: 0; changed: 8

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_model_collision_preview`
- `function|addon/wavelength/source/model_collision_preview.py|clear`
- `function|addon/wavelength/source/model_collision_preview.py|draw`
- `function|addon/wavelength/source/model_collision_preview.py|geometry`
- `function|addon/wavelength/source/model_collision_preview.py|redraw`
- `function|addon/wavelength/source/model_collision_preview.py|register`
- `function|addon/wavelength/source/model_collision_preview.py|show`
- `function|addon/wavelength/source/model_collision_preview.py|unregister`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_collision_preview.run`
- `module|addon/wavelength/source/model_collision_preview.py|model_collision_preview`
- `setting|addon/wavelength/source/model_io.py|WL_OT_model_collision_preview.clear`
- `test|tests/blender_model_collision_preview.py|blender_model_collision_preview`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_collision_preview.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_collision_preview.bl_label`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_io.py|register`
- `function|addon/wavelength/source/model_io.py|unregister`
- `function|addon/wavelength/source/model_smd.py|export`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_smd.py|model_smd`

## 2026-11-18T19:46:01+00:00

Features: WL-MODEL-027, WL-MODEL-017

Add named portable model checkpoint saving and independent variant restoration with checksum verification. Variants do not inherit revision histories. No surfaces removed. Background Blender verified unchanged later source edits, restored world geometry, changed-package rejection and blend save/reopen. Restore is independent, not in-place; project package files must be retained.

added: 12; removed: 0; changed: 6

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_model_revision`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_revision.invoke`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_revision.run`
- `function|addon/wavelength/source/model_revisions.py|open_variant`
- `function|addon/wavelength/source/model_revisions.py|records`
- `function|addon/wavelength/source/model_revisions.py|save`
- `module|addon/wavelength/source/model_revisions.py|model_revisions`
- `setting|addon/wavelength/source/model_io.py|WL_OT_model_revision.name`
- `setting|addon/wavelength/source/model_io.py|WL_OT_model_revision.revision_id`
- `test|tests/blender_model_revisions.py|blender_model_revisions`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_revision.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_revision.bl_label`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_lifecycle.py|_make_unique`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`

## 2026-11-18T19:49:29+00:00

Features: WL-MODEL-028, WL-MODEL-027

Restore an attached placement from a checkpoint with an automatic backup and independent restored definition. Preserve other instances and carry revision history forward. No removed surfaces. Background Blender tested selected binding, entity pose, other geometry, automatic backup and save/reopen.

added: 2; removed: 0; changed: 9

### Added

- `function|addon/wavelength/source/model_revisions.py|restore_placement`
- `setting|addon/wavelength/source/model_io.py|WL_OT_model_revision.restore`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_OT_model_revision`
- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_revision.run`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `function|addon/wavelength/source/model_revisions.py|open_variant`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_revisions.py|model_revisions`
- `test|tests/blender_model_revisions.py|blender_model_revisions`

## 2026-11-18T19:53:36+00:00

Features: WL-MODEL-029, WL-MODEL-023

Add shared asset source-part membership controls. Preserve world geometry and retain removed objects as excluded model content. Reject foreign ownership, required controls, collision references and last-mesh removal. No surfaces removed. Background Blender verified rotated/scaled source membership, export counts and dependency checks.

added: 8; removed: 0; changed: 5

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_model_part`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_part.run`
- `function|addon/wavelength/source/model_lifecycle.py|add_sources`
- `function|addon/wavelength/source/model_lifecycle.py|remove_source`
- `setting|addon/wavelength/source/model_io.py|WL_OT_model_part.source_name`
- `test|tests/blender_model_parts.py|blender_model_parts`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_part.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_part.bl_label`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`

## 2026-11-18T19:56:43+00:00

Features: WL-MODEL-030, WL-MODEL-018

Add shared model pivot relocation to the 3D cursor with source-parent and instance-transform compensation. Preserve visible geometry and clear stale collision preview. No removed surfaces. Blender verified standalone and rotated shared-instance pivots, preserved geometry, selection and bindings. Animated/constrained placements require baking.

added: 6; removed: 0; changed: 5

### Added

- `class|addon/wavelength/source/model_io.py|WL_OT_model_origin`
- `function|addon/wavelength/source/model_io.py|WL_OT_model_origin.run`
- `function|addon/wavelength/source/model_lifecycle.py|set_origin`
- `test|tests/blender_model_origin.py|blender_model_origin`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_origin.bl_idname`
- `ui|addon/wavelength/source/model_io.py|WL_OT_model_origin.bl_label`

### Changed

- `class|addon/wavelength/source/model_io.py|WL_PT_model_asset`
- `function|addon/wavelength/source/model_io.py|WL_PT_model_asset.draw`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/model_io.py|model_io`
- `module|addon/wavelength/source/model_lifecycle.py|model_lifecycle`

## 2026-11-18T20:05:32+00:00

Features: WL-MODEL-031, WL-MODEL-011

Make managed static/dynamic prop export honor Collision None and excluded assigned collision sources with solid=0, leaving authored keys untouched. No surfaces removed. Real Blender model/map build verified export keys and packed dependencies. HL2 runtime crash persists after the mismatch fix and remains under investigation.

added: 0; removed: 0; changed: 4

### Changed

- `function|addon/wavelength/source/scene.py|export_map`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/scene.py|scene`
- `test|tests/blender_custom_model_map.py|blender_custom_model_map`

## 2026-11-18T20:23:57+00:00

Features: WL-IO-047, WL-MODEL-005, WL-MODEL-031

Canonicalize legacy scalar angle keys in Source entity and VMF export and correct the bundled room fixture. Preserve authored pairs and vector-angle literals. No removed surfaces. Dump captured server stack overflow while processing angle. Replacing it with angles loaded the control room and rebuilt packed blue model successfully in HL2. Angle, VMF metadata and real model-map compilation regressions passed.

added: 1; removed: 0; changed: 8

### Added

- `function|addon/wavelength/source/source_pose.py|canonical_pairs`

### Changed

- `asset|addon/wavelength/environment/maps/minimal_source.vmf|minimal_source.vmf`
- `function|addon/wavelength/source/source_pose.py|export_pairs`
- `function|addon/wavelength/source/source_pose.py|rotation`
- `function|addon/wavelength/source/vmf.py|write`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/source_pose.py|source_pose`
- `module|addon/wavelength/source/vmf.py|vmf`
- `test|tests/blender_source_entity_angles.py|blender_source_entity_angles`

## 2026-11-18T20:40:40+00:00

Features: WL-DIST-001, WL-DIST-002, WL-IO-017

Prepare v0.51.0-pre.alpha with the current tested executable, regenerate and round-trip the Windows binary delta, and pin its source and release hashes. Correct the obsolete Hammer group test to assert explicitly preserved group metadata. No implementation surfaces removed. Full release validation follows.

added: 0; removed: 0; changed: 4

### Changed

- `build-contract|native/blender/source-5.2.3-candidate.json|source-5.2.3-candidate.json`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/__init__.py|__init__`
- `test|tests/test_source.py|test_source`

## 2026-11-24T02:33:55+00:00

Features: WL-ENV-001, WL-ENV-002, WL-ENV-003, WL-ENV-004, WL-TERR-013

Reviewed first Privateer environment slice: native independent masks, deterministic world-cell candidates, reusable static palettes, shared GN previews, persisted manual overrides, staged modular Godot export and packaged loader. Terrain copy_surface now forks layer IDs and clears disposable preview pointers while preserving existing shared resource references. Blender environment/save-reopen and existing create-terrain regressions passed; real Godot Compatibility renderer verified 180 instance transforms, terrain and prototype scale. No removed implementation entries. Scope remains selected patches; interactive strokes, custom biome shading, full-world adoption and general compositions are not claimed.

added: 75; removed: 0; changed: 9

### Added

- `asset|addon/wavelength/environment/adapters/godot/environment_loader.gd|environment_loader.gd`
- `class|addon/wavelength/source/environment_godot.py|WL_OT_export_environment`
- `class|addon/wavelength/source/environment_layers.py|Surface`
- `class|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer`
- `class|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer`
- `class|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers`
- `class|addon/wavelength/source/environment_layers.py|WL_UL_environment_layers`
- `function|addon/wavelength/source/distribution.py|candidates`
- `function|addon/wavelength/source/distribution.py|choose`
- `function|addon/wavelength/source/distribution.py|random_value`
- `function|addon/wavelength/source/environment_godot.py|WL_OT_export_environment.execute`
- `function|addon/wavelength/source/environment_godot.py|WL_OT_export_environment.invoke`
- `function|addon/wavelength/source/environment_godot.py|export`
- `function|addon/wavelength/source/environment_godot.py|export_mesh`
- `function|addon/wavelength/source/environment_godot.py|godot_transform`
- `function|addon/wavelength/source/environment_godot.py|register`
- `function|addon/wavelength/source/environment_godot.py|unregister`
- `function|addon/wavelength/source/environment_layers.py|Surface.__init__`
- `function|addon/wavelength/source/environment_layers.py|Surface.close`
- `function|addon/wavelength/source/environment_layers.py|Surface.hit`
- `function|addon/wavelength/source/environment_layers.py|Surface.weight`
- `function|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.edit_action`
- `function|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.execute`
- `function|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.draw`
- `function|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.draw.button`
- `function|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.poll`
- `function|addon/wavelength/source/environment_layers.py|WL_UL_environment_layers.draw_item`
- `function|addon/wavelength/source/environment_layers.py|active_layer`
- `function|addon/wavelength/source/environment_layers.py|add_layer`
- `function|addon/wavelength/source/environment_layers.py|fork_layer_set`
- `function|addon/wavelength/source/environment_layers.py|identity`
- `function|addon/wavelength/source/environment_layers.py|overrides`
- `function|addon/wavelength/source/environment_layers.py|palette`
- `function|addon/wavelength/source/environment_layers.py|preview`
- `function|addon/wavelength/source/environment_layers.py|records`
- `function|addon/wavelength/source/environment_layers.py|register`
- `function|addon/wavelength/source/environment_layers.py|set_override`
- `function|addon/wavelength/source/environment_layers.py|stamp`
- `function|addon/wavelength/source/environment_layers.py|unregister`
- `hook|addon/wavelength/source/environment_godot.py|bpy.utils.register_class(WL_OT_export_environment)`
- `hook|addon/wavelength/source/environment_godot.py|bpy.utils.unregister_class(WL_OT_export_environment)`
- `hook|addon/wavelength/source/environment_layers.py|bpy.utils.register_class(cls)`
- `hook|addon/wavelength/source/environment_layers.py|bpy.utils.unregister_class(cls)`
- `module|addon/wavelength/source/distribution.py|distribution`
- `module|addon/wavelength/source/environment_godot.py|environment_godot`
- `module|addon/wavelength/source/environment_layers.py|environment_layers`
- `setting|addon/wavelength/source/environment_godot.py|WL_OT_export_environment.directory`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.align_normal`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.cell_size`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.density`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.enabled`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.kind`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.manual_prototype`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.mask`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.material`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.max_slope`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.overrides`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.palette`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.preview`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.preview_fraction`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.scale_max`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.scale_min`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.seed`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.status`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.uid`
- `setting|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.action`
- `setting|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.kind`
- `test|tests/blender_environment_layers.py|blender_environment_layers`
- `test|tests/test_distribution.py|test_distribution`
- `ui|addon/wavelength/source/environment_godot.py|WL_OT_export_environment.bl_idname`
- `ui|addon/wavelength/source/environment_godot.py|WL_OT_export_environment.bl_label`
- `ui|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.bl_idname`
- `ui|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.bl_label`
- `ui|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.bl_label`
- `ui|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.bl_space_type`

### Changed

- `function|addon/wavelength/source/terrain_revision.py|copy_surface`
- `function|addon/wavelength/source/terrain_surface.py|register`
- `function|addon/wavelength/source/terrain_surface.py|unregister`
- `function|installer/wavelength_installer/source_bundle.py|addon_files`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/terrain_revision.py|terrain_revision`
- `module|addon/wavelength/source/terrain_surface.py|terrain_surface`
- `module|installer/wavelength_installer/source_bundle.py|source_bundle`
- `test|tests/test_source_bundle.py|test_source_bundle`

## 2026-11-24T02:35:43+00:00

Features: WL-ENV-001, WL-CTX-002

Reviewed final environment UI integration: authoring panel/operator now use the existing central context policy, preserving editing restrictions outside the Wavelength workspace and in non-mesh profiles. Blender end-to-end regression passed with the final poll. The 274-test Python suite passed before this context-only change; no removals or existing context-policy implementation changes.

added: 1; removed: 0; changed: 4

### Added

- `function|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.poll`

### Changed

- `class|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer`
- `class|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers`
- `function|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.poll`
- `module|addon/wavelength/source/environment_layers.py|environment_layers`

## 2026-11-25T08:25:45+00:00

Features: WL-ENV-001, WL-ENV-003, WL-ENV-004, WL-ENV-005, WL-ENV-006, WL-TERR-013

Reviewed completion of the Privateer module workflow: adopt native point sets with exact transforms and outside remainder; retain original source checksum; object-owned correction storage with legacy fallback and checkpoint remapping; live native mask attributes and lightweight representative biome preview; Godot PBR/native material adapters and instantiable bundle scene. Real UI brush stroke saved/reopened, textured preview inspected, focused adoption/layer/terrain regressions passed, real patch and Godot native-biome assertions passed. Original 103047 tree points are accounted for. No removed surface entries. World-scale performance, arbitrary shaders and cross-module brush strokes are not claimed; the existing Godot shutdown fault remains documented.

added: 30; removed: 0; changed: 17

### Added

- `function|addon/wavelength/source/environment_adopt.py|_supported`
- `function|addon/wavelength/source/environment_adopt.py|adopt`
- `function|addon/wavelength/source/environment_adopt.py|normalize_atlas`
- `function|addon/wavelength/source/environment_adopt.py|placement_candidates`
- `function|addon/wavelength/source/environment_adopt.py|prototype`
- `function|addon/wavelength/source/environment_layers.py|read_overrides`
- `function|addon/wavelength/source/environment_layers.py|write_overrides`
- `function|addon/wavelength/source/environment_materials.py|biome_preview_group`
- `function|addon/wavelength/source/environment_materials.py|biome_preview_group.math`
- `function|addon/wavelength/source/environment_materials.py|biome_preview_group.vector`
- `function|addon/wavelength/source/environment_materials.py|env_id`
- `function|addon/wavelength/source/environment_materials.py|export_description`
- `function|addon/wavelength/source/environment_materials.py|local_biomes`
- `function|addon/wavelength/source/environment_materials.py|pbr_description`
- `function|addon/wavelength/source/environment_materials.py|refresh`
- `function|addon/wavelength/source/environment_materials.py|save_image`
- `function|addon/wavelength/source/environment_materials.py|shader_group`
- `module|addon/wavelength/source/environment_adopt.py|environment_adopt`
- `module|addon/wavelength/source/environment_materials.py|environment_materials`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.adopt_remainder`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.adopt_source`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.biome`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.follow_terrain`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.mode`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.placements`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.source_hidden`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.source_origin`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.source_render_hidden`
- `test|tests/blender_environment_adoption.py|blender_environment_adoption`
- `test|tests/blender_privateer_environment.py|blender_privateer_environment`

### Changed

- `asset|addon/wavelength/environment/adapters/godot/environment_loader.gd|environment_loader.gd`
- `class|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer`
- `class|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer`
- `class|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers`
- `function|addon/wavelength/source/environment_godot.py|export`
- `function|addon/wavelength/source/environment_godot.py|export_mesh`
- `function|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.execute`
- `function|addon/wavelength/source/environment_layers.py|WL_PT_environment_layers.draw`
- `function|addon/wavelength/source/environment_layers.py|fork_layer_set`
- `function|addon/wavelength/source/environment_layers.py|records`
- `function|addon/wavelength/source/environment_layers.py|register`
- `function|addon/wavelength/source/environment_layers.py|unregister`
- `ledger|documentation/FEATURES.md|behavioral-contracts`
- `module|addon/wavelength/source/environment_godot.py|environment_godot`
- `module|addon/wavelength/source/environment_layers.py|environment_layers`
- `setting|addon/wavelength/source/environment_layers.py|WLEnvironmentLayer.overrides`
- `setting|addon/wavelength/source/environment_layers.py|WL_OT_environment_layer.action`
