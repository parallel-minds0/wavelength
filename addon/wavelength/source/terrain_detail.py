"""Optional local-space noise and image detail for continuous terrain."""

import bpy

GROUP = 'wavelength · Terrain Detail'


def detail_group():
    existing = bpy.data.node_groups.get(GROUP)
    if existing and existing.get('wl_terrain_detail'):
        return existing
    tree = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    tree['wl_terrain_detail'] = True
    interface = tree.interface
    interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    for name, default in [('Noise Height', 0), ('Noise Frequency', 1), ('Image Height', 0), ('Image Frequency', 1)]:
        socket = interface.new_socket(name=name, in_out='INPUT', socket_type='NodeSocketFloat')
        socket.default_value = default
    interface.new_socket(name='Heightmap', in_out='INPUT', socket_type='NodeSocketImage')
    nodes, links = tree.nodes, tree.links

    def node(kind, x, y):
        result = nodes.new(kind)
        result.location = (x, y)
        return result

    def math(operation, left, right, x, y):
        result = node('ShaderNodeMath', x, y)
        result.operation = operation
        links.new(left, result.inputs[0])
        if isinstance(right, (int, float)):
            result.inputs[1].default_value = right
        else:
            links.new(right, result.inputs[1])
        return result.outputs[0]

    inputs = node('NodeGroupInput', -840, 160).outputs
    position = node('GeometryNodeInputPosition', -840, -140).outputs[0]
    noise = node('ShaderNodeTexNoise', -610, -40)
    links.new(position, noise.inputs['Vector'])
    links.new(inputs['Noise Frequency'], noise.inputs['Scale'])
    image_coordinates = node('ShaderNodeVectorMath', -610, -380)
    image_coordinates.operation = 'SCALE'
    links.new(position, image_coordinates.inputs[0])
    links.new(inputs['Image Frequency'], image_coordinates.inputs['Scale'])
    image = node('GeometryNodeImageTexture', -400, -380)
    links.new(inputs['Heightmap'], image.inputs['Image'])
    links.new(image_coordinates.outputs['Vector'], image.inputs['Vector'])
    noise_height = math('MULTIPLY', math('SUBTRACT', noise.outputs['Fac'], .5, -360, 0),
                        inputs['Noise Height'], -160, 0)
    image_height = math('MULTIPLY', math('SUBTRACT', image.outputs['Color'], .5, -160, -320),
                        inputs['Image Height'], 40, -320)
    offset = node('ShaderNodeCombineXYZ', 440, -60)
    links.new(math('ADD', noise_height, image_height, 240, -60), offset.inputs['Z'])
    deform = node('GeometryNodeSetPosition', 640, 160)
    links.new(inputs['Geometry'], deform.inputs['Geometry'])
    links.new(offset.outputs[0], deform.inputs['Offset'])
    links.new(deform.outputs['Geometry'], node('NodeGroupOutput', 840, 160).inputs['Geometry'])
    return tree
