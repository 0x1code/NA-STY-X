const fs=require('fs'),path=require('path');
const {chromium}=require('playwright');
const sharp=require('sharp');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1254,height:1254},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<style>body{margin:0;background:#202222}#player{width:1254px;height:1254px}</style><div id="player"></div>');
 await page.addScriptTag({path:path.join(root,'assets/lottie.min.js')});
 await page.evaluate(data=>{window.animation=lottie.loadAnimation({container:document.getElementById('player'),renderer:'svg',loop:false,autoplay:false,animationData:data});animation.setSubframe(false)},JSON.parse(fs.readFileSync(path.join(root,'assets/naxi-intro.json'))));
 await page.waitForFunction(()=>animation.isLoaded);
 const frames=[12,32,52,78,110,160,240,304,335,369,402,420,442,475,561];
 fs.mkdirSync(path.join(root,'qa/frames'),{recursive:true});
 const tiles=[];
 for(const f of frames){await page.evaluate(f=>animation.goToAndStop(f,true),f);const img=await page.screenshot();fs.writeFileSync(path.join(root,'qa/frames',f+'.png'),img);tiles.push(await sharp(img).resize(250,250).png().toBuffer())}
 await sharp({create:{width:1250,height:750,channels:4,background:'#202222'}}).composite(tiles.map((input,i)=>({input,left:(i%5)*250,top:Math.floor(i/5)*250}))).png().toFile(path.join(root,'qa/contact-sheet.png'));
 if(process.argv.includes('--all')){for(let f=0;f<562;f++){await page.evaluate(f=>animation.goToAndStop(f,true),f);await page.screenshot({path:path.join(root,'qa/frames','frame-'+String(f).padStart(4,'0')+'.png')});if(f%60===0)console.log('frame',f)}}
 fs.writeFileSync(path.join(root,'qa/browser-report.json'),JSON.stringify({errors,frames:562,fps:60,duration:562/60,renderer:'lottie-web SVG'},null,2));
 await browser.close();if(errors.length)throw Error(errors.join('\n'));
})();
