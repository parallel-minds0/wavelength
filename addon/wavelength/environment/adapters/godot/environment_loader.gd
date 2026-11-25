extends Node3D
## Small bundle reader. The game decides when to load/unload each exported cell.
## No collision, seasonal shader replacement, lighting or gameplay policy here.
@export_file("*.json") var manifest_path: String
var manifest: Dictionary

func environment_material(spec: Dictionary, base: String) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	var code: String
	if spec.adapter == "PRIVATEER":
		var original := load(spec.native_material) as ShaderMaterial
		if original == null or original.shader == null:
			push_error("Missing native Privateer terrain material")
			return null
		code = original.shader.code
		if code.count("int first=0,second=1;") != 1 or not code.contains("float weights[6]"):
			push_error("Unsupported Privateer biome shader revision")
			return null
		material = original.duplicate()
		for kind: String in ["albedo", "normal", "surface"]:
			if original.get_shader_parameter(kind+"_layers") == null:
				var bank: Resource = load(spec.native_material.get_base_dir().path_join(kind+"-compressed.res"))
				if bank == null:
					return null
				var images: Array[Image] = []
				images.assign(bank.get("layers"))
				var texture := Texture2DArray.new()
				if texture.create_from_images(images) != OK:
					return null
				material.set_shader_parameter(kind+"_layers", texture)
	else:
		code = "shader_type spatial;\nvarying vec3 wp;\nvoid vertex(){wp=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}\nuniform sampler2D wl_base_tex : source_color, repeat_enable, hint_default_white;\nuniform vec4 wl_base_color : source_color;\nuniform float wl_base_roughness;\nvoid fragment(){ ALBEDO=texture(wl_base_tex,UV).rgb*wl_base_color.rgb;ROUGHNESS=wl_base_roughness; /*WL_PAINT*/ }\n"
	var uniforms := "\nuniform vec4 wl_paint_bounds;\n"
	var paint := "\nvec2 wl_mask_uv=(wp.xz-wl_paint_bounds.xy)/(wl_paint_bounds.zw-wl_paint_bounds.xy);\n"
	for index in range(spec.layers.size()):
		var prefix := "wl_paint_"+str(index)
		uniforms += "uniform sampler2D "+prefix+"_mask : repeat_disable, filter_linear;\n"
		paint += "float "+prefix+"_weight=texture("+prefix+"_mask,wl_mask_uv).r;\n"
		if spec.adapter == "PRIVATEER":
			for biome in range(6):
				paint += "weights[%d]=mix(weights[%d],%s,%s_weight);\n" % [biome,biome,"1.0" if biome==int(spec.layers[index].biome) else "0.0",prefix]
		else:
			uniforms += "uniform sampler2D "+prefix+"_tex : source_color, repeat_enable, hint_default_white;\nuniform vec4 "+prefix+"_color : source_color;\nuniform float "+prefix+"_roughness;\n"
			paint += "ALBEDO=mix(ALBEDO,texture("+prefix+"_tex,UV).rgb*"+prefix+"_color.rgb,"+prefix+"_weight);ROUGHNESS=mix(ROUGHNESS,"+prefix+"_roughness,"+prefix+"_weight);\n"
	code = code.replace("int first=0,second=1;",paint+"int first=0,second=1;") if spec.adapter=="PRIVATEER" else code.replace("/*WL_PAINT*/",paint)
	var shader := Shader.new()
	shader.code = code.replace("shader_type spatial;","shader_type spatial;"+uniforms)
	# Preserve all game-owned shader inputs, including seasons and lighting.
	var saved: Dictionary = {}
	if material.shader:
		for parameter in material.shader.get_shader_uniform_list():
			saved[parameter.name] = material.get_shader_parameter(parameter.name)
	material.shader = shader
	for key in saved:
		if saved[key] != null:
			material.set_shader_parameter(key,saved[key])
	var bounds: Array = spec.bounds
	material.set_shader_parameter("wl_paint_bounds",Vector4(bounds[0],bounds[1],bounds[2],bounds[3]))
	if spec.adapter != "PRIVATEER":
		set_paint_pbr(material,"wl_base",spec.base,base)
	for index in range(spec.layers.size()):
		var layer: Dictionary = spec.layers[index]
		var prefix := "wl_paint_"+str(index)
		material.set_shader_parameter(prefix+"_mask",load(resolve_path(base,layer.mask)))
		if spec.adapter != "PRIVATEER":
			set_paint_pbr(material,prefix,layer.pbr,base)
	return material

