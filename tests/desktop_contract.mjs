import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source=fs.readFileSync(new URL('../src/desktop.js',import.meta.url),'utf8').replace(/^import .*\n/gm,'').replace('export default','const plugin =');
const value=x=>({get:()=>x});
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};
const coachingState=(mode='coach')=>({session:{id:'canonical-a',initialized:true,game_id:'game-a',coaching_queue:[
  {id:'event-a',game_id:'game-a',kind:'auto',prompt:'Review move one.'}]},board:{mode:'play',play_mode:mode}});

function desktop(overrides={}) {
  const env={focused:'chat-a',runtime:'runtime-a',profile:'default',activeProfile:'default',connection:'local',ownerConnection:'local',
    epoch:1,now:100000,busy:{},draft:'',state:coachingState(),fetchWait:null,draftWait:null,ackWait:null,fetchError:null,submitAccepted:true,
    stateCalls:0,...overrides};
  const contributions=[],intervals=[],submissions=[],acks=[],listeners={},disposers=[],rpcRoutes=[],opened=[],stored=new Map(overrides.stored||[]);
  const started={fetchWait:deferred(),draftWait:deferred(),ackWait:deferred(),createWait:deferred()};
  const hooks=[],effects=[];
  let hookIndex=0,requestRender=()=>{},renderedBoard=null,rendering=false,renderPending=false;
  const sameDeps=(first,second)=>first&&second&&first.length===second.length&&first.every((value,index)=>Object.is(value,second[index]));
  const React={
    createElement:(type,props,...children)=>({type,props,children}),
    useCallback:(callback,deps)=>{
      const index=hookIndex++,old=hooks[index];
      if(!old||!sameDeps(old.deps,deps))hooks[index]={callback,deps};
      return hooks[index].callback;
    },
    useState:initial=>{
      const index=hookIndex++;
      if(!hooks[index])hooks[index]={value:initial,set:next=>{
        if(!Object.is(hooks[index].value,next)){hooks[index].value=next;requestRender();}
      }};
      return [hooks[index].value,hooks[index].set];
    },
    useEffect:(effect,deps)=>{
      const index=hookIndex++,old=hooks[index];
      if(!old||!sameDeps(old.deps,deps)){
        hooks[index]={deps,cleanup:old?.cleanup};
        effects.push(()=>{hooks[index].cleanup?.();hooks[index].cleanup=effect();});
      }
    }
  };
  const routeListeners=new Set(),atom=get=>({get,listen:callback=>{routeListeners.add(callback);return ()=>routeListeners.delete(callback);}});
  let profileHolds=0;
  const host={state:{focusedStoredSessionId:atom(()=>env.focused),focusedSessionId:atom(()=>env.runtime),
    activeSessionId:atom(()=>env.primaryRuntime),cwd:value('/workspace'),
    focusedSessionProfile:atom(()=>env.profile),profile:atom(()=>env.activeProfile),connectionId:atom(()=>env.connection),
    focusedSessionOwner:atom(()=>env.ownerConnection?({connectionId:env.ownerConnection,profile:env.profile}):null),gateway:value('open'),busyBySession:{get:()=>env.busy}},
    composer:{getDraft:async()=>{started.draftWait.resolve();if(env.draftWait)await env.draftWait;return env.draft;},submit:(sid,text)=>{
      if(!env.submitAccepted)return false;
      submissions.push({sid,text});env.onSubmit?.();return true;
    }},revealPane:()=>{},undismissPane:()=>{},paneVisibility:()=>value(true),
    profileRoutes:async()=>{if(env.discoveryError)throw env.discoveryError;return [{connectionId:env.ownerConnection||env.connection,mode:'local',profile:env.profile,targetProfile:env.profile}];},
    retainProfile:async()=>{profileHolds++;let released=false;return ()=>{if(!released){released=true;profileHolds--;}};},
    requestProfile:async(route,method,params)=>{
      if(env.requireHold)assert.ok(profileHolds>0,'A multi-request startup must retain its route.');
      rpcRoutes.push({route,method,params});
      if(method==='session.info')return {profile_name:route.profile};
      if(method==='session.create'){started.createWait.resolve();if(env.createWait)await env.createWait;if(env.createError)throw env.createError;return {session_id:'created-runtime',stored_session_id:'created-stored'};}
      if(method==='session.title'){if(env.titleError)throw env.titleError;return {};}
      assert.equal(method,'command.dispatch');assert.equal(params.name,'chess');
      const {path,options}=JSON.parse(params.arg.slice('__board__ '.length));
      return {type:'exec',output:JSON.stringify(await boardRest(path,options))};
    },openSession:async(id,options)=>{if(env.requireHold)assert.ok(profileHolds>0);opened.push({id,options});}};
  const context={host,React,
    useValue:store=>store.get(),gatewayActivationEpoch:()=>env.epoch,createBoard:()=>function Board(){},
    window:{location:{hash:env.hash||'#/'}},Date:{now:()=>env.now},console:{warn:()=>{}}};
  const plugin=vm.runInNewContext(source+'\nplugin;',context);
  const boardRest=async(path,options)=>{
    if(path==='/diagnostic')return {ok:true};
    if(path.startsWith('/state?')){env.stateCalls++;started.fetchWait.resolve();if(env.fetchWait)await env.fetchWait;if(env.fetchError)throw env.fetchError;return structuredClone(env.state);}
    if(options?.body?.action==='coach_ack'){acks.push(options.body);started.ackWait.resolve();if(env.ackWait)await env.ackWait;return {ok:true};}
    if(options?.body?.action==='start')return {ok:true,session:{initialized:true},board:{id:'started-game'}};
    if(options?.body?.action==='find_games')return {ok:true,games:[]};
    throw Error(path);
  };
  const ctx={rest:boardRest,storage:{get:(key,fallback)=>stored.has(key)?stored.get(key):fallback,set:(key,v)=>stored.set(key,v)},
    register:contribution=>{contributions.push(contribution);return ()=>{const index=contributions.indexOf(contribution);if(index>=0)contributions.splice(index,1);};},
    onEvent:(name,callback)=>{listeners[name]=callback;return ()=>{};},setInterval:callback=>intervals.push(callback),
    setTimeout:callback=>callback(),addEventListener:()=>{},onDispose:callback=>disposers.push(callback)};
  plugin.register(ctx);
  const renderBoard=()=>{
    if(rendering){renderPending=true;return renderedBoard;}
    rendering=true;
    try{
      do{
        renderPending=false;hookIndex=0;
        const native=contributions.find(c=>c.area==='panes').render();renderedBoard=native.type();
        effects.splice(0).forEach(effect=>effect());
      }while(renderPending);
      return renderedBoard;
    }finally{rendering=false;}
  };
  requestRender=()=>{if(renderedBoard)renderBoard();};
  return {env,contributions,submissions,acks,listeners,stored,started,rpcRoutes,opened,renderBoard,deliver:intervals[0],
    currentBoard:()=>renderedBoard,profileHolds:()=>profileHolds,
    notifyRoute:()=>routeListeners.forEach(callback=>callback()),dispose:()=>disposers.forEach(callback=>callback())};
}

