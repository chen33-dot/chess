import {Game,canMove,names,sideName,chooseAction} from './engine.js';
import {API_URL} from './config.js';
const $=id=>document.getElementById(id);
let mode='ai',game=new Game(),state=game.public(),selected=null,busy=false,online=null,connected=false,timer,epoch=0;
let endpoint=localStorage.getItem('chess-api')||API_URL||(location.hostname==='localhost'||location.hostname==='127.0.0.1'?location.origin:'');
let token=sessionStorage.getItem('chess-token')||'';
$('endpoint').value=endpoint;
const hint={K:'九宫内横竖一格，不可质变。',A:'全盘斜走一格，可离开九宫。',E:'全盘走田，保留塞象眼。',H:'全盘走日，保留蹩马腿。',R:'直线任意距离，不能越子。',C:'移动同车；吃子恰隔一个炮架。',P:'上下左右一格，可以后退。'};
const mine=()=>mode==='online'?online?.side:mode==='ai'?'red':state.turn;
const active=()=>!state.result&&!busy&&(mode!=='online'||(connected&&online?.status==='playing'))&&state.turn===mine();
function render(){
  for(const id of ['ai','local','online','save','leave'])$(id).disabled=busy;
  $('mode').textContent=mode==='online'?(online?.side?`联机 · 你执${sideName(online.side)}`:'联机匹配'):mode==='ai'?'人机练习 · 你执红方':'同屏双人';
  $('turn').textContent=state.result||(mode==='online'&&online?.status!=='playing'?'等待对手':`${sideName(state.turn)}行动${busy?' · 请稍候':''}`);
  $('round').textContent=`第 ${Math.floor(state.ply/2)+1} 回合`;
  const p=state.board[selected];
  $('selection').textContent=p?.face?`${sideName(p.side)} · ${names[p.side][p.kind]}`:'未选择棋子';
  $('hint').textContent=p?.face?hint[p.kind]:'点击己方明棋，查看可走的位置。';
  $('mutate').disabled=!(active()&&p?.face&&p.side===mine()&&p.kind!=='K');
  $('count').textContent=`${state.ply} 步`;
  $('history').replaceChildren(...(state.history.length?[...state.history].reverse():['故事从第一枚暗棋开始。']).map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
  const parts=[];const line=(x1,y1,x2,y2)=>parts.push(`<path d="M${x1} ${y1}L${x2} ${y2}" stroke="#8f764d" fill="none"/>`);
  for(let y=0;y<10;y++)line(30,30+y*60,510,30+y*60);
  for(let x=0;x<9;x++){line(30+x*60,30,30+x*60,x===0||x===8?570:270);if(x!==0&&x!==8)line(30+x*60,330,30+x*60,570);}
  for(const y of [30,450]){line(210,y,330,y+120);line(330,y,210,y+120);}
  parts.push('<text x="150" y="309" fill="#92764d" font-size="25" font-family="KaiTi,serif" text-anchor="middle">楚 河</text><text x="390" y="309" fill="#92764d" font-size="25" font-family="KaiTi,serif" text-anchor="middle">汉 界</text>');
  for(let i=0;i<90;i++){
    const p=state.board[i],x=30+i%9*60,y=30+Math.floor(i/9)*60;
    const movable=selected!==null&&active()&&canMove(state.board,selected,i);
    const name=p?(p.face?sideName(p.side)+names[p.side][p.kind]:'暗棋'):'空位';
    parts.push(`<g class="cell" role="button" tabindex="0" data-pos="${i}" aria-label="${i%9+1}路${10-Math.floor(i/9)}行 ${name}${movable?'，可落子':''}"><rect x="${x-28}" y="${y-28}" width="56" height="56" fill="transparent"/><circle class="focus-ring" cx="${x}" cy="${y}" r="27" fill="none" stroke="${selected===i?'#fff':state.last?.src===i||state.last?.dst===i?'#ab813f':'none'}"/>`);
    if(p){const ink=p.face?(p.side==='red'?'#ac3f31':'#263e32'):'#d7c18d';parts.push(`<g class="piece"><circle cx="${x}" cy="${y}" r="24" fill="${p.face?'#f2dfb5':'#304e3d'}" stroke="#a38a59" stroke-width="2"/><circle cx="${x}" cy="${y}" r="20" fill="none" stroke="${ink}"/><text x="${x}" y="${y+10}" text-anchor="middle" font-family="KaiTi,serif" font-size="29" fill="${ink}">${p.face?names[p.side][p.kind]:'弈'}</text></g>`);}
    if(movable)parts.push(`<circle cx="${x}" cy="${y}" r="${p?27:6}" stroke="${p?'#bd4738':'#557c55'}" stroke-width="3" fill="${p?'none':'#557c55'}"/>`);
    parts.push('</g>');
  }
  const focused=document.activeElement?.dataset?.pos;
  $('board').innerHTML=parts.join('');
  if(focused!==undefined)$('board').querySelector(`[data-pos="${focused}"]`)?.focus({preventScroll:true});
  $('leave').hidden=mode!=='online';
}
function notice(text){$('notice').textContent=text;}
function select(i){if(!active())return;const p=state.board[i];if(p&&!p.face)act({kind:'flip',src:i});else if(p?.side===mine()){selected=selected===i?null:i;render();}else if(selected!==null&&canMove(state.board,selected,i))act({kind:'move',src:selected,dst:i});else notice('请点击可走的绿点，或翻开任意暗棋。');}
$('board').onclick=e=>{const c=e.target.closest('[data-pos]');if(c)select(Number(c.dataset.pos));};
$('board').onkeydown=e=>{const c=e.target.closest('[data-pos]');if(c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();select(Number(c.dataset.pos));}};
$('mutate').onclick=()=>selected!==null&&act({kind:'mutate',src:selected});
async function request(path,data={},timeout=12000){
  const control=new AbortController(),t=setTimeout(()=>control.abort(),timeout);
  try{const response=await fetch(endpoint+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,...data}),signal:control.signal});
    const out=await response.json();if(!response.ok)throw Error(out.error||'服务暂不可用');return out;
  }finally{clearTimeout(t);}
}
function accept(out){if(out.room&&out.room===online?.room&&out.game.ply<state.ply)return;online=out;connected=true;if(out.game){state=out.game;if(selected!==null&&state.board[selected]?.side!==mine())selected=null;notice(state.result||state.history.at(-1)||'匹配成功，红方先手。');}
  $('connection').textContent=out.status==='waiting'?'正在寻找对手… 可取消匹配':out.status==='playing'?(out.opponentOnline?'已连接 · 对手在线':'对手暂时离线，保留90秒重连时间'):'尚未匹配，点击随机匹配开始。';render();}
