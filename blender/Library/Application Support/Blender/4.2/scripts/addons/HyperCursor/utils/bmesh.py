import bpy
from mathutils import Vector, Matrix
from math import sqrt
from . math import get_sca_matrix

def ensure_custom_data_layers(bm, vertex_groups=True, bevel_weights=True, crease=True):

    vert_vg_layer = bm.verts.layers.deform.verify() if vertex_groups else None

    if bpy.app.version >= (4, 0, 0):

        if bevel_weights:
            edge_bw_layer = bm.edges.layers.float.get('bevel_weight_edge')

            if not edge_bw_layer:
                edge_bw_layer = bm.edges.layers.float.new('bevel_weight_edge')
        else:
            edge_bw_layer = None

        if crease:
            edge_crease_layer = bm.edges.layers.float.get('crease_edge')

            if not edge_crease_layer:
                edge_crease_layer = bm.edges.layers.float.new('crease_edge')
        else:
            edge_crease_layer = None
    else:
        edge_bw_layer = bm.edges.layers.bevel_weight.verify() if bevel_weights else None
        edge_crease_layer = bm.edges.layers.crease.verify() if crease else None

    return [layer for layer in [vert_vg_layer, edge_bw_layer, edge_crease_layer] if layer is not None]

def ensure_edge_glayer(bm):
    edge_glayer = bm.edges.layers.int.get('HyperEdgeGizmo')

    if not edge_glayer:
        edge_glayer = bm.edges.layers.int.new('HyperEdgeGizmo')

    return edge_glayer

def ensure_face_glayer(bm):
    face_glayer = bm.faces.layers.int.get('HyperFaceGizmo')

    if not face_glayer:
        face_glayer = bm.faces.layers.int.new('HyperFaceGizmo')

    return face_glayer

def ensure_gizmo_layers(bm):
    edge_glayer = ensure_edge_glayer(bm)
    face_glayer = ensure_face_glayer(bm)

    return edge_glayer, face_glayer

def ensure_edge_slayer(bm):
    edge_slayer = bm.edges.layers.int.get('HyperEdgeSelect')

    if not edge_slayer:
        edge_slayer = bm.edges.layers.int.new('HyperEdgeSelect')

    return edge_slayer

def ensure_face_slayer(bm):
    face_slayer = bm.faces.layers.int.get('HyperFaceSelect')

    if not face_slayer:
        face_slayer = bm.faces.layers.int.new('HyperFaceSelect')

    return face_slayer

def ensure_select_layers(bm):
    edge_slayer = ensure_edge_slayer(bm)
    face_slayer = ensure_face_slayer(bm)

    return edge_slayer, face_slayer

def get_tri_coords(loop_triangles, faces, mx=Matrix()):
    return [mx @ l.vert.co for tri in loop_triangles if tri[0].face in faces for l in tri]

def get_face_dim(face, mx):
    scale_mx = get_sca_matrix(mx.decompose()[2])
    return (scale_mx @ Vector((sqrt(face.calc_area()), 0, 0))).length
