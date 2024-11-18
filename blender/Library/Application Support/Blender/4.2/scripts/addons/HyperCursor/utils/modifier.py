import bpy
from bpy.types import bpy_prop_array
from mathutils import Vector
from math import radians, degrees
from time import time
import os
from . append import append_nodetree
from . nodes import get_nodegroup_input_identifier
from . registration import get_path
from . system import printd
from . property import get_biggest_index_among_names

def add_boolean(obj, operator, method='DIFFERENCE', solver='FAST'):
    boolean = obj.modifiers.new(name=method.title(), type="BOOLEAN")

    boolean.object = operator
    boolean.solver = solver
    boolean.operation = 'DIFFERENCE' if method == 'SPLIT' else method
    boolean.show_in_editmode = True

    if method == 'SPLIT':
        boolean.show_viewport = False

    boolean.show_expanded = False

    return boolean

def add_bevel(obj, name="Bevel", offset_type='OFFSET', width=0.1, clamp=False, limit_method='VGROUP', vertex_group=''):
    bevel = obj.modifiers.new(name=name, type="BEVEL")

    bevel.offset_type = offset_type
    bevel.width = width

    bevel.use_clamp_overlap = clamp
    bevel.limit_method = limit_method

    if limit_method == 'VGROUP':
        bevel.vertex_group = vertex_group

    bevel.miter_outer = 'MITER_ARC'

    bevel.show_expanded = False

    return bevel

def add_subdivision(obj, name="Subdivision", subdivision_type='CATMULL_CLARK', levels=1):
    subd = obj.modifiers.new(name=name, type="SUBSURF")

    subd.levels = levels
    subd.render_levels = levels
    subd.subdivision_type = subdivision_type
    subd.show_expanded = False

    return subd

def add_cast(obj, name="Cast", factor=1, radius=1):
    cast = obj.modifiers.new(name=name, type="CAST")
    cast.factor = factor
    cast.radius = radius

    return cast

