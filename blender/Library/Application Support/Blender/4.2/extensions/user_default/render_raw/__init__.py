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

bl_info = {
    "name": "Render Raw",
    "author": "Jonathan Lampel",
    "version": (1, 0, 8),
    "blender": (4, 1, 0),
    "location": "Properties > Render > Color Management",
    "description": "Tools for easy color correction",
    "wiki_url": "",
    "category": "Render",
}

import bpy, sys

from . import settings, preferences
from .handlers import handle_render
from .interface import adjustment_panels
from .operators import op_presets, op_refresh, op_report, op_scene_settings

files = [
    settings, preferences, 
    handle_render,
    adjustment_panels,
    op_report, op_presets, op_refresh, op_scene_settings,
    ]

def cleanse_modules():
    # Based on https://devtalk.blender.org/t/plugin-hot-reload-by-cleaning-sys-modules/20040
    for module_name in sorted(sys.modules.keys()):
        if module_name.startswith(__name__):
            del sys.modules[module_name]

def register():
    for f in files:
        f.register()

def unregister():
    for f in files:
        f.unregister()
    cleanse_modules()

if __name__ == "__main__":
    register()