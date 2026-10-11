/* Editable vector animation import. NAXI_DATA is embedded above this template. */
(function () {
    var data = NAXI_DATA;
    var fps = data.fr;
    function shapeValue(value) {
        if (value instanceof Array) value = value[0];
        var shape = new Shape();
        shape.vertices = value.v;
        shape.inTangents = value.i;
        shape.outTangents = value.o;
        shape.closed = value.c;
        return shape;
    }
    function converted(value, kind) {
        if (kind === 'shape') return shapeValue(value);
        if (kind === 'scalar') return value instanceof Array ? value[0] : value;
        if (kind === 'color') return [value[0], value[1], value[2], value.length > 3 ? value[3] : 1];
        if (kind === '3d') return [value[0], value[1], value.length > 2 ? value[2] : 0];
        if (kind === 'scale3d') return [value[0], value[1], value.length > 2 ? value[2] : 100];
        if (kind === '2d') return [value[0], value[1]];
        return value;
    }
    function component(value) { return value instanceof Array ? value[0] : value; }
    function isLinear(key) {
        if (!key || !key.i || !key.o) return true;
        return Math.abs(component(key.i.x) - component(key.i.y)) < 0.00001 &&
               Math.abs(component(key.o.x) - component(key.o.y)) < 0.00001;
    }
    function easeDimensions(property) {
        if (property.propertyValueType === PropertyValueType.TwoD_SPATIAL || property.propertyValueType === PropertyValueType.ThreeD_SPATIAL) return 1;
        if (property.propertyValueType === PropertyValueType.TwoD) return 2;
        if (property.propertyValueType === PropertyValueType.ThreeD) return 3;
        return 1;
    }
    function propertyValue(property, source, kind) {
        if (!source) return;
        if (!source.a) { property.setValue(converted(source.k, kind)); return; }
        var keys = source.k, i, j;
        for (i = 0; i < keys.length; i++) {
            if (keys[i].s !== undefined) property.setValueAtTime(keys[i].t / fps, converted(keys[i].s, kind));
        }
        for (i = 1; i <= property.numKeys; i++) {
            var prior = i > 1 ? keys[i - 2] : null;
            var current = keys[i - 1];
            var incoming = prior && !isLinear(prior) ? KeyframeInterpolationType.BEZIER : KeyframeInterpolationType.LINEAR;
            var outgoing = current.h === 1 ? KeyframeInterpolationType.HOLD :
                (!isLinear(current) ? KeyframeInterpolationType.BEZIER : KeyframeInterpolationType.LINEAR);
            if (prior && prior.h === 1) incoming = KeyframeInterpolationType.HOLD;
            property.setInterpolationTypeAtKey(i, incoming, outgoing);
            if (incoming === KeyframeInterpolationType.BEZIER || outgoing === KeyframeInterpolationType.BEZIER) {
                var easeIn = [], easeOut = [];
                for (j = 0; j < easeDimensions(property); j++) {
                    easeIn.push(new KeyframeEase(0, 33.333333));
                    easeOut.push(new KeyframeEase(0, 33.333333));
                }
                property.setTemporalEaseAtKey(i, easeIn, easeOut);
                property.setTemporalAutoBezierAtKey(i, false);
            }
            if (property.propertyValueType === PropertyValueType.TwoD_SPATIAL || property.propertyValueType === PropertyValueType.ThreeD_SPATIAL) {
                property.setSpatialAutoBezierAtKey(i, false);
                var zero = property.propertyValueType === PropertyValueType.ThreeD_SPATIAL ? [0, 0, 0] : [0, 0];
                property.setSpatialTangentsAtKey(i, zero, zero);
            }
        }
    }
    function transform(group, source, vector) {
        var prefix = vector ? 'ADBE Vector ' : 'ADBE ';
        propertyValue(group.property(vector ? 'ADBE Vector Anchor' : 'ADBE Anchor Point'), source.a, vector ? '2d' : '3d');
        propertyValue(group.property(prefix + 'Position'), source.p, vector ? '2d' : '3d');
        propertyValue(group.property(prefix + 'Scale'), source.s, vector ? '2d' : 'scale3d');
        propertyValue(group.property(vector ? 'ADBE Vector Rotation' : 'ADBE Rotate Z'), source.r, 'scalar');
        propertyValue(group.property(vector ? 'ADBE Vector Group Opacity' : 'ADBE Opacity'), source.o, 'scalar');
    }
    function contents(group, items) {
        for (var n = 0; n < items.length; n++) {
            var item = items[n], entry;
            if (item.ty === 'gr') {
                entry = group.addProperty('ADBE Vector Group');
                entry.name = item.nm || 'Vector group';
                contents(entry.property('ADBE Vectors Group'), item.it);
                for (var t = 0; t < item.it.length; t++) {
                    if (item.it[t].ty === 'tr') transform(entry.property('ADBE Vector Transform Group'), item.it[t], true);
                }
            } else if (item.ty === 'sh') {
                entry = group.addProperty('ADBE Vector Shape - Group');
                entry.name = item.nm || 'Contour';
                propertyValue(entry.property('ADBE Vector Shape'), item.ks, 'shape');
            } else if (item.ty === 'el') {
                entry = group.addProperty('ADBE Vector Shape - Ellipse');
                entry.name = item.nm || 'Circle';
                propertyValue(entry.property('ADBE Vector Ellipse Position'), item.p, '2d');
                propertyValue(entry.property('ADBE Vector Ellipse Size'), item.s, '2d');
            } else if (item.ty === 'fl') {
                entry = group.addProperty('ADBE Vector Graphic - Fill');
                entry.name = item.nm || 'Fill';
                propertyValue(entry.property('ADBE Vector Fill Color'), item.c, 'color');
                propertyValue(entry.property('ADBE Vector Fill Opacity'), item.o, 'scalar');
                if (item.r) entry.property('ADBE Vector Fill Rule').setValue(item.r);
            } else if (item.ty === 'st') {
                entry = group.addProperty('ADBE Vector Graphic - Stroke');
                entry.name = item.nm || 'Stroke';
                propertyValue(entry.property('ADBE Vector Stroke Color'), item.c, 'color');
                propertyValue(entry.property('ADBE Vector Stroke Opacity'), item.o, 'scalar');
                propertyValue(entry.property('ADBE Vector Stroke Width'), item.w, 'scalar');
                entry.property('ADBE Vector Stroke Line Cap').setValue(item.lc || 2);
                entry.property('ADBE Vector Stroke Line Join').setValue(item.lj || 2);
            } else if (item.ty === 'tm') {
                entry = group.addProperty('ADBE Vector Filter - Trim');
                entry.name = item.nm || 'Draw';
                propertyValue(entry.property('ADBE Vector Trim Start'), item.s, 'scalar');
                propertyValue(entry.property('ADBE Vector Trim End'), item.e, 'scalar');
                propertyValue(entry.property('ADBE Vector Trim Offset'), item.o, 'scalar');
                entry.property('ADBE Vector Trim Type').setValue(item.m || 1);
            }
        }
    }
    app.beginUndoGroup('NAXI vector animation');
    try {
        if (!app.project) app.newProject();
        var comp = app.project.items.addComp('NAXI - Intro', data.w, data.h, 1, (data.op - data.ip) / fps, fps);
        comp.bgColor = [0.12549, 0.13333, 0.12941];
        for (var l = data.layers.length - 1; l >= 0; l--) {
            var source = data.layers[l];
            if (source.ty !== 4) throw new Error('Unsupported layer: ' + source.nm);
            var layer = comp.layers.addShape();
            layer.name = source.nm || ('Vector ' + source.ind);
            layer.startTime = (source.st || 0) / fps;
            layer.inPoint = source.ip / fps;
            layer.outPoint = source.op / fps;
            transform(layer.property('ADBE Transform Group'), source.ks, false);
            contents(layer.property('ADBE Root Vectors Group'), source.shapes);
            var masks = source.masksProperties || source.maskProperties || [];
            for (var m = 0; m < masks.length; m++) {
                var mask = layer.property('ADBE Mask Parade').addProperty('ADBE Mask Atom');
                mask.name = masks[m].nm || ('Aperture ' + (m + 1));
                mask.maskMode = masks[m].mode === 's' ? MaskMode.SUBTRACT : MaskMode.ADD;
                mask.inverted = !!masks[m].inv;
                propertyValue(mask.property('ADBE Mask Shape'), masks[m].pt, 'shape');
                propertyValue(mask.property('ADBE Mask Opacity'), masks[m].o, 'scalar');
                propertyValue(mask.property('ADBE Mask Offset'), masks[m].x, 'scalar');
            }
        }
        comp.time = (data.op - 10) / fps;
        $.global.NAXI_ANIM_COMP = comp;
        if (!$.global.NAXI_BATCH_EXPORT) comp.openInViewer();
    } finally {
        app.endUndoGroup();
    }
})();
