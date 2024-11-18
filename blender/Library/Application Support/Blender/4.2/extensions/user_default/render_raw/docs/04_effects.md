---
excerpt: Documentation for the Render Raw add-on for Blender
nav_order: 4
nav_exclude: false
search_exclude: false
---

# Effects Adjustments
All Effects adjustments can be enabled or disabled at once by using the checkbox in the panel header. Due to the way the viewport compositor works, the most accurate way to view the effects is through the camera with the camera's Passeparout setting set to 1 so that the aspect ratio of the viewport composite will be the same as the render. 

## Lens Distortion and Dispersion
Simulates the bulging, pinching, and fringing effects of real camera lenses. Unlike the default Blender Lens Distortion, the Render Raw setup supports transparency. It's important to note that the 3D View overlays will not be distorted, so the grid may overlap your objects a bit and it is recommended to turn off overlays when previewing distortion in the viewport. 

## Film Grain
Simulates the grain from a camera's film or sensor, which is much different than render noise. 

The Fast method simply overlays instances of a voronoi texture on top of the image using a Soft Light blend mode while the Accurate method actually distorts the image so that each grain contains one color just like film. The Accurate method has a Steps setting which controls how many layers of grain get mixed together. Higher values look more natural but are much slower. 

Due to the lack of mapping options in the compositor, the Aspect Correction setting is sometimes needed to fix grain stretching. 

The Animate option will change the grain pattern on every frame, which looks more believable but is much slower to compute in the viewport. 

## Glare
Simulates glow around bright pixels. The Bloom effect is a custom implementation that supports transparency, avoids clipping on reflective surfaces, and matches the viewport result with the render result. Since the glare uses iterations of blur, which can be expensive, a quality control allows you to set how many iterations are used. 

## Vignette
Simulates darkening or lightening around the edges of the viewport. The Highlights option can be used to retain vivid colors. 
