"""Generate the native NAXI Lottie motion identity from vector geometry."""

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS, END = 60, 460
MINT, WHITE, DARK = '#57F4B4', '#F8F7F5', '#202222'
GEOMETRY = json.loads((ROOT / 'source/geometry.json').read_text())


def color(value):
    return [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]


def fixed(value):
    return {'a': 0, 'k': value}


def animated(points, linear=False):
    frames = []
    for index, (time, value) in enumerate(points):
        scalar = isinstance(value, (int, float))
        shape = isinstance(value, dict)
        packed = [value] if scalar or shape else value
        key = {'t': time, 's': packed}
        if index < len(points)-1:
            target = points[index+1][1]
            key['e'] = [target] if scalar or shape else target
            key['o'] = {'x': [1/3], 'y': [1/3 if linear else 0]}
            key['i'] = {'x': [2/3], 'y': [2/3 if linear else 1]}
        frames.append(key)
    return {'a': 1, 'k': frames}


def shape(ae):
    return {'v': ae['vertices'], 'i': ae['inTangents'], 'o': ae['outTangents'], 'c': ae['closed']}


def path(vertices, closed=False):
    return {'v': vertices, 'i': [[0, 0] for _ in vertices],
            'o': [[0, 0] for _ in vertices], 'c': closed}


def circle(cx, cy, radius):
    k = radius * .5522847498
    return {'v': [[cx, cy-radius], [cx+radius, cy], [cx, cy+radius], [cx-radius, cy]],
            'i': [[-k, 0], [0, -k], [k, 0], [0, k]],
            'o': [[k, 0], [0, k], [-k, 0], [0, -k]], 'c': True}


def capsule(a, b, radius):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    u = [dx/length, dy/length] if length > 1e-5 else [0, 1]
    n = [-u[1], u[0]]
    def point(base, along, normal):
        return [base[i]+along*u[i]+normal*n[i] for i in range(2)]
    k = radius*.5522847498
    vertices = [point(a, 0, radius), point(b, 0, radius), point(b, radius, 0),
                point(b, 0, -radius), point(a, 0, -radius), point(a, -radius, 0)]
    incoming = [point([0, 0], -k, 0), [0, 0], point([0, 0], 0, k),
                point([0, 0], k, 0), [0, 0], point([0, 0], 0, -k)]
    outgoing = [[0, 0], point([0, 0], k, 0), point([0, 0], 0, -k),
                [0, 0], point([0, 0], -k, 0), point([0, 0], 0, k)]
    return {'v': vertices, 'i': incoming, 'o': outgoing, 'c': True}


def transform(anchor=(0, 0), position=None, scale=None, rotation=None, opacity=None):
    position = position if position is not None else fixed([*anchor, 0])
    return {'a': fixed([*anchor, 0]), 'p': position, 's': scale or fixed([100, 100, 100]),
            'r': rotation or fixed(0), 'o': opacity or fixed(100)}


def group(items, name):
    return {'ty': 'gr', 'nm': name, 'it': items + [
        {'ty': 'tr', 'p': fixed([0, 0]), 'a': fixed([0, 0]), 's': fixed([100, 100]),
         'r': fixed(0), 'o': fixed(100), 'sk': fixed(0), 'sa': fixed(0)}]}


def fill(hexcolor, rule=1):
    return {'ty': 'fl', 'nm': 'Fill', 'c': fixed(color(hexcolor)), 'o': fixed(100), 'r': rule}


def vector_layer(name, items, anchor=(0, 0), ip=0, op=END, **transforms):
    return {'ddd': 0, 'ty': 4, 'nm': name, 'sr': 1, 'ks': transform(anchor, **transforms),
            'ao': 0, 'shapes': [group(items, name)], 'ip': ip, 'op': op, 'st': 0, 'bm': 0}


def mask(name, mode, data):
    return {'nm': name, 'mode': mode, 'inv': False, 'pt': data, 'o': fixed(100), 'x': fixed(0)}


