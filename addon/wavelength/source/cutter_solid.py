"""Capped solid operations from a planar cutter path."""
import bpy,bmesh,random
from mathutils import Vector
from . import draw_geometry as geo,profiles,formats


def apply(context,guide,points,closed,normal):
    target=guide.wavelength_cutter.target;settings=guide.wavelength_cutter
    if settings.operation=='SUBTRACT' and not closed:raise ValueError('Close the outline to subtract a volume')
    if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    original=target.data
    bm=bmesh.new();bm.from_mesh(original)
    manifold=all(e.is_manifold for e in bm.edges) and bool(bm.faces);bm.free()
    if not manifold:raise ValueError('Solid operations require a closed manifold mesh; use Faces for open meshes')
    n=normal.normalized();base=points[0]
    points=[p-n*(p-base).dot(n) for p in points]
    bounds=[target.matrix_world@Vector(p) for p in target.bound_box]
    extent=max(1,max((p-base).length for p in bounds+points)*8)
    if any((b-a).length<1e-6 for a,b in zip(points,points[1:])):raise ValueError('Path collapses along the chosen direction; choose another axis')
    if not closed:
        a=(points[1]-points[0]).normalized();b=(points[-1]-points[-2]).normalized()
        side=n.cross(points[-1]-points[0])
        if side.length<1e-7:raise ValueError('Open path endpoints must be distinct')
        side.normalize();points=[points[0]-a*extent]+points+[points[-1]+b*extent]
        points += [points[-1]+side*extent*4,points[0]+side*extent*4]
    if not geo.simple_polygon(points,n):raise ValueError('The projected cutting outline crosses itself')
    if settings.through:
        low=min((p-base).dot(n) for p in bounds)-extent
        high=max((p-base).dot(n) for p in bounds)+extent
    else:
        low=-profiles.engine_to_world(context.scene.wavelength,settings.depth);high=extent*1e-6
    from . import node_pencil
    cutter=node_pencil.volume(context,points,n,low,high);cutter.name='.Cutter Volume'
    # The node volume is evaluated in its own plane; bake its transform into the
    # temporary cutter so the existing world-space cap projection remains exact.
    data=cutter.data;data.transform(cutter.matrix_world);cutter.matrix_world.identity()
    # docs:begin cap-materials
    # Transfer an actual used texture onto Boolean caps, including projected UVs.
    materials=list(dict.fromkeys(
        original.materials[face.material_index]
        for face in original.polygons
        if face.material_index<len(original.materials)
        and original.materials[face.material_index]
    ))
    if materials:
        material=random.choice(materials);data.materials.clear();data.materials.append(material)
        for face in data.polygons:face.material_index=0
        unit=target.get(
            'wl_unit_meters',profiles.engine_to_world(context.scene.wavelength,1)
        )
        width=material.get('wl_width',1);height=material.get('wl_height',1)
        names=[layer.name for layer in original.uv_layers] or ['UVMap']
        for name in names:
            uv=data.uv_layers.get(name) or data.uv_layers.new(name=name)
            for face in data.polygons:
                axes=formats.quake_axes(face.normal,(0,0,0,1,1))
                for loop in face.loop_indices:
                    p=data.vertices[data.loops[loop].vertex_index].co/unit
                    uv.data[loop].uv=(
                        sum(axes[0][j]*p[j] for j in range(3))/width,
                        1-sum(axes[1][j]*p[j] for j in range(3))/height,
                    )
    # docs:end cap-materials
    results=[];pieces=[];success=False
    try:
        for operation in (['DIFFERENCE','INTERSECT'] if settings.operation=='SPLIT' and settings.keep=='BOTH' else ['INTERSECT'] if settings.operation=='SPLIT' and settings.keep=='INSIDE' else ['DIFFERENCE']):
            work=bpy.data.objects.new('.Cutter Work',original.copy());work.matrix_world=target.matrix_world.copy();context.collection.objects.link(work)
            try:
                # Geometry Nodes removes empty material slots. Compact explicitly
                # so polygon indices retain their meaning during a Boolean join.
                slots=list(work.data.materials);indices=[face.material_index for face in work.data.polygons]
                compact=list(dict.fromkeys(material for material in slots if material))
                work.data.materials.clear()
                for material in compact:work.data.materials.append(material)
                for face,index in zip(work.data.polygons,indices):
                    face.material_index=compact.index(slots[index]) if index<len(slots) and slots[index] else 0
                node_pencil.boolean(work,cutter,operation)
                context.view_layer.update()
                result=bpy.data.meshes.new_from_object(work.evaluated_get(context.evaluated_depsgraph_get()),preserve_all_data_layers=True,depsgraph=context.evaluated_depsgraph_get())
                if result.uv_layers and result.uv_layers.active is None:result.uv_layers.active_index=0
                results.append(result)
            finally:
                mesh=work.data;bpy.data.objects.remove(work,do_unlink=True);bpy.data.meshes.remove(mesh)
        if any(not m.polygons for m in results):raise ValueError('The guide does not divide the solid; extend the open path across its silhouette')
        def volume(mesh):
            bm=bmesh.new();bm.from_mesh(mesh);v=abs(bm.calc_volume());valid=all(e.is_manifold for e in bm.edges);bm.free()
            if not valid:raise ValueError('The cut could not produce closed solid pieces')
            return v
        before=volume(original);after=[volume(m) for m in results]
        if before<1e-10 or abs(before-after[0])<max(1e-9,before*1e-6):raise ValueError('The cutting volume misses the target')
        bsp=target.get('wl_role')=='BRUSH' and profiles.requires_convex_brushes(context.scene.wavelength.engine)
        if settings.operation=='SPLIT' and settings.keep=='BOTH':
            if abs(sum(after)-before)>max(1e-6,before*1e-4):raise ValueError('Solid split failed volume validation')
        if bsp:
            # A concave Boolean mesh cannot masquerade as one BSP brush. Reuse
            # the CSG plane partition and stage every convex piece before commit.
            from . import csg
            converted=[]
            for result in tuple(results):
                meshes=csg._bsp_meshes(result,target,context.scene.wavelength.engine)
                converted.extend(meshes);results.extend(meshes)
            results.remove(converted[0]);results.insert(0,converted[0])
            for mesh in converted[1:]:
                piece=target.copy();piece.data=mesh;piece.name=target.name+' CSG Part';pieces.append(piece)
                for collection in target.users_collection or (context.collection,):collection.objects.link(piece)
                from . import scene
                piece['wl_id']=scene.uid()
        elif settings.operation=='SPLIT' and settings.keep=='BOTH':
            if settings.separate_objects:
                piece=target.copy();piece.data=results[1];piece.name=target.name+' Inside';pieces.append(piece)
                for collection in target.users_collection or (context.collection,):collection.objects.link(piece)
                if piece.get('wl_id'):
                    from . import scene
                    piece['wl_id']=scene.uid()
            else:
                # Keep coincident caps separate to retain two manifold volumes.
                combined=original.copy();results.append(combined)
                palette=list(dict.fromkeys(material for mesh in results[:2] for material in mesh.materials if material))
                combined.materials.clear()
                for material in palette:combined.materials.append(material)
                bm=bmesh.new()
                try:
                    for mesh in results[:2]:
                        existing=set(bm.faces);bm.from_mesh(mesh)
                        for face in bm.faces:
                            if face not in existing:
                                material=mesh.materials[face.material_index] if face.material_index<len(mesh.materials) else None
                                face.material_index=palette.index(material) if material in palette else 0
                    bm.to_mesh(combined)
                finally:bm.free()
                results[0],results[-1]=combined,results[0]
        target.data=results[0]
        for obj in [target]+pieces:
            if obj.get('wl_role')=='BRUSH':
                from . import scene
                scene.mark_brush(obj)
                if bsp:
                    from . import editor
                    editor.apply_uv(obj,context.scene.wavelength.engine)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [target]+pieces:obj.select_set(True)
        context.view_layer.objects.active=target
        success=True
        return pieces
    except Exception:
        target.data=original
        for piece in pieces:bpy.data.objects.remove(piece,do_unlink=True)
        raise
    finally:
        bpy.data.objects.remove(cutter,do_unlink=True);bpy.data.meshes.remove(data)
        for mesh in results:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        if success and original.users==0:bpy.data.meshes.remove(original)
