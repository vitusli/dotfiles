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

from ..update_nodes import RR_node_name

RGB_curve_default = [
    [[0, 0], [1, 1]],
    [[0, 0], [1, 1]],
    [[0, 0], [1, 1]],
    [[0, 0], [1, 1]],
]

def create_curve_preset(node):
    curve_preset = []
    for curve in node.mapping.curves:
        curve_preset.append(
            [ [x.location[0], x.location[1]] for x in curve.points ]
        )
    return curve_preset

def set_curve_node(node, curve_preset):
    for curve_idx, curve in enumerate(node.mapping.curves):
        points_to_remove = list(range(1, len(curve.points) - 1))
        for point_idx in points_to_remove:
            curve.points.remove(curve.points[1])

        preset_points = curve_preset[curve_idx]
        curve.points[0].location = preset_points[0]
        curve.points[1].location = preset_points[-1]
        new_points = preset_points.copy()
        new_points.pop(0)
        new_points.pop(-1)
        for point in new_points:
            curve.points.new(point[0], point[1])
    node.mapping.update()
    node.update()

            
'''
class SetCurveNode(bpy.types.Operator):
    bl_label = 'Set Curves'
    bl_idname = "node.render_raw_set_curves"

    node_name: bpy.props.StringProperty(
        name = 'Node Name'
    )
    node_path: bpy.props.EnumProperty(
        name = 'Node Path',
        items = [
            ('RENDER RAW', 'Render Raw', '')
        ]
    )
    curve_preset: bpy.props.EnumProperty(
        name = 'Curve Preset',
        items = [
            ('RGB', 'RGB', '')
        ]
    )

    @classmethod 
    def poll(self, context):
        return hasattr(context.scene, 'render_raw')

    def execute(self, context):
        if self.node_path == 'RENDER RAW':
            nodes = bpy.data.node_groups[RR_node_name].nodes

        if self.curve_preset == 'RGB':
            node_preset = RGB_curve_default

        set_curve_node(nodes[self.node_name], node_preset)

        return {'FINISHED'}
'''