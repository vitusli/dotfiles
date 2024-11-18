from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_plane
from math import log10, floor, degrees, pi
import numpy as np

def dynamic_format(value, decimal_offset=0, clear_trailing_zeros=False):
    if round(value, 6) == 0:
        return '0'

    l10 = log10(abs(value))
    f = floor(abs(l10))

    if l10 < 0:
        precision = f + 1 + decimal_offset

    else:
        precision = decimal_offset
    
    float_str = f"{'-' if value < 0 else ''}{abs(value):.{max(0, precision)}f}"

    if clear_trailing_zeros:
        float_str = float_str.rstrip('0').rstrip('.')

    return float_str

def dynamic_snap(value, offset=0):
    if value == 0:
        return 0

    l10 = log10(value)
    f = floor(abs(l10))

    if l10 < 0:
        value = round(value, f + 1 + offset)

    else:
        p = pow(10, f - offset)
        m = value % p

        value -= m

    return value

def snap_value(value, snap_value):
    mod = value % snap_value

    return value + (snap_value - mod) if mod >= (snap_value / 2) else value - mod

def get_angle_between_edges(edge1, edge2, radians=True):
    if not all([edge1.calc_length(), edge2.calc_length()]):

        angle = pi

    else:
        centervert = None

        for vert in edge1.verts:
            if vert in edge2.verts:
                centervert = vert

        if centervert:
            vector1 = centervert.co - edge1.other_vert(centervert).co
            vector2 = centervert.co - edge2.other_vert(centervert).co
        else:
            vector1 = edge1.verts[0].co - edge1.verts[1].co
            vector2 = edge2.verts[0].co - edge2.verts[1].co

        angle = vector1.angle(vector2)

    return angle if radians else degrees(vector1.angle(vector2))

def tween(a, b, tw):
    return a * (1 - tw) + b * tw

def get_center_between_points(point1, point2, center=0.5):
    return point1 + (point2 - point1) * center

def get_center_between_verts(vert1, vert2, center=0.5):
    return get_center_between_points(vert1.co, vert2.co, center=center)

def average_normals(normalslist):
    avg = Vector()

    for n in normalslist:
        avg += n

    return avg.normalized()

def get_edge_normal(edge):
    return average_normals([f.normal for f in edge.link_faces])

def get_face_center(face, method='PROJECTED_BOUNDS'):
    if method == 'MEDIAN':
        center = face.calc_center_median()

    elif method == 'MEDIAN_WEIGHTED':
        center = face.calc_center_median_weighted()

    elif method == 'BOUNDS':
        center = face.calc_center_bounds()

    elif method == 'ORIENTED_BOUNDS':

        median_center = face.calc_center_median()

        normal = face.normal.copy()
        tangent = face.calc_tangent_edge()
        binormal = normal.cross(tangent)

        rot = Matrix()
        rot.col[0].xyz = tangent
        rot.col[1].xyz = binormal
        rot.col[2].xyz = normal

        face_mx = Matrix.LocRotScale(median_center, rot.to_quaternion(), Vector((1, 1, 1)))

        face_coords = [face_mx.inverted_safe() @ v.co for v in face.verts]

        min_bounds = np.min(face_coords, axis=0)
        max_bounds = np.max(face_coords, axis=0)

        bounds_center = Vector((min_bounds + max_bounds) / 2)

        center = face_mx @ bounds_center

    elif method == 'PROJECTED_BOUNDS':
        median_center = face.calc_center_median()
        bounds_center = face.calc_center_bounds()

        i = intersect_line_plane(bounds_center, bounds_center + face.normal, median_center, face.normal)

        center = i if i else get_face_center(face, method='MEDIAN_WEIGHTED')

    return center

def average_locations(locationslist, size=3):
    avg = Vector.Fill(size)

    for n in locationslist:
        avg += n

    return avg / len(locationslist)

def get_world_space_normal(normal, mx):
    return (mx.inverted_safe().transposed().to_3x3() @ normal).normalized()

def get_local_space_normal(normal, mx):
    return (mx.transposed().to_3x3() @ normal).normalized()

def flatten_matrix(mx):
    dimension = len(mx)
    return [mx[j][i] for i in range(dimension) for j in range(dimension)]

def compare_matrix(mx1, mx2, precision=4):
    round1 = [round(i, precision) for i in flatten_matrix(mx1)]
    round2 = [round(i, precision) for i in flatten_matrix(mx2)]
    return round1 == round2