{
  const x=desktop();
  assert.equal(x.contributions.filter(c=>c.area==='titleBar.right').length,1);
  assert.equal(x.contributions.filter(c=>/sidebar|chat/i.test(c.area)).length,0);
  assert.match(x.contributions.find(c=>c.id==='knight-button').render().props.title,/show or hide the chessboard.*\/chess.*play Hermes.*review/i);
  x.env.busy={'runtime-a':true};await x.deliver();assert.equal(x.env.stateCalls,0);
  x.env.busy={};x.env.draft='My unfinished message';await x.deliver();assert.equal(x.submissions.length,0);
  x.env.draft='';await x.deliver();assert.equal(x.submissions.length,1);assert.equal(x.submissions[0].sid,'chat-a');assert.equal(x.acks.length,1);
  await x.deliver();assert.equal(x.submissions.length,1);assert.equal(x.acks.length,2);
  x.env.focused='durable-alias-a';x.env.runtime='runtime-alias-a';await x.deliver();
  assert.equal(x.submissions.length,1,'The same canonical event must stay deduplicated across session aliases.');
  x.env.state=coachingState('normal');x.env.state.session.coaching_queue[0].id='event-b';await x.deliver();
  assert.equal(x.submissions.length,1);assert.equal(x.acks.length,4);
  x.env.state.session.coaching_queue.push({id:'summary-a',game_id:'game-a',kind:'summary',prompt:'Requested summary.'});await x.deliver();
  assert.equal(x.submissions.length,2,'Normal mode still delivers explicitly requested summaries.');
}