def add_solidify(obj, name="Solidify", thickness=0, offset=-1, even=True, high_quality=True):
    mod = obj.modifiers.new(name=name, type="SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = even
    mod.use_quality_normals = high_quality

    mod.show_on_cage = offset > -1
    mod.show_expanded = False

    return mod

def add_displace(obj, name="Displace", mid_level=0.9999, strength=1):
    displace = obj.modifiers.new(name=name, type="DISPLACE")
    displace.mid_level = mid_level
    displace.strength = strength

    displace.show_expanded = False

    return displace

def add_weld(obj, name="Weld", distance=0.001, mode='CONNECTED'):
    mod = obj.modifiers.new(name=name, type='WELD')
    mod.merge_threshold = distance
    mod.mode = mode

    mod.show_expanded = False
    return mod

def add_mirror(obj):
    mod = obj.modifiers.new(name="Mirror", type="MIRROR")

    mod.show_expanded = False

    return mod

def add_auto_smooth(obj, angle=20):
    smooth_by_angles = [tree for tree in bpy.data.node_groups if tree.name.startswith('Smooth by Angle')]

    if smooth_by_angles:
        ng = smooth_by_angles[0]

    else:
        path = os.path.join(bpy.utils.system_resource('DATAFILES'), 'assets', 'geometry_nodes', 'smooth_by_angle.blend')
        ng = append_nodetree(path, 'Smooth by Angle')

        if not ng:
            print("WARNING: Could not import Smooth by Angle node group from ESSENTIALS! This should never happen")
            return

    mod = obj.modifiers.new(name="Auto Smooth", type="NODES")
    mod.node_group = ng
    mod.show_expanded = False

    set_mod_input(mod, 'Angle', radians(angle))

    mod.id_data.update_tag()
    return mod

def add_linear_hyper_array(obj):
    name = 'Linear Hyper Array'
    arrays = [tree for tree in bpy.data.node_groups if tree.name.startswith(name) and tree.HC.version == '1.0']

    if arrays:
        ng = arrays[0]

    else:
        path = os.path.join(get_path(), 'assets', 'Nodes.blend')
        ng = append_nodetree(path, name)

        if not ng:
            print(f"WARNING: Could not import {name} node group from {path}! This should never happen")
            return

    mod = obj.modifiers.new(name=name, type="NODES")
    mod.node_group = ng
    mod.show_expanded = False

    return mod

def add_radial_hyper_array(obj):
    name = 'Radial Hyper Array'
    arrays = [tree for tree in bpy.data.node_groups if tree.name.startswith(name) and tree.HC.version == '1.1']

    if arrays:
        ng = arrays[0]

    else:
        path = os.path.join(get_path(), 'assets', 'Nodes.blend')
        ng = append_nodetree(path, name)

        if not ng:
            print(f"WARNING: Could not import {name} node group from {path}! This should never happen")
            return

    mod = obj.modifiers.new(name=name, type="NODES")
    mod.node_group = ng
    mod.show_expanded = False

    return mod

def get_subdivision(obj):
    subds = [mod for mod in obj.modifiers if mod.type == 'SUBSURF']

    if subds:
        return subds[0]

def get_cast(obj):
    casts = [mod for mod in obj.modifiers if mod.type == 'CAST']

    if casts:
        return casts[0]

def get_auto_smooth(obj):
    if (mod := obj.modifiers.get('Auto Smooth', None)) and mod.type == 'NODES':
        return mod

    elif (mod := obj.modifiers.get('Smooth by Angle', None)) and mod.type == 'NODES':
        return mod
    
    else:
        mods = [mod for mod in obj.modifiers if mod.type == 'NODES' and (ng := mod.node_group) and (ng.name.startswith('Smooth by Angle') or ng.name.startswith('Auto Smooth'))]

        if mods:
            return mods[0]

def is_edge_bevel(mod):
    return mod.type == 'BEVEL' and 'Edge Bevel' in mod.name

def is_auto_smooth(mod):
    return mod.type == 'NODES' and (ng := mod.node_group) and (ng.name.startswith('Smooth by Angle') or ng.name.startswith('Auto Smooth'))

def is_invalid_auto_smooth(mod):
    if is_auto_smooth(mod):
        return get_mod_input(mod, 'Ignore Sharpness') is None or get_mod_input(mod, 'Angle') is None

def is_array(mod):
    if mod.type == 'ARRAY':
        if arr := is_linear_array(mod):
            return arr

        elif arr := is_radial_array(mod):
            return arr

        return 'LEGACY'

    elif mod.type == 'NODES' and (ng := mod.node_group):
        if ng.name.startswith('Linear Hyper Array' ):
            return 'LINEAR'

        elif ng.name.startswith('Radial Hyper Array'):

            if get_mod_input(mod, 'Origin'):
                return 'RADIAL'

def is_hyper_array(mod):
    return (arr := is_array(mod)) and arr in ['LINEAR', 'RADIAL']

def is_linear_array(mod):
    if mod.type == 'ARRAY':
        if 'Linear Array' in mod.name:
            return 'LEGACY_LINEAR'

    elif mod.type == 'NODES' and (ng := mod.node_group):
        if ng.name.startswith('Linear Hyper Array' ):
            return 'LINEAR'

def is_radial_array(mod):
    if mod.type == 'ARRAY':
        if 'Radial Array' in mod.name and mod.offset_object:
            return 'LEGACY_RADIAL'

    elif mod.type == 'NODES' and (ng := mod.node_group):
        if ng.name.startswith('Radial Hyper Array'):
            if get_mod_input(mod, 'Origin'):
                return 'RADIAL'

def hypercut_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if 'Hyper Cut' in mod.name]

def hyperbevel_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if 'Hyper Bevel' in mod.name]

def array_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'ARRAY']

def hyper_array_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if is_hyper_array(mod)]
    return []

def boolean_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'BOOLEAN']

def local_boolean_poll(context, obj, hyperbevel=True, hypercut=True, other=True, dictionary=False):
    all_booleans = [mod for mod in obj.modifiers if mod.type == 'BOOLEAN' and mod.object]

    hyperbevel_booleans = list(filter(lambda x: 'Hyper Bevel' in x.name, all_booleans)) if hyperbevel else []
    hypercut_booleans = list(filter(lambda x: 'Hyper Cut' in x.name, all_booleans)) if hypercut else []
    other_booleans = list(filter(lambda x: not any(name in x.name for name in ['Hyper Bevel', 'Hyper Cut']), all_booleans)) if other else []

    if dictionary:
        return {'Hyper Bevel': hyperbevel_booleans,
                'Hyper Cut': hypercut_booleans,
                'Other': other_booleans}
    else:
        return hyperbevel_booleans + hypercut_booleans + other_booleans

