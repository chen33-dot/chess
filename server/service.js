import {randomBytes, webcrypto} from 'node:crypto';
import {Game,other,sideName} from '../web/engine.js';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const id=()=>randomBytes(24).toString('hex');
export class Service {
  constructor(){this.sessions=new Map();this.rooms=new Map();this.queue=[];}
  session(token){const s=this.sessions.get(token);if(!s)throw Error('会话失效，请重新连接');s.seen=Date.now();return s;}
  create(){if(this.sessions.size>=2000)throw Error('服务器繁忙');const token=id();this.sessions.set(token,{token,seen:Date.now(),room:null,queued:false});return {token};}
  pair(a,b){const room={id:id(),red:a.token,black:b.token,game:new Game()};this.rooms.set(room.id,room);a.room=b.room=room.id;a.queued=b.queued=false;}
  match(s){
    if(s.room)throw Error('请先离开当前对局');
    if(s.queued)return;
    while(this.queue.length){const t=this.queue.shift(),p=this.sessions.get(t);if(p&&p.token!==s.token&&p.queued&&!p.room&&Date.now()-p.seen<15000){this.pair(p,s);return;}}
    s.queued=true;this.queue.push(s.token);
  }
  state(s){const r=this.rooms.get(s.room);return r?{status:'playing',room:r.id,side:r.red===s.token?'red':'black',game:r.game.public(),opponentOnline:Date.now()-(this.sessions.get(r.red===s.token?r.black:r.red)?.seen||0)<15000}:{status:s.queued?'waiting':'idle'};}
  leave(s){
    s.queued=false;this.queue=this.queue.filter(t=>t!==s.token);
    const r=this.rooms.get(s.room);
    if(r&&!r.game.result)r.game.result=`${sideName(r.red===s.token?'black':'red')}获胜 · 对手离开`;
    s.room=null;
  }
  action(s,data){
    const r=this.rooms.get(s.room);if(!r)throw Error('尚未进入对局');
    const side=r.red===s.token?'red':'black';
    if(r.game.turn!==side)throw Error('请等待对方行动');
    if(data.ply!==r.game.ply)throw Error('棋局已更新，请重试');
    r.game.play(data.action);
  }
  cleanup(){
    const now=Date.now();
    for(const [token,s]of this.sessions){
      if(s.queued&&now-s.seen>15000){s.queued=false;this.queue=this.queue.filter(t=>t!==token);}
      if(now-s.seen>90000){this.leave(s);this.sessions.delete(token);}
    }
    for(const [key,r]of this.rooms){if(![r.red,r.black].some(t=>this.sessions.get(t)?.room===key))this.rooms.delete(key);}
  }
  dispatch(path,data){
    if(path==='/session')return this.create();
    const s=this.session(data.token);
    if(path==='/match')this.match(s);
    else if(path==='/leave')this.leave(s);
    else if(path==='/action')this.action(s,data);
    else if(path!=='/state')throw Error('接口不存在');
    return this.state(s);
  }
}