func set_paint_pbr(material: ShaderMaterial, prefix: String, pbr: Dictionary, base: String) -> void:
	var color: Array = pbr.color
	material.set_shader_parameter(prefix+"_color",Color(color[0],color[1],color[2],color[3]))
	material.set_shader_parameter(prefix+"_roughness",float(pbr.roughness))
	if pbr.has("texture"):
		material.set_shader_parameter(prefix+"_tex",load(resolve_path(base,pbr.texture)))

func _ready() -> void:
	if not manifest_path.is_empty():
		var path:=manifest_path
		if not path.is_absolute_path():
			path=get_script().resource_path.get_base_dir().path_join(path)
		load_bundle(path)

func resolve_path(base: String, resource: String) -> String:
	return resource if resource.begins_with("res://") else base.path_join(resource)

func transform_from(values: Array) -> Transform3D:
	assert(values.size() == 12, "Invalid environment transform")
	return Transform3D(Vector3(values[0],values[1],values[2]), Vector3(values[3],values[4],values[5]), Vector3(values[6],values[7],values[8]), Vector3(values[9],values[10],values[11]))

func mesh_parts(node: Node3D, parent_transform := Transform3D.IDENTITY) -> Array:
	var result: Array = []
	var pose: Transform3D = parent_transform * node.transform
	if node is MeshInstance3D:
		assert(node.skin == null, "Environment prototypes must be static meshes")
		result.append([node.mesh, pose, node.material_override])
	for child in node.get_children():
		if child is Node3D:
			result.append_array(mesh_parts(child, pose))
	return result

func failed(message: String) -> bool:
	push_error(message)
	for child in get_children():
		child.free()
	return false

func load_bundle(path: String) -> bool:
	if get_child_count() != 0:
		push_error("Load into an empty environment container")
		return false
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		return failed("Invalid environment manifest")
	manifest = parsed
	if manifest.get("schema") != 1 or manifest.get("up_axis") != "Y":
		return failed("Unsupported environment schema")
	var base := path.get_base_dir()
	for terrain in manifest.terrain:
		var packed := load(resolve_path(base, terrain.mesh)) as PackedScene
		if packed == null:
			return failed("Missing terrain module")
		var instance := packed.instantiate()
		if terrain.get("material_adapter") != null:
			var material := environment_material(terrain.material_adapter,base)
			if material == null:
				instance.free()
				return failed("Environment terrain material could not be resolved")
			for mesh in instance.find_children("*","MeshInstance3D",true,false):
				# Game collectors inspect surface materials, not only overrides.
				mesh.mesh=mesh.mesh.duplicate()
				for surface in range(mesh.mesh.get_surface_count()):
					mesh.mesh.surface_set_material(surface,material)
				mesh.material_override=material
		instance.set_meta("wavelength_terrain_id", terrain.id)
		instance.set_meta("wavelength_masks", resolve_path(base, terrain.masks))
		add_child(instance)
	var prototypes: Dictionary = {}
	for key in manifest.prototypes:
		var packed := load(resolve_path(base, manifest.prototypes[key].scene)) as PackedScene
		if packed == null:
			return failed("Missing prototype " + key)
		var prototype := packed.instantiate() as Node3D
		prototypes[key] = mesh_parts(prototype)
		prototype.free()
		if prototypes[key].is_empty():
			return failed("Prototype has no supported mesh parts: " + key)
	for batch in manifest.batches:
		var group := Node3D.new()
		group.name = "Cell_%s_%s" % batch.cell
		group.set_meta("wavelength_layer", batch.layer)
		group.set_meta("wavelength_instances", batch.instances)
		add_child(group)
		for part in prototypes[batch.prototype]:
			var multi := MultiMesh.new()
			multi.transform_format = MultiMesh.TRANSFORM_3D
			multi.mesh = part[0]
			multi.instance_count = batch.instances.size()
			for index in range(batch.instances.size()):
				multi.set_instance_transform(index, transform_from(batch.instances[index].transform) * part[1])
			var visual := MultiMeshInstance3D.new()
			visual.multimesh = multi
			visual.material_override = part[2]
			group.add_child(visual)
	return true
