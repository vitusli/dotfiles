from mathutils import Vector, Matrix
import numpy as np

def get_bbox(mesh=None, coords=None):
    vert_count = len(mesh.vertices)
    coords = np.empty((vert_count, 3), float)
    mesh.vertices.foreach_get('co', np.reshape(coords, vert_count * 3))

    xmin = np.min(coords[:, 0])
    xmax = np.max(coords[:, 0])
    ymin = np.min(coords[:, 1])
    ymax = np.max(coords[:, 1])
    zmin = np.min(coords[:, 2])
    zmax = np.max(coords[:, 2])

    bbox = [Vector((xmin, ymin, zmin)),
            Vector((xmax, ymin, zmin)),
            Vector((xmax, ymax, zmin)),
            Vector((xmin, ymax, zmin)),
            Vector((xmin, ymin, zmax)),
            Vector((xmax, ymin, zmax)),
            Vector((xmax, ymax, zmax)),
            Vector((xmin, ymax, zmax))]

    xcenter = (xmin + xmax) / 2
    ycenter = (ymin + ymax) / 2
    zcenter = (zmin + zmax) / 2

    centers = [Vector((xmin, ycenter, zcenter)),
               Vector((xmax, ycenter, zcenter)),
               Vector((xcenter, ymin, zcenter)),
               Vector((xcenter, ymax, zcenter)),
               Vector((xcenter, ycenter, zmin)),
               Vector((xcenter, ycenter, zmax))]

    xdim = (bbox[1] - bbox[0]).length
    ydim = (bbox[2] - bbox[1]).length
    zdim = (bbox[4] - bbox[0]).length

    dimensions = Vector((xdim, ydim, zdim))

    return bbox, centers, dimensions

def get_coords(mesh, mx=None, offset=0, edge_indices=False):
    verts = mesh.vertices
    vert_count = len(verts)

    coords = np.empty((vert_count, 3), float)
    mesh.vertices.foreach_get('co', np.reshape(coords, vert_count * 3))

    if offset:
        normals = np.empty((vert_count, 3), float)
        mesh.vertices.foreach_get('normal', np.reshape(normals, vert_count * 3))

        coords = coords + normals * offset

    if mx:
        coords_4d = np.ones((vert_count, 4), dtype=float)
        coords_4d[:, :-1] = coords

        coords = np.einsum('ij,aj->ai', mx, coords_4d)[:, :-1]

    coords = np.float32(coords)

    if edge_indices:
        edges = mesh.edges
        edge_count = len(edges)

        indices = np.empty((edge_count, 2), 'i')
        edges.foreach_get('vertices', np.reshape(indices, edge_count * 2))

        return coords, indices

    return coords

def unhide_deselect(mesh):
    polygons = len(mesh.polygons)
    edges = len(mesh.edges)
    vertices = len(mesh.vertices)

    mesh.polygons.foreach_set('hide', [False] * polygons)
    mesh.edges.foreach_set('hide', [False] * edges)
    mesh.vertices.foreach_set('hide', [False] * vertices)

    mesh.polygons.foreach_set('select', [False] * polygons)
    mesh.edges.foreach_set('select', [False] * edges)
    mesh.vertices.foreach_set('select', [False] * vertices)

    mesh.update()
