// @neon-template: gaze-physarum
// Paste this WHOLE file into Donut MIDI Workshop, then Run.
// Original implementation, inspired by Jones-style Physarum and the two linked works.
// Editor supplies p5, neon, MAT_URL and NeonEffects. No extra libraries.
(() => {
const OPTIONS = { particles: 22000, maxParticles: 42000, burst: 1800,
  gridWidth: 560, decay: 0.975, deposit: 0.85, radius: 48 };
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
  function startFlood(x,y){
    // Weighted shortest paths: fast along membranes, slower across open pores.
    const dist=new Float64Array(mw*mh);dist.fill(Infinity);
    const source=clamp(Math.floor(y/4),0,mh-1)*mw+clamp(Math.floor(x/4),0,mw-1);
    const heap=[];
    function push(item){let i=heap.length;heap.push(item);while(i){const p=(i-1)>>1;if(heap[p][0]<=item[0])break;heap[i]=heap[p];i=p;}heap[i]=item;}
    function pop(){const first=heap[0],end=heap.pop();if(heap.length){let i=0;while(i*2+1<heap.length){let j=i*2+1;if(j+1<heap.length&&heap[j+1][0]<heap[j][0])j++;if(heap[j][0]>=end[0])break;heap[i]=heap[j];i=j;}heap[i]=end;}return first;}
    dist[source]=0;push([0,source]);
    while(heap.length){const [d,k]=pop();if(d>dist[k])continue;const x=k%mw,y=Math.floor(k/mw);
      const neighbors=[];if(x>0)neighbors.push(k-1);if(x<mw-1)neighbors.push(k+1);if(y>0)neighbors.push(k-mw);if(y<mh-1)neighbors.push(k+mw);
      for(const j of neighbors){const cost=1+5*(1-Math.max(membrane[k],membrane[j]));const next=d+cost;
        if(next<dist[j]){dist[j]=next;push([next,j]);}}
    }
    let duration=0;for(const d of dist)duration=Math.max(duration,d*12);
    floods.push({dist,start:p.millis(),duration});if(floods.length>3)floods.shift();
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
  function warpedIndex(x,y){
    const cx=clamp(x/4,0,mw-1.001),cy=clamp(y/4,0,mh-1.001),ix=Math.floor(cx),iy=Math.floor(cy),tx=cx-ix,ty=cy-iy,k=iy*mw+ix;
    const warp=a=>(a[k]*(1-tx)+a[k+1]*tx)*(1-ty)+(a[k+mw]*(1-tx)+a[k+mw+1]*tx)*ty;
    return clamp(Math.round(y-warp(bendY)),0,h-1)*w+clamp(Math.round(x-warp(bendX)),0,w-1);
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
    const sites=[];
    // Jittered sites produce irregular connected pores rather than radial trees.
    for(let yy=-1;yy<8;yy++)for(let xx=-1;xx<12;xx++){
      sites.push({x:(xx+.15+Math.random()*.8)*w/10,y:(yy+.15+Math.random()*.8)*h/6});
    }
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const qx=x+10*Math.sin(y*.038)+5*Math.sin(x*.023+y*.055);
      const qy=y+8*Math.sin(x*.029)+4*Math.cos(y*.047-x*.018);
      let d1=Infinity,d2=Infinity;
      for(const site of sites){const dx=qx-site.x,dy=qy-site.y,d=dx*dx+dy*dy;
        if(d<d1){d2=d1;d1=d;}else if(d<d2)d2=d;
      }
      const edge=(Math.sqrt(d2)-Math.sqrt(d1))*.5;
      const radial=Math.hypot((x/w-.53)*1.2,(y/h-.5)*.95);
      const envelope=clamp((.61-radial)*7,0,1);
      const wall=Math.exp(-edge*edge/2.8);
      // Fine contour filaments hug the membranes; outer tissue folds into parallel waves.
      const lamella=Math.pow(.5+.5*Math.cos(edge*3.5),18)*Math.exp(-edge*.12);
      const waves=Math.pow(.5+.5*Math.sin(y*1.9+9*Math.sin(x*.018)+4*Math.sin(y*.032+x*.026)),16);
      const outer=clamp((radial-.30)*5,0,1);
      const k=y*w+x;
      tissue[k]=wall*envelope;
      fibers[k]=(lamella*(1-outer)+waves*outer)*envelope;
    }
  }
  function reset(){
    w=OPTIONS.gridWidth; h=Math.round(w*(p.height*.96)/(p.width*.96));h=Math.max(60,h);
    field=new Float32Array(w*h);next=new Float32Array(w*h);img=p.createImage(w,h);
    buildTissue();initElastic();
    count=0;recycle=0;pulses=[];gazeQueue=[];holdUntil=0;last=null;gaze=null;lastSeen=-Infinity;
    for(let i=0;i<OPTIONS.particles;i++)add(2+Math.random()*(w-4),2+Math.random()*(h-4),0);
  }
  function point(g){return g&&g.x>.02&&g.x<.98&&g.y>.02&&g.y<.98&&!covered(g)?
    {x:(g.x-.02)/.96*w,y:(g.y-.02)/.96*h}:null;}
  function burst(){
    if(!gaze||p.millis()-lastSeen>1000)return;
    startFlood(gaze.x,gaze.y);
    for(let i=0;i<OPTIONS.burst;i++)add(gaze.x,gaze.y,13);
    pulses.push({x:gaze.x,y:gaze.y,t:p.millis()});if(pulses.length>8)pulses.shift();
    paint(gaze.x,gaze.y,gaze.x,gaze.y,10,4);
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
  function sense(x,y,a,d){const xx=clamp(Math.round(x+Math.cos(a)*d),0,w-1),yy=clamp(Math.round(y+Math.sin(a)*d),0,h-1);return field[yy*w+xx]+tissue[warpedIndex(xx,yy)]*3;}
  function step(now,dt,current,previous){
    const profile=profiles[mode],sd=profile[0],sa=profile[1],turn=profile[2],speed=profile[3];
    if(current){const prev=previous||current;paint(prev.x,prev.y,current.x,current.y,10,.85*dt);}
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
  function render(){
    img.loadPixels();const px=img.pixels,renderNow=p.millis(),phase=renderNow*.0006;
    for(let i=0;i<field.length;i++){
      const flow=1-Math.exp(-field[i]*.28),j=i*4;
      const breath=.94+.06*Math.sin(phase+i%w*.012);
      const x=i%w,y=Math.floor(i/w),wi=warpedIndex(x,y);
      const mk=Math.min(mh-1,Math.floor(y/4))*mw+Math.min(mw-1,Math.floor(x/4));
      const wave=waveMap[mk];
      const wall=tissue[wi]*breath,fine=fibers[wi];
      const v=clamp(flow*.62+wall*.55+fine*.32,0,1),hot=Math.pow(v,3);
      // Violet membranes / magenta colonies, with separately exposed near-white blink light.
      const red=5+v*174+flow*55+hot*55;
      const green=7+v*61+hot*112;
      const blue=18+v*203+hot*35;
      const mask=clamp(wall*1.9+fine*.9+flow*.65,0,1);
      const flash=clamp(wave*1.65*mask,0,1);
      px[j]=Math.min(255,red*(1-flash)+255*flash);
      px[j+1]=Math.min(255,green*(1-flash)+237*flash);
      px[j+2]=Math.min(255,blue*(1-flash)+255*flash);px[j+3]=255;
    }img.updatePixels();p.image(img,p.width*.02,p.height*.02,p.width*.96,p.height*.96);
  }
  function calibrate(){if(neon.mode!=='live'){status='Connect Live Neon first, then capture open eyes';return;}
    gate=new NeonEffects.BlinkGate();capture=p.millis();samples=[];stamp=null;status='Keep both eyes open for 2 seconds';}
  p.preload=()=>{mat=p.loadImage(MAT_URL);};
  p.setup=()=>{
    if(typeof NeonEffects.BlinkGate!=='function')throw Error('This sketch needs the current Donut MIDI workshop with BlinkGate support.');
    fitCanvas(true);p.pixelDensity(1);p.frameRate(30);gate=new NeonEffects.BlinkGate();reset();
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
      if(now-capture>=2000){capture=null;if(samples.length>=15){samples.sort((a,b)=>a-b);gate.setReference(samples[Math.floor(samples.length/2)]);status='Blink ready · close then reopen to bloom';}
        else status='No reliable eyelid data · check Neon Companion eye state';}
    }else if(gate.update(input,now))burst();
    pulses=pulses.filter(v=>now-v.t<2000);
    if(!paused){elasticStep(now,dt,g,last);step(now,dt,g,last);}last=g;
    p.background(5,7,18);render();drawMarkers();
    const cursor=g||(protectedLive&&input.fresh&&input.worn&&now<holdUntil&&now-lastSeen<1000?gaze:null);
    if(show&&cursor){
      const cx=p.width*(.02+cursor.x/w*.96),cy=p.height*(.02+cursor.y/h*.96);
      const scale=clamp(p.width/1000,.7,1.6),breath=1+.06*Math.sin(now*.004);
      // Layered translucent light remains distinct from the cyan Physarum.
      p.noStroke();
      for(let layer=10;layer>=1;layer--){
        p.fill(220,165,255,3+(10-layer)*.65);
        p.circle(cx,cy,(30+layer*8)*scale*breath);
      }
      p.noFill();p.stroke(255,200,250,210);p.strokeWeight(1.6*scale);
      p.circle(cx,cy,38*scale*breath);
      p.noStroke();p.fill(255,235,255,245);p.circle(cx,cy,10*scale);
      p.fill(255,255,255,255);p.circle(cx,cy,4*scale);
    }
    p.noStroke();p.fill(0);p.rect(p.width*.20,p.height*.015,p.width*.60,p.height*.04);
    p.fill(210);p.textAlign(p.CENTER,p.CENTER);p.textSize(Math.max(9,Math.min(12,p.width/90)));
    const label=input.live?(input.aperture===null?'LIVE · No eyelid data':status):'MOUSE · move to stir · click / B to bloom';
    p.text(label,p.width*.5,p.height*.035);
  };
  p.mousePressed=()=>{if(neon.mode==='live')return;const g=point({x:p.mouseX/p.width,y:p.mouseY/p.height});if(g){gaze=g;lastSeen=p.millis();burst();}};
  p.keyPressed=()=>{const k=(p.key||'').toLowerCase();if(k==='r')reset();if(k==='g')show=!show;if(k==='1')mode=0;if(k==='2')mode=1;if(k==='3')mode=2;if(k==='b'&&neon.mode!=='live')burst();if(k===' ') {paused=!paused;return false;}};
  p.windowResized=()=>{fitCanvas();reset();};
});
})();
