/* Run in a dedicated empty After Effects instance. */
(function () {
    var sourceDir = File($.fileName).parent;
    var outputDir = Folder(sourceDir.fsName + '/../after-effects');
    if (!outputDir.exists) outputDir.create();
    var log = File(outputDir.fsName + '/batch-export-status.txt');
    function status(message) {
        log.open('w');
        log.write(message);
        log.close();
    }
    try {
        if (app.project && app.project.numItems > 0) throw new Error('Batch export requires an empty project.');
        $.global.NAXI_BATCH_EXPORT = true;
        $.evalFile(File(outputDir.fsName + '/NAXI-Intro.jsx'));
        var comp = $.global.NAXI_ANIM_COMP;
        if (!comp) throw new Error('Animation composition was not created.');
        app.project.save(File(outputDir.fsName + '/NAXI-Intro.aep'));
        comp.saveFrameToPng(comp.time, File(outputDir.fsName + '/NAXI-Intro-final.png'));
        status('SUCCESS\nNative editable AEP saved. Final settled frame exported at '+comp.time+' seconds.');
    } catch (error) {
        status('ERROR\n' + error.toString() + '\nLine: ' + error.line);
        throw error;
    } finally {
        $.global.NAXI_BATCH_EXPORT = false;
    }
})();