def bevel_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'BEVEL']

def edgebevel_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if is_edge_bevel(mod)]

def mirror_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'MIRROR']

def solidify_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'SOLIDIFY']

def displace_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'DISPLACE']

def hook_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'HOOK']

def subd_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type == 'SUBSURF']

def other_poll(context, obj=None):
    obj = obj if obj else context.active_object

    if obj:
        return [mod for mod in obj.modifiers if mod.type not in ['BOOLEAN', 'SOLIDIFY', 'BEVEL', 'MIRROR', 'ARRAY'] and not is_hyper_array(mod)]

def remote_boolean_poll(context, obj):

    booleans = {}

    for ob in context.scene.objects:
        for mod in ob.modifiers:
            if mod.type == 'BOOLEAN' and mod.object == obj:
                if ob in booleans:
                    booleans[ob].append(mod)
                else:
                    booleans[ob] = [mod]

    return booleans

def remote_hook_poll(context, obj):
    hooks = {}

    for ob in context.scene.objects:
        for mod in ob.modifiers:
            if mod.type == 'HOOK' and mod.object == obj:
                if ob in hooks:
                    hooks[ob].append(mod)
                else:
                    hooks[ob] = [mod]

    return hooks

def remote_radial_array_poll(context, obj):
    arrays = {}

    for ob in context.scene.objects:
        for mod in ob.modifiers:
            if is_radial_array(mod) and get_mod_obj(mod) == obj:
                if obj in arrays:
                    arrays[ob].append(mod)

                else:
                    arrays[ob] = [mod]

    return arrays

def remote_mirror_poll(context, obj):
    mirrors = {}

    for ob in context.scene.objects:
        for mod in ob.modifiers:
            if mod.type == 'MIRROR'and get_mod_obj(mod) == obj:
                if obj in mirrors:
                    mirrors[ob].append(mod)

                else:
                    mirrors[ob] = [mod]

    return mirrors

def apply_mod(modname, context=None, object=None):
    if context and object:
        with context.temp_override(object=object):
            bpy.ops.object.modifier_apply(modifier=modname, single_user=True)
    else:
        bpy.ops.object.modifier_apply(modifier=modname, single_user=True)

def remove_mod(mod):
    obj = mod.id_data
    obj.modifiers.remove(mod)

def get_mod_obj(mod):
    if mod.type in ['BOOLEAN', 'HOOK', 'LATTICE', 'DATA_TRANSFER']:
        return mod.object

    elif mod.type == 'MIRROR':
        return mod.mirror_object

    elif mod.type == 'ARRAY':
        return mod.offset_object

    elif mod.type == 'NODES' and (ng := mod.node_group):
        for item in ng.interface.items_tree:
            if item.socket_type == 'NodeSocketObject':
                return mod[item.identifier]

def is_mod_obj(obj):
    return [mod for ob in bpy.data.objects for mod in ob.modifiers if get_mod_obj(mod) == obj]

def is_remote_mod_obj(obj, modobj=None, mod=None, debug=False):
    if mod:
        modobj = get_mod_obj(mod)

    remote_objs = [ob for ob in bpy.data.objects if ob != obj and ob.modifiers]

    for ob in remote_objs:
        for mod in ob.modifiers:
            modob = get_mod_obj(mod)

            if modob == modobj:
                if debug:
                    print("modobj", modobj.name, "is used by mod", mod.name, "on object", ob.name)
                return True
    return False

def get_mod_objects(obj, mod_objects, mod_types=['BOOLEAN', 'MIRROR', 'ARRAY', 'HOOK', 'LATTICE', 'DATA_TRANSFER'], recursive=True, depth=0, debug=False):
    depthstr = " " * depth

    if debug:
        print(f"\n{depthstr}{obj.name}")

    for mod in obj.modifiers:
        if mod.type in mod_types or 'ARRAY' in mod_types and is_radial_array(mod):   # NOTE: if ARRAYs are included, usethe is_radial_array() function which also checks NODES type mods
            mod_obj = get_mod_obj(mod)

            if debug:
                print(f" {depthstr}mod: {mod.name} | obj: {mod_obj.name if mod_obj else mod_obj}")

            if mod_obj:
                if mod_obj not in mod_objects:
                    mod_objects.append(mod_obj)

                if recursive:
                    get_mod_objects(mod_obj, mod_objects, mod_types=mod_types, recursive=True, depth=depth + 1, debug=debug)

