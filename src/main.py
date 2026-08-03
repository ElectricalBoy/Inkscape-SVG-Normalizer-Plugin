#!/usr/bin/env python3

import inkex
from inkex import Transform
from inkex.elements import ShapeElement, PathElement
import math
import re


class NormalizeSvg(inkex.EffectExtension):

    CANVAS = 1000
    CANVAS_LARGE = 1000000

    def effect(self):

        svg = self.svg

        # --------------------------------------------------
        # Scale everything up to avoid rounding errors later
        # --------------------------------------------------

        svg.set("viewBox", f"0 0 {self.CANVAS_LARGE} {self.CANVAS_LARGE}")
        svg.set("width", self.CANVAS_LARGE)
        svg.set("height", self.CANVAS_LARGE)

        # --------------------------------------------------
        # Set viewbox
        # --------------------------------------------------

        svg.set("viewBox", f"0 0 {self.CANVAS} {self.CANVAS}")
        svg.set("width", self.CANVAS)
        svg.set("height", self.CANVAS)

        # --------------------------------------------------
        # Convert everything to paths
        # --------------------------------------------------

        for element in svg.descendants():

            # Already a path
            if isinstance(element, PathElement):
                continue

            tag = element.TAG

            d = None

            #
            # RECT
            #
            if tag == "rect":

                x = float(element.get("x", 0))
                y = float(element.get("y", 0))
                w = float(element.get("width"))
                h = float(element.get("height"))

                # Ignore rounded corners for now
                d = (
                    f"M {x},{y} "
                    f"L {x+w},{y} "
                    f"L {x+w},{y+h} "
                    f"L {x},{y+h} Z"
                )

            #
            # CIRCLE
            #
            elif tag == "circle":

                cx = float(element.get("cx", 0))
                cy = float(element.get("cy", 0))
                r = float(element.get("r"))

                d = (
                    f"M {cx-r},{cy} "
                    f"A {r},{r} 0 1 0 {cx+r},{cy} "
                    f"A {r},{r} 0 1 0 {cx-r},{cy} Z"
                )

            #
            # ELLIPSE
            #
            elif tag == "ellipse":

                cx = float(element.get("cx", 0))
                cy = float(element.get("cy", 0))
                rx = float(element.get("rx"))
                ry = float(element.get("ry"))

                d = (
                    f"M {cx-rx},{cy} "
                    f"A {rx},{ry} 0 1 0 {cx+rx},{cy} "
                    f"A {rx},{ry} 0 1 0 {cx-rx},{cy} Z"
                )

            #
            # LINE
            #
            elif tag == "line":

                x1 = float(element.get("x1"))
                y1 = float(element.get("y1"))
                x2 = float(element.get("x2"))
                y2 = float(element.get("y2"))

                d = f"M {x1},{y1} L {x2},{y2}"

            #
            # POLYLINE
            #
            elif tag == "polyline":

                pts = element.get("points", "").strip()

                if pts:
                    nums = pts.replace(",", " ").split()

                    coords = [
                        (float(nums[i]), float(nums[i + 1]))
                        for i in range(0, len(nums), 2)
                    ]

                    d = "M " + " L ".join(
                        f"{x},{y}" for x, y in coords
                    )

            #
            # POLYGON
            #
            elif tag == "polygon":

                pts = element.get("points", "").strip()

                if pts:
                    nums = pts.replace(",", " ").split()

                    coords = [
                        (float(nums[i]), float(nums[i + 1]))
                        for i in range(0, len(nums), 2)
                    ]

                    d = (
                        "M "
                        + " L ".join(f"{x},{y}" for x, y in coords)
                        + " Z"
                    )

            if d is None:
                continue

            #
            # Create replacement path
            #
            path = PathElement()
            path.set("d", d)

            #
            # Copy attributes
            #
            for k, v in element.attrib.items():
                if k not in (
                    "x", "y", "width", "height",
                    "cx", "cy", "rx", "ry", "r",
                    "x1", "y1", "x2", "y2",
                    "points",
                ):
                    path.set(k, v)

            #
            # Preserve transform
            #
            if element.get("transform"):
                path.set("transform", element.get("transform"))

            parent = element.getparent()
            index = parent.index(element)

            parent.remove(element)
            parent.insert(index, path)

        # --------------------------------------------------
        # Collect all shape elements
        # --------------------------------------------------

        shapes = []

        for element in svg.descendants():

            if isinstance(element, ShapeElement):
                try:
                    bbox = element.bounding_box()
                    shapes.append(element)
                except Exception:
                    pass

        if not shapes:
            return

        # --------------------------------------------------
        # Bounding box
        # --------------------------------------------------

        xmin = float("inf")
        ymin = float("inf")
        xmax = float("-inf")
        ymax = float("-inf")

        for s in shapes:
            bx1, by1, bx2, by2 = get_stroke_expanded_bounds(s)

            xmin = min(xmin, bx1)
            ymin = min(ymin, by1)

            xmax = max(xmax, bx2)
            ymax = max(ymax, by2)

        width = xmax - xmin
        height = ymax - ymin

        if width == 0 or height == 0:
            return

        # --------------------------------------------------
        # Scale to fill canvas
        # --------------------------------------------------

        scale = min(
            self.CANVAS / width,
            self.CANVAS / height
        )

        new_w = width * scale
        new_h = height * scale

        tx = (self.CANVAS - new_w) / 2 - xmin * scale
        ty = (self.CANVAS - new_h) / 2 - ymin * scale

        transform = Transform(f"matrix({scale},0,0,{scale},{tx},{ty})")

        for s in shapes:
            if isinstance(s, PathElement):
                # resize paths to scale, first resolve possible preexisting transforms, then do the resize
                if s.transform:
                    s.path = s.path.transform(s.transform)
                    s.attrib.pop("transform", None)
                s.path = s.path.transform(transform)
                s.attrib.pop("transform", None)

                # resize strokes to scale
                stroke_width = s.style.get("stroke-width")
                if stroke_width:
                    try:
                        s.style["stroke-width"] = float(stroke_width) * scale
                    except ValueError:
                        pass

        # --------------------------------------------------
        # Adjust colors
        # --------------------------------------------------

        # colors in <style> tags
        for style_element in svg.xpath("//svg:style"):
            css = style_element.text
            if not css:
                continue

            css = re.sub(
                r'(\bfill\s*:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|[a-zA-Z]+)',
                r'\1#000000',
                css
            )
            css = re.sub(
                r'(\bstroke\s*:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|[a-zA-Z]+)',
                r'\1#000000',
                css
            )
            style_element.text = css

        # colors in inline styles
        for element in svg.descendants():
            style = element.get("style")
            if style:
                style = re.sub(
                    r'(\bfill\s*:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|[a-zA-Z]+)',
                    r'\1#000000',
                    style
                )
                style = re.sub(
                    r'(\bstroke\s*:\s*)(#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|[a-zA-Z]+)',
                        r'\1#000000',
                    style
                )
                element.set("style", style)

        # colors in attributes
        for element in svg.descendants():
            if element.get("fill"):
                element.set("fill", "#000000")
            if element.get("stroke"):
                element.set("stroke", "#000000")