def artwork(element, ip=0, op=END, **transforms):
    paths = [{'ty': 'sh', 'nm': name, 'ks': fixed(shape(outline))}
             for outline, name in zip(element['paths'], element['names'])]
    return vector_layer(element['name'], paths+[fill(element['color'], 2 if element['evenOdd'] else 1)],
                        element['anchor'], ip, op, **transforms)


def smooth(u):
    u = max(0, min(1, u))
    return u*u*(3-2*u)


def mix(a, b, u):
    return [x+(y-x)*u for x, y in zip(a, b)]


def orbit_position(frame, second=False):
    u = max(0, min(1, frame/54))
    angle = (0.08 if second else math.pi) + (-1 if second else 1)*math.tau*u
    tilt = .27 if second else -.27
    px, py = 180*math.cos(angle), 115*math.sin(angle)
    position = [627.5+px*math.cos(tilt)-py*math.sin(tilt),
                543+px*math.sin(tilt)+py*math.cos(tilt)]
    if frame >= 44:
        position = mix(position, [746, 653] if second else [511, 434], smooth((frame-44)/22))
    return [*position, 0]


def orb(second=False):
    positions = [(f, orbit_position(min(f, 66), second)) for f in range(0, 85)]
    return vector_layer('Orbit - clockwise' if not second else 'Orbit - counterclockwise',
                        [{'ty': 'el', 'nm': 'Circle', 'p': fixed([0, 0]), 's': fixed([68, 68])}, fill(MINT)],
                        ip=0, op=85, position=animated(positions, True),
                        opacity=animated([(0, 100), (66, 100), (84, 0)]),
                        scale=animated([(0, [25, 25, 100]), (9, [108, 108, 100]),
                                        (15, [100, 100, 100]), (44, [100, 100, 100]),
                                        (66, [174, 174, 100])]))


def main_mark():
    final_body = shape(GEOMETRY[0]['paths'][0])
    sealed_body = copy.deepcopy(final_body)
    # The right inner opening is cut only after the N has grown together.
    for index in range(3, 11):
        sealed_body['v'][index] = mix([559, 396], [686, 434], (index-2)/9)
        sealed_body['i'][index] = [0, 0]
        sealed_body['o'][index] = [0, 0]
    sealed_body['o'][2] = [0, 0]
    sealed_body['i'][11] = [0, 0]
    layer = vector_layer('Mark - growing N', [
        {'ty': 'sh', 'nm': 'Body - opening releases the flying dot',
         'ks': animated([(65, sealed_body), (100, sealed_body), (114, final_body)])}, fill(MINT)],
        anchor=(627.5, 543), ip=65,
        scale=animated([(0, [100, 100, 100]), (320, [100, 100, 100]),
                        (342, [112, 90, 100]), (360, [94, 106, 100]),
                        (377, [103, 97, 100]), (393, [99, 101, 100]), (408, [100, 100, 100])]),
        rotation=animated([(0, 0), (320, 0), (342, -2.4), (360, 1.4), (377, -.4), (408, 0)]))
    for prop in ('s', 'r'):
        for key in layer['ks'][prop]['k']:
            if key['t'] >= 295:
                key['t'] += 16
    layer['hasMask'] = True
    layer['masksProperties'] = [
        mask('Reveal - left round cap grows downward', 'a', animated([
            (65, capsule([511, 434], [511, 434.01], 66)),
            (96, capsule([511, 434], [507, 654], 66))])),
        mask('Reveal - right round cap grows upward', 'a', animated([
            (65, capsule([746, 653], [746, 652.99], 66)),
            (96, capsule([746, 653], [745, 434], 66))])),
        mask('Reveal - diagonal joins the caps', 'a', animated([
            (75, capsule([511, 434], [511.01, 434.01], .01)),
            (82, capsule([511, 434], [564, 483], 66)),
            (110, capsule([511, 434], [746, 653], 70))])),
        mask('Counter - travels from lower notch to upper circle', 's', animated([
            (0, circle(708, 588, 34)), (311, circle(708, 588, 34)),
            (325, circle(653, 542, 34)), (342, circle(519, 423, 34)),
            (351, circle(531, 433, 34)), (360, circle(528, 431, 34))]))]
    layer['masksProperties'][-1]['o'] = animated([(0, 0), (100, 0), (114, 100)])
    return layer