// A turn can begin while either REST or the live draft read is pending.
for(const waitAt of ['fetchWait','draftWait']) {
  const wait=deferred(),x=desktop({[waitAt]:wait.promise});
  const delivery=x.deliver();await x.started[waitAt].promise;x.env.busy={'runtime-a':true};wait.resolve();await delivery;
  assert.equal(x.submissions.length,0,`Do not steer a turn that began during ${waitAt}.`);
  assert.equal(x.acks.length,0);
  x.env.busy={};x.env[waitAt]=null;await x.deliver();assert.equal(x.submissions.length,1);
}

// Undo or a mode change may finish after the event was fetched but before the
// composer draft read returns. Neither old feedback nor an old branch may send.
for(const change of [
  state=>{state.session.coaching_queue=[];state.board.history=[];},
  state=>{state.board.history=[{uci:'d2d4'},{uci:'e7e5'}];},
  state=>{state.board.play_mode='normal';}
]) {
  const state=coachingState(),wait=deferred();
  state.board.history=[{uci:'e2e4'},{uci:'e7e5'}];state.board.result='*';
  state.session.coaching_queue[0].position={initial_fen:'start',moves:['e2e4','e7e5'],result:'*'};
  const x=desktop({state,draftWait:wait.promise});
  const delivery=x.deliver();await x.started.draftWait.promise;change(x.env.state);wait.resolve();await delivery;
  assert.equal(x.submissions.length,0,'Recheck the recorded move and queue after the composer await.');
}

for(const change of [
  env=>{env.profile='other';env.activeProfile='other';},
  env=>{env.epoch++;},
  env=>{env.focused='chat-b';},
  env=>{env.runtime='runtime-replaced';},
  env=>{env.connection='remote';env.ownerConnection='remote';}
]) {
  for(const waitAt of ['fetchWait','draftWait']) {
    const wait=deferred(),x=desktop({[waitAt]:wait.promise});
    const delivery=x.deliver();await x.started[waitAt].promise;change(x.env);wait.resolve();await delivery;
    assert.equal(x.submissions.length,0,`A changed destination must invalidate ${waitAt}.`);assert.equal(x.acks.length,0);
  }
}

{
  const x=desktop({fetchError:new Error('Gateway still starting')});
  await x.deliver();x.env.fetchError=null;await x.deliver();
  assert.equal(x.submissions.length,1,'A failed first lookup must remain retryable.');
}
{
  const wait=deferred(),x=desktop({fetchWait:wait.promise}),stale=x.deliver();
  await x.started.fetchWait.promise;x.env.focused='chat-b';x.notifyRoute();
  x.env.focused='chat-a';x.notifyRoute();x.env.fetchWait=null;
  await x.deliver();assert.equal(x.submissions.length,1,'The old request cannot block the newly focused chat.');
  wait.resolve();await stale;assert.equal(x.submissions.length,1,'Returning to the same chat must not revive its old request.');
}
for(const change of [env=>{env.profile='other';env.activeProfile='other';},env=>{env.epoch++;}]) {
  const x=desktop({state:{session:{initialized:false},board:null}});
  await x.deliver();await x.deliver();assert.equal(x.env.stateCalls,1);
  change(x.env);x.env.state=coachingState();await x.deliver();
  assert.equal(x.submissions.length,1,'An uninitialized old backend cannot suppress discovery after a profile/restart change.');
}
for(const overrides of [{profile:'other'},{ownerConnection:'remote'}]) {
  const x=desktop(overrides);await x.deliver();
  assert.equal(x.env.stateCalls,2,'The board follows the visible chat without switching the ambient profile.');
  assert.equal(x.rpcRoutes[0].route.profile,x.env.profile);
  assert.equal(x.rpcRoutes[0].route.connectionId,x.env.ownerConnection);
  assert.equal(x.env.activeProfile,'default');assert.equal(x.env.connection,'local');
}
{
  const x=desktop({ownerConnection:null});await x.deliver();
  assert.equal(x.env.stateCalls,0,'An unknown tile must not fall through to the ambient backend.');
}
{
  const x=desktop({ownerConnection:null,primaryRuntime:'runtime-a'});await x.deliver();
  assert.equal(x.submissions.length,1,'An ordinary primary chat can resolve its owner through the gateway.');
  assert.equal(x.rpcRoutes[0].method,'session.info');
}
{
  const x=desktop({state:{session:{initialized:false},board:null}});
  await x.deliver();x.env.state=coachingState();x.env.now+=10001;await x.deliver();
  assert.equal(x.submissions.length,1,'Polling must recover when an initialization event was missed.');
}

