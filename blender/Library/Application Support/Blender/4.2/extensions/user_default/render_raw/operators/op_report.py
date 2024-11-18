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

import bpy

class Report(bpy.types.Operator):
    bl_label = 'Report'
    bl_idname = "render.render_raw_report"
    bl_description = 'Reports Render Raw warnings that occur outside of an operator'
    bl_options = {'REGISTER', 'BLOCKING'}

    message_type: bpy.props.EnumProperty(
        name = 'Message Type',
        items = [
            ('WARNING', 'Warning', ''),
            ('INFO', 'Info', ''),
            ('ERROR', 'Error', ''),
        ],
        default = 'WARNING'
    )
    message: bpy.props.StringProperty(
        name = 'Message',
        default = ''
    )
    
    def execute(self, context):
        self.report({self.message_type}, self.message)
        return{'FINISHED'}
    
def register():
    bpy.utils.register_class(Report)

def unregister():
    bpy.utils.unregister_class(Report)