async function poll(){const version=epoch;if(mode!=='online')return;try{const out=await request('/state');if(version!==epoch)return;accept(out);}catch(e){if(version!==epoch)return;connected=false;$('connection').textContent='连接中断：'+e.message+'。正在重连；会话失效时请重新匹配。';render();}if(version===epoch)timer=setTimeout(poll,1500);}
async function act(a){if(!active())return;const version=epoch;busy=true;render();try{
    if(mode==='online'){const out=await request('/action',{action:a,ply:state.ply});if(version!==epoch)return;selected=null;accept(out);}
    else{game.play(a);state=game.public();selected=null;notice(state.result||state.history.at(-1));}
  }catch(e){notice(e.message);}finally{if(version===epoch){busy=false;render();}}
  if(mode==='ai'&&!state.result&&state.turn==='black'){
    busy=true;render();setTimeout(()=>{if(epoch!==version)return;const a=chooseAction(game.public().board,'black');if(a)game.play(a);state=game.public();busy=false;notice(state.result||state.history.at(-1));render();},350);
  }
}
async function leave(){if(mode!=='online')return true;if(online?.status==='playing'&&!state.result&&!confirm('离开本局会判负，确定离开？'))return false;
  try{await request('/leave');}catch(e){notice('无法通知服务器；离线90秒后判离开。');}
  epoch++;clearTimeout(timer);mode='local';online=null;connected=false;busy=false;return true;
}
async function startLocal(next){if(!await leave())return;if(mode!=='online'&&state.ply&&!state.result&&!confirm('开始新局？当前练习进度不会保存。'))return;epoch++;clearTimeout(timer);mode=next;game=new Game();state=game.public();selected=null;busy=false;notice('新局已就绪，红方先手。');$('connection').textContent='单机模式 · 无需联网';render();}
$('ai').onclick=()=>startLocal('ai');$('local').onclick=()=>startLocal('local');
$('leave').onclick=async()=>{if(await leave()){mode='local';game=new Game();state=game.public();selected=null;$('connection').textContent='已离开联机模式';render();}};
$('online').onclick=async()=>{
  if(busy)return;if(!endpoint){$('connection').textContent='匹配服务尚未配置，请先部署服务并填写地址。';document.querySelector('details').open=true;return;}
  if(mode==='online'&&online?.status==='waiting')return;
  if(mode==='online'&&online?.status==='playing'&&!await leave())return;
  epoch++;clearTimeout(timer);const version=epoch;mode='online';online=null;connected=false;busy=true;selected=null;render();$('connection').textContent='正在连接服务（免费服务唤醒可能约需一分钟）…';
  try{
    if(token){try{accept(await request('/state',{},75000));}catch{token='';}}
    if(!token){const s=await request('/session',{},75000);token=s.token;sessionStorage.setItem('chess-token',token);}
    const out=await request('/state');
    if(out.status==='playing')accept(out);else accept(await request('/match'));
    poll();
  }catch(e){$('connection').textContent='连接失败：'+e.message+'。请稍后重新匹配。';}finally{if(version===epoch){busy=false;render();}}
};
$('save').onclick=async()=>{
  let url;try{url=new URL($('endpoint').value.trim());if(url.protocol!=='https:'&&!(url.protocol==='http:'&&['localhost','127.0.0.1'].includes(url.hostname)))throw Error();}catch{notice('请输入 HTTPS 服务地址；本机测试可使用 http://localhost:8080。');return;}
  if(!await leave())return;endpoint=url.origin;localStorage.setItem('chess-api',endpoint);sessionStorage.removeItem('chess-token');token='';notice('服务地址已保存，点击随机匹配。');render();
};
$('help').onclick=()=>$('rules').showModal();$('close-rules').onclick=()=>$('rules').close();
render();
// Resume a tab's existing session only when explicitly entering online mode.
