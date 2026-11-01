export const other = s => s === 'red' ? 'black' : 'red';
export const names = {red:{K:'帅',R:'车',H:'马',E:'相',A:'仕',C:'炮',P:'兵'},black:{K:'将',R:'车',H:'马',E:'象',A:'士',C:'炮',P:'卒'}};
export const sideName = s => s === 'red' ? '红方' : '黑方';
const pool = [...'RRHHEEAACC PPPPP'.replace(' ','')];
export function randomInt(n) {
  const a = new Uint32Array(1), limit = 4294967296 - 4294967296 % n;
  do { globalThis.crypto.getRandomValues(a); } while(a[0] >= limit);
  return a[0] % n;
}
export function canMove(b, src, dst) {
  if (!Number.isInteger(src) || !Number.isInteger(dst) || dst < 0 || dst >= 90 || src === dst) return false;
  const p=b[src], t=b[dst];
  if (!p?.face || (t && (!t.face || t.side===p.side))) return false;
  const x=src%9,y=Math.floor(src/9), nx=dst%9,ny=Math.floor(dst/9),dx=nx-x,dy=ny-y,ax=Math.abs(dx),ay=Math.abs(dy);
  switch(p.kind) {
    case 'K': return ax+ay===1 && nx>=3 && nx<=5 && (p.side==='red'? ny>=7:ny<=2);
    case 'A': return ax===1 && ay===1;
    case 'E': return ax===2 && ay===2 && !b[(y+dy/2)*9+x+dx/2];
    case 'H': return ((ax===2&&ay===1)||(ax===1&&ay===2)) && !b[ax===2?y*9+x+dx/2:(y+dy/2)*9+x];
    case 'P': return ax+ay===1;
    case 'R': case 'C': {
      if(dx && dy) return false;
      let count=0;
      for(let i=1;i<Math.max(ax,ay);i++) if(b[(y+Math.sign(dy)*i)*9+x+Math.sign(dx)*i]) count++;
      return count===(p.kind==='C'&&t?1:0);
    }
    default: return false;
  }
}
export function actions(board,side) {
  const out=[];
  board.forEach((p,src)=>{
    if(!p) return;
    if(!p.face) out.push({kind:'flip',src});
    else if(p.side===side) {
      if(p.kind!=='K') out.push({kind:'mutate',src});
      for(let dst=0;dst<90;dst++) if(canMove(board,src,dst)) out.push({kind:'move',src,dst});
    }
  });
  return out;
}
export class Game {
  constructor(rand=randomInt) {
    this.rand=rand; this.board=Array(90).fill(null); this.turn='red';this.ply=0;this.quiet=0;this.result=null;this.history=[];this.last=null;
    const pieces=['red','black'].flatMap(side=>pool.map(kind=>({side,kind,face:false})));
    for(let i=pieces.length-1;i>0;i--){const j=rand(i+1);[pieces[i],pieces[j]]=[pieces[j],pieces[i]];}
    const positions=[];
    for(const y of [0,9]) for(let x=0;x<9;x++) if(x!==4) positions.push(y*9+x);
    for(const y of [2,7]) for(const x of [1,7]) positions.push(y*9+x);
    for(const y of [3,6]) for(const x of [0,2,4,6,8]) positions.push(y*9+x);
    positions.forEach((pos,i)=>this.board[pos]=pieces[i]);
    this.board[4]={side:'black',kind:'K',face:true};this.board[85]={side:'red',kind:'K',face:true};
    this.repetitions=new Map([[this.key(),1]]);
  }
  key(){return JSON.stringify([this.turn,this.board]);}
  public(){return {board:this.board.map(p=>p?(p.face?{...p}:{face:false}):null),turn:this.turn,ply:this.ply,quiet:this.quiet,result:this.result,history:this.history.slice(-100),last:this.last};}
  legal(a){
    if(this.result || !a || !Number.isInteger(a.src) || a.src<0 || a.src>=90) return false;
    const p=this.board[a.src];if(!p)return false;
    if(a.kind==='flip')return !p.face;
    if(!p.face||p.side!==this.turn)return false;
    return a.kind==='mutate'?p.kind!=='K':a.kind==='move'&&canMove(this.board,a.src,a.dst);
  }
  play(a){
    if(!this.legal(a))throw Error('不合法的行动');
    a={kind:a.kind,src:a.src,...(a.kind==='move'?{dst:a.dst}:{})};
    const p=this.board[a.src],actor=this.turn;let captured=null,detail='';
    const at=i=>`${i%9+1}路${10-Math.floor(i/9)}行`;
    if(a.kind==='flip') {p.face=true;detail=`翻开 ${at(a.src)} → ${sideName(p.side)}${names[p.side][p.kind]}`;}
    else if(a.kind==='mutate'){
      const old=names[p.side][p.kind],betray=this.rand(5)===0;
      if(betray)p.side=other(p.side);p.kind=pool[this.rand(15)];
      detail=`${at(a.src)} ${old}质变 → ${sideName(p.side)}${names[p.side][p.kind]}${betray?' · 叛变！':''}`;
    }else{captured=this.board[a.dst];this.board[a.dst]=p;this.board[a.src]=null;detail=`${names[p.side][p.kind]} ${at(a.src)} → ${at(a.dst)}${captured?' · 吃'+names[captured.side][captured.kind]:''}`;}
    this.ply++;this.last=a;this.quiet=a.kind==='move'&&!captured?this.quiet+1:0;
    this.history.push(`${this.ply}. ${sideName(actor)} ${detail}`);
    if(captured?.kind==='K'){this.result=`${sideName(actor)}获胜 · 吃将`;return;}
    this.turn=other(actor);
    if(!actions(this.board,this.turn).length){this.result=`${sideName(actor)}获胜 · 对方无合法动作`;return;}
    const key=this.key(),count=(this.repetitions.get(key)||0)+1;this.repetitions.set(key,count);
    if(this.quiet>=240)this.result='和棋 · 连续120回合仅移动';
    else if(this.ply>=600)this.result='和棋 · 达到300完整回合';
    else if(count>=3)this.result='和棋 · 三次重复局面';
  }
}
export function chooseAction(board,side) {
  const values={K:100000,R:90,C:50,H:45,E:25,A:20,P:18};
  let best=null,score=-Infinity;
  for(const a of actions(board,side)){
    let s=Math.random()*4;
    if(a.kind==='flip')s+=8;
    else if(a.kind==='mutate')s-=5;
    else{
      const target=board[a.dst];if(target?.kind==='K')return a;
      s+=target?values[target.kind]:0;
      const b=board.slice();b[a.dst]=b[a.src];b[a.src]=null;
      let danger=0;
      b.forEach((p,src)=>{if(p?.face&&p.side!==side)b.forEach((q,dst)=>{if(q?.face&&q.side===side&&canMove(b,src,dst))danger=Math.max(danger,values[q.kind]);});});
      s-=danger*.9;
    }
    if(s>score){score=s;best=a;}
  }
  return best;
}