def get_mod_as_dict(mod, debug=False):
    moddict = {}

    if debug:
        print("\n", mod.name, mod.type)

    for d in dir(mod):
        if debug:
            print("", d, getattr(mod, d))

        if d.startswith('__') or d in ['bl_rna', 'rna_type', 'custom_profile', 'is_active', 'is_override_data', 'execution_time']:
            if debug:
                print("  skipping")
            continue

        if type(getattr(mod, d)) in [bpy_prop_array, Vector]:
            if debug:
                print("  tupeling", type(getattr(mod, d)))

            moddict[d] = tuple(getattr(mod, d))
        else:
            moddict[d] = getattr(mod, d)

    if debug:
        printd(moddict)

    return moddict

def create_mod_from_dict(obj, mod):
    m = obj.modifiers.new(mod['name'], type=mod['type'])

    for name, value in mod.items():
        if name in ['name', 'type']:
            continue

        setattr(m, name, value)
    return m

def move_mod(mod, index=0):
    obj = mod.id_data
    current_index = list(obj.modifiers).index(mod)

    if current_index != index:
        obj.modifiers.move(current_index, index)

def sort_modifiers(obj, remove_invalid=True, debug=False):

    if not obj.HC.ishyper:
        print(f"WARNING: Avoiding mod sorting as {obj.name} is not a Hyper Object")
        return

    if debug:
        start = time()

    remove = []

    for mod in obj.modifiers:
        if remove_invalid:
            if mod.type == 'BOOLEAN':
                if mod.operand_type == 'OBJECT' and not mod.object:
                    remove.append(mod)
                    continue

            elif mod.type == 'BEVEL':
                if mod.offset_type == 'OFFSET' and mod.width == 0:
                    remove.append(mod)
                    continue

                elif mod.offset_type == 'PERCENT' and mod.width_pct == 0:
                    remove.append(mod)
                    continue

            elif mod.type == 'NODES' and not mod.node_group:
                remove.append(mod)

            elif is_invalid_auto_smooth(mod):
                remove.append(mod)

        if mod.show_expanded:
            mod.show_expanded = False

        if mod.type == 'SOLIDIFY':

            if not 'Shell' in mod.name:
                mod.name = mod.name.replace('Solidify', 'Shell')
                print(f"INFO: Renamed {obj.name}'s Solidify mod to {mod.name}")

        elif mod.type == 'SUBSURF':
            if mod.levels > mod.render_levels:
                mod.render_levels = mod.levels
                print(f"INFO: Set {obj.name}'s Subsurf mod render_levels to {mod.levels}")

    for mod in remove:
        print(f"INFO: Removing invalid mod {mod.name}")
        obj.modifiers.remove(mod)

    if not obj.modifiers:
        print(f"WARNING: Can't sort {obj.name}'s modifiers, as there are none")
        return

    if not validate_mod_prefixes(obj):
        print("WARNING: Could not sort modifiers, due to unexpected, unresolvable prefix situation!")
        for idx, mod in enumerate(obj.modifiers):
            print(idx, mod.name)
        return

    mods = list(obj.modifiers)

    hooks = []
    edge_bevels = []
    subds = []
    displaces = []
    solidifies = []
    booleans = []
    autosmooths = []
    mirrors = []
    arrays = []
    curves = []

    others = []

    stars = []
    double_stars = []

    minus = []
    plus = []

    for idx, mod in enumerate(mods):
        if mod.name.startswith('- '):
            nextmod = mods[idx + 1] if idx + 1 < len(mods) else None

            if nextmod:
                minus.append((mod, nextmod))
                continue

        elif mod.name.startswith('+ '):
            prevmod = mods[idx - 1] if idx > 0 else None

            if prevmod:
                plus.append((mod, prevmod))
                continue

        if mod.name.startswith('* '):
            stars.append(mod)

        elif mod.name.startswith('** '):
            double_stars.append(mod)

        elif mod.type == 'HOOK':
            hooks.append(mod)

        elif is_edge_bevel(mod):
            edge_bevels.append(mod)

        elif mod.type == 'SUBSURF':
            subds.append(mod)

        elif mod.type == 'DISPLACE':
            displaces.append(mod)

        elif mod.type == 'SOLIDIFY':
            solidifies.append(mod)

        elif mod.type == 'BOOLEAN' and not any(n in mod.name for n in ['Hyper Cut', 'Hyper Bevel']):
            booleans.append(mod)

        elif is_auto_smooth(mod):
            autosmooths.append(mod)

        elif mod.type == 'MIRROR':
            mirrors.append(mod)

        elif is_array(mod):
            arrays.append(mod)

        elif mod.type == 'CURVE':
            curves.append(mod)

        else:
            others.append(mod)

    sorted_mods = hooks + edge_bevels + subds + displaces + solidifies + stars + others + booleans + autosmooths + mirrors + arrays + curves + double_stars

    for mod, nextmod in reversed(minus):

        index = sorted_mods.index(nextmod)
        sorted_mods.insert(index, mod)

    for mod, prevmod in plus:

        index = sorted_mods.index(prevmod)
        sorted_mods.insert(index + 1, mod)

    if debug:
        print("\n'NEW LEGACY SORTING!")
        print("\nsorted modifiers")

    for idx, mod in enumerate(sorted_mods):
        move_mod(mod, index=idx)

        if debug:
            print("", idx, mod.type, mod.name)

    if debug:
        print("\ntime:", time() - start)