def get_stroke_expanded_bounds(path):
    """
    Returns the approximate painted bounds of a path,
    including stroke width, joins, and caps.

    The path itself is not modified.
    """

    bbox = path.bounding_box()

    xmin = bbox.left
    ymin = bbox.top
    xmax = bbox.right
    ymax = bbox.bottom

    stroke = path.style.get("stroke")

    if not stroke or stroke == "none":
        return xmin, ymin, xmax, ymax

    try:
        width = float(
            path.style.get(
                "stroke-width",
                1
            )
        )
    except ValueError:
        width = 1


    # Default SVG stroke expansion
    expand = width / 2


    join = path.style.get(
        "stroke-linejoin",
        "miter"
    )

    cap = path.style.get(
        "stroke-linecap",
        "butt"
    )


    # Miter joins can extend further
    if join == "miter":

        try:
            limit = float(
                path.style.get(
                    "stroke-miterlimit",
                    4
                )
            )
        except ValueError:
            limit = 4

        expand = max(
            expand,
            width / 2 * limit
        )


    # Square caps extend by half stroke width
    if cap == "square":
        expand = max(
            expand,
            width / 2
        )


    # Round caps are also radius extensions
    if cap == "round":
        expand = max(
            expand,
            width / 2
        )


    return (
        xmin - expand,
        ymin - expand,
        xmax + expand,
        ymax + expand
    )


if __name__ == "__main__":
    NormalizeSvg().run()
