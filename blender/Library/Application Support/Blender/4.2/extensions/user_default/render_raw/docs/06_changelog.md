---
excerpt: Documentation for the Render Raw add-on for Blender
nav_order: 6
nav_exclude: false
search_exclude: false
---

# Changelog

## 1.0.8
- Enabled Show Raw While Rendering by default since the transform swap does not work with some edge cases

## 1.0.7
- Added option to disable RAW view while rendering

## 1.0.6
- Added option to switch compositor device
- Added size control to Bloom

## 1.0.5
- Added support for Khronos PBR Neutral
- Fixed issue with ACES gamma

## 1.0.4
- Fixed shifting vignette in Blender 4.2 CPU compositor
- Added support for new bloom in Blender 4.2

## 1.0.3
- Added compatibility for Blender 4.2 Alpha

## 1.0.2
- Fixed Color Management panel appearing in all tabs after disabling RR

## 1.0.1
- Fixed incorrect preset names on Mac

## 1.0.0
- We're out of beta! 
- Made highlight, midtone, and shadow ordering consistent
- Centered value controls around 0 
- Added version handling to presets for when controls change
- Added steps control to fast film grain
- Added ability to scale vignette outside of camera bounds
- Added 'under the hood' scene color management settings to utilities panel
- Fixed darkening when desaturating film grain
- Fixed color blending not muting when Use Colors was disabled
- Improved default presets
- Minimum Blender version bumped to 4.1 for stability

## 0.9.5
- Added Perceptual control to saturation per value panel
- Added Offset Power Slope control to color balance panel
- Reorganized color panels

## 0.9.4
- Fixed issue with setting preset folder on Mac
- Added descriptive tooltips to all controls
- Removed the Keep Color control under Texture for being cryptic and not very useful
- Fixed panel error when addon preferences could not be found

## 0.9.3
- Fixed issue when duplicate RR sub node groups exist in the file
- Fixed issue with glare sometimes causing black spots in 8 bit renders

## 0.9.2
- Added button to refresh node tree
- Added link to docs

## 0.9.1
- Improved contrast control to better match AgX looks
- Improved color boost and perceptual saturation with the YUV color model
- Added control for saturation of film grain

## 0.9.0
- First public release