{
  const x=desktop({submitAccepted:false});await x.deliver();assert.equal(x.acks.length,0);
  x.env.submitAccepted=true;await x.deliver();assert.equal(x.submissions.length,1);assert.equal(x.acks.length,1);
}
{
  const wait=deferred(),x=desktop({fetchWait:wait.promise});const delivery=x.deliver();x.dispose();wait.resolve();await delivery;
  assert.equal(x.submissions.length,0,'An unloaded plugin cannot finish submitting a pending coaching request.');
}
{
  const x=desktop();x.env.onSubmit=()=>{x.env.profile='other';x.env.activeProfile='other';};
  await x.deliver();assert.equal(x.submissions.length,1);assert.equal(x.acks.length,0,'Do not acknowledge through a backend selected by a synchronous composer callback.');
  x.env.onSubmit=null;x.env.profile='default';x.env.activeProfile='default';await x.deliver();
  assert.equal(x.submissions.length,1);assert.equal(x.acks.length,1);
}
{
  const wait=deferred(),x=desktop({state:coachingState('normal'),ackWait:wait.promise});
  x.env.state.session.coaching_queue.push({id:'event-b',game_id:'game-a',kind:'auto',prompt:'Other move.'});
  const delivery=x.deliver();await x.started.ackWait.promise;x.env.profile='other';x.env.activeProfile='other';wait.resolve();await delivery;
  assert.equal(x.acks.length,1,'A route change during an acknowledgement must stop the remaining queue.');
}

