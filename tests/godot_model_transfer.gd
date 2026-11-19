extends SceneTree

func _initialize():
    var packed = load("res://animated.glb") as PackedScene
    assert(packed != null)
    var model = packed.instantiate()
    root.add_child(model)
    var players = model.find_children("*", "AnimationPlayer", true, false)
    var skeletons = model.find_children("*", "Skeleton3D", true, false)
    assert(players.size() > 0 and skeletons.size() == 1)
    assert(players[0].has_animation("bend"))
    assert(abs(players[0].get_animation("bend").length - 4.0 / 24.0) < 0.003)
    assert(load("res://barrel.glb") is PackedScene)
    print("PASS Godot native import: static textured model and skeletal named clip")
    quit(0)
