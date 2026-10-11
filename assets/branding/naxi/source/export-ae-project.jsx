/* Run only in a dedicated After Effects batch instance. */
(function () {
    var root = File($.fileName).parent.parent;
    function report(text) {
        var file = File(root.fsName + "/preview/ae-export-status.txt");
        if (file.open("w")) { file.writeln(text); file.close(); }
    }
    app.beginSuppressDialogs();
    try {
        report("Started After Effects " + app.version);
        if (app.project && (app.project.numItems > 0 || app.project.dirty)) {
            throw new Error("Batch export requires an empty project.");
        }
        $.global.NAXI_BATCH_EXPORT = true;
        $.evalFile(File(root.fsName + "/after-effects/NAXI-Shape-Layers.jsx"));
        var comp = $.global.NAXI_MASTER_COMP;
        app.project.bitsPerChannel = 8;
        app.project.save(File(root.fsName + "/after-effects/NAXI-Master.aep"));
        comp.saveFrameToPng(0, File(root.fsName + "/preview/naxi-ae-preview.png"));
        report("NAXI_EXPORT_OK: " + app.version + "; " + comp.numLayers + " layers");
        $.writeln("NAXI_EXPORT_OK: " + comp.numLayers + " layers");
        app.exitCode = 0;
    } catch (error) {
        try { report("NAXI_EXPORT_ERROR: " + error.toString() + " at line " + error.line); } catch (ignored) {}
        $.writeln("NAXI_EXPORT_ERROR: " + error.toString() + " at line " + error.line);
        app.exitCode = 1;
    } finally {
        app.endSuppressDialogs(false);
        app.quit();
    }
})();
