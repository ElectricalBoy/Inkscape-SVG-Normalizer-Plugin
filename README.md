# Inkscape-SVG-Normalizer-Plugin

An Inkscape plugin that normalizes SVG files. The normalization target is an SVG file that follows the following rules:
* viewbox of 1000x1000
* width and height of 1000
* monochrome black
* only paths, no other shapes
* existing shapes are scaled and centered to fit the canvas

## FAQ
:question: **Should I use this?**
> Unless you need SVG files with this very particular format probably no.

:question: **How do I use this if I still want to use it?**
> Download the repository, put them into a folder inside your Inkscape extensions folder. On Linux this is `/usr/share/inkscape/extensions/`. The extension can be accessed through the menu under `Extensions > Modify Path > Normalize SVG (1000x1000)`.

:question: **Was this vibecoded?**
> Absolutely yes because I have no idea about how Inkscape works and my knowledge about image processing is miniscule. The code is probably terrible. I don't care, it's useful to me.

:question: **Can this have feature...**
> No.

