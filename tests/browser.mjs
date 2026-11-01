// Optional E2E: node tests/browser.mjs <path-to-playwright> [deployed-page-url]
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import {createServer} from '../server/index.js';
const require=createRequire(import.meta.url),{chromium}=require(process.argv[2]||'playwright');
const remote=process.argv[3],base=remote||'http://localhost:8080';
const server=remote?null:createServer();if(server)await new Promise(r=>server.listen(8080,'127.0.0.1',r));
let browser;
try{
  browser=await chromium.launch({channel:'msedge',headless:true});
  const a=await browser.newContext({viewport:{width:1440,height:1000}}),b=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  if(!remote)for(const context of [a,b])await context.addInitScript(()=>localStorage.setItem('chess-api','http://localhost:8080'));
  const pa=await a.newPage(),pb=await b.newPage(),errors=[];
  for(const page of [pa,pb]){page.setDefaultTimeout(remote?90000:30000);page.on('pageerror',e=>errors.push(e.message));await page.goto(base);}
  assert.equal(await pa.locator('[data-pos]').count(),90);
  if(!remote){await pa.screenshot({path:'web-preview.png',fullPage:true});await pb.screenshot({path:'mobile-preview.png',fullPage:true});}
  assert.ok(await pb.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await pa.click('#online');await pa.waitForFunction(()=>document.querySelector('#connection').textContent.includes('寻找'));
  await pb.click('#online');
  for(const page of [pa,pb])await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('对手在线'));
  assert.ok((await pa.textContent('#mode')).includes('红方'));
  await pa.click('[data-pos="0"]');await pb.waitForFunction(()=>document.querySelector('#count').textContent==='1 步');
  await pb.click('[data-pos="8"]');await pa.waitForFunction(()=>document.querySelector('#count').textContent==='2 步');
  await pa.reload();await pa.click('#online');await pa.waitForFunction(()=>document.querySelector('#count').textContent==='2 步');
  pa.on('dialog',d=>d.accept());await pa.click('#leave');await pb.waitForFunction(()=>document.querySelector('#turn').textContent.includes('黑方获胜'));
  await pb.click('#leave');
  await pa.click('#local');await pa.click('[data-pos="0"]');assert.equal(await pa.textContent('#count'),'1 步');
  assert.deepEqual(errors,[]);console.log('Browser E2E passed: desktop/mobile, match, two moves, reconnect, leave, local play.');
}finally{await browser?.close();if(server){server.closeAllConnections();await new Promise(r=>server.close(r));}}
