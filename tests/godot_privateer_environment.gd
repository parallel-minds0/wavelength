extends SceneTree
const BUNDLE="res://development/environment/maps/wavelength-estuary-edit-test/environment/"
var container:Node3D

func _initialize() -> void:
	call_deferred("verify")

func verify() -> void:
	container=load(BUNDLE+"environment_loader.gd").new()
	root.add_child(container)
	assert(container.load_bundle(BUNDLE+"environment.json"),"Privateer bundle load failed")
	var doc:Dictionary=container.manifest
	var expected:=0
	var manual:=false
	for batch in doc.batches:
		expected+=batch.instances.size()
		for instance in batch.instances:
			manual=manual or instance.id=="manual:estuary-hero"
	assert(manual)
	var actual:=0
	for visual:MultiMeshInstance3D in container.find_children("*","MultiMeshInstance3D",true,false):
		actual+=visual.multimesh.instance_count
		var records:Array=visual.get_parent().get_meta("wavelength_instances")
		for index in range(records.size()):
			assert(visual.multimesh.get_instance_transform(index).is_equal_approx(container.transform_from(records[index].transform)),"Placement differs from Blender")
	assert(actual==expected)
	var terrain:MeshInstance3D=container.get_child(0).find_children("*","MeshInstance3D",true,false)[0]
	var material:=terrain.material_override as ShaderMaterial
	assert(material!=null and material.shader.code.contains("wl_paint_0_weight"))
	assert(material.shader.code.contains("season_snow") and material.shader.code.contains("landscape_lighting"))
	assert(material.get_shader_parameter("albedo_layers") is Texture2DArray)
	var seasons:Node=load("res://development/environment/maps/city-design/iteration-06/SeasonController.gd").new()
	container.add_child(seasons)
	assert(material in seasons.get("_materials"),"Privateer season collector cannot discover painted terrain")
	var mask:Texture2D=material.get_shader_parameter("wl_paint_0_mask")
	assert(mask!=null)
	var image:=mask.get_image()
	if image.is_compressed():image.decompress()
	assert(image.get_pixel(image.get_width()/2,image.get_height()/2).r>.95,"Paint mask center was not retained")
	assert(image.get_pixel(0,0).r<.1,"Paint mask covered the entire patch")
	var bounds:=terrain.mesh.get_aabb()
	assert(bounds.size.x>120 and bounds.size.x<130 and bounds.size.z>120 and bounds.size.z<130)
	var center:=bounds.get_center()
	var world:=WorldEnvironment.new();world.environment=Environment.new()
	world.environment.background_mode=Environment.BG_COLOR;world.environment.background_color=Color(.45,.56,.65)
	world.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;world.environment.ambient_light_color=Color(.8,.86,1);world.environment.ambient_light_energy=.6
	root.add_child(world)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-40,-30,0);light.light_energy=1.3;root.add_child(light)
	var camera:=Camera3D.new();root.add_child(camera)
	camera.position=center+Vector3(95,115,120);camera.look_at(center);camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=180;camera.current=true
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	# The shader is exercised by the real renderer, not merely parsed as text.
	var output:=OS.get_cmdline_user_args()[0] if not OS.get_cmdline_user_args().is_empty() else "user://privateer-wavelength.png"
	assert(root.get_texture().get_image().save_png(output)==OK)
	seasons.call("set_season",3,true)
	await process_frame
	await RenderingServer.frame_post_draw
	assert(is_equal_approx(float(material.get_shader_parameter("season_snow")),1.0))
	print("PASS PRIVATEER ENVIRONMENT: ",actual," placements; native biome shader, live paint mask, normals/season inputs and real terrain scale")
	container.free();quit(0)
