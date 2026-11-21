// Browser-only fixtures are injected by the test, never shipped with the game.
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createServer} from '../server/index.js';
const {chromium}=createRequire(import.meta.url)(process.argv[2]||'playwright');
const server=createServer();await new Promise(r=>server.listen(8080,'127.0.0.1',r));
let browser;
try{
  browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1200,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const source=await readFile(new URL('../web/app.js',import.meta.url),'utf8');
  await page.route('**/app.js',route=>route.fulfill({contentType:'text/javascript',body:source+`
globalThis.fixture=(pieces,turn='red')=>{epoch++;clearEffects();clearTimeout(timer);mode='local';busy=false;selected=null;game=new Game();game.board=Array(90).fill(null);for(const [i,kind,side,face=true]of pieces)game.board[i]={kind,side,face};game.turn=turn;game.repetitions=new Map([[game.key(),1]]);state=game.public();render();};
globalThis.networkFixture=(next,side='red',viewMode='online')=>{epoch++;clearEffects();mode=viewMode;online={room:'test-room',side,status:'playing'};connected=true;state={...next,ply:0,result:null};render();return viewMode==='ai'?showState(next):accept({room:'test-room',side,status:'playing',opponentOnline:true,game:next});};
`}));
  await page.goto('http://localhost:8080');
  await page.evaluate(()=>fixture([[85,'K','red'],[4,'K','black'],[40,'P','red',false]]));
  await page.click('[data-pos="40"]');await page.waitForSelector('.reveal-glow');
  assert.ok((await page.getAttribute('[data-pos="40"]','aria-label')).includes('暗棋'));
  await page.waitForTimeout(650);assert.equal(await page.locator('.reveal-glow').count(),1);assert.equal(await page.textContent('#count'),'0 步');
  await page.click('[data-pos="4"]');assert.equal(await page.textContent('#count'),'0 步');
  await page.waitForFunction(()=>document.querySelector('#count').textContent==='1 步');assert.ok((await page.getAttribute('[data-pos="40"]','aria-label')).includes('红方兵'));
  await page.evaluate(()=>fixture([[85,'K','red'],[4,'K','black'],[40,'P','red']]));
  await page.click('[data-pos="40"]');await page.click('#mutate');await page.waitForSelector('.reveal-glow');
  assert.ok((await page.getAttribute('[data-pos="40"]','aria-label')).includes('红方兵'));
  await page.waitForFunction(()=>document.querySelector('#count').textContent==='1 步');assert.equal(await page.locator('.reveal-glow').count(),0);
  await page.evaluate(()=>fixture([[85,'K','red'],[4,'K','black'],[40,'R','red']]));
  await page.click('[data-pos="40"]');await page.click('[data-pos="41"]');await page.waitForSelector('.move-trail');
  assert.equal(await page.locator('.move-trail circle').getAttribute('cx'),'270');
  assert.equal(await page.locator('.move-trail path').getAttribute('marker-end'),'url(#move-arrow)');
  await page.screenshot({path:'move-effect-preview.png'});
  await page.waitForTimeout(2200);assert.equal(await page.locator('.move-trail').count(),1);
  await page.waitForSelector('.move-trail',{state:'detached'});
  // Each online seat sees only its opponent; the human in AI mode always plays red.
  for(const viewMode of ['online','ai'])for(const viewer of viewMode==='ai'?['red']:['red','black'])for(const actor of ['red','black']){
    await page.evaluate(({viewer,actor,viewMode})=>{const next={board:Array(90).fill(null),turn:actor==='red'?'black':'red',ply:1,quiet:1,result:null,last:{kind:'move',src:40,dst:41},history:[]};next.board[41]={face:true,kind:'R',side:actor};return networkFixture(next,viewer,viewMode);},{viewer,actor,viewMode});
    assert.equal(await page.locator('.move-trail').count(),actor===viewer?0:1,`${viewMode}: ${viewer} viewing ${actor}'s move`);
  }
  // In shared-screen mode, handing the turn back hides one's own older trail.
  await page.evaluate(()=>fixture([[85,'K','red'],[4,'K','black'],[40,'R','red']]));
  await page.click('[data-pos="40"]');await page.click('[data-pos="41"]');
  assert.equal(await page.locator('.move-trail').count(),1);
  await page.click('[data-pos="4"]');await page.click('[data-pos="3"]');
  assert.equal(await page.locator('.move-trail').count(),1);
  assert.equal(await page.locator('.move-trail circle').getAttribute('cy'),'30');
  for(const side of ['red','black']){
    const src=side==='red'?13:76,dst=side==='red'?4:85;
    await page.evaluate(({side,src})=>fixture([[85,'K','red'],[4,'K','black'],[src,'R',side]],side),{side,src});
    await page.click(`[data-pos="${src}"]`);await page.click(`[data-pos="${dst}"]`);await page.waitForSelector('.victory-overlay');
    assert.ok((await page.textContent('.victory-overlay')).includes(side==='red'?'红方获胜':'黑方获胜'));
    if(side==='red')await page.screenshot({path:'victory-effect-preview.png'});
    await page.waitForTimeout(4200);assert.equal(await page.locator('.victory-overlay').count(),1);
    await page.waitForSelector('.victory-overlay',{state:'detached'});assert.equal(await page.locator('.piece').count(),32);assert.equal(await page.textContent('#count'),'0 步');
  }
  // An online win must leave the room and reset to an idle board after five seconds.
  await page.route('**/leave',route=>route.fulfill({contentType:'application/json',body:'{"status":"idle"}'}));
  await page.evaluate(()=>{const next={board:Array(90).fill(null),turn:'red',ply:1,quiet:0,result:'红方获胜 · 吃将',last:{kind:'move',src:13,dst:4},history:[]};next.board[4]={face:true,side:'red',kind:'R'};return networkFixture(next);});
  await page.waitForSelector('.victory-overlay');await page.waitForSelector('.victory-overlay',{state:'detached',timeout:7000});
  await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('等待重新匹配'));
  assert.equal(await page.locator('.piece').count(),32);assert.deepEqual(errors,[]);
  console.log('Effects passed: delayed flip/mutation, 3s arrow, red/black 5s victory reset, online reset.');
}finally{await browser?.close();server.closeAllConnections();await new Promise(r=>server.close(r));}
