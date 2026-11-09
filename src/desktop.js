import { host, useValue, gatewayActivationEpoch } from '@hermes/plugin-sdk';
import * as React from 'react';

const h = React.createElement;
const Board = createBoard(React);
const PANE_ID = 'gambit:board';

function Knight({size=17}) {
  return h('svg',{viewBox:'0 0 24 24',width:size,height:size,fill:'none',stroke:'currentColor',strokeWidth:1.65,
    strokeLinecap:'round',strokeLinejoin:'round','aria-hidden':true},
    h('path',{d:'M5 21h15M7 18h11.2l-.5-3.1c-.3-2.1-1.4-3.8-3.1-5.2l1.2-3.3L12 3l-1.5 3-3.8 3.9.9 3.1 4.5-1.8L8.6 18'}),
    h('path',{d:'m10.5 6 3.1 1.4M7 18v3m11-3v3'}),h('circle',{cx:11.9,cy:8.5,r:.65,fill:'currentColor',stroke:'none'}));
}

export default {
  id:'gambit',name:'Gambit Chess',defaultEnabled:false,
  register(ctx) {
    const diagnostic=event=>ctx.rest('/diagnostic',{method:'POST',body:{event}}).catch(error=>console.warn('[gambit]',String(error)));
    diagnostic('desktop_registered');
    let visit=0;
    const routeRenderers=new Set();
    const route=()=>{
      const runtime=host.state.focusedSessionId.get(),owner=host.state.focusedSessionOwner?.get();
      const profile=owner?.profile||host.state.focusedSessionProfile.get()||host.state.profile?.get()||'default';
      const connection=owner?.connectionId||host.state.connectionId?.get()||'local';
      const sid=host.state.focusedStoredSessionId.get()||runtime;
      const primary=(!sid&&!runtime)||!!(runtime&&runtime===host.state.activeSessionId?.get());
      return {sid,runtime,profile,connection,owned:!host.state.focusedSessionOwner||!!owner,primary,epoch:gatewayActivationEpoch(),visit};
    };
    const routeIdentity=value=>[value.connection,value.profile,value.sid,value.runtime,value.owned,value.primary,value.epoch];
    const routeKey=value=>JSON.stringify([...routeIdentity(value),value.visit]);
    let lastRouteIdentity=JSON.stringify(routeIdentity(route()));
    const routeChanged=()=>{
      // The host recomputes owner objects when any session-list row changes.
      // Only a different destination invalidates work in the visible chat.
      const identity=JSON.stringify(routeIdentity(route()));
      if(identity===lastRouteIdentity)return;
      lastRouteIdentity=identity;visit++;routeRenderers.forEach(refresh=>refresh());
    };
    const routeStops=[host.state.focusedStoredSessionId,host.state.focusedSessionId,host.state.focusedSessionProfile,
      host.state.focusedSessionOwner,host.state.activeSessionId,host.state.profile,host.state.connectionId]
      .map(atom=>atom?.listen?.(routeChanged)).filter(Boolean);
    const sessionKey=(value,sid=value.sid)=>JSON.stringify([value.connection,value.profile,sid]);
    let disposed=false;
    const current=value=>!disposed&&routeKey(value)===routeKey(route())&&(value.owned||value.primary);
    const routingError=()=>new Error('This chat is still connecting. Keep it open and try again.');
    const gatewayRoute=async target=>{
      if(!current(target))throw routingError();
      // A focused local owner is already a complete public SDK route. Do not
      // make its board wait for unrelated remote gateway discovery.
      if(target.connection==='local')return {connectionId:'local',mode:'local',profile:target.profile,targetProfile:target.profile};
      const routes=typeof host.profileRoutes==='function'?await host.profileRoutes():[];
      if(!current(target))throw routingError();
      const found=routes.find(item=>item.connectionId===target.connection&&
        (item.profile===target.profile||item.targetProfile===target.profile));
      if(found)return found;
      throw routingError();
    };
    const requestAt=async(target,method,params,timeout=30000)=>{
      if(!current(target))throw routingError();
      if(typeof host.requestProfile==='function'){
        const destination=await gatewayRoute(target);
        return host.requestProfile(destination,method,params,timeout,{spawnPriority:'foreground'});
      }
      if(target.profile!==host.state.profile?.get()||target.connection!==(host.state.connectionId?.get()||'local'))throw routingError();
      return host.request(method,params,timeout);
    };
    const boardRequest=async(target,path,options={},address=target.runtime||target.sid)=>{
      if(!address)throw routingError();
      if(!target.owned)await requestAt(target,'session.info',{session_id:address});
      if(!current(target))throw routingError();
      const response=await requestAt(target,'command.dispatch',{
        name:'chess',session_id:address,arg:'__board__ '+JSON.stringify({path,options})
      },options.timeoutMs||60000);
      if(!current(target))throw routingError();
      try{return JSON.parse(response.output);}catch{throw new Error('Gambit is updating. Reload the chessboard and try again.');}
    };
    const idle=value=>current(value)&&!host.state.busyBySession.get()[value.runtime];
    const coachingMatches=(event,state)=>{
      if(event.game_id!==state.session.game_id)return false;
      if(!event.position)return true;
      const recorded=state.board?.history||[],moves=event.position.moves;
      if(event.position.result!==state.board?.result||moves.length>recorded.length||!moves.every((move,index)=>move===recorded[index].uci))return false;
      return event.kind!=='summary'||(moves.length===recorded.length&&event.position.result===state.board.result);
    };
    const knownSessions=new Set(ctx.storage.get('chessSessions',[]));
    const delivered=new Set(ctx.storage.get('deliveredCoaching',[]));
    const delivering=new Set();
    let lastCheckedRoute=null,lastCheckedAt=0;
    const deliverCoaching=async(force=false)=>{
      const target=route(),sid=target.sid,key=routeKey(target);
      if(!sid||delivering.has(key)||!idle(target)||(!force&&key===lastCheckedRoute&&!knownSessions.has(sessionKey(target))&&Date.now()-lastCheckedAt<10000))return;
      delivering.add(key);
      try{
        const state=await boardRequest(target,'/state?session_id='+encodeURIComponent(sid));
        if(!idle(target))return;
        lastCheckedRoute=key;lastCheckedAt=Date.now();
        if(state.session.initialized){knownSessions.add(sessionKey(target));ctx.storage.set('chessSessions',[...knownSessions].slice(-200));}
        for(const event of state.session.coaching_queue||[]){
          if(!idle(target))return;
          if(event.game_id!==state.session.game_id)continue;
          if(!coachingMatches(event,state)){
            await boardRequest(target,'/action',{method:'POST',body:{session_id:sid,action:'coach_ack',event_id:event.id}});continue;
          }
          if(state.board?.mode==='play'&&state.board?.play_mode==='normal'&&event.kind==='auto'){
            await boardRequest(target,'/action',{method:'POST',body:{session_id:sid,action:'coach_ack',event_id:event.id}});continue;
          }
          const deliveryKey=JSON.stringify([target.connection,target.profile,state.session.id||sid,event.game_id,event.id]);
          if(!delivered.has(deliveryKey)&&!delivered.has(event.id)){
            const draft=await host.composer.getDraft(sid);
            if(draft?.trim()||!idle(target))return;
            const latest=await boardRequest(target,'/state?session_id='+encodeURIComponent(sid));
            if(!idle(target))return;
            if(!latest.session.coaching_queue?.some(queued=>queued.id===event.id)||!coachingMatches(event,latest)||
              (latest.board?.mode==='play'&&latest.board?.play_mode==='normal'&&event.kind==='auto'))continue;
            if(!host.composer.submit(sid,event.prompt))return;
            delivered.add(deliveryKey);ctx.storage.set('deliveredCoaching',[...delivered].slice(-300));
          }
          // A composer callback can navigate synchronously. Never acknowledge
          // the old event through a newly selected backend.
          if(!current(target))return;
          await boardRequest(target,'/action',{method:'POST',body:{session_id:sid,action:'coach_ack',event_id:event.id}});
          break;
        }
      }catch(error){console.warn('[gambit] Coaching waits for its visible chat:',String(error));}
      finally{delivering.delete(key);}
    };
    ctx.onEvent('plugin.gambit.coaching.ready',event=>{
      const data=event.payload||event.data||event;
      const sid=host.state.focusedStoredSessionId.get()||host.state.focusedSessionId.get();
      if(data.session_id===sid||(data.session_aliases||[]).includes(sid))deliverCoaching(true);
    });
    ctx.setInterval(()=>deliverCoaching(),1800);
    const subscribe = callback => {
      const stops=['board.changed','initialized','hint'].map(name=>ctx.onEvent('plugin.gambit.'+name,event=>callback({...event,type:'plugin.gambit.'+name})));
      return ()=>stops.forEach(stop=>stop());
    };
    function NativeBoard() {
      const [,setVisit]=React.useState(visit);
      React.useEffect(()=>{
        const refresh=()=>setVisit(visit);
        routeRenderers.add(refresh);refresh();
        return()=>routeRenderers.delete(refresh);
      },[]);
      const sid=useValue(host.state.focusedStoredSessionId);
      const runtime=useValue(host.state.focusedSessionId);
      const profile=useValue(host.state.focusedSessionProfile);
      const busy=useValue(host.state.busyBySession);
      // Rebind the board even when reconnecting the same stored conversation.
      useValue(host.state.gateway||host.state.focusedSessionProfile);
      useValue(host.state.profile||host.state.focusedSessionProfile);
      useValue(host.state.activeSessionId||host.state.focusedSessionId);
      useValue(host.state.connectionId||host.state.focusedSessionProfile);
      useValue(host.state.focusedSessionOwner||host.state.focusedSessionProfile);
      const target=route();
      const boardApi=React.useCallback((path,options)=>{
        if(!current(target))return Promise.reject(routingError());
        return boardRequest(target,path,options);
      },[sid,runtime,profile,target.connection,target.epoch,target.visit]);
      const prompt=React.useCallback((sessionId,text)=>current(target)&&sessionId===target.sid&&host.composer.submit(sessionId||'new',text),
        [sid,runtime,profile,target.connection,target.epoch,target.visit]);
      const start=React.useCallback(async options=>{
        if(!current(target)||target.sid)throw routingError();
        const destination=await gatewayRoute(target);
        const release=typeof host.retainProfile==='function'?await host.retainProfile(destination,{spawnPriority:'foreground'}):()=>{};
        try{
          const created=await requestAt(target,'session.create',{source:'gui',cwd:host.state.cwd?.get()||undefined},60000);
          if(!current(target))throw routingError();
          const address=created.session_id,stored=created.stored_session_id||address;
          if(!address||!stored)throw new Error('Hermes could not create a chess chat. Try again.');
          const title=(options.action==='find_games'?'Chess review':'Chess with Hermes')+' · '+stored.slice(-10);
          try{await requestAt(target,'session.title',{session_id:address,title});}
          catch(error){console.warn('[gambit] Chat title could not be set:',String(error));}
          const result=await boardRequest(target,'/action',{method:'POST',body:{action:'start',...options}},address);
          if(!result.ok)throw new Error(result.message||'Could not start the chess game.');
          if(!current(target))throw routingError();
          await host.openSession(stored,{route:destination,awaitHydration:true});
        }finally{release();}
      },[sid,runtime,profile,target.connection,target.epoch,target.visit]);
      return h(Board,{key:routeKey(target),api:boardApi,sessionId:sid||runtime,onPrompt:prompt,onStart:start,subscribe,chatBusy:!!busy[runtime]});
    }
    const contribution={id:'board',area:'panes',title:'Gambit',
      data:{placement:'right',dock:{pane:'workspace',pos:'right'},width:'440px'},render:()=>h(NativeBoard)};
    let disposePane=null;
    const reveal=()=>{host.undismissPane?.(PANE_ID);host.revealPane?.(PANE_ID);};
    const show=()=>{if(!disposePane)disposePane=ctx.register(contribution);reveal();ctx.setTimeout(reveal,70);ctx.storage.set('open',true);diagnostic('board_opened');};
    const hide=()=>{disposePane?.();disposePane=null;ctx.storage.set('open',false);};
    const toggle=()=>{
      const visible=disposePane&&(typeof host.paneVisibility!=='function'||host.paneVisibility(PANE_ID).get());
      visible?hide():show();
    };
    const isChatRoute=()=>{
      const path=(window.location.hash||'#/').slice(1).split(/[?#]/)[0]||'/';
      if(path==='/')return true;
      let segment;
      try{segment=decodeURIComponent(path.slice(1));}catch{return false;}
      return !segment.includes('/')&&segment.length>=16&&/\d/.test(segment)&&/^[\w.:-]+$/.test(segment);
    };
    let disposeButton=null;
    const button=()=>{
      if(isChatRoute()&&!disposeButton){disposeButton=ctx.register({id:'knight-button',area:'titleBar.right',order:6,
        render:()=>h('button',{type:'button',title:'Gambit Chess: show or hide the chessboard. Start in chat with /chess to play Hermes or review your matches.','aria-label':'Show or hide chessboard',
          onPointerDown:event=>event.stopPropagation(),onClick:toggle,
          style:{WebkitAppRegion:'no-drag',appRegion:'no-drag',pointerEvents:'auto',position:'relative',zIndex:5,
            display:'inline-flex',alignItems:'center',justifyContent:'center',width:26,height:26,borderRadius:6,
            padding:0,border:0,background:'none',color:'var(--ui-text-tertiary,#8f9aab)',cursor:'pointer'}},h(Knight))});diagnostic('toolbar_registered');}
      else if(!isChatRoute()&&disposeButton){disposeButton();disposeButton=null;}
    };
    button();ctx.addEventListener(window,'hashchange',button);
    ctx.onEvent('plugin.gambit.initialized',event=>{
      const data=event.payload||event.data||event,sid=data.session_id;
      const target=route();
      [sid,...(data.session_aliases||[])].filter(id=>typeof id==='string'&&id).forEach(id=>knownSessions.add(sessionKey(target,id)));ctx.storage.set('chessSessions',[...knownSessions].slice(-200));
      if(current(target)&&(sid===target.sid||(data.session_aliases||[]).includes(target.sid)))show();
    });
    ctx.register({id:'open',area:'palette',data:{id:'gambit.open',label:'Gambit: Show or hide chessboard',
      keywords:['chess','gambit','board','knight'],run:toggle}});
    if(ctx.storage.get('open',false))show();
    ctx.onDispose(()=>{disposed=true;routeStops.forEach(stop=>stop());disposePane?.();disposeButton?.();});
  }
};