def cubic(a, b, c, d, u):
    return [(1-u)**3*a[i]+3*(1-u)**2*u*b[i]+3*(1-u)*u*u*c[i]+u**3*d[i] for i in range(2)]


def sampled_path(data):
    samples = [data['v'][0]]
    for index in range(len(data['v'])-1):
        start, end = data['v'][index:index+2]
        c1 = [start[i]+data['o'][index][i] for i in range(2)]
        c2 = [end[i]+data['i'][index+1][i] for i in range(2)]
        samples += [cubic(start, c1, c2, end, step/80) for step in range(1, 81)]
    cumulative = [0]
    for a, b in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1]+math.dist(a, b))
    def at(u):
        target = max(0, min(1, u))*cumulative[-1]
        for index in range(1, len(samples)):
            if cumulative[index] >= target:
                distance = cumulative[index]-cumulative[index-1]
                return mix(samples[index-1], samples[index], (target-cumulative[index-1])/max(distance, 1e-9))
        return samples[-1]
    return at


# Open centerlines: the stylus travels at the same eased arc-length as trim paths.
nline = path([[408.5, 867], [408.5, 789], [419, 786], [491, 862], [500.5, 861], [500.5, 781.5]])
nline['o'][1], nline['i'][2] = [0, -8], [-7, -9]
nline['o'][3], nline['i'][4] = [5, 6], [0, 7]
aline = path([[553, 867], [592, 790], [612, 790], [652, 867]])
aline['o'][1], aline['i'][2] = [5, -12], [-5, -12]
STROKES = [
    ('N', nline, 114, 151), ('A', aline, 164, 199),
    ('X - first stroke', path([[706, 781.5], [788, 867]]), 211, 230),
    ('X - second stroke', path([[783, 781.5], [702, 867]]), 241, 260),
    ('I', path([[845.5, 867], [845.5, 781.5]]), 272, 288)]
STROKES = [(name, line, start+16, end+16) for name, line, start, end in STROKES]


def writing_layers():
    layers = []
    exact_starts = {'N': 167, 'A': 215, 'X': 276, 'I': 304}
    for name, line, start, end in STROKES:
        finish = exact_starts[name[0]]
        layers.append(vector_layer('Draw - '+name, [
            {'ty': 'sh', 'nm': 'Pen centerline', 'ks': fixed(line)},
            {'ty': 'st', 'nm': 'White ink', 'c': fixed(color(WHITE)), 'o': fixed(100),
             'w': fixed(23), 'lc': 2, 'lj': 2, 'ml': 4},
            {'ty': 'tm', 'nm': 'Write on', 's': fixed(0),
             'e': animated([(start, 0), (end, 100)]), 'o': fixed(0), 'm': 1}],
            ip=start, op=finish+1))
    for element in GEOMETRY[1:]:
        layers.append(artwork(element, ip=exact_starts[element['name'][-1]]))
    return layers


