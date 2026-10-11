/* NAXI vector master. Creates editable shapes in the current project. */
(function () {
    app.beginUndoGroup("NAXI - Create vector master");
    try {
        if (!app.project) app.newProject();
        var elements = [{"id":"mark","name":"Mark - N","color":"#57F4B4","anchor":[627.5,543],"evenOdd":true,"names":["Body","Circular counter"],"paths":[{"vertices":[[451,434],[511,375],[559,396],[727,560],[707,555],[676,588],[708,622],[750,578],[716,503],[697,483],[686,454],[686,434],[745,375],[804,434],[804,653],[746,711],[700,687],[551,498],[506,487],[501,531],[554,593],[564,621],[564,654],[507,711],[451,654]],"inTangents":[[0,0],[-32,0],[-14,-14],[0,0],[7,-1],[0,-19],[-18,0],[-4,23],[22,23],[0,0],[0,12],[0,0],[-33,0],[0,-33],[0,0],[32,0],[12,17],[0,0],[15,-10],[-11,-14],[0,0],[0,-13],[0,0],[31,0],[0,32]],"outTangents":[[0,-33],[19,0],[0,0],[-6,-3],[-18,0],[0,19],[22,0],[4,-30],[0,0],[-8,-8],[0,0],[0,-33],[33,0],[0,0],[0,33],[-19,0],[0,0],[-11,-16],[-15,10],[0,0],[7,9],[0,0],[0,32],[-31,0],[0,0]],"closed":true},{"vertices":[[528,397],[494,431],[528,465],[562,431]],"inTangents":[[18.777681494246963,0],[0,-18.777681494246963],[-18.777681494246963,0],[0,18.777681494246963]],"outTangents":[[-18.777681494246963,0],[0,18.777681494246963],[18.777681494246963,0],[0,-18.777681494246963]],"closed":true}]},{"id":"letter-n","name":"Wordmark - N","color":"#F8F7F5","anchor":[454.5,824],"evenOdd":false,"names":["N outline"],"paths":[{"vertices":[[408,878],[397,867],[397,789],[415,770],[431,779],[489,848],[489,782],[500,770],[512,782],[512,861],[495,878],[479,871],[420,802],[420,867]],"inTangents":[[7,0],[0,6],[0,0],[-11,0],[-5,-6],[0,0],[0,0],[-6,0],[0,-7],[0,0],[10,0],[5,5],[0,0],[0,0]],"outTangents":[[-6,0],[0,0],[0,-11],[6,0],[0,0],[0,0],[0,-7],[7,0],[0,0],[0,10],[-6,0],[0,0],[0,0],[0,6]],"closed":true}]},{"id":"letter-a","name":"Wordmark - A","color":"#F8F7F5","anchor":[602,824],"evenOdd":false,"names":["A outline"],"paths":[{"vertices":[[543,862],[581,784],[602,770],[623,784],[662,862],[656,878],[640,872],[604,796],[600,796],[564,872],[548,878]],"inTangents":[[-3,6],[0,0],[-9,0],[-4,-9],[0,0],[6,-3],[3,6],[0,0],[1,-3],[0,0],[6,3]],"outTangents":[[0,0],[5,-9],[9,0],[0,0],[3,6],[-6,3],[0,0],[-1,-3],[0,0],[-3,6],[-6,-3]],"closed":true}]},{"id":"letter-x","name":"Wordmark - X","color":"#F8F7F5","anchor":[745,824],"evenOdd":false,"names":["X descending","X ascending"],"paths":[{"vertices":[[697.7001670628576,789.4600736941014],[779.7001670628576,874.9600736941014],[795.9600736941014,875.2998329371424],[796.2998329371424,859.0399263058986],[714.2998329371424,773.5399263058986],[698.0399263058986,773.2001670628576]],"inTangents":[[-4.3962273087814765,-4.583871157327053],[0,0],[-4.583871157327053,4.3962273087814765],[4.3962273087814765,4.583871157327053],[0,0],[4.583871157327053,-4.3962273087814765]],"outTangents":[[0,0],[4.3962273087814765,4.583871157327053],[4.583871157327053,-4.3962273087814765],[0,0],[-4.3962273087814765,-4.583871157327053],[-4.583871157327053,4.3962273087814765]],"closed":true},{"vertices":[[774.651544135083,773.590936549026],[693.651544135083,859.090936549026],[694.090936549026,875.348455864917],[710.348455864917,874.909063450974],[791.348455864917,789.409063450974],[790.909063450974,773.151544135083]],"inTangents":[[4.36805512941703,-4.610724858829144],[0,0],[-4.610724858829144,-4.36805512941703],[-4.36805512941703,4.610724858829144],[0,0],[4.610724858829144,4.36805512941703]],"outTangents":[[0,0],[-4.36805512941703,4.610724858829144],[4.610724858829144,4.36805512941703],[0,0],[4.36805512941703,-4.610724858829144],[-4.610724858829144,-4.36805512941703]],"closed":true}]},{"id":"letter-i","name":"Wordmark - I","color":"#F8F7F5","anchor":[845.5,824],"evenOdd":false,"names":["I outline"],"paths":[{"vertices":[[834.0,781.5],[834.0,867.0],[845.5,878.5],[857.0,867.0],[857.0,781.5],[845.5,770.0]],"inTangents":[[0.0,-6.35127462305411],[0,0],[-6.35127462305411,0.0],[0.0,6.35127462305411],[0,0],[6.35127462305411,0.0]],"outTangents":[[0,0],[0.0,6.35127462305411],[6.35127462305411,0.0],[0,0],[0.0,-6.35127462305411],[-6.35127462305411,0.0]],"closed":true}]}];
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