{
  const x=desktop({stored:[['open',true]]}),first=x.renderBoard();
  assert.equal(x.renderBoard().props.api,first.props.api,'Unchanged routes must preserve memoized API identity.');
  assert.equal(first.props.onPrompt('other-chat','Wrong chat'),false);
  assert.equal(first.props.onPrompt('chat-a','Explain this move.'),true);
  x.env.epoch++;assert.equal(first.props.onPrompt('chat-a','Old gateway'),false);
  await assert.rejects(first.props.api('/action',{method:'POST',body:{action:'resign'}}),/still connecting/);
  const fresh=x.renderBoard();assert.notEqual(fresh.props.key,first.props.key);assert.equal(fresh.props.onPrompt('chat-a','New gateway'),true);
  x.env.runtime='new-runtime';assert.equal(fresh.props.onPrompt('chat-a','Old runtime'),false);
}
{
  const x=desktop({stored:[['open',true]]});x.renderBoard();
  // A derived host atom can render the new chat before a later route listener
  // publishes its navigation token. The token must trigger its own rerender.
  x.env.focused='chat-b';x.env.runtime='runtime-b';const early=x.renderBoard();
  x.notifyRoute();const settled=x.currentBoard();
  assert.notEqual(settled.props.key,early.props.key,'A late navigation-token update must refresh the mounted board.');
  assert.notEqual(settled.props.api,early.props.api,'Memoized callbacks must capture the refreshed navigation token.');
  await assert.rejects(early.props.api('/state?session_id=chat-b'),/still connecting/);
  assert.equal((await settled.props.api('/state?session_id=chat-b')).session.game_id,'game-a');
  assert.equal(settled.props.onPrompt('chat-b','Current route works.'),true);
}
{
  const x=desktop({focused:null,runtime:null,stored:[['open',true]]}),board=x.renderBoard();
  assert.equal(board.props.onPrompt(null,'/chess play white normal'),true);
  assert.equal(x.submissions[0].sid,'new','Fresh-draft startup must address the exact new composer.');
  x.env.focused='created-chat';assert.equal(board.props.onPrompt(null,'Old draft'),false);
}
{
  const x=desktop({focused:null,runtime:null,stored:[['open',true]]}),board=x.renderBoard();
  await board.props.onStart({colour:'white',mode:'normal'});
  assert.equal(x.submissions.length,0,'Starting directly must not depend on slash-command submission.');
  assert.equal(x.rpcRoutes[0].method,'session.create');
  assert.equal(x.opened[0].id,'created-stored');
  const start=x.rpcRoutes.find(call=>call.method==='command.dispatch');
  assert.equal(start.params.session_id,'created-runtime');
  assert.equal(JSON.parse(start.params.arg.slice('__board__ '.length)).options.body.action,'start');
}
{
  const x=desktop({focused:null,runtime:null,stored:[['open',true]]}),board=x.renderBoard();
  await board.props.onStart({action:'find_games',platform:'chess.com',username:'Alice',refresh:true});
  const request=x.rpcRoutes.find(call=>call.method==='command.dispatch');
  assert.deepEqual(JSON.parse(request.params.arg.slice('__board__ '.length)).options.body,
    {action:'find_games',platform:'chess.com',username:'Alice',refresh:true});
  assert.equal(x.opened[0].id,'created-stored');assert.equal(x.submissions.length,0);
}
{
  const wait=deferred(),x=desktop({focused:null,runtime:null,stored:[['open',true]],createWait:wait.promise}),board=x.renderBoard();
  const starting=board.props.onStart({colour:'white',mode:'normal'});
  await x.started.createWait.promise;
  x.env.focused='another-chat';x.env.runtime='another-runtime';x.notifyRoute();
  wait.resolve();await assert.rejects(starting,/still connecting/);
  assert.equal(x.rpcRoutes.length,1,'Navigating away during chat creation must stop game startup.');
  assert.equal(x.opened.length,0,'Late chat creation must not steal focus from the new chat.');
}
{
  const wait=deferred(),x=desktop({focused:null,runtime:null,stored:[['open',true]],createWait:wait.promise}),board=x.renderBoard();
  const starting=board.props.onStart({colour:'white',mode:'normal'});
  await x.started.createWait.promise;
  x.notifyRoute();x.notifyRoute();
  assert.equal(x.currentBoard().props.key,board.props.key,'A refreshed owner object for the same chat must preserve the mounted board.');
  wait.resolve();await starting;
  assert.equal(x.opened[0].id,'created-stored','Background session-list refreshes must not cancel fresh-chat startup.');
}
{
  const wait=deferred(),x=desktop({fetchWait:wait.promise}),delivery=x.deliver();
  await x.started.fetchWait.promise;x.notifyRoute();wait.resolve();await delivery;
  assert.equal(x.submissions.length,1,'Refreshing the same owner during a read must not starve coaching delivery.');
}
{
  const x=desktop({focused:null,runtime:null,stored:[['open',true]],discoveryError:new Error('An unrelated remote gateway is offline')}),board=x.renderBoard();
  await board.props.onStart({colour:'white',mode:'normal'});
  assert.equal(x.opened[0].id,'created-stored','Local startup must not depend on discovering unrelated remote connections.');
}
for(const createError of [null,new Error('Could not create session')]) {
  const x=desktop({focused:null,runtime:null,stored:[['open',true]],requireHold:true,createError}),board=x.renderBoard();
  if(createError)await assert.rejects(board.props.onStart({mode:'normal'}),/Could not create session/);
  else await board.props.onStart({mode:'normal'});
  assert.equal(x.profileHolds(),0,'Release the startup connection after success or failure.');
}
{
  const x=desktop({focused:null,runtime:null,stored:[['open',true]],titleError:new Error('Title is already in use')}),board=x.renderBoard();
  await board.props.onStart({mode:'normal'});
  assert.equal(x.opened[0].id,'created-stored','An optional chat title must not prevent starting the game.');
  assert.match(x.rpcRoutes.find(call=>call.method==='session.title').params.title,/^Chess with Hermes · /);
  assert.equal(x.profileHolds(),0);
}
{
  const x=desktop();x.listeners['plugin.gambit.initialized']({payload:{session_id:'route-a',session_aliases:['chat-a']}});
  assert.equal(x.contributions.filter(c=>c.area==='panes').length,1);
  assert.doesNotThrow(()=>desktop({hash:'#/%malformed-route'}));
}

console.log('Desktop contract passed: toolbar hover help, exact session/profile/source routing, new-chat startup, busy/draft races, retryable discovery, scoped deduplication, Normal silence, disposal and gateway guards.');
