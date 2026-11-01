import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Service} from './service.js';
export function createServer({origins=['http://localhost:8080','http://127.0.0.1:8080','https://chen33-dot.github.io']}={}){
  const service=new Service(),buckets=new Map();
  const timer=setInterval(()=>{service.cleanup();buckets.clear();},10000);timer.unref();
  const server=http.createServer(async(req,res)=>{
    const origin=req.headers.origin;
    if(origin&&!origins.includes(origin)){res.writeHead(403);res.end();return;}
    if(origin)res.setHeader('Access-Control-Allow-Origin',origin);
    res.setHeader('Vary','Origin');res.setHeader('Cache-Control','no-store');
    res.setHeader('Access-Control-Allow-Headers','Content-Type');res.setHeader('Access-Control-Allow-Methods','POST, OPTIONS');
    if(req.method==='OPTIONS'){res.writeHead(204);res.end();return;}
    const url=new URL(req.url,'http://localhost');
    if(req.method==='GET'){
      if(url.pathname==='/health'){res.setHeader('Content-Type','application/json');res.end('{"ok":true}');return;}
      // Only explicitly public static files can be served.
      const files={'/':'index.html','/index.html':'index.html','/style.css':'style.css','/app.js':'app.js','/engine.js':'engine.js','/config.js':'config.js'};
      const file=files[url.pathname];
      if(!file){res.writeHead(404);res.end();return;}
      try{const body=await readFile(fileURLToPath(new URL('../web/'+file,import.meta.url)));res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8');res.end(body);}catch{res.writeHead(500);res.end();}return;
    }
    if(req.method!=='POST'){res.writeHead(405);res.end();return;}
    const ip=req.socket.remoteAddress,n=(buckets.get(ip)||0)+1;buckets.set(ip,n);
    if(n>200){res.writeHead(429);res.end('{"error":"请求过于频繁"}');return;}
    try{
      let body='';for await(const chunk of req){body+=chunk;if(body.length>4096)throw Error('请求过大');}
      const data=JSON.parse(body);if(!data||typeof data!=='object')throw Error('无效请求');
      const out=service.dispatch(url.pathname,data);res.setHeader('Content-Type','application/json; charset=utf-8');res.end(JSON.stringify(out));
    }catch(e){res.writeHead(400,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify({error:e.message}));}
  });
  server.on('close',()=>clearInterval(timer));return server;
}
if(process.argv[1]===fileURLToPath(import.meta.url))createServer({origins:(process.env.ALLOWED_ORIGINS||'http://localhost:8080,http://127.0.0.1:8080,https://chen33-dot.github.io').split(',')}).listen(Number(process.env.PORT)||8080,'0.0.0.0',()=>console.log('弈变服务已启动：http://localhost:'+(process.env.PORT||8080)));