def writer():
    ranges = [(name, line, start-16, end-16, sampled_path(line)) for name, line, start, end in STROKES]
    def location(frame):
        if frame < 114:
            u = smooth((frame-101)/13)
            xy = mix([708, 588], ranges[0][1]['v'][0], u)
            xy[1] -= 90*math.sin(math.pi*u)
            return xy
        for index, (name, line, start, end, at) in enumerate(ranges):
            if frame <= end:
                return at(smooth((frame-start)/(end-start)))
            if index < len(ranges)-1 and frame < ranges[index+1][2]:
                nxt = ranges[index+1]
                u = (frame-end)/(nxt[2]-end)
                xy = mix(line['v'][-1], nxt[1]['v'][0], smooth(u))
                xy[1] -= 60*math.sin(math.pi*u)
                return xy
        u = smooth((frame-288)/10)
        xy = mix(ranges[-1][1]['v'][-1], [708, 588], u)
        xy[0] += 45*math.sin(math.pi*u)
        return xy
    pos = animated([(f+16, [*location(f), 0]) for f in range(101, 299)], True)
    scale_keys = [(101, [150, 150, 100]), (107, [75, 130, 100]), (114, [125, 72, 100]), (118, [100, 100, 100])]
    for start in [164, 211, 241, 272]:
        scale_keys += [(start-5, [78, 128, 100]), (start, [125, 72, 100]), (start+4, [100, 100, 100])]
    scale_keys += [(288, [100, 100, 100]), (297, [283.33, 283.33, 100])]
    return vector_layer('Dot - writes and returns to the notch', [
        {'ty': 'el', 'nm': 'Stylus dot', 'p': fixed([0, 0]), 's': fixed([24, 24])}, fill(MINT)],
        ip=117, op=315, position=pos, scale=animated([(f+16, value) for f, value in scale_keys]),
        opacity=animated([(117, 100), (311, 100), (315, 0)], True))


def document(layers, duration=END, name='NAXI - Intro'):
    for index, layer in enumerate(layers, 1):
        layer['ind'] = index
    return {'v': '5.13.0', 'fr': FPS, 'ip': 0, 'op': duration, 'w': 1254, 'h': 1254,
            'nm': name, 'ddd': 0, 'assets': [], 'layers': layers,
            'markers': [{'tm': 0, 'cm': 'Opposing orbits', 'dr': 65},
                        {'tm': 65, 'cm': 'Build N', 'dr': 49},
                        {'tm': 114, 'cm': 'Opening releases the flying dot', 'dr': 16},
                        {'tm': 130, 'cm': 'Dot writes NAXI', 'dr': 185},
                        {'tm': 311, 'cm': 'Counter travels and N settles', 'dr': 113},
                        {'tm': 424, 'cm': 'Final hold', 'dr': 36}] if duration == END else []}


def with_background(data):
    result = copy.deepcopy(data)
    layer = vector_layer('Background - graphite', [
        {'ty': 'rc', 'nm': 'Background', 'p': fixed([627, 627]),
         's': fixed([1254, 1254]), 'r': fixed(0)}, fill(DARK)], op=data['op'])
    layer['ind'] = len(result['layers'])+1
    result['layers'].append(layer)
    return result


def build():
    for folder in ('assets', 'after-effects', 'qa', 'renders'):
        (ROOT/folder).mkdir(exist_ok=True)
    intro = document([writer(), *writing_layers(), main_mark(), orb(), orb(True)])
    idle_layers = [artwork(element, op=144) for element in GEOMETRY]
    idle_layers[0]['ks']['s'] = animated([(0, [100, 100, 100]), (36, [102, 98.5, 100]),
                                        (72, [100, 100, 100]), (108, [98.5, 102, 100]),
                                        (144, [100, 100, 100])])
    idle = document(idle_layers, 144, 'NAXI - Idle loop')
    for name, data in [('naxi-intro.json', intro), ('naxi-intro-dark.json', with_background(intro)),
                       ('naxi-idle.json', idle), ('naxi-idle-dark.json', with_background(idle))]:
        (ROOT/'assets'/name).write_text(json.dumps(data, separators=(',', ':'), allow_nan=False)+'\n', encoding='utf-8')
        print(name, len(data['layers']), 'layers', (ROOT/'assets'/name).stat().st_size, 'bytes')
    template = ROOT/'source/ae-import-template.jsx'
    for filename, variable, data in [('intro-data.js', 'NAXI_ANIMATION', intro), ('idle-data.js', 'NAXI_IDLE', idle)]:
        (ROOT/'assets'/filename).write_text('window.'+variable+'='+json.dumps(data,separators=(',', ':'))+';\n', encoding='utf-8')
    if template.exists():
        (ROOT/'after-effects/NAXI-Intro.jsx').write_text(
            'var NAXI_DATA = '+json.dumps(with_background(intro), separators=(',', ':'))+';\n'+template.read_text(),
            encoding='utf-8')


if __name__ == '__main__':
    build()
