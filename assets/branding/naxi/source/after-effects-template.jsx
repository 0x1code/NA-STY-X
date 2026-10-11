/* NAXI vector master. Creates editable shapes in the current project. */
(function () {
    app.beginUndoGroup("NAXI - Create vector master");
    try {
        if (!app.project) app.newProject();
        /* GEOMETRY */
        var folder = app.project.items.addFolder("NAXI - Vector master");
        var comp = app.project.items.addComp("NAXI - Master", 1254, 1254, 1, 4, 30);
        comp.parentFolder = folder;
        comp.bgColor = [32/255, 34/255, 34/255];

        function rgb(hex) {
            return [parseInt(hex.substr(1, 2), 16)/255,
                    parseInt(hex.substr(3, 2), 16)/255,
                    parseInt(hex.substr(5, 2), 16)/255];
        }
        function shapePath(group, definition, name) {
            var prop = group.addProperty("ADBE Vector Shape - Group");
            prop.name = name;
            var shape = new Shape();
            shape.vertices = definition.vertices;
            shape.inTangents = definition.inTangents;
            shape.outTangents = definition.outTangents;
            shape.closed = definition.closed;
            prop.property("ADBE Vector Shape").setValue(shape);
        }
        function createElement(element) {
            var layer = comp.layers.addShape();
            layer.name = element.name;
            layer.property("ADBE Transform Group").property("ADBE Anchor Point").setValue(element.anchor);
            layer.property("ADBE Transform Group").property("ADBE Position").setValue(element.anchor);
            var group = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
            group.name = element.id;
            var contents = group.property("ADBE Vectors Group");
            for (var p = 0; p < element.paths.length; p++) {
                shapePath(contents, element.paths[p], element.names[p]);
            }
            var fill = contents.addProperty("ADBE Vector Graphic - Fill");
            fill.property("ADBE Vector Fill Color").setValue(rgb(element.color));
            fill.property("ADBE Vector Fill Rule").setValue(element.evenOdd ? 2 : 1);
            return layer;
        }
        var background = comp.layers.addShape();
        background.name = "Background - optional";
        background.property("ADBE Transform Group").property("ADBE Position").setValue([0, 0]);
        var bg = background.property("ADBE Root Vectors Group");
        var rect = bg.addProperty("ADBE Vector Shape - Rect");
        rect.property("ADBE Vector Rect Size").setValue([1254, 1254]);
        rect.property("ADBE Vector Rect Position").setValue([627, 627]);
        var bgFill = bg.addProperty("ADBE Vector Graphic - Fill");
        bgFill.property("ADBE Vector Fill Color").setValue(rgb("#202222"));

        var control = comp.layers.addNull();
        control.name = "NAXI - Controls";
        control.source.parentFolder = folder;
        control.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([0, 0]);
        control.property("ADBE Transform Group").property("ADBE Position").setValue([627, 627]);
        for (var i = elements.length - 1; i >= 0; i--) {
            var layer = createElement(elements[i]);
            layer.parent = control;
        }
        control.moveToBeginning();
        background.moveToEnd();
        background.locked = true;
        $.global.NAXI_MASTER_COMP = comp;
        if (!$.global.NAXI_BATCH_EXPORT) comp.openInViewer();
    } finally {
        app.endUndoGroup();
    }
})();