def get_previous_mod(mod):
    obj = mod.id_data
    idx = list(obj.modifiers).index(mod)

    if idx > 0:
        return list(obj.modifiers)[idx - 1]

def get_next_mod(mod):
    obj = mod.id_data
    idx = list(obj.modifiers).index(mod)

    if idx < len(obj.modifiers) - 1:
        return list(obj.modifiers)[idx + 1]

def get_new_mod_name(obj, modtype, debug=False):
    maxidx = None

    existing_mod_names = [mod.name for mod in obj.modifiers if mod.type == modtype]

    if existing_mod_names:
        if debug:
            print("existing mods:")

            for name in existing_mod_names:
                print(name)

        maxidx = get_biggest_index_among_names(existing_mod_names)

    if maxidx is None:
        mod_name = modtype.title()

    else:
        mod_name = f"{modtype.title()}.{str(maxidx + 1).zfill(3)}"

    if debug:
        print("new mod name:", mod_name)

    return mod_name.replace('Solidify', 'Shell')

def get_mod_base_name(mod):
    name = mod.name.replace('- ', '').replace('+ ', '').replace('** ', '').replace('* ', '')
    return name

def get_prefix_from_mod(mod):
    prefix = "+" if mod.name.startswith('+ ') else "-" if mod.name.startswith('- ') else "*" if mod.name.startswith('* ') else "**" if mod.name.startswith('** ') else None
    return prefix

def validate_mod_prefixes(obj):
    mods = list(obj.modifiers)

    illegal = True

    count = 0

    while illegal:
        count += 1
        illegal = False

        for idx, mod in enumerate(mods):

            if idx < len(mods) - 1:
                next_mod = mods[idx + 1]

                prefix = get_prefix_from_mod(mod)
                next_prefix = get_prefix_from_mod(next_mod)

                if prefix == '-' and next_prefix == '+':
                    illegal = True

                    if idx == 0:
                        mod.name = mod.name.replace('- ', '')

                    else:
                        mod.name = mod.name.replace('- ', '+ ')

        first_prefix = get_prefix_from_mod(mods[0])
        last_prefix = get_prefix_from_mod(mods[-1])

        if first_prefix == '+':
            mods[0].name = mods[0].name.replace('+ ', '')

        if last_prefix == '-':
            mods[-1].name = mods[-1].name.replace('- ', '')
        
        if count == 1000:
            return False

    return True

def get_edge_bevel_from_edge(obj, edge, vertex_group_layer):
    mods = [mod for mod in obj.modifiers if is_edge_bevel(mod)]

    if mods:
        verts = [v for v in edge.verts]

        vgroups = {vg.index: {'name': vg.name,
                              'verts': []} for vg in obj.vertex_groups if 'Edge Bevel' in vg.name}

        for v in verts:
            for vgindex, weight in v[vertex_group_layer].items():
                if vgindex in vgroups and weight == 1:
                    vgroups[vgindex]['verts'].append(v.index)

        edgevgroups = [vgdata['name'] for vgdata in vgroups.values() if len(vgdata['verts']) == 2]

        if edgevgroups:

            for mod in mods:
                for vgroupname in edgevgroups:
                    if mod.vertex_group == vgroupname:
                        return mod, vgroupname
    return None, None