def get_loc_matrix(location):
    return Matrix.Translation(location)

def get_rot_matrix(rotation):
    return rotation.to_matrix().to_4x4()

def get_sca_matrix(scale):
    scale_mx = Matrix()
    for i in range(3):
        scale_mx[i][i] = scale[i]
    return scale_mx

def create_rotation_matrix_from_vertex(mx, vert):
    normal = (mx.to_quaternion() @ vert.normal).normalized()

    if vert.link_edges:
        longest_edge = max([e for e in vert.link_edges], key=lambda x: x.calc_length())
        binormal = (mx.to_3x3() @ (longest_edge.other_vert(vert).co - vert.co)).normalized()

        tangent = binormal.cross(normal).normalized()

        binormal = normal.cross(tangent).normalized()

    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        dot = normal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = normal.cross(objup).normalized()
        binormal = normal.cross(tangent).normalized()

    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal
    return rot

def create_rotation_matrix_from_edge(context, mx, edge):
    binormal = (mx.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()

    view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))
    binormal_dot = binormal.dot(view_up)

    if binormal_dot < 0:
        binormal.negate()

    if edge.link_faces:
        normal = average_normals([get_world_space_normal(f.normal, mx) for f in edge.link_faces]).normalized()

        tangent = binormal.cross(normal).normalized()

        normal = tangent.cross(binormal).normalized()

    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        dot = binormal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = (binormal.cross(objup)).normalized()
        normal = tangent.cross(binormal)

    rotmx = Matrix()
    rotmx.col[0].xyz = tangent
    rotmx.col[1].xyz = binormal
    rotmx.col[2].xyz = normal
    return rotmx

def create_rotation_matrix_from_face(context, mx, face, edge_pair=True, cylinder_threshold=0.01, align_binormal_with_view=True):
    normal = get_world_space_normal(face.normal, mx)
    binormal = None
    face_center = face.calc_center_median()

    circle = False

    if len(face.verts) > 4:
        edge_lengths = [e.calc_length() for e in face.edges]
        center_distances = [(v.co - face_center).length for v in face.verts]

        avg_edge_length = sum(edge_lengths) / len(face.edges)
        avg_center_distance = sum(center_distances) / len(face.verts)

        edges_are_same_length = all([abs(l - avg_edge_length) < avg_edge_length * cylinder_threshold for l in edge_lengths])
        verts_have_same_center_distance = all([abs(d - avg_center_distance) < avg_center_distance * cylinder_threshold for d in center_distances])

        if edges_are_same_length and verts_have_same_center_distance:
            circle = True

    if circle:
        for axis in [Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))]:

            i = intersect_line_plane(face_center + axis, face_center + axis + face.normal, face_center, face.normal)

            if i:
                projected = i - face_center

                if round(projected.length, 6):
                    binormal = (mx.to_3x3() @ projected).normalized()
                    break

    if not binormal:

        binormal = (mx.to_3x3() @ face.calc_tangent_edge_pair()).normalized() if edge_pair else (mx.to_3x3() @ face.calc_tangent_edge()).normalized()

    tangent = binormal.cross(normal).normalized()

    if align_binormal_with_view:
        view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))

        tangent_dot = tangent.dot(view_up)
        binormal_dot = binormal.dot(view_up)

        if abs(tangent_dot) >= abs(binormal_dot):
            binormal, tangent = tangent, -binormal
            binormal_dot = tangent_dot

        if binormal_dot < 0:
            binormal, tangent = -binormal, -tangent

    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal

    return rot

def create_rotation_matrix_from_normal(obj, normal):
    mx = obj.matrix_world

    objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()
    normal = normal.normalized()
    dot = normal.normalized().dot(objup)

    if abs(round(dot, 6)) == 1:
        objup = mx.to_3x3() @ Vector((1, 0, 0))

    tangent = objup.cross(normal)
    binormal = tangent.cross(-normal)

    rotmx = Matrix()
    rotmx.col[0].xyz = tangent.normalized()
    rotmx.col[1].xyz = binormal.normalized()
    rotmx.col[2].xyz = normal.normalized()
    return rotmx

def create_rotation_matrix_from_vector(vector, mx=None):
    normal = mx.to_3x3() @ vector if mx else vector
    binormal = normal.orthogonal()
    tangent = normal.cross(binormal)

    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal

    return rot

def create_rotation_matrix_from_vectors(tangent, binormal, normal):
    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal
    return rot
