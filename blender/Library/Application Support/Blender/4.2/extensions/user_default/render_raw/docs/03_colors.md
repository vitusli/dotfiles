---
excerpt: Documentation for the Render Raw add-on for Blender
nav_order: 3
nav_exclude: false
search_exclude: false
---

# Color Adjustments
All color adjustments can be enabled or disabled at once by using the checkbox in the panel header. 

## Temperature and Tint
Increasing or decreasing the Temperature control moves the colors towards a warmer or cooler hue by adjusting the red and blue channels of each pixel. Tint manages the amount of green in the green channel. Both controls happen before the color space conversion. 

## Color Boost
Increases or decreases the saturation in lower saturated areas without affecting higher saturated areas. This is helpful for making the image more colorful overall without blowing out the already saturated colors. This happens before the color space conversion. 

## Saturation
Increases or decreases the saturation uniformly after the color space conversion. The Perceptual control attempts to keep the perceived values of the colors the same using the HSL method instead of the HSV method, which is more intuitive but can cause banding. HSL is not as perceptually accurate as I would like and I hope to improve it with my own implementation in the future. 

## Per Hue Adjustments 
Hue, Saturation, and Value can also be adjusted per hue after the color space conversion. Each hue control is evenly spaced around the color wheel except for Orange, which has been added for convenience. Since it is quite close to Red and Yellow, all three of those controls are closely tied together and should be balanced carefully. Changing the Orange control may change the result of the Red and Yellow controls. 

## Per Value Adjustments 
Saturation can be adjusted separately for highlights, midtones, and shadows after the color space conversion, which can be helpful for emulating some film looks and making sure highlights are not blown out. 

## Color Balance
Lift, Gamma, and Gain can be adjusted after the color space conversion like in most editing software, but the Highlight, Midtone, and Shadow blending options give you much more control and allow for a wide variety of creative looks. To make highlights, midtones, or shadows an exact color, just set the blending type to Mix. 


