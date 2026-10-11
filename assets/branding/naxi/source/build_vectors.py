"""Build the NAXI vector masters and After Effects shape-layer importer.

Run from any directory with Python 3.10+. No external packages are required.
Geometry is defined in the 1254 x 1254 reference coordinate system.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINT = "#57F4B4"
WHITE = "#F8F7F5"
DARK = "#202222"


class Outline:
    def __init__(self, start):
        self.commands = [("M", list(start))]

    def line(self, x, y):
        self.commands.append(("L", [x, y]))
        return self

    def curve(self, *values):
        self.commands.append(("C", list(values)))
        return self

    def close(self):
        self.commands.append(("Z", []))
        return self

    def svg(self):
        return " ".join(cmd + " " + " ".join(f"{v:.4f}".rstrip("0").rstrip(".") for v in values)
                        for cmd, values in self.commands)

    def ae(self):
        vertices, incoming, outgoing = [], [], []
        for cmd, values in self.commands:
            if cmd == "M":
                vertices.append(values[:])
                incoming.append([0, 0])
                outgoing.append([0, 0])
            elif cmd == "L":
                if values != vertices[0]:
                    vertices.append(values[:])
                    incoming.append([0, 0])
                    outgoing.append([0, 0])
            elif cmd == "C":
                c1, c2, end = values[:2], values[2:4], values[4:]
                outgoing[-1] = [c1[i] - vertices[-1][i] for i in range(2)]
                if end == vertices[0]:
                    incoming[0] = [c2[i] - end[i] for i in range(2)]
                else:
                    vertices.append(end)
                    incoming.append([c2[i] - end[i] for i in range(2)])
                    outgoing.append([0, 0])
        return dict(vertices=vertices, inTangents=incoming, outTangents=outgoing, closed=True)


def circle(cx, cy, radius):
    k = radius * 0.5522847498307936
    # Counterclockwise in screen coordinates: the circular counter is a real hole.
    return (Outline((cx, cy-radius))
            .curve(cx-k, cy-radius, cx-radius, cy-k, cx-radius, cy)
            .curve(cx-radius, cy+k, cx-k, cy+radius, cx, cy+radius)
            .curve(cx+k, cy+radius, cx+radius, cy+k, cx+radius, cy)
            .curve(cx+radius, cy-k, cx+k, cy-radius, cx, cy-radius).close())


def capsule(a, b, radius):
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    u = (math.cos(angle), math.sin(angle))
    n = (-u[1], u[0])
    def point(base, along, normal):
        return [base[i] + along*u[i] + normal*n[i] for i in range(2)]
    k = radius * 0.5522847498307936
    p = Outline(point(a, 0, radius)).line(*point(b, 0, radius))
    p.curve(*point(b, k, radius), *point(b, radius, k), *point(b, radius, 0))
    p.curve(*point(b, radius, -k), *point(b, k, -radius), *point(b, 0, -radius))
    p.line(*point(a, 0, -radius))
    p.curve(*point(a, -k, -radius), *point(a, -radius, -k), *point(a, -radius, 0))
    p.curve(*point(a, -radius, k), *point(a, -k, radius), *point(a, 0, radius))
    return p.close()


body = (Outline((451, 434))
        .curve(451, 401, 479, 375, 511, 375)
        .curve(530, 375, 545, 382, 559, 396)
        .line(727, 560)
        .curve(721, 557, 714, 554, 707, 555)
        .curve(689, 555, 676, 569, 676, 588)
        .curve(676, 607, 690, 622, 708, 622)
        .curve(730, 622, 746, 601, 750, 578)
        .curve(754, 548, 738, 526, 716, 503)
        .line(697, 483)
        .curve(689, 475, 686, 466, 686, 454)
        .line(686, 434)
        .curve(686, 401, 712, 375, 745, 375)
        .curve(778, 375, 804, 401, 804, 434)
        .line(804, 653)
        .curve(804, 686, 778, 711, 746, 711)
        .curve(727, 711, 712, 704, 700, 687)
        .line(551, 498)
        .curve(540, 482, 521, 477, 506, 487)
        .curve(491, 497, 490, 517, 501, 531)
        .line(554, 593)
        .curve(561, 602, 564, 608, 564, 621)
        .line(564, 654)
        .curve(564, 686, 538, 711, 507, 711)
        .curve(476, 711, 451, 686, 451, 654)
        .line(451, 434).close())

counter = circle(528, 431, 34)

letter_n = (Outline((408, 878))
            .curve(402, 878, 397, 873, 397, 867).line(397, 789)
            .curve(397, 778, 404, 770, 415, 770)
            .curve(421, 770, 426, 773, 431, 779).line(489, 848)
            .line(489, 782).curve(489, 775, 494, 770, 500, 770)
            .curve(507, 770, 512, 775, 512, 782).line(512, 861)
            .curve(512, 871, 505, 878, 495, 878)
            .curve(489, 878, 484, 876, 479, 871).line(420, 802)
            .line(420, 867).curve(420, 873, 415, 878, 408, 878).close())

letter_a = (Outline((543, 862)).line(581, 784)
            .curve(586, 775, 593, 770, 602, 770)
            .curve(611, 770, 619, 775, 623, 784).line(662, 862)
            .curve(665, 868, 662, 875, 656, 878)
            .curve(650, 881, 643, 878, 640, 872).line(604, 796)
            .curve(603, 793, 601, 793, 600, 796).line(564, 872)
            .curve(561, 878, 554, 881, 548, 878)
            .curve(542, 875, 540, 868, 543, 862).close())

letters_x = [capsule((706, 781.5), (788, 867), 11.5),
             capsule((783, 781.5), (702, 867), 11.5)]
letter_i = capsule((845.5, 781.5), (845.5, 867), 11.5)

ELEMENTS = [
    dict(id="mark", name="Mark - N", color=MINT, anchor=[627.5, 543],
         evenOdd=True, paths=[body, counter], names=["Body", "Circular counter"]),
    dict(id="letter-n", name="Wordmark - N", color=WHITE, anchor=[454.5, 824],
         evenOdd=False, paths=[letter_n], names=["N outline"]),
    dict(id="letter-a", name="Wordmark - A", color=WHITE, anchor=[602, 824],
         evenOdd=False, paths=[letter_a], names=["A outline"]),
    dict(id="letter-x", name="Wordmark - X", color=WHITE, anchor=[745, 824],
         evenOdd=False, paths=letters_x, names=["X descending", "X ascending"]),
    dict(id="letter-i", name="Wordmark - I", color=WHITE, anchor=[845.5, 824],
         evenOdd=False, paths=[letter_i], names=["I outline"]),
]


def svg(elements, viewbox, background=None, monochrome=None):
    x, y, width, height = viewbox
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" viewBox="{x} {y} {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="title">',
             '<title id="title">NAXI logo</title>']
    if background:
        parts.append(f'<rect id="background" x="{x}" y="{y}" width="{width}" height="{height}" fill="{background}"/>')
    for element in elements:
        color = monochrome or element["color"]
        rule = "evenodd" if element["evenOdd"] else "nonzero"
        parts.append(f'<g id="{element["id"]}" inkscape:groupmode="layer" inkscape:label="{element["name"]}" fill="{color}">')
        if element["evenOdd"]:
            data = " ".join(p.svg() for p in element["paths"])
            parts.append(f'<path id="mark-outline" fill-rule="{rule}" d="{data}"/>')
        else:
            for index, path in enumerate(element["paths"]):
                parts.append(f'<path id="{element["id"]}-{index+1}" d="{path.svg()}"/>')
        parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def build():
    for directory in [ROOT / "svg", ROOT / "after-effects", ROOT / "preview"]:
        directory.mkdir(parents=True, exist_ok=True)
    exports = {
        "naxi-master.svg": svg(ELEMENTS, (0, 0, 1254, 1254)),
        "naxi-on-dark.svg": svg(ELEMENTS, (0, 0, 1254, 1254), DARK),
        "naxi-lockup.svg": svg(ELEMENTS, (365, 343, 524, 568)),
        "naxi-mark.svg": svg(ELEMENTS[:1], (419, 343, 417, 400)),
        "naxi-wordmark.svg": svg(ELEMENTS[1:], (373, 746, 508, 157)),
        "naxi-monochrome.svg": svg(ELEMENTS, (365, 343, 524, 568), monochrome=DARK),
    }
    for name, content in exports.items():
        (ROOT / "svg" / name).write_text(content, encoding="utf-8")
    data = []
    for element in ELEMENTS:
        entry = {key: value for key, value in element.items() if key != "paths"}
        entry["paths"] = [path.ae() for path in element["paths"]]
        data.append(entry)
    (ROOT / "source" / "geometry.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    template = (ROOT / "source" / "after-effects-template.jsx").read_text(encoding="utf-8")
    (ROOT / "after-effects" / "NAXI-Shape-Layers.jsx").write_text(
        template.replace("/* GEOMETRY */", "var elements = " + json.dumps(data, separators=(",", ":")) + ";"),
        encoding="utf-8")
    print("Built six SVG files and the self-contained After Effects importer.")


if __name__ == "__main__":
    build()
