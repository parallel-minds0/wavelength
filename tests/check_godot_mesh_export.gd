extends SceneTree

func _initialize():
    call_deferred("verify")

func verify():
    var packed = load("res://mesh_smoke/mesh_smoke.glb") as PackedScene
    if packed == null:
        push_error("Exported GLB failed to import")
        quit(1)
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    var meshes = scene.find_children("*", "MeshInstance3D", true, false)
    if meshes.size() != 1:
        push_error("Unexpected mesh/helper count: " + str(meshes.size()))
        quit(1)
        return
    var node = meshes[0] as MeshInstance3D
    var bounds = node.mesh.get_aabb()
    if not bounds.size.is_equal_approx(Vector3(2,2,2)) or not is_equal_approx(bounds.position.y,0):
        push_error("Meter scale or Y-up orientation incorrect: " + str(bounds))
        quit(1)
        return
    var material = node.mesh.surface_get_material(0) as StandardMaterial3D
    if material == null or material.albedo_texture == null or material.albedo_texture.get_width() != 2:
        push_error("Texture/material import failed")
        quit(1)
        return
    var arrays = node.mesh.surface_get_arrays(0)
    if arrays[Mesh.ARRAY_TEX_UV].is_empty():
        push_error("UVs missing")
        quit(1)
        return
    var pixels = material.albedo_texture.get_image()
    if pixels.is_compressed():
        pixels.decompress()
    var red = false
    var green = false
    var blue = false
    for y in range(pixels.get_height()):
        for x in range(pixels.get_width()):
            var color = pixels.get_pixel(x,y)
            red = red or (color.r > 0.8 and color.g < 0.2 and color.b < 0.2)
            green = green or (color.g > 0.8 and color.r < 0.2 and color.b < 0.2)
            blue = blue or (color.b > 0.8 and color.r < 0.2 and color.g < 0.2)
    if not (red and green and blue):
        push_error("Imported texture pixels do not match the source checker")
        quit(1)
        return
    print("PASS GODOT IMPORT: mesh, image, UVs, meters, Y-up and helper exclusion")
    quit(0)
