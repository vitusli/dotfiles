---
excerpt: Documentation for the Render Raw add-on for Blender
nav_order: 1
nav_exclude: false
search_exclude: false
---

# Enabling Render Raw

The Render Raw color settings can be found in the Properties Editor in the Render tab under Color Management. 

_Render Raw replaces the existing Color Management panel because it needs to change those settings under the hood in order for it to work correctly._

To use the add-on, click Enable Render Raw. This will add the compositing setup, switch on Viewport Compositing (if enabled in the preferences), and display the adjustment panels. 

The adjustment panels are also displayed in the Render tab in the 3D Viewport sidebar by default. 

The View Transform, Look, and Exposure settings are not the same as the default Blender settings by the same name. Changing the Blender settings via python while Render Raw is enabled may break the look of the scene. If this happens, just toggle Enable Render Raw off and then on again. I will try to make Render Raw more compatible with other add-ons which set exposure in the future. 

When Render Raw is enabled, viewport compositing needs to be enabled in order for the adjustments to display in the viewport. If you create a new 3D View, be sure to go to Viewport Shading and set Compositing to Always. 

The Render Raw compositing node is added right before the output node by default. You can move it to anywhere in your node tree if you have an existing compositing setup, but if the node is deleted, renamed, or altered too much the add-on will not work. 