def get_edges_from_edge_bevel_mod_vgroup(bm, vertex_group_layer, vg_index, verts_too=False):
    vg_edges = [e for e in bm.edges if all(vg_index in v[vertex_group_layer] and v[vertex_group_layer][vg_index] == 1 for v in e.verts)]

    if verts_too:
        verts = list(set(v for e in vg_edges for v in e.verts))
        return vg_edges, verts

    else:
        return vg_edges

def create_bevel_profile(mod, coords):
    data = get_bevel_profile_as_dict(mod)

    mod.id_data.HC['init_custom_profile'] = data

    profile = mod.custom_profile
    points = profile.points

    if mod.profile_type != 'CUSTOM':
        mod.profile_type = 'CUSTOM'

    profile.use_clip = False
    profile.use_sample_even_lengths = False
    profile.use_sample_straight_edges = True

    while len(points) > 2:
        points.remove(points[1])

    for idx, co in enumerate(coords):
        x = (idx + 1) / (len(coords) + 1)
        point = points.add(x, 1 - x)

        point.handle_type_1 = 'VECTOR'
        point.handle_type_2 = 'VECTOR'

    reversed_coords = list(reversed(coords))

    for idx, point in enumerate(points):
        if 0 < idx < len(points) -1:
            point.location = reversed_coords[idx-1]

    profile.update()

    mod.segments = len(profile.points) - 1

def flip_bevel_profile(mod):
    profile = mod.custom_profile
    points = profile.points

    flipped_coords = reversed([Vector((p.location.y, p.location.x)) for p in points])

    for idx, (point, co) in enumerate(zip(points, flipped_coords)):
        if 0 < idx < len(points) - 1:
            point.location = co

    profile.update()
    mod.segments = mod.segments

def flop_bevel_profile(mod):
    profile = mod.custom_profile
    points = profile.points

    axis = Vector((1, 1))

    flopped_coords = [(p.location - axis).reflect(axis) for p in points]

    for idx, (point, co) in enumerate(zip(points, flopped_coords)):
        if 0 < idx < len(points) - 1:
            point.location = co

    profile.update()
    mod.segments = mod.segments

def get_bevel_profile_as_dict(mod):
    profile = mod.custom_profile
    points = profile.points

    data = {'segments': mod.segments,
            'profile_type': mod.profile_type,
            'use_clip': profile.use_clip,
            'use_sample_even_lengths': profile.use_sample_even_lengths,
            'use_sample_straight_edges': profile.use_sample_straight_edges,
            'points': [(p.location.copy(), p.handle_type_1, p.handle_type_2) for p in points[1:-1]]}

    return data

def set_bevel_profile_from_dict(mod, data):

    mod.segments = data['segments']
    mod.profile_type = data['profile_type']

    mod.custom_profile.use_clip = data['use_clip']
    mod.custom_profile.use_sample_even_lengths = data['use_sample_even_lengths']
    mod.custom_profile.use_sample_straight_edges = data['use_sample_straight_edges']

    points = mod.custom_profile.points

    while len(points) > 2:
        points.remove(points[1])

    for idx, (_, handle1, handle2) in enumerate(data['points']):
        x = (idx + 1) / (len(data['points']) + 1)
        point = points.add(x, 1 - x)

        point.handle_type_1 = handle1
        point.handle_type_2 = handle2

    for idx, point in enumerate(mod.custom_profile.points):
        if 0 < idx < len(points) -1:
            point.location = data['points'][idx-1][0]

    mod.custom_profile.update()

def get_mod_input(mod, name):
    if ng := mod.node_group:
        identifier, socket_type = get_nodegroup_input_identifier(ng, name)

        if identifier:
            return mod[identifier]

def set_mod_input(mod, name, value):
    if ng := mod.node_group:
        identifier, socket_type = get_nodegroup_input_identifier(ng, name)

        mod[identifier] = value
