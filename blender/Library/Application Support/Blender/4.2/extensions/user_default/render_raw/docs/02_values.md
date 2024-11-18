---
excerpt: Documentation for the Render Raw add-on for Blender
nav_order: 2
nav_exclude: false
search_exclude: false
---

# Value Adjustments

All value adjustments can be enabled or disabled at once by using the checkbox in the panel header. 

## Exposure
Used to control the image brightness (in stops). 

The exposure in Render Raw can be used just like Blender's scene exposure control, but is not the same under the hood. The Render Raw exposure is the first node in the compositing chain while Blender's exposure is applied after all compositing. Because of this, Render Raw needs the Blender scene exposure to be set to 0 under the hood. Enabling Render Raw will set the scene exposure to 0 and swap out that control for the Render Raw node exposure control and set it to the same value. You should not notice any difference in using the control. 

The one issue that may arise from this setup is that the colors could break if another add-on changes the scene exposure out from under Render Raw. If this happens, simply toggle the Enable Render Raw button off and on again to fix it. 

## Gamma
Extra gamma correction applied after color space conversion and after all compositing. Blender's scene gamma control works great with Render Raw, so it is set directly rather than with a custom node. 

## Contrast
A scaling factor by which to make brighter pixels brighter while keeping the darker pixels dark. This is applied before the color space conversion and should function like Filmic and AgX's contrast looks but with more control. 

## Levels
The White Level and Black Level controls can be used to map the range of values in the render. Lowering the White Level is often helpful for making almost-white pixels perfectly white, and increasing the Black Level can be helpful for making almost-black pixels perfectly black. You may also want to do the opposite in order to expand the dynamic range if other Render Raw settings are causing the values to clip. 

The Highlights and Shadows controls smoothly increase or decrease the values around the 0.75 and 0.25 points respectively. If you need to adjust the midtones, consider changing the exposure or curves. 

All of the Levels controls happen after the color space conversion. 

## Sharpening
Adds contrast to edges after the color space conversion to make the image appear more crisp. The Masking option can be used to only sharpen edges that already have a high contrast. 

## Texture
Increases or decreases contrast in only the midtone values after the color space conversion. The Keep Color control makes it so that the contrast only affects the each color's values and not its hue and saturation. 

## Clarity
Increases or decreases the difference between neighboring values after the color space conversion. The main difference between Clarity and Sharpening is that Clarity can be smoothly spread over a wider area with the Size control. 

## Curves 
Increases or decreases the output value per input value. Since this happens after the color space conversion, it works in the intuitive 0-1 range. 


