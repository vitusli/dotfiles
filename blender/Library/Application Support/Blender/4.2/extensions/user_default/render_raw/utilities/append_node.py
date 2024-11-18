'''
Copyright (C) 2024 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of the Render Raw add-on, created by Jonathan Lampel for Orange Turbine.

All code distributed with this add-on is open source as described below.

Render Raw is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses/>.
'''

import bpy, os

def append_node(self, nodes, node_tree_name):
    node_file = 'render_raw_nodes.blend'
    path = bpy.path.native_pathsep(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'assets', f'{node_file}\\NodeTree\\'
    ))

    node_group = nodes.new("CompositorNodeGroup")
    initial_nodetrees = set(bpy.data.node_groups)

    try:
        bpy.ops.wm.append(filename=node_tree_name, directory=path)
    except:
        self.report({'ERROR'}, 'Render Raw nodes not detected. Please download from the Blender Market and install again.')
        self.report({'ERROR'}, f'{node_tree_name} could not be appended from {path}')
        nodes.remove(node_group)

    appended_nodetrees = set(bpy.data.node_groups) - initial_nodetrees
    appended_node = [x for x in appended_nodetrees if node_tree_name in x.name][0]
    node_group.node_tree = bpy.data.node_groups[appended_node.name]
    node_group.node_tree.name = node_tree_name
    return node_group