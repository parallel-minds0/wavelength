extends SceneTree

func _initialize() -> void:
	call_deferred("verify")

func verify() -> void:
	var document: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://environment/environment.json"))
	var loader = load("res://environment/environment_loader.gd").new()
	root.add_child(loader)
	assert(loader.load_bundle("res://environment/environment.json"), "Environment bundle did not load")
	var expected_count := 0
	var manual_seen := false
	for batch in document.batches:
		expected_count += batch.instances.size()
		for item in batch.instances:
			if item.id == "manual:hero-tree":
				manual_seen = true
				assert(Vector3(item.transform[9],item.transform[10],item.transform[11]).is_equal_approx(Vector3(116,9,34)), "Blender/Godot placement mismatch")
	assert(manual_seen)
	var actual_count := 0
	for visual: MultiMeshInstance3D in loader.find_children("*", "MultiMeshInstance3D", true, false):
		actual_count += visual.multimesh.instance_count
		var batch: Array = visual.get_parent().get_meta("wavelength_instances")
		for index in range(batch.size()):
			var expected: Transform3D = loader.transform_from(batch[index].transform)
			assert(visual.multimesh.get_instance_transform(index).is_equal_approx(expected), "Actual MultiMesh transform mismatch")
	assert(actual_count == expected_count, "Placements lost during Godot import")
	var terrain: Node3D = loader.get_child(0)
	var meshes: Array[Node] = terrain.find_children("*", "MeshInstance3D", true, false)
	assert(meshes.size() == 1)
	var mesh: MeshInstance3D = meshes[0]
	var aabb := mesh.mesh.get_aabb()
	assert(is_equal_approx(aabb.size.x,32) and is_equal_approx(aabb.size.z,32), "Terrain physical scale incorrect")
	assert(is_equal_approx(aabb.position.x,100) and is_equal_approx(aabb.position.z,18), "Terrain orientation/placement incorrect")
	assert(document.prototypes.size() == 3)
	for key in document.prototypes:
		var proto = load("res://environment/"+document.prototypes[key].scene).instantiate()
		var part := proto.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
		var bounds := part.mesh.get_aabb()
		assert(bounds.position.y >= -0.00001 and bounds.size.y > 0.5 and bounds.size.y <= 5.01, "Prototype feet/scale incorrect")
		proto.free()
	print("PASS GODOT ENVIRONMENT: ", actual_count, " instances, full transforms, 32m terrain, three shared prototypes, manual clearing override")
	loader.free()
	quit(0)
