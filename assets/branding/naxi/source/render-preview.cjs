// Render the SVG exports; requires the sharp package.
const sharp = require('sharp');
const path = require('path');
const root = path.resolve(__dirname, '..');
(async function () {
  await sharp(path.join(root, 'svg', 'naxi-on-dark.svg'))
    .png().toFile(path.join(root, 'preview', 'naxi-vector-preview.png'));
  await sharp(path.join(root, 'svg', 'naxi-master.svg'))
    .png().toFile(path.join(root, 'preview', 'naxi-transparent.png'));
  await sharp(path.join(root, 'svg', 'naxi-mark.svg'))
    .resize(256, 256, {fit: 'contain', background: '#202222'})
    .png().toFile(path.join(root, 'preview', 'naxi-icon-256.png'));
  console.log('Rendered the actual SVG files to PNG.');
})().catch(error => { console.error(error); process.exitCode = 1; });
