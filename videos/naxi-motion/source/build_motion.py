"""Generate the native NAXI Lottie motion identity from vector geometry."""

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS, END = 60, 370
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


def main_mark():
    return artwork(GEOMETRY[0], ip=65,
        opacity=animated([(65, 0), (95, 100)]),
        scale=animated([(65, [92, 92, 100]), (110, [100, 100, 100])]))


def retime_intro(data, offset):
    def keys(node):
        if isinstance(node, dict):
            if 't' in node and 's' in node:
                node['t'] = max(0, node['t']-offset)
            for value in node.values():
                keys(value)
        elif isinstance(node, list):
            for value in node:
                keys(value)
    keys(data)
    data['op'] -= offset
    for layer in data['layers']:
        layer['ip'] = max(0, layer['ip']-offset)
        layer['op'] -= offset
    data['markers'] = [{'tm': 0, 'cm': 'Original N appears', 'dr': 45},
                       {'tm': 52, 'cm': 'Dot writes NAXI', 'dr': 187},
                       {'tm': 239, 'cm': 'I becomes lowercase i', 'dr': 30},
                       {'tm': 269, 'cm': 'Final NAXi hold', 'dr': 36}]
    return data


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
        layer = artwork(element, ip=exact_starts[element['name'][-1]])
        if element['name'].endswith('I'):
            layer['nm'] = 'Wordmark - I shrinks into lowercase i'
            layer['shapes'][0]['it'][0]['ks'] = animated([
                (304, shape(element['paths'][0])), (330, lowercase_i_shape())])
        layers.append(layer)
    return layers


def lowercase_i_shape():
    result = shape(copy.deepcopy(GEOMETRY[-1]['paths'][0]))
    for index in (0, 4):
        result['v'][index][1] = 826
    result['v'][5][1] = 814.5
    return result


def writer():
    ranges = [(name, line, start, end, sampled_path(line)) for name, line, start, end in STROKES]
    def location(frame):
        if frame < 130:
            u = smooth((frame-117)/13)
            xy = mix([340, 965], ranges[0][1]['v'][0], u)
            xy[1] -= 65*math.sin(math.pi*u)
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
        if frame < 312:
            return mix([845.5, 781.5], [845.5, 770], smooth((frame-304)/8))
        if frame < 326:
            return mix([845.5, 770], [845.5, 789], smooth((frame-312)/14))
        return mix([845.5, 789], [845.5, 787], smooth((frame-326)/8))
    pos = animated([(f, [*location(f), 0]) for f in range(117, 335)], True)
    scale_keys = [(101, [150, 150, 100]), (107, [75, 130, 100]), (114, [125, 72, 100]), (118, [100, 100, 100])]
    for start in [164, 211, 241, 272]:
        scale_keys += [(start-5, [78, 128, 100]), (start, [125, 72, 100]), (start+4, [100, 100, 100])]
    scale_keys = [(f+16, value) for f, value in scale_keys]
    scale_keys += [(304, [100, 100, 100]), (312, [90, 110, 100]), (326, [110, 90, 100]), (334, [100, 100, 100])]
    ink = fill(MINT)
    return vector_layer('Dot - writes and becomes the lowercase i dot', [
        {'ty': 'el', 'nm': 'Stylus dot', 'p': fixed([0, 0]), 's': fixed([24, 24])}, ink],
        ip=117, op=END, position=pos, scale=animated(scale_keys),
        opacity=animated([(117, 0), (123, 100)], True))


def document(layers, duration=END, name='NAXI - Intro'):
    for index, layer in enumerate(layers, 1):
        layer['ind'] = index
    return {'v': '5.13.0', 'fr': FPS, 'ip': 0, 'op': duration, 'w': 1254, 'h': 1254,
            'nm': name, 'ddd': 0, 'assets': [], 'layers': layers,
            'markers': [{'tm': 0, 'cm': 'Tornado forms the N', 'dr': 110},
                        {'tm': 65, 'cm': 'Build N', 'dr': 49},
                        {'tm': 117, 'cm': 'Independent dot writes NAXI', 'dr': 187},
                        {'tm': 304, 'cm': 'I shrinks and dot settles into lowercase i', 'dr': 30},
                        {'tm': 334, 'cm': 'Final NAXi hold', 'dr': 36}] if duration == END else []}


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
    intro = retime_intro(document([writer(), *writing_layers(), main_mark()]), 65)
    idle_layers = [artwork(element, op=144) for element in GEOMETRY]
    idle_layers[-1]['shapes'][0]['it'][0]['ks'] = fixed(lowercase_i_shape())
    idle_layers.insert(0, vector_layer('Wordmark - green i dot', [
        {'ty': 'el', 'nm': 'Dot', 'p': fixed([845.5, 787]), 's': fixed([24, 24])}, fill(MINT)], op=144))
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
