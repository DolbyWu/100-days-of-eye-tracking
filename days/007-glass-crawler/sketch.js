// @neon-template: digital-centipede
// Particle-stream interaction inspired by nicoptere/physarum/src/Controls.js.
// Independent p5 implementation; no Three.js or shader dependency.
// Paste this WHOLE file into Donut MIDI Workshop, then Run.
// Original implementation, inspired by Jones-style Physarum and the two linked works.
// Editor supplies p5, neon, MAT_URL and NeonEffects. No extra libraries.
(() => {
const OPTIONS = { particles: 22000, maxParticles: 42000, burst: 1800,
  gridWidth: 840, decay: 0.975, deposit: 0.85, radius: 48 };
new p5(p => {
  let mat, img, w, h, field, next, count=0, recycle=0;
  const X=new Float32Array(OPTIONS.maxParticles),Y=new Float32Array(OPTIONS.maxParticles);
  const A=new Float32Array(OPTIONS.maxParticles);
  let gate, capture=null, samples=[],stamp=null,status='Mouse: move to stir · click / B to bloom';
  let last=null, gaze=null, lastSeen=-Infinity, pulses=[],mode=0,show=true,paused=false,button;
  let gazeQueue=[],holdUntil=0;
  let tissue, fibers, mw, mh, bendX, bendY, velX, velY, driveX, driveY, membrane, waveMap, floods=[];
  function initElastic(){
    mw=Math.ceil(w/4);mh=Math.ceil(h/4);const n=mw*mh;
    bendX=new Float32Array(n);bendY=new Float32Array(n);velX=new Float32Array(n);velY=new Float32Array(n);
    driveX=new Float32Array(n);driveY=new Float32Array(n);membrane=new Float32Array(n);waveMap=new Float32Array(n);floods=[];
    for(let y=0;y<mh;y++)for(let x=0;x<mw;x++){
      let wall=0;for(let yy=0;yy<4;yy++)for(let xx=0;xx<4;xx++){
        const k=Math.min(h-1,y*4+yy)*w+Math.min(w-1,x*4+xx);wall=Math.max(wall,tissue[k]);
      }membrane[y*mw+x]=wall;
    }
  }
  let propagationJob=null,lastBurstAt=-Infinity,blinkRecycle=0;
  function startFlood(x,y){
    // Start cheaply. Relax a bounded number of path nodes per draw frame.
    const dist=new Float64Array(mw*mh);dist.fill(Infinity);
    const source=clamp(Math.floor(y/4),0,mh-1)*mw+clamp(Math.floor(x/4),0,mw-1);
    const heap=[];
    function push(item){let i=heap.length;heap.push(item);while(i){const parent=(i-1)>>1;if(heap[parent][0]<=item[0])break;heap[i]=heap[parent];i=parent;}heap[i]=item;}
    function pop(){const first=heap[0],end=heap.pop();if(heap.length){let i=0;while(i*2+1<heap.length){let j=i*2+1;if(j+1<heap.length&&heap[j+1][0]<heap[j][0])j++;if(heap[j][0]>=end[0])break;heap[i]=heap[j];i=j;}heap[i]=end;}return first;}
    dist[source]=0;push([0,source]);
    const flood={dist,start:p.millis(),duration:40000,complete:false};
    floods.push(flood);if(floods.length>2)floods.shift();
    propagationJob={dist,heap,push,pop,flood,maxDistance:0};
  }
  function advancePropagation(){
    const job=propagationJob;if(!job)return;
    const {dist,heap,push,pop}=job;let budget=384;
    while(heap.length&&budget-->0){
      const [d,k]=pop();if(!Number.isFinite(d)||d>dist[k])continue;
      job.maxDistance=Math.max(job.maxDistance,d);
      const x=k%mw,y=Math.floor(k/mw);
      const relax=j=>{
        const density=clamp(Math.max(membrane[k],membrane[j]),0,1);
        const next=d+1+5*(1-density);
        if(next<dist[j]){dist[j]=next;push([next,j]);}
      };
      if(x>0)relax(k-1);if(x<mw-1)relax(k+1);if(y>0)relax(k-mw);if(y<mh-1)relax(k+mw);
    }
    if(!heap.length){job.flood.duration=job.maxDistance*12;job.flood.complete=true;propagationJob=null;}
  }
  function networkWave(k,now){let value=0;for(const f of floods){
    const elapsed=now-f.start-f.dist[k]*12;
    if(elapsed>=0&&elapsed<2400)value+=1.65*Math.exp(-elapsed/850)*(1-Math.exp(-elapsed/35));
  }return Math.min(1.5,value);}
  function elasticStep(now,dt,current,previous){
    floods=floods.filter(f=>now-f.start<f.duration+2400);
    for(let k=0;k<waveMap.length;k++)waveMap[k]=networkWave(k,now);
    const vx=current&&previous?clamp(current.x-previous.x,-16,16):0;
    const vy=current&&previous?clamp(current.y-previous.y,-16,16):0;
    for(let y=1;y<mh-1;y++)for(let x=1;x<mw-1;x++){
      const k=y*mw+x;
      const lx=(bendX[k-1]+bendX[k+1]+bendX[k-mw]+bendX[k+mw])*.25-bendX[k];
      const ly=(bendY[k-1]+bendY[k+1]+bendY[k-mw]+bendY[k+mw])*.25-bendY[k];
      let fx=0,fy=0;
      if(current){const dx=x*4-current.x,dy=y*4-current.y,d=Math.hypot(dx,dy),q=Math.exp(-d*d/1000);
        fx=(vx*.55+dx/(d+1)*.65)*q;fy=(vy*.55+dy/(d+1)*.65)*q;}
      const wave=waveMap[k];
      fx+=Math.sin(x*.5+y*.31)*wave*.12;fy+=Math.cos(y*.5-x*.27)*wave*.12;
      driveX[k]=(velX[k]+(lx*.22-bendX[k]*.018+fx)*dt)*Math.pow(.86,dt);
      driveY[k]=(velY[k]+(ly*.22-bendY[k]*.018+fy)*dt)*Math.pow(.86,dt);
    }
    for(let k=0;k<bendX.length;k++){
      velX[k]=driveX[k];velY[k]=driveY[k];bendX[k]=clamp(bendX[k]+velX[k]*dt,-22,22);bendY[k]=clamp(bendY[k]+velY[k]*dt,-22,22);
      const wave=waveMap[k];if(wave>.05){const x=k%mw*4,y=Math.floor(k/mw)*4,idx=Math.min(h-1,y)*w+Math.min(w-1,x);field[idx]=Math.min(25,field[idx]+wave*membrane[k]*.55*dt);}
    }
  }
  let growthX,growthY,growthTime=0;
  function initGrowth(){growthX=new Float32Array(mw*mh);growthY=new Float32Array(mw*mh);growthTime=0;updateGrowth(0);}
  function updateGrowth(time){
    growthX.fill(0);growthY.fill(0);
    for(const c of cells){
      const speed=.00016+(c.phase/6.28)*.00012;
      const scale=1+.13*Math.sin(time*speed+c.phase)+.025*Math.sin(time*speed*.43+c.phase*2);
      const reach=c.r*2.5;
      for(let y=Math.max(0,Math.floor((c.y-reach)/4));y<Math.min(mh,Math.ceil((c.y+reach)/4));y++)
      for(let x=Math.max(0,Math.floor((c.x-reach)/4));x<Math.min(mw,Math.ceil((c.x+reach)/4));x++){
        const dx=x*4-c.x,dy=y*4-c.y,d=Math.hypot(dx,dy)/reach;
        if(d>=1)continue;
        const falloff=1-d*d*(3-2*d),factor=(1-1/scale)*falloff,k=y*mw+x;
        growthX[k]+=dx*factor;growthY[k]+=dy*factor;
      }
    }
  }
  let textureX=0,textureY=0;
  function warpedIndex(x,y){
    const cx=clamp(x/4,0,mw-1.001),cy=clamp(y/4,0,mh-1.001),ix=Math.floor(cx),iy=Math.floor(cy),tx=cx-ix,ty=cy-iy,k=iy*mw+ix;
    const warp=a=>(a[k]*(1-tx)+a[k+1]*tx)*(1-ty)+(a[k+mw]*(1-tx)+a[k+mw+1]*tx)*ty;
    textureX=clamp(x-warp(bendX)-warp(growthX),0,w-1.001);textureY=clamp(y-warp(bendY)-warp(growthY),0,h-1.001);
    return Math.round(textureY)*w+Math.round(textureX);
  }
  function smoothTexture(a){const x=Math.floor(textureX),y=Math.floor(textureY),tx=textureX-x,ty=textureY-y,k=y*w+x;return (a[k]*(1-tx)+a[k+1]*tx)*(1-ty)+(a[k+w]*(1-tx)+a[k+w+1]*tx)*ty;}
  let cells=[],soma,nuclei,cutStamp,cutDepth,damage;
  let brush,brushNext,brushHead=0,brushCount=0;
  const brushAgents=Array.from({length:6000},()=>({x:0,y:0,a:0,until:-Infinity}));
  function initBrush(){brush=new Float32Array(w*h);brushNext=new Float32Array(w*h);brushHead=0;brushCount=0;for(const a of brushAgents)a.until=-Infinity;}
  function streamGaze(current,previous,now){
    if(!current)return;
    const d=previous?Math.hypot(current.x-previous.x,current.y-previous.y):0;
    if(previous&&d<.6)return; // Looking steadily does not repeatedly flood the spot.
    const from=previous&&d<w*.4?previous:current;
    const steps=Math.max(1,Math.min(36,Math.ceil(Math.hypot(current.x-from.x,current.y-from.y)/2)));
    for(let k=0;k<=steps;k++){
      const t=k/steps,x=from.x+(current.x-from.x)*t,y=from.y+(current.y-from.y)*t;
      for(let j=0;j<12;j++){
        const a=brushAgents[brushHead++%brushAgents.length],angle=Math.random()*Math.PI*2,r=Math.random()*6;
        a.x=clamp(x+Math.cos(angle)*r,2,w-3);a.y=clamp(y+Math.sin(angle)*r,2,h-3);
        a.a=Math.random()*Math.PI*2;a.until=now+6500;brushCount=Math.min(brushAgents.length,brushCount+1);
      }
    }
  }
  function brushStep(now,dt,current,previous){
    streamGaze(current,previous,now);
    const [offset,angle,turn,speed]=profiles[mode];
    const read=(x,y,a)=>{
      const xx=clamp(Math.round(x+Math.cos(a)*offset),0,w-1),yy=clamp(Math.round(y+Math.sin(a)*offset),0,h-1);
      const k=yy*w+xx;return brush[k]*2+field[k]*.12;
    };
    for(const a of brushAgents){
      if(a.until<now)continue;
      const f=read(a.x,a.y,a.a),l=read(a.x,a.y,a.a-angle),r=read(a.x,a.y,a.a+angle);
      if(f<l&&f<r)a.a+=(Math.random()<.5?-turn:turn)*dt;
      else if(l>r&&l>f)a.a-=turn*dt;else if(r>l&&r>f)a.a+=turn*dt;
      a.a+=(Math.random()-.5)*.05*dt;
      const x=a.x+Math.cos(a.a)*speed*dt,y=a.y+Math.sin(a.a)*speed*dt;
      if(x<2||x>w-3||y<2||y>h-3){a.until=-Infinity;continue;}
      const steps=Math.max(1,Math.ceil(Math.hypot(x-a.x,y-a.y)*1.5));
      for(let j=0;j<=steps;j++){
        const ix=Math.floor(a.x+(x-a.x)*j/steps),iy=Math.floor(a.y+(y-a.y)*j/steps),k=iy*w+ix;
        brush[k]=Math.min(18,brush[k]+1.2*dt/(steps+1));
      }a.x=x;a.y=y;
    }
    brushNext.fill(0);const decay=Math.pow(.979,dt);
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
      const k=y*w+x;brushNext[k]=(brush[k]*.78+(brush[k-1]+brush[k+1]+brush[k-w]+brush[k+w])*.055)*decay;
    }[brush,brushNext]=[brushNext,brush];
  }
  const profiles=[ [9,.58,.34,1.05], [16,.8,.55,1.25], [6,.42,.26,.8] ];
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  function add(x,y,r=12) {
    const i=count<OPTIONS.maxParticles?count++:(recycle++%OPTIONS.maxParticles);
    const angle=Math.random()*Math.PI*2, rr=Math.sqrt(Math.random())*r;
    X[i]=clamp(x+Math.cos(angle)*rr,2,w-3);Y[i]=clamp(y+Math.sin(angle)*rr,2,h-3);
    A[i]=Math.random()*Math.PI*2;
  }
  // Keep marker positions and proportions unchanged for the existing surface mapping.
  const tagBoxes=[[15,15,150,150],[1035,15,150,150],[15,635,150,150],[1035,635,150,150]];
  function covered(g){return tagBoxes.some(([x,y,w,h])=>g.x>=x/1200&&g.x<=(x+w)/1200&&g.y>=y/800&&g.y<=(y+h)/800);}
  function fitCanvas(first=false){
    const width=Math.max(1,Math.min(p.windowWidth,(p.windowHeight-40)*1.5));
    if(first){const c=p.createCanvas(width,width/1.5);c.style('margin','40px auto 0');neon.useMouse(c);}
    else p.resizeCanvas(width,width/1.5);
  }
  function drawMarkers(){
    if(!mat)return;
    for(const [x,y,w,h] of tagBoxes){
      p.image(mat,x/1200*p.width,y/800*p.height,w/1200*p.width,h/800*p.height,
        x/1200*mat.width,y/800*mat.height,w/1200*mat.width,h/800*mat.height);
    }
  }
  // A connected, warped cellular scaffold with pores and nested fine lamellae.
  // Independent procedural structure inspired by the supplied reference image.
  function buildTissue(){
    tissue=new Float32Array(w*h);fibers=new Float32Array(w*h);
    soma=new Float32Array(w*h);nuclei=new Float32Array(w*h);
    cells=[];
    // Asymmetric colonies control pore density, wall width and nested filaments.
    const colonies=[{x:w*.59,y:h*.38,r:w*.13},{x:w*.25,y:h*.72,r:w*.075},{x:w*.88,y:h*.76,r:w*.09}];
    const density=(x,y)=>colonies.reduce((v,c)=>v+Math.exp(-((x-c.x)**2+(y-c.y)**2)/(c.r*c.r)),0);
    const sites=[];
    // Variable separation gives big open chambers beside tightly packed small pores.
    for(let attempt=0;attempt<5000&&sites.length<135;attempt++){
      const x=(-.08+Math.random()*1.16)*w,y=(-.08+Math.random()*1.16)*h;
      const dense=density(x,y),sep=5+33/(1+dense*12);
      if(sites.every(c=>Math.hypot(c.x-x,c.y-y)>(c.sep+sep)*.5))sites.push({x,y,sep});
    }
    // Outer sites keep membranes connected to the edge of the composition.
    for(let j=0;j<16;j++){const t=j/15;sites.push({x:t*w,y:-12},{x:t*w,y:h+12});}
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const qx=x+14*Math.sin(y*.025+x*.008)+5*Math.sin(x*.054+y*.038);
      const qy=y+10*Math.sin(x*.023-y*.011)+5*Math.cos(y*.058-x*.031);
      let d1=Infinity,d2=Infinity;
      for(const c of sites){const d=(qx-c.x)**2+(qy-c.y)**2;if(d<d1){d2=d1;d1=d;}else if(d<d2)d2=d;}
      const edge=(Math.sqrt(d2)-Math.sqrt(d1))*.5,dense=clamp(density(qx,qy),0,1.4);
      const wall=Math.exp(-edge*edge/(.65+dense*2.9));
      const rad=Math.hypot((x/w-.53)*1.05,(y/h-.5)*.92);
      const outer=clamp((rad-.27)*4.8,0,1);
      const fold=y*1.67+11*Math.sin(x*.014)+6*Math.sin(x*.027+y*.022)+3*Math.sin(y*.042);
      const bands=Math.pow(.5+.5*Math.sin(fold),22);
      const nested=Math.pow(.5+.5*Math.cos(edge*3.8+.3*Math.sin(x*.14)),18)*Math.exp(-edge*.18);
      const curl=Math.pow(.5+.5*Math.sin(Math.hypot(qx-w*.59,(qy-h*.38)*1.3)*2.8+Math.atan2(qy-h*.38,qx-w*.59)*4),16);
      const grain=.82+.18*Math.sin(x*8.17+y*2.31)*Math.sin(y*6.7-x*4.1);
      const k=y*w+x;
      const tangled=Math.pow(.5+.5*Math.sin(qx*.9+Math.sin(qy*.32)*6+Math.atan2(qy-h*.38,qx-w*.59)*3),10);
      tissue[k]=(wall*(.55+dense*.4)+tangled*dense*dense*.28)*grain;
      fibers[k]=(nested*(1-outer)*.6+bands*outer*.9+curl*dense*.85)*grain;
    }
  }
  function buildNeurons(){
    soma=new Float32Array(w*h);nuclei=new Float32Array(w*h);cells=[];
    // Uneven colonies: large somas, small satellites and open areas; no grid.
    const scale=w/560;
    const centers=[[.58,.39,38],[.24,.73,28],[.85,.72,21]];
    for(const [x,y,r] of centers)cells.push({x:x*w,y:y*h,r:r*scale,phase:Math.random()*6.28});
    for(let attempt=0;attempt<900&&cells.length<21;attempt++){
      const c=centers[Math.floor(Math.random()*centers.length)];
      const clustered=Math.random()<.72,angle=Math.random()*6.28,rad=(.07+Math.random()*.19)*w;
      const x=clustered?c[0]*w+Math.cos(angle)*rad:(.08+Math.random()*.84)*w;
      const y=clustered?c[1]*h+Math.sin(angle)*rad*.7:(.09+Math.random()*.82)*h;
      const r=(5+Math.pow(Math.random(),2)*16)*scale;
      if(x<r*1.6||x>w-r*1.6||y<r*1.6||y>h-r*1.6)continue;
      if(cells.some(n=>Math.hypot(n.x-x,n.y-y)<(n.r+r)*1.35+4*scale))continue;
      cells.push({x,y,r,phase:Math.random()*6.28});
    }
    function ink(x,y,r,strength){
      for(let yy=Math.max(0,Math.floor(y-r*2.5));yy<=Math.min(h-1,y+r*2.5);yy++)
      for(let xx=Math.max(0,Math.floor(x-r*2.5));xx<=Math.min(w-1,x+r*2.5);xx++){
        const d=((xx-x)**2+(yy-y)**2)/(r*r),k=yy*w+xx;
        tissue[k]=Math.max(tissue[k],Math.exp(-d*1.5)*strength);
      }
    }
    function curve(a,b,width){
      const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy),phase=Math.random()*6.28;
      const n=Math.max(8,Math.ceil(len*1.3)),normalX=-dy/(len||1),normalY=dx/(len||1);
      const pts=[];
      for(let j=0;j<=n;j++){
        const t=j/n,wiggle=Math.sin(t*Math.PI)*(Math.sin(t*8+phase)*len*.07+Math.sin(t*17+phase)*2);
        const x=a.x+dx*t+normalX*wiggle,y=a.y+dy*t+normalY*wiggle;
        const taper=.4+.6*Math.pow(Math.abs(t-.5)*2,2);
        ink(x,y,width*taper,.92);pts.push({x,y});
      }return pts;
    }
    const connected=new Set();
    for(let i=0;i<cells.length;i++){
      const c=cells[i],near=cells.map((v,j)=>({j,d:Math.hypot(c.x-v.x,c.y-v.y)})).filter(v=>v.j!==i).sort((a,b)=>a.d-b.d).slice(0,3);
      for(const other of near){const key=[i,other.j].sort((a,b)=>a-b).join(',');if(connected.has(key))continue;connected.add(key);
        const pts=curve(c,cells[other.j],1.1+Math.random()*1.4);
        const target=cells[other.j];
        for(let f=0;f<2;f++){
          const shift=(f?1:-1)*2.4;
          curve({x:c.x+shift,y:c.y-shift},{x:target.x+shift,y:target.y-shift},.42);
        }
        for(let b=0;b<5;b++){
          const q=pts[Math.floor((.2+Math.random()*.6)*pts.length)];
          const angle=Math.random()*6.28,length=12+Math.random()*26;
          curve(q,{x:q.x+Math.cos(angle)*length,y:q.y+Math.sin(angle)*length},.7+Math.random()*.7);
        }
      }
      for(let a=0;a<7;a++){
        const angle=a*6.28/7+c.phase,rr=c.r*(1.9+Math.random()*1.6);
        const tip={x:c.x+Math.cos(angle)*rr,y:c.y+Math.sin(angle)*rr};
        curve(c,tip,Math.max(.8,c.r*.085));
        for(let j=0;j<2;j++){const aa=angle+(j?1:-1)*.65;curve(tip,{x:tip.x+Math.cos(aa)*14,y:tip.y+Math.sin(aa)*14},.65);}
      }
    }
    for(const c of cells){
      for(let y=Math.max(0,Math.floor(c.y-c.r*1.5));y<Math.min(h,c.y+c.r*1.5);y++)
      for(let x=Math.max(0,Math.floor(c.x-c.r*1.5));x<Math.min(w,c.x+c.r*1.5);x++){
        const dx=(x-c.x)/c.r,dy=(y-c.y)/(c.r*.87),angle=Math.atan2(dy,dx);
        // Asymmetric envelope, without periodic petal lobes.
        const warpX=dx+.10*Math.sin(dy*3+c.phase)+.045*Math.sin(dy*7+dx*2);
        const warpY=dy+.13*Math.sin(dx*2.6-c.phase)+.045*Math.cos(dx*6-dy*3);
        const rr=Math.hypot(warpX,warpY);
        const k=y*w+x,envelope=clamp((1.10-rr)*7,0,1);
        // A small offset irregular pore replaces the solid nucleus.
        const hx=(warpX+.13)/(.20+.025*Math.sin(angle*3+c.phase));
        const hy=(warpY+.11)/.145;
        const hole=clamp((1-Math.hypot(hx,hy))*6,0,1);
        const radial=Math.hypot(warpX+.06,warpY-.04)*c.r;
        const twist=Math.atan2(warpY-.04,warpX+.06);
        const sweep=radial*3.25+Math.sin(twist*2+radial*.12)*2.2+Math.sin(warpY*7+warpX*3)*.8;
        const winding=Math.pow(.5+.5*Math.sin(sweep),9);
        const crossing=Math.pow(.5+.5*Math.sin((warpX*.65+warpY)*c.r*2.7+Math.sin(warpX*8)*2.2),13);
        const grain=.7+.3*Math.sin(x*7.71+y*3.13)*Math.sin(y*8.31-x*2.17);
        const bundle=envelope*(1-hole)*(.36+.85*winding+.38*crossing)*grain;
        soma[k]=Math.max(soma[k],bundle);
        nuclei[k]=Math.max(nuclei[k],hole);
        tissue[k]*=1-hole*.96;
        tissue[k]=Math.max(tissue[k],bundle*.82);
        fibers[k]=Math.max(fibers[k],bundle*.95);

      }
    }
  }
  function initCuts(){cutStamp=new Float64Array(mw*mh);cutStamp.fill(-Infinity);cutDepth=new Float32Array(mw*mh);damage=new Float32Array(mw*mh);}
  function updateCuts(now,current,previous){
    if(current){
      const prev=previous&&Math.hypot(current.x-previous.x,current.y-previous.y)<90?previous:current;
      const dx=current.x-prev.x,dy=current.y-prev.y,den=dx*dx+dy*dy||1,r=18;
      for(let y=Math.max(0,Math.floor((Math.min(prev.y,current.y)-r)/4));y<Math.min(mh,Math.ceil((Math.max(prev.y,current.y)+r)/4)+1);y++)
      for(let x=Math.max(0,Math.floor((Math.min(prev.x,current.x)-r)/4));x<Math.min(mw,Math.ceil((Math.max(prev.x,current.x)+r)/4)+1);x++){
        const t=clamp(((x*4-prev.x)*dx+(y*4-prev.y)*dy)/den,0,1);
        const d=Math.hypot(x*4-prev.x-t*dx,y*4-prev.y-t*dy),k=y*mw+x;
        if(d<r){cutStamp[k]=now;cutDepth[k]=Math.max(damage[k],clamp((r-d)/7,0,1));}
      }
    }
    for(let k=0;k<damage.length;k++){
      const age=now-cutStamp[k],heal=clamp((age-650)/1900,0,1);
      damage[k]=cutDepth[k]*(1-heal*heal*(3-2*heal));
    }
    // Erase trail memory inside the lesion so it does not instantly bridge the gap.
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const k=Math.floor(y/4)*mw+Math.floor(x/4);if(damage[k]>.1)field[y*w+x]*=1-damage[k]*.8;
    }
  }
  // Independent two-link IK crawler, with planted feet and alternating step groups.
  let crawler=null,footprints=[],memoryThreads=[],neuralEvent=null;
  function localPoint(x,y){const c=Math.cos(crawler.a),s=Math.sin(crawler.a);return {x:crawler.x+c*x-s*y,y:crawler.y+s*x+c*y};}
  function contact(x,y,now,leg){
    if(leg){if(leg.lastContact&&Math.hypot(x-leg.lastContact.x,y-leg.lastContact.y)<100){memoryThreads.push({a:leg.lastContact,b:{x,y},t:now,side:leg.side});if(memoryThreads.length>80)memoryThreads.shift();}leg.lastContact={x,y};}
    x=clamp(x,4,w-5);y=clamp(y,4,h-5);
    footprints.push({x,y,t:now});if(footprints.length>64)footprints.shift();
    for(let yy=Math.max(0,Math.floor((y-20)/4));yy<Math.min(mh,Math.ceil((y+20)/4));yy++)for(let xx=Math.max(0,Math.floor((x-20)/4));xx<Math.min(mw,Math.ceil((x+20)/4));xx++){
      const d=Math.hypot(xx*4-x,yy*4-y),k=yy*mw+xx;if(d<20){cutStamp[k]=now;cutDepth[k]=Math.max(damage[k],(1-d/20)*.95);velX[k]+=(xx*4-x)*.05;velY[k]+=(yy*4-y)*.05;}
    }
    streamGaze({x,y},null,now);
  }
  function segmentPoint(index,forward,side){const b=crawler.spine[index],c=Math.cos(b.a),s=Math.sin(b.a);return {x:b.x+c*forward-s*side,y:b.y+s*forward+c*side};}
  function crawl(now,dt,target){
    if(!crawler){crawler={x:w*.62,y:h*.48,a:0,legs:[],spine:[],catchArmed:true};for(let i=0;i<19;i++)crawler.spine.push({x:crawler.x-i*8.7,y:crawler.y,a:0});
      for(let row=0;row<4;row++)for(const side of [-1,1]){const index=1+row,reach=[57,76.5,79.5,64.5][row],forward=[64.5,30,-28.5,-67.5][row];const foot=segmentPoint(index,forward,side*reach);foot.x=clamp(foot.x,3,w-4);foot.y=clamp(foot.y,3,h-4);crawler.legs.push({side,row,index,reach,forward,foot,step:null});}}
    const c=crawler;
    c.resting=!!target&&Math.hypot(target.x-c.x,target.y-c.y)<24;
    if(target){const dx=target.x-c.x,dy=target.y-c.y,d=Math.hypot(dx,dy),da=Math.atan2(Math.sin(Math.atan2(dy,dx)-c.a),Math.cos(Math.atan2(dy,dx)-c.a));c.a+=clamp(da,-.055*dt,.055*dt);const speed=Math.min(3.3,Math.max(0,(d-12)*.05))*dt*Math.max(.22,1-Math.abs(da)/Math.PI);c.x=clamp(c.x+Math.cos(c.a)*speed,12,w-12);c.y=clamp(c.y+Math.sin(c.a)*speed,12,h-12);}
    c.spine[0]={x:c.x,y:c.y,a:c.a};
    for(let i=1;i<c.spine.length;i++){const b=c.spine[i],prev=c.spine[i-1],raw=Math.atan2(prev.y-b.y,prev.x-b.x),delta=Math.atan2(Math.sin(raw-prev.a),Math.cos(raw-prev.a));b.a=prev.a+clamp(delta,-.34,.34);b.x=prev.x-Math.cos(b.a)*8.7;b.y=prev.y-Math.sin(b.a)*8.7;}
    for(const l of c.legs){const ideal=segmentPoint(l.index,l.forward+5,l.side*l.reach);ideal.x=clamp(ideal.x,3,w-4);ideal.y=clamp(ideal.y,3,h-4);
      if(c.resting&&l.row===0){ideal.x=clamp(ideal.x+Math.cos(c.a)*Math.sin(now*.0018+l.side)*9,3,w-4);ideal.y=clamp(ideal.y+Math.sin(now*.0018+l.side*2)*7,3,h-4);}
      const phase=((now/95-l.row*.7+(l.side>0?2:0))%4+4)%4;
      if(!l.step&&phase<1.4&&Math.hypot(l.foot.x-ideal.x,l.foot.y-ideal.y)>8)l.step={from:{...l.foot},end:ideal,t:now};
      if(l.step){const u=clamp((now-l.step.t)/190,0,1),v=u*u*(3-2*u);l.foot={x:l.step.from.x+(l.step.end.x-l.step.from.x)*v,y:l.step.from.y+(l.step.end.y-l.step.from.y)*v};if(u===1){contact(l.foot.x,l.foot.y,now,l);l.step=null;}}
    }
    if(target){
      const distance=Math.hypot(target.x-c.x,target.y-c.y);
      if(distance>42)c.catchArmed=true;
      if(distance<=19&&c.catchArmed&&burst())c.catchArmed=false;
    }
    footprints=footprints.filter(f=>now-f.t<1800);
    memoryThreads=memoryThreads.filter(f=>now-f.t<6500);
    if(neuralEvent){
      for(let i=0;i<c.legs.length;i++){const l=c.legs[i],arrival=neuralEvent.t+350+l.row*95+440;if(!neuralEvent.feet[i]&&now>=arrival){neuralEvent.feet[i]=true;contact(l.foot.x,l.foot.y,now,l);}}
      if(!neuralEvent.emitted&&now-neuralEvent.t>=1150){neuralEvent.emitted=true;emitPulse(neuralEvent.origin);}
      if(now-neuralEvent.t>2300)neuralEvent=null;
    }
  }
  function drawCrawler(now){
    if(!crawler)return;const ctx=p.drawingContext;ctx.save();ctx.translate(p.width*.02,p.height*.02);ctx.scale(p.width*.96/w,p.height*.96/h);ctx.lineCap='round';ctx.lineJoin='round';
    function path(points,color,width){ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(let i=1;i<points.length;i++)ctx.lineTo(points[i].x,points[i].y);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
    for(const m of memoryThreads){
      const age=now-m.t,fade=Math.pow(clamp(1-age/6500,0,1),1.3),growth=clamp(age/1000,0,1);
      const dx=m.b.x-m.a.x,dy=m.b.y-m.a.y,len=Math.max(1,Math.hypot(dx,dy)),nx=-dy/len,ny=dx/len;
      const end={x:m.a.x+dx*growth,y:m.a.y+dy*growth};
      path([m.a,{x:(m.a.x+end.x)*.5+nx*3,y:(m.a.y+end.y)*.5+ny*3},end],`rgba(139,255,84,${fade*.65})`,.65);
      for(let j=1;j<=3;j++){const t=j/4;if(t>growth)continue;const base={x:m.a.x+dx*t,y:m.a.y+dy*t},reach=(5+j*2)*Math.min(1,(growth-t)*4);path([base,{x:base.x+nx*reach*m.side+dx*.08,y:base.y+ny*reach*m.side+dy*.08}],`rgba(181,239,109,${fade*.45})`,.4);}
    }
    for(const f of footprints){
      const u=clamp((now-f.t)/1800,0,1),fade=(1-u)*(1-u),radius=5+u*32;
      const glow=ctx.createRadialGradient(f.x,f.y,0,f.x,f.y,18+u*15);
      glow.addColorStop(0,`rgba(151,255,78,${fade*.65})`);glow.addColorStop(.35,`rgba(71,255,60,${fade*.25})`);glow.addColorStop(1,'rgba(71,255,60,0)');
      ctx.fillStyle=glow;ctx.beginPath();ctx.arc(f.x,f.y,18+u*15,0,Math.PI*2);ctx.fill();
      ctx.beginPath();ctx.arc(f.x,f.y,radius,0,Math.PI*2);ctx.strokeStyle=`rgba(133,255,61,${fade*.9})`;ctx.lineWidth=1.4*(1-u)+.3;ctx.stroke();
      ctx.beginPath();ctx.arc(f.x,f.y,2+u*13,0,Math.PI*2);ctx.strokeStyle=`rgba(194,255,139,${fade*.85})`;ctx.lineWidth=.65;ctx.stroke();
    }
    for(const l of crawler.legs){
      const hip=segmentPoint(l.index,0,l.side*6),f=l.foot;
      const dx=f.x-hip.x,dy=f.y-hip.y,d=Math.max(.001,Math.hypot(dx,dy));
      const b=crawler.spine[l.index],c=Math.cos(b.a),sn=Math.sin(b.a);
      const lift=l.step?Math.sin(clamp((now-l.step.t)/190,0,1)*Math.PI)*5:0;
      // Raised proximal joint and an outward ankle make all three sections readable.
      const outward={x:-sn*l.side,y:c*l.side};
      const forward={x:c,y:sn},fan=[1,.5,-.5,-1][l.row];
      const joint1={x:hip.x+outward.x*24+forward.x*fan*16,y:hip.y+outward.y*24+forward.y*fan*16-lift};
      const joint2={x:f.x-outward.x*12+forward.x*fan*8,y:f.y-outward.y*12+forward.y*fan*8-lift*.5};
      const points=[hip,joint1,joint2,f];
      path(points,'#020304',3.6);path(points,'#ff648b',1.35);
      if(neuralEvent){const progress=(now-neuralEvent.t-350-l.row*95)/440;if(progress>=0&&progress<=1.3){const head=clamp(progress,0,1)*3;for(let j=0;j<3;j++){const t=clamp(head-j,0,1);if(t>0)path([points[j],{x:points[j].x+(points[j+1].x-points[j].x)*t,y:points[j].y+(points[j+1].y-points[j].y)*t}],`rgba(145,255,49,${clamp((1.3-progress)*3,0,1)})`,2);}}}
      for(const j of [joint1,joint2]){ctx.beginPath();ctx.arc(j.x,j.y,2.0,0,Math.PI*2);ctx.fillStyle='#56ffad';ctx.fill();}
      ctx.beginPath();ctx.arc(f.x,f.y,1.1,0,Math.PI*2);ctx.fillStyle='#ff577e';ctx.fill();
    }
    // Digital specimen: an open ring skeleton, with a continuous curved spine.
    const spine=crawler.spine;
    path(spine,'#080509',2.3);path(spine,'#ff83ba',.75);
    const rings=[{i:0,r:2.7,rx:6.5},{i:2,r:10,rx:10},{i:5,r:7.5,rx:10},{i:8,r:9,rx:10},{i:11,r:6,rx:10},{i:14,r:4.3,rx:10},{i:17,r:2.8,rx:9},{i:18,r:1.3,rx:4}];
    for(let n=rings.length-1;n>=0;n--){const ring=rings[n],b=spine[ring.i];ctx.save();ctx.translate(b.x,b.y);ctx.rotate(b.a);ctx.scale(1.5,1.5);
      // A faint glass membrane keeps the ring skeleton visible through the surface.
      const glass=ctx.createLinearGradient(-ring.rx,-ring.r,ring.rx,ring.r);
      glass.addColorStop(0,'rgba(255,235,248,.22)');glass.addColorStop(.23,'rgba(255,153,206,.08)');glass.addColorStop(.58,'rgba(207,78,155,.025)');glass.addColorStop(1,'rgba(255,191,223,.14)');
      ctx.beginPath();ctx.ellipse(0,0,ring.rx,ring.r,0,0,Math.PI*2);ctx.fillStyle=glass;ctx.fill();
      ctx.beginPath();ctx.ellipse(-ring.rx*.12,-ring.r*.12,ring.rx*.78,ring.r*.73,0,-Math.PI*.85,-Math.PI*.35);ctx.strokeStyle='rgba(255,247,253,.8)';ctx.lineWidth=.55;ctx.stroke();
      // Transparent centre; outlined sections evoke a scanned three-dimensional specimen.
      ctx.beginPath();ctx.ellipse(0,0,ring.rx,ring.r,0,0,Math.PI*2);ctx.strokeStyle='#ff7bb3';ctx.lineWidth=.9;ctx.stroke();
      // Closely nested oval contours create a delicate glass wire skeleton.
      for(let layer=1;layer<=5;layer++){
        const inset=1-layer*.135;
        ctx.beginPath();ctx.ellipse(0,0,ring.rx*inset,ring.r*inset,0,0,Math.PI*2);
        ctx.strokeStyle=`rgba(255,158,203,${.40-layer*.035})`;ctx.lineWidth=.34;ctx.stroke();
      }
      for(const squeeze of [.28,.58]){
        ctx.beginPath();ctx.ellipse(0,0,ring.rx*squeeze,ring.r*.94,0,0,Math.PI*2);
        ctx.strokeStyle='rgba(255,195,221,.35)';ctx.lineWidth=.3;ctx.stroke();
      }
      ctx.beginPath();ctx.ellipse(0,0,ring.rx,ring.r,0,-Math.PI*.7,-Math.PI*.12);ctx.strokeStyle='#a1ff46';ctx.lineWidth=1;ctx.stroke();
      ctx.beginPath();ctx.ellipse(0,0,ring.rx,ring.r,0,Math.PI*.24,Math.PI*.6);ctx.strokeStyle='#a1ff46';ctx.lineWidth=.8;ctx.stroke();
      ctx.beginPath();ctx.arc(0,0,n===1?1.7:1,0,Math.PI*2);ctx.fillStyle='#ff9ac6';ctx.fill();ctx.restore();
    }
    const head=crawler.spine[0];for(const side of [-1,1]){path([segmentPoint(0,2,side*2),segmentPoint(0,14,side*7),segmentPoint(0,26,side*11)],'#ff648b',.65);}
    ctx.restore();
  }

  function reset(){
    crawler=null;footprints=[];memoryThreads=[];neuralEvent=null;
    w=OPTIONS.gridWidth; h=Math.round(w*(p.height*.96)/(p.width*.96));h=Math.max(60,h);
    field=new Float32Array(w*h);next=new Float32Array(w*h);img=p.createImage(w,h);
    buildTissue();
    for(let i=0;i<tissue.length;i++){tissue[i]*=.63;fibers[i]*=.8;}
    buildNeurons();initElastic();initCuts();initBrush();initGrowth();
    for(let i=0;i<field.length;i++)field[i]=tissue[i]*.9;
    propagationJob=null;lastBurstAt=-Infinity;blinkRecycle=0;
    count=0;recycle=0;pulses=[];gazeQueue=[];holdUntil=0;last=null;gaze=null;lastSeen=-Infinity;
    for(let i=0;i<OPTIONS.particles;i++){
      if(Math.random()<.48){
        const roots=[[.59,.38,.12],[.25,.72,.07],[.88,.76,.08]],c=roots[i%3];
        add(c[0]*w,c[1]*h,Math.sqrt(Math.random())*w*c[2]);
      }else add(2+Math.random()*(w-4),2+Math.random()*(h-4),0);
    }
  }
  function point(g){return g&&g.x>.02&&g.x<.98&&g.y>.02&&g.y<.98&&!covered(g)?
    {x:(g.x-.02)/.96*w,y:(g.y-.02)/.96*h}:null;}
  function burst(){
    const now=p.millis();if(!gaze||now-lastSeen>1000||neuralEvent||now-lastBurstAt<2500)return false;
    lastBurstAt=now;neuralEvent={t:now,origin:{...gaze},feet:new Array(8).fill(false),emitted:false};return true;
  }
  function emitPulse(origin){
    const now=p.millis();startFlood(origin.x,origin.y);
    // Redistribute the existing agents, preserving the burst size without growing frame cost.
    const amount=Math.min(OPTIONS.burst,count);
    for(let j=0;j<amount;j++){
      const i=blinkRecycle++%count,angle=Math.random()*Math.PI*2,r=Math.sqrt(Math.random())*13;
      X[i]=clamp(origin.x+Math.cos(angle)*r,2,w-3);Y[i]=clamp(origin.y+Math.sin(angle)*r,2,h-3);A[i]=Math.random()*Math.PI*2;
    }
    pulses.push({x:origin.x,y:origin.y,t:p.millis()});if(pulses.length>8)pulses.shift();
    paint(origin.x,origin.y,origin.x,origin.y,10,4);
    return true;
  }
  function paint(ax,ay,bx,by,r,strength){
    const steps=Math.max(1,Math.ceil(Math.hypot(bx-ax,by-ay)/3));
    for(let s=0;s<=steps;s++){
      const x=ax+(bx-ax)*s/steps,y=ay+(by-ay)*s/steps;
      for(let yy=Math.max(1,Math.floor(y-r));yy<Math.min(h-1,y+r);yy++)
      for(let xx=Math.max(1,Math.floor(x-r));xx<Math.min(w-1,x+r);xx++){
        const d=Math.hypot(xx-x,yy-y)/r;if(d<1){const k=yy*w+xx;field[k]=Math.min(25,field[k]+strength*(1-d));}
      }
    }
  }
  function sense(x,y,a,d){const xx=clamp(Math.round(x+Math.cos(a)*d),0,w-1),yy=clamp(Math.round(y+Math.sin(a)*d),0,h-1);return (field[yy*w+xx]+tissue[warpedIndex(xx,yy)]*3)*(1-damage[Math.floor(yy/4)*mw+Math.floor(xx/4)]);}
  function step(now,dt,current,previous){
    const profile=profiles[mode],sd=profile[0],sa=profile[1],turn=profile[2],speed=profile[3];
    // The separate live particle stream replaces the old painted pheromone stripe.
    const vx=current&&previous?clamp(current.x-previous.x,-22,22):0;
    const vy=current&&previous?clamp(current.y-previous.y,-22,22):0;
    for(let i=0;i<count;i++){
      let x=X[i],y=Y[i],a=A[i];
      const f=sense(x,y,a,sd),l=sense(x,y,a-sa,sd),r=sense(x,y,a+sa,sd);
      if(f<l||f<r)a+=(l>r?-turn:turn)*dt;
      a+=(Math.random()-.5)*.16*dt;
      if(current){const dx=x-current.x,dy=y-current.y,d2=dx*dx+dy*dy;
        if(d2<OPTIONS.radius*OPTIONS.radius){const q=Math.exp(-d2/(OPTIONS.radius*OPTIONS.radius*.35));
          x+=vx*q*.7;y+=vy*q*.7;
          const swirl=Math.atan2(dy,dx)+1.4,delta=Math.atan2(Math.sin(swirl-a),Math.cos(swirl-a));a+=delta*q*.11*dt;
        }
      }
      for(const pulse of pulses){const age=(now-pulse.t)/1000,dx=x-pulse.x,dy=y-pulse.y,d=Math.hypot(dx,dy),r=age*65;
        if(Math.abs(d-r)<9&&d>.01){const force=(1-age/2)*1.5*dt;x+=dx/d*force;y+=dy/d*force;}}
      x+=Math.cos(a)*speed*dt;y+=Math.sin(a)*speed*dt;
      if(x<2||x>w-3){a=Math.PI-a;x=clamp(x,2,w-3);}if(y<2||y>h-3){a=-a;y=clamp(y,2,h-3);}
      X[i]=x;Y[i]=y;A[i]=a;const k=Math.floor(y)*w+Math.floor(x);field[k]=Math.min(25,field[k]+OPTIONS.deposit*dt);
    }
    next.fill(0);const decay=Math.pow(OPTIONS.decay,dt);
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
      const k=y*w+x;next[k]=(field[k]*.5+(field[k-1]+field[k+1]+field[k-w]+field[k+w])*.125)*decay;
    }[field,next]=[next,field];
  }
  function softDamage(x,y){
    const gx=clamp(x/4,0,mw-1.001),gy=clamp(y/4,0,mh-1.001);
    const ix=Math.floor(gx),iy=Math.floor(gy),k=iy*mw+ix;
    const tx=gx-ix,ty=gy-iy;
    return (damage[k]*(1-tx)+damage[k+1]*tx)*(1-ty)+
      (damage[k+mw]*(1-tx)+damage[k+mw+1]*tx)*ty;
  }
  function render(){
    img.loadPixels();const px=img.pixels,renderNow=p.millis(),phase=renderNow*.0006;
    for(let i=0;i<field.length;i++){
      const flow=1-Math.exp(-field[i]*.28),j=i*4;
      const breath=.94+.06*Math.sin(phase+i%w*.012);
      const x=i%w,y=Math.floor(i/w),wi=warpedIndex(x,y);
      const mk=Math.min(mh-1,Math.floor(y/4))*mw+Math.min(mw-1,Math.floor(x/4));
      const wave=waveMap[mk];
      const wall=smoothTexture(tissue)*breath,fine=smoothTexture(fibers);
      const v=clamp(flow*.34+wall*.62+fine*.48,0,1),hot=Math.pow(v,3);
      // Monochrome tissue; green is reserved for the active network impulse.
      const body=smoothTexture(soma)*breath,core=smoothTexture(nuclei);
      const gray=Math.min(255,(v*210+hot*35+body*85)*(1-core*.94));
      const mask=clamp(wall*1.9+fine*.9+flow*.65,0,1);
      const flash=clamp(wave*1.65*mask,0,1)*(1-core);
      const intact=1-softDamage(x,y);
      const ink=1-Math.exp(-brush[i]*.72),light=Math.pow(ink,3);
      const under=(210+light*45)*ink*.98;
      const coverage=intact*clamp(body*1.8+wall*1.8+fine*.9+flow*.35+flash,0,1);
      const trail=under*(1-coverage);
      px[j]=Math.min(255,intact*(gray*(1-flash)+110*flash)+trail);
      px[j+1]=Math.min(255,intact*(gray*(1-flash)+255*flash)+trail);
      px[j+2]=Math.min(255,intact*(gray*(1-flash)+40*flash)+trail);px[j+3]=255;
    }img.updatePixels();p.drawingContext.imageSmoothingEnabled=true;p.drawingContext.imageSmoothingQuality='high';p.image(img,p.width*.02,p.height*.02,p.width*.96,p.height*.96);
  }
  function calibrate(){if(neon.mode!=='live'){status='Connect Live Neon first, then capture open eyes';return;}
    gate=new NeonEffects.BlinkGate();capture=p.millis();samples=[];stamp=null;status='Keep both eyes open for 2 seconds';}
  p.preload=()=>{mat=p.loadImage(MAT_URL);};
  p.setup=()=>{
    if(typeof NeonEffects.BlinkGate!=='function')throw Error('This sketch needs the current Donut MIDI workshop with BlinkGate support.');
    fitCanvas(true);p.pixelDensity(Math.min(3, p.displayDensity ? p.displayDensity() : 2));p.frameRate(30);gate=new NeonEffects.BlinkGate();reset();
    button=p.createButton('Capture open eyes · 2 s');button.position(8,8);button.mousePressed(calibrate);
  };
  p.draw=()=>{
    const now=p.millis(),raw=point(neon.update()),input=NeonEffects.read(neon);
    const dt=clamp((p.deltaTime||33.33)/33.33,.2,2);
    let g=raw;
    const protectedLive=input.live&&gate.reference!==null;
    if(protectedLive){
      // Buffer 100 ms so eyelid-related gaze errors preceding closure are discarded.
      const closing=!input.fresh||!input.worn||input.aperture===null||
        input.aperture<gate.reference*.78;
      if(closing){holdUntil=now+180;gazeQueue=[];}
      if(closing||now<holdUntil){g=null;last=null;}
      else if(raw){
        gazeQueue.push({g:raw,t:now});g=null;
        while(gazeQueue.length&&gazeQueue[0].t<=now-100)g=gazeQueue.shift().g;
      }else {g=null;gazeQueue=[];last=null;}
    }else {gazeQueue=[];holdUntil=0;}
    if(g){gaze=g;lastSeen=now;}
    if(capture!==null){
      if(input.live&&input.fresh&&input.worn&&input.aperture>0&&input.stamp!==null&&input.stamp!==stamp){samples.push(input.aperture);stamp=input.stamp;}
      if(now-capture>=2000){capture=null;if(samples.length>=15){samples.sort((a,b)=>a-b);gate.setReference(samples[Math.floor(samples.length/2)]);status='Eye reference ready · catch the gaze target to pulse';}
        else status='No reliable eyelid data · check Neon Companion eye state';}
    }else gate.update(input,now);
    pulses=pulses.filter(v=>now-v.t<2000);
    if(!paused){advancePropagation();growthTime+=dt*33.333;updateGrowth(growthTime);crawl(now,dt,g);updateCuts(now,null,null);elasticStep(now,dt,null,null);step(now,dt,null,null);brushStep(now,dt,null,null);}last=g;
    p.background(0);render();drawCrawler(now);drawMarkers();
    const cursor=g||(protectedLive&&input.fresh&&input.worn&&now<holdUntil&&now-lastSeen<1000?gaze:null);
    if(show&&cursor){
      const cx=p.width*(.02+cursor.x/w*.96),cy=p.height*(.02+cursor.y/h*.96);
      const scale=clamp(p.width/1000,.7,1.6),breath=1+.06*Math.sin(now*.004);
      // Layered translucent light remains distinct from the cyan Physarum.
      p.noStroke();
      for(let layer=10;layer>=1;layer--){
        p.fill(229,197,122,2+(10-layer)*.45);
        p.circle(cx,cy,(30+layer*8)*scale*breath);
      }
      p.noFill();p.stroke(246,220,160,185);p.strokeWeight(1.6*scale);
      p.circle(cx,cy,38*scale*breath);
      p.noStroke();p.fill(253,241,207,220);p.circle(cx,cy,10*scale);
      p.fill(255,255,255,255);p.circle(cx,cy,4*scale);
    }
    p.noStroke();p.fill(0);p.rect(p.width*.20,p.height*.015,p.width*.60,p.height*.04);
    p.fill(210);p.textAlign(p.CENTER,p.CENTER);p.textSize(Math.max(9,Math.min(12,p.width/90)));
    const label=input.live?(input.aperture===null?'LIVE · No eyelid data':status):'Guide the crawler with your gaze · footsteps disturb and heal · catch the gaze target to pulse';
    p.text(label,p.width*.5,p.height*.035);
  };
  p.mousePressed=()=>{};
  p.keyPressed=()=>{const k=(p.key||'').toLowerCase();if(k==='r')reset();if(k==='g')show=!show;if(k==='1')mode=0;if(k==='2')mode=1;if(k==='3')mode=2;if(k===' ') {paused=!paused;return false;}};
  p.windowResized=()=>{fitCanvas();reset();};
});
})();
