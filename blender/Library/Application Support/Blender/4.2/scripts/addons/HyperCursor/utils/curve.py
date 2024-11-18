from . system import printd
from . math import average_locations, get_sca_matrix, get_loc_matrix
from mathutils import Vector, Matrix

def get_curve_as_dict(curve, debug=False):
    data = {# all the curve's splines
            'splines': [],

            'active': None,
            'active_selection': [],
            'active_selection_mid_point': None}

    for sidx, spline in enumerate(curve.splines):
        is_active = spline == curve.splines.active

        spline_data = {'index': sidx,
                       'active': is_active,

                       'type': spline.type,

                       'smooth': spline.use_smooth,
                       'cyclic': spline.use_cyclic_u,

                       'points': []}

        if is_active:
            data['active'] = spline_data

        for pidx, point in enumerate(spline.points):
            point_data = {'index': pidx,

                          'co': point.co.copy(),
                          'radius': point.radius,
                          'tilt': point.tilt,

                          'select': point.select,
                          'hide': point.hide}

            spline_data['points'].append(point_data)

            if is_active and point.select:
                data['active_selection'].append(point_data)

        if data['active_selection']:
            data['active_selection_mid_point'] = average_locations([point['co'].xyz for point in data['active_selection']])

        data['splines'].append(spline_data)

    if debug:
        printd(data, name="curve as dict")

    return data

def verify_curve_data(data, type=''):
    if type == 'has_active_spline':
        return data['active']

    elif type == 'has_active_selection':
        return data['active_selection']

    elif type == 'is_active_end_selected':
        spline = data['active']

        if spline:
            return (spline['points'][0]['select'] or spline['points'][-1]['select'])

    elif type == 'is_active_selection_continuous':
        selection = data['active_selection']

        return all(point['index'] == selection[idx]['index'] + 1 for idx, point in enumerate(selection[1:]))

    elif type == 'is_first_spline_non-cyclic':
        if not data['splines'][0]['cyclic']:
            return data['splines'][0]

    elif type == 'is_first_spline_profile':
        spline = data['splines'][0]

        first_point = spline['points'][0]['co']
        last_point = spline['points'][-1]['co']

        return first_point.x < last_point.x and first_point.y > last_point.y

def get_curve_coords(curve, mx):
    coords = []
    indices = []

    spline_offset = 0

    for spline in curve.splines:
        points = spline.points if spline.type in ['POLY', 'NURBS'] else spline.bezier_points

        coords.extend([mx @ p.co.xyz for p in points])
        indices.extend([(idx + spline_offset, idx + 1 + spline_offset) for idx in range(len(points) - 1)])

        if spline.use_cyclic_u:
            indices.append((len(points) - 1 + spline_offset, 0 + spline_offset))

        spline_offset += len(points)

    return coords, indices

def get_profile_coords_from_spline(spline, flop=False, debug=False):

    points = spline['points']

    first_co = points[0]['co'].xy
    last_co = points[-1]['co'].xy

    origin = Vector((first_co.x, last_co.y))

    scale_x = 1 / (last_co - origin).length
    scale_y = 1 / (first_co - origin).length

    sca = get_sca_matrix(Vector((scale_x, scale_y, 1)))
    loc = get_loc_matrix(-origin.resized(3))

    mx = sca @ loc

    coords = []

    for p in points:

        co = mx @ p['co'].xyz  

        coords.append(co.xy)
    
    if debug:
        print()
        print("original coords:")

        for p in points:
            print("", p['co'].xy)

        print()
        print("transformed coords:")

        for co in coords:
            print("", co)

    if flop:
        if debug:
            print("flopping coodrs!")

        axis = Vector((1, 1))

        flopped_coords = [(co - axis).reflect(axis) for co in coords]
        return flopped_coords[1:-1]

    else:

        return coords[1:-1]
