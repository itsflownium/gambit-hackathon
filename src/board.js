import { PIECES } from './pieces.js';
import { createCelebration } from './celebration.js';

export function createBoard(React) {
  const { createElement: h, useState, useEffect, useRef, useCallback } = React;
  const Celebration = createCelebration(React);
  const glyphs = {
    knight:'M5 21h15M7 18h11l-.5-3c-.3-2-1.4-4-3-5l1-3-4-4-1.5 3L7 10l1 3 4-2-3.5 7M10.5 6l3 1.5',
    first:'M6 5v14M18 5l-9 7 9 7z', previous:'m15 5-7 7 7 7', play:'m8 5 11 7-11 7z', pause:'M9 5v14M15 5v14',
    next:'m9 5 7 7-7 7',last:'M18 5v14M6 5l9 7-9 7z',
    flip:'M7 3v18m-4-14 4-4 4 4M17 21V3m-4 14 4 4 4-4',more:'M5 12h.01M12 12h.01M19 12h.01',
    hint:'M9 18h6m-5 3h4M8.5 14.5a6 6 0 1 1 7 0L15 18H9z',
    back:'M20 12H4m6-6-6 6 6 6',undo:'m9 5-5 5 5 5M4 10h9a7 7 0 0 1 7 7',external:'M14 3h7v7m0-7L10 14M21 14v6H4V3h6',
    flag:'M5 21V4m0 0c5-4 9 4 14 0v10c-5 4-9-4-14 0',folder:'M3 7h7l2 2h9v11H3zM3 7V4h7l2 3',close:'m6 6 12 12M18 6 6 18'
  };
  const icon = (name,size=16) => h('svg',{viewBox:'0 0 24 24',width:size,height:size,fill:'none',stroke:'currentColor',strokeWidth:name==='more'?3:1.65,strokeLinecap:'round',strokeLinejoin:'round','aria-hidden':true},h('path',{d:glyphs[name]||glyphs.more}));
  const INITIAL = {};
  ['rnbqkbnr','pppppppp','8','8','8','8','PPPPPPPP','RNBQKBNR'].forEach((row, i) => {
    [...row].forEach((piece, j) => { if (!/\d/.test(piece)) INITIAL['abcdefgh'[j] + (8-i)] = piece; });
  });
  const NAMES = {p:'pawn',n:'knight',b:'bishop',r:'rook',q:'queen',k:'king'};
  const formatGameDate=game=>{
    const date=game?.ended_at?new Date(game.ended_at*1000):game?.date?new Date(game.date+'T00:00:00Z'):null;
    return date&&!Number.isNaN(date.getTime())?new Intl.DateTimeFormat(undefined,{day:'numeric',month:'short',year:'numeric',...(game.ended_at?{hour:'numeric',minute:'2-digit'}:{timeZone:'UTC'})}).format(date):'Date unavailable';
  };
  const css = `
  .gambit-board-root{height:100%;min-height:250px;display:flex;flex-direction:column;background:#0d131c;color:#dce4f0;font:12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;box-sizing:border-box;position:relative;overflow:hidden;isolation:isolate}
  .gambit-board-root *{box-sizing:border-box}.gambit-board-root button{font:inherit;color:inherit;cursor:pointer}.gambit-board-root button:disabled{cursor:default;opacity:.42}
  .gambit-board-root .gb-header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;padding:14px 16px 10px;flex-shrink:0}.gambit-board-root .gb-header-actions{display:flex;align-items:center;gap:6px;margin-left:auto}
  .gambit-board-root .gb-brand{display:flex;align-items:center;gap:8px;color:#a9bddb;font-size:11px;letter-spacing:.12em;font-weight:600}.gambit-board-root .gb-brand svg{color:#8baeea}
  .gambit-board-root .gb-new{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid #3a5276;border-radius:7px;background:#1b2c44;color:#c9dcfa;padding:0 11px;height:31px;white-space:nowrap;font-size:11px;font-weight:600}
  .gambit-board-root .gb-new:hover:not(:disabled){background:#253d5c;border-color:#6284b4}
  .gambit-board-root .gb-match{margin:0 16px 5px;padding:9px 10px;border:1px solid #27374c;border-radius:7px;background:#121d2b;flex-shrink:0;min-width:0}
  .gambit-board-root .gb-match-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0}.gambit-board-root .gb-match-source{display:inline-flex;align-items:center;gap:5px;min-width:0;font-size:11px;font-weight:600;color:#aac8f4;text-decoration:none}.gambit-board-root a.gb-match-source:hover{text-decoration:underline;color:#d0e2ff}.gambit-board-root a.gb-match-source:focus-visible{outline:2px solid #8cb3ff;outline-offset:3px;border-radius:2px}.gambit-board-root .gb-match-source span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.gambit-board-root .gb-match-source svg{flex-shrink:0}.gambit-board-root .gb-match-type{color:#8298b7;font-size:9px;white-space:nowrap}.gambit-board-root .gb-match-details{font-size:10px;color:#97a9c1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:5px}
  .gambit-board-root .gb-bar{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 0;flex-shrink:0;min-height:36px}
  .gambit-board-root .gb-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:65%;color:var(--ui-text-secondary,#aeb9ca);font-weight:500}
  .gambit-board-root .gb-status{display:inline-flex;align-items:center;gap:5px;color:#a4c9b8;font-size:10px;white-space:nowrap}.gambit-board-root .gb-status:before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor}.gambit-board-root .gb-status.pending{color:#cdb58d}.gambit-board-root .gb-status.replay{color:#8eabc8}
  .gambit-board-root .gb-stage{flex:1;min-height:0;position:relative;display:grid;place-items:center;padding:0 16px}.gambit-board-root .gb-position{max-width:100%}
  .gambit-board-root .gb-board{position:relative;display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);border-radius:5px;overflow:hidden;box-shadow:0 8px 28px #0003;flex-shrink:0;isolation:isolate}
  .gambit-board-root .gb-square{position:relative;border:0;border-radius:0;min-width:0;min-height:0;margin:0;padding:0;display:grid;place-items:center;touch-action:manipulation;outline-offset:-3px}
  .gambit-board-root .gb-square.light{background:#c4d0df}.gambit-board-root .gb-square.dark{background:#6a809d}
  .gambit-board-root .gb-square.last:after{content:'';position:absolute;inset:0;background:#8ebce95c;pointer-events:none;z-index:0}
  .gambit-board-root .gb-square.chosen{box-shadow:inset 0 0 0 3px #3979ff;z-index:1}.gambit-board-root .gb-square.checked{background:radial-gradient(ellipse,#d14a4a 0%,#b45c65 50%,#687c93 100%)}
  .gambit-board-root .gb-square:focus-visible{outline:3px solid #327aff;z-index:3}.gambit-board-root .gb-piece{width:88%;height:88%;display:grid;place-items:center;z-index:1;pointer-events:none;filter:drop-shadow(0 1px 1px #0003)}
  .gambit-board-root .gb-piece svg{width:100%;height:100%;display:block}.gambit-board-root .gb-dot{position:absolute;width:24%;height:24%;border-radius:50%;background:#14355e65;pointer-events:none;z-index:2}
  .gambit-board-root .gb-ring{position:absolute;inset:5%;border-radius:50%;border:5px solid #14355e65;pointer-events:none;z-index:2}
  .gambit-board-root .gb-coord{position:absolute;z-index:3;font-size:9px;font-weight:600;line-height:1;pointer-events:none}.gambit-board-root .light .gb-coord{color:#405b7d}.gambit-board-root .dark .gb-coord{color:#d9e4f1}
  .gambit-board-root .gb-rank{top:4px;left:4px}.gambit-board-root .gb-file{bottom:3px;right:4px}
  .gambit-board-root .gb-controls{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:5px;padding:7px 16px 14px;min-height:42px;flex-shrink:0}
  .gambit-board-root .gb-control{display:inline-flex;align-items:center;justify-content:center;gap:5px;appearance:none;border:1px solid #283548;background:#111b28;border-radius:7px;min-width:30px;height:30px;padding:0 8px;color:#a9b8cd;line-height:1;font-size:11px}
  .gambit-board-root .gb-control:hover:not(:disabled){border-color:#6797f7;color:#8cb3ff;background:#3e68ad18}.gambit-board-root .gb-primary{color:#8cb3ff;border-color:#3f6cb8}
  .gambit-board-root .gb-count{font-variant-numeric:tabular-nums;color:var(--ui-text-tertiary,#8792a5);font-size:10px;min-width:49px;text-align:center}
  .gambit-board-root .gb-overlay{position:absolute;inset:0;background:#0c1422b8;display:flex;align-items:center;justify-content:center;z-index:5;padding:20px;backdrop-filter:blur(2px)}
  .gambit-board-root .gb-message{max-width:290px;text-align:center;line-height:1.65;color:#cbd6e7}.gambit-board-root .gb-message strong{display:block;font-size:15px;color:#f0f4fb;margin-bottom:5px}.gambit-board-root code{color:#94b9ff;background:#2d467c55;border-radius:4px;padding:2px 5px}
  .gambit-board-root .gb-error{color:#e1a7a7;font-size:11px;padding:0 16px 10px;line-height:1.5;flex-shrink:0}
  .gambit-board-root .gb-menu{position:absolute;bottom:52px;right:16px;left:auto;width:224px;max-width:calc(100% - 32px);max-height:calc(100% - 68px);overflow-y:auto;overscroll-behavior:contain;min-width:0;height:auto;background:#151e2c;border:1px solid #303d50;border-radius:11px;padding:6px;box-shadow:0 14px 40px #0009;z-index:20;color:#d0dced;opacity:1}
  .gambit-board-root .gb-menu button{appearance:none;display:flex;align-items:center;gap:9px;width:100%;min-width:0;height:34px;min-height:0;text-align:left;background:transparent;border:0;padding:0 9px;border-radius:6px;font:12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.2;color:#c5d2e4}.gambit-board-root .gb-menu button:hover{background:#253449}.gambit-board-root .gb-menu .gb-danger{color:#e0a0a6}.gambit-board-root .gb-menu-heading{font-size:9px;letter-spacing:.1em;color:#7e91ac;padding:7px 9px 5px}.gambit-board-root .gb-menu-separator{height:1px;background:#2a3546;margin:5px 3px}.gambit-board-root .gb-mode-switch{display:flex;gap:3px;background:#0d1521;border-radius:6px;padding:3px;margin:3px}.gambit-board-root .gb-mode-switch button{justify-content:center;height:28px;font-size:11px}.gambit-board-root .gb-mode-switch .selected{background:#2a3e5a;color:#d8e8ff}.gambit-board-root .gb-menu-note{font-size:10px;color:#8699b4;padding:5px 9px 7px}
  .gambit-board-root .gb-modal{position:absolute;inset:0;background:#070d16e8;z-index:25;display:grid;place-items:center;padding:20px}
  .gambit-board-root .gb-import-overlay{position:absolute;inset:0;background:#070d16eb;z-index:30;display:flex;align-items:center;justify-content:center;padding:16px}
  .gambit-board-root .gb-import-dialog{display:flex;flex-direction:column;width:100%;max-width:390px;max-height:100%;min-height:0;background:#141f2f;border:1px solid #34465e;border-radius:12px;box-shadow:0 20px 60px #0007;overflow:hidden}
  .gambit-board-root .gb-import-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:15px 16px 0}.gambit-board-root .gb-import-heading h2{margin:0;color:#e1eaf8;font-size:15px;font-weight:600}.gambit-board-root .gb-import-description{margin:5px 16px 14px;color:#93a6c0;font-size:11px;line-height:1.5}
  .gambit-board-root .gb-import-form{padding:0 16px 14px;flex-shrink:0}.gambit-board-root .gb-platforms{display:flex;gap:4px;padding:3px;background:#0b1420;border:1px solid #27394f;border-radius:8px;margin-bottom:13px}.gambit-board-root .gb-platforms button{flex:1;border:0;background:transparent;color:#8fa4c0;border-radius:5px;height:31px;font-weight:500}.gambit-board-root .gb-platforms button[aria-pressed=true]{background:#294364;color:#d8e8ff}
  .gambit-board-root .gb-input-label{display:block;margin-bottom:6px;color:#b7c6db;font-size:11px}.gambit-board-root .gb-search-row{display:flex;gap:7px}.gambit-board-root .gb-username{font:inherit;min-width:0;flex:1;background:#0d1724;border:1px solid #354a65;border-radius:7px;height:34px;padding:0 10px;color:#e3edfb;outline:none}.gambit-board-root .gb-username::placeholder{color:#697e9b}.gambit-board-root .gb-username:focus{border-color:#78a1df;box-shadow:0 0 0 2px #659aff20}.gambit-board-root .gb-search-row .gb-new{height:34px}
  .gambit-board-root .gb-import-results{overflow-y:auto;overscroll-behavior:contain;min-height:0;border-top:1px solid #2a3b50;padding:5px 8px 8px}.gambit-board-root .gb-results-label{font-size:10px;color:#98acc8;padding:8px}.gambit-board-root .gb-import-game{appearance:none;display:flex;align-items:center;gap:9px;width:100%;padding:11px 9px;border:0;border-radius:7px;background:transparent;text-align:left;line-height:1.5}.gambit-board-root .gb-import-game:hover:not(:disabled){background:#223550}.gambit-board-root .gb-game-number{display:grid;place-items:center;width:23px;height:23px;flex-shrink:0;background:#2a405e;border-radius:6px;font-size:10px;color:#b4cef2}.gambit-board-root .gb-game-info{min-width:0;flex:1}.gambit-board-root .gb-game-info strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;font-weight:500;color:#d3dff0}.gambit-board-root .gb-game-info small{display:block;color:#8da3c0;font-size:10px}.gambit-board-root .gb-import-notice{color:#acbdd5;font-size:11px;line-height:1.5;padding:9px 16px 13px;margin:0}.gambit-board-root .gb-import-error{color:#e4a6ad;font-size:11px;line-height:1.5;padding:0 16px 12px}
  .gambit-board-root .gb-import-results,.gambit-board-root .gb-menu{scrollbar-width:thin;scrollbar-color:#405672 #141f2f}.gambit-board-root .gb-import-results::-webkit-scrollbar,.gambit-board-root .gb-menu::-webkit-scrollbar{width:7px}.gambit-board-root .gb-import-results::-webkit-scrollbar-track,.gambit-board-root .gb-menu::-webkit-scrollbar-track{background:#141f2f}.gambit-board-root .gb-import-results::-webkit-scrollbar-thumb,.gambit-board-root .gb-menu::-webkit-scrollbar-thumb{background:#405672;border:2px solid #141f2f;border-radius:8px}
  .gambit-board-root .gb-dialog{background:#182233;border:1px solid #34445e;padding:18px;border-radius:12px;max-width:300px;line-height:1.6;text-align:center}.gambit-board-root .gb-promotions{display:flex;gap:5px;margin-top:12px}.gambit-board-root .gb-promotions button{width:52px;height:56px;background:#879bb54d;border:1px solid #778eaf;border-radius:5px;padding:3px}.gambit-board-root .gb-promotions svg{width:100%;height:100%}
  .gambit-board-root .gb-arrow{position:absolute;inset:0;width:100%;height:100%;z-index:4;pointer-events:none}.gambit-board-root .gb-fallback{color:#bba37b;font-size:10px}.gambit-board-root .gb-replay-note{font-size:10px;line-height:1.4;color:#8094b0;text-align:center;padding:0 16px 7px;flex-shrink:0}
  @media(prefers-reduced-motion:no-preference){.gambit-board-root .gb-piece{animation:gb-appear .12s ease-out}@keyframes gb-appear{from{opacity:.6;transform:scale(.95)}to{opacity:1;transform:scale(1)}}}
  `;

  return function Board({ api, sessionId, onPrompt, onStart, subscribe, chatBusy=false }) {
    const [state, setState] = useState(null), [error, setError] = useState('');
    const [selected, setSelected] = useState(null), [promotion, setPromotion] = useState(null);
    const [flipped, setFlipped] = useState(false), [menu, setMenu] = useState(false);
    const [confirm, setConfirm] = useState(false), [autoplay, setAutoplay] = useState(false);
    const [requesting,setRequesting] = useState(''), [finish,setFinish] = useState(null);
    const [importOpen,setImportOpen]=useState(false),[importPlatform,setImportPlatform]=useState('chess.com');
    const [importUsername,setImportUsername]=useState(''),[importResults,setImportResults]=useState(null);
    const [guided, setGuided] = useState(true), [coachPending, setCoachPending] = useState(false);
    const [speed,setSpeed]=useState(1);
    const [hint, setHint] = useState(null), [size, setSize] = useState(360), [now, setNow] = useState(Date.now());
    const stage = useRef(null), mounted = useRef(true), sequence = useRef(0), active = useRef(false), reading=useRef(false);
    const squares = useRef({}), seenBusy = useRef(false), networkError=useRef(false);
    const importTrigger=useRef(null),importClose=useRef(null);
    const board = state?.board;
    const sid = sessionId;
    const identity = useRef(sid), boardRef=useRef(board), actRef=useRef(null);
    identity.current=sid;boardRef.current=board;
    const load = useCallback(async () => {
      if (!sid || active.current || reading.current) return;
      reading.current=true;
      const version = ++sequence.current;
      try {
        const value = await api('/state?session_id=' + encodeURIComponent(sid));
        if (mounted.current && version === sequence.current) { setState(value); if(networkError.current){setError('');networkError.current=false;} }
      } catch (err) {
        if (mounted.current && version === sequence.current) {networkError.current=true;setError(String(err.message || err));}
      } finally {reading.current=false;}
    }, [api, sid]);
    useEffect(() => {
      mounted.current = true; load();
      const timer = setInterval(() => {setNow(Date.now());load();}, 1200);
      return () => { mounted.current=false; sequence.current++; clearInterval(timer); };
    }, [load]);
    useEffect(() => {
      if (!stage.current) return;
      const resize = () => setSize(Math.max(80, Math.floor(Math.min(stage.current.clientWidth-32, stage.current.clientHeight-76))));
      const observer = new ResizeObserver(resize); observer.observe(stage.current); resize();
      return () => observer.disconnect();
    }, []);
    useEffect(() => {setSelected(null);setPromotion(null);setHint(null);}, [board?.fen]);
    useEffect(() => {
      if (chatBusy) seenBusy.current = true;
      if (!chatBusy && seenBusy.current) {seenBusy.current=false;setCoachPending(false);}
    }, [chatBusy]);
    useEffect(() => {
      if (!coachPending) return;
      const timer = setTimeout(() => {if (!seenBusy.current) setCoachPending(false);}, 3000);
      return () => clearTimeout(timer);
    }, [coachPending]);
    useEffect(() => subscribe ? subscribe(event => {
      const data = event.payload || event.data || event;
      if (data.session_id && data.session_id !== sid && !(data.session_aliases||[]).includes(sid)) return;
      if (event.type?.endsWith('.hint') && data.game_id === board?.id && data.ply === board?.ply) setHint(data);
      else load();
    }) : undefined, [subscribe, sid, board?.id, board?.ply, load]);

    const sendPrompt = useCallback(text => {
      const sent = onPrompt?.(sid, text);
      if (!sent) {setError('Open the coaching chat for this board, then try again.');setAutoplay(false);}
      return sent;
    }, [onPrompt, sid]);
    const act = useCallback(async (action, data={}) => {
      if (active.current || !sid) return null;
      active.current=true; sequence.current++;networkError.current=false;setError('');setRequesting(action);
      const alive=()=>mounted.current&&identity.current===sid;
      try {
        const body={session_id:sid, action,game_id:board?.id, revision:board?.revision, ...data};
        let result = await api('/action', {method:'POST',body});
        if(!alive())return null;
        if(result.error==='stale_position'&&['resign','set_mode','undo','claim_draw'].includes(action)){
          const latest=await api('/state?session_id='+encodeURIComponent(sid));
          if(!alive())return null;
          if(latest.board?.id===body.game_id)result=await api('/action',{method:'POST',body:{...body,revision:latest.board.revision}});
        }
        if(!alive())return null;
        if (!result.ok) throw new Error(result.message || 'This action could not be completed.');
        if (result.session) setState(result);
        if(action==='resign'&&result.board?.result!=='*'){
          setFinish({id:result.board.id,result:result.board.result,mode:result.board.play_mode||'normal'});
          setAutoplay(false);
        }
        setSelected(null); setMenu(false); return result;
      } catch (err) {if(alive())setError(String(err.message||err));return null;}
      finally {active.current=false;if(alive())setRequesting('');}
    }, [api,sid,board?.id,board?.revision]);
    actRef.current=act;
    const closeImport=()=>{setImportOpen(false);setTimeout(()=>{if(mounted.current)importTrigger.current?.focus();},0);};
    const showImport=()=>{
      const search=state?.session?.last_search;
      if(!importUsername&&search?.username&&Array.isArray(search.games)){setImportPlatform(search.platform);setImportUsername(search.username);setImportResults({ok:true,...search});}
      setMenu(false);setAutoplay(false);setError('');setImportOpen(true);
    };
    useEffect(()=>{
      const search=state?.session?.last_search;
      if(!board&&!importUsername&&search?.username&&Array.isArray(search.games)){
        setImportPlatform(search.platform);setImportUsername(search.username);
        setImportResults({ok:true,...search});setImportOpen(true);
      }
    },[state?.session?.last_search,board,importUsername]);
    useEffect(()=>{if(importOpen&&requesting)importClose.current?.focus();},[importOpen,requesting]);
    const findImported=async before=>{
      if(!sid){
        if(onStart){
          if(active.current)return;
          active.current=true;
          setRequesting('find_games');setError('');
          try{await onStart({action:'find_games',platform:importPlatform,username:importUsername.trim(),limit:10,refresh:true});}
          catch(error){if(mounted.current)setError(error.message||'Could not find games. Try again.');}
          finally{active.current=false;if(mounted.current)setRequesting('');}
        }else if(sendPrompt('/chess '+importPlatform+' '+importUsername.trim()))closeImport();
        return;
      }
      setImportResults(null);
      const result=await act('find_games',{platform:importPlatform,username:importUsername.trim(),limit:10,refresh:true,...(before?{before}:{})});
      if(result&&mounted.current)setImportResults(result);
    };
    const searchGames=event=>{event.preventDefault();findImported();};
    const openImported=async game=>{
      const result=await act('open_replay',{platform:importResults.platform,username:importResults.username,source_id:game.source_id,game_number:game.number});
      if(result&&mounted.current){closeImport();setFlipped(false);setFinish(null);setCoachPending(false);}
    };

    const startGame = useCallback(async () => {
      setAutoplay(false);setMenu(false);setConfirm(false);
      const mode=finish?.mode||(board?.mode==='play'?board.play_mode:'normal')||'normal';
      if(!sid){
        if(onStart){
          if(active.current)return;
          active.current=true;
          setRequesting('start');setError('');
          try{await onStart({colour:'white',mode});}
          catch(error){if(mounted.current)setError(error.message||'Could not start the game. Try again.');}
          finally{active.current=false;if(mounted.current)setRequesting('');}
        }else sendPrompt('/chess play white '+mode);
        return;
      }
      const next=await act('start',{colour:'white',mode});
      if(next){setFinish(null);setFlipped(false);setCoachPending(false);}
    },[act,sid,sendPrompt,onStart,board?.mode,board?.play_mode,finish?.mode]);
    useEffect(()=>{
      if(!finish)return;
      const timer=setTimeout(async()=>{
        if(!mounted.current||boardRef.current?.id!==finish.id)return;
        const next=await actRef.current('start',{colour:'white',mode:finish.mode});
        if(next&&mounted.current){setFinish(null);setFlipped(false);setCoachPending(false);}
      },3000);
      return()=>clearTimeout(timer);
    },[finish?.id,sid]);
    useEffect(()=>{if(finish&&board?.id&&board.id!==finish.id)setFinish(null);},[board?.id,finish?.id]);

    const beginPractice=useCallback(async square=>{
      setAutoplay(false);setCoachPending(false);
      const result=await act('practice',{view_revision:board?.view_revision,mode:'coach'});
      if(result?.board&&square&&result.board.legal_moves.some(move=>move.from===square))setSelected(square);
      return result;
    },[act,board?.view_revision]);

    const step = useCallback(async ply => {
      const result = await act('seek',{ply,view_revision:board?.view_revision});
      if (mounted.current&&result?.board && guided && ply>0) {
        const b = result.board, last = b.history[ply-1];
        if (last?.colour === b.human) {
          const anchor=b.review_anchor||{game_id:b.id,ply};
          if (sendPrompt(`Explain my recorded ${last.colour==='white'?'White':'Black'} move ${Math.ceil(ply/2)}${last.colour==='black'?'...':'.'} ${last.san}. Use chess_review with ${JSON.stringify(anchor)}; skip this review if that match or move has changed. Keep it brief and do not give a future hint.`)) setCoachPending(true);
        }
      }
      return result;
    }, [act,board?.view_revision,guided,sendPrompt]);
    useEffect(() => {
      if (!autoplay || !board || board.mode!=='replay' || (guided&&(chatBusy||coachPending))) return;
      if (board.ply >= board.total_plies) {setAutoplay(false);return;}
      const timer = setTimeout(() => step(board.ply+1), 1400/speed);
      return () => clearTimeout(timer);
    }, [autoplay,board?.id,board?.ply,board?.total_plies,board?.mode,chatBusy,coachPending,guided,step,speed]);
    const pieces = board?.pieces || INITIAL;
    const reversed = (board?.perspective==='black') !== flipped;
    const files = reversed ? 'hgfedcba' : 'abcdefgh';
    const ranks = reversed ? [1,2,3,4,5,6,7,8] : [8,7,6,5,4,3,2,1];
    const replay=board?.mode==='replay';
    const coachingWait=guided&&(chatBusy||coachPending);
    const playable = !!board && !requesting && !finish && !board.pending && board.turn===board.human &&
      (replay?board.position_result==='*':board.result==='*');
    const legal = board?.legal_moves || [];
    const targets = selected ? legal.filter(m=>m.from===selected) : [];
    const attempt = useCallback((from,to) => {
      const possibilities=legal.filter(m=>m.from===from&&m.to===to);
      if (!possibilities.length) {setSelected(null);return;}
      if (possibilities.length>1) setPromotion(possibilities);
      else act(replay?'practice_move':'move',{move:possibilities[0].uci,view_revision:board?.view_revision,mode:'coach'});
    }, [legal,act,replay,board?.view_revision]);
    const clickSquare = sq => {
      const piece=board?.pieces?.[sq];
      if(replay&&!playable&&!requesting&&piece&&(piece===piece.toUpperCase())===(board.human==='white')){
        beginPractice(sq);return;
      }
      if (!playable) return;
      if (selected && sq!==selected && targets.some(m=>m.to===sq)) {attempt(selected,sq);return;}
      setSelected(legal.some(m=>m.from===sq) ? (selected===sq ? null : sq) : null);
    };
    const iconButton = (label,visual,onClick,disabled=false,extra={}) => h('button',{
      type:'button',className:'gb-control',title:label,'aria-label':label,onClick,disabled:disabled||!!requesting,...extra},glyphs[visual]?icon(visual):visual);
    const positionOf = sq => [files.indexOf(sq[0])*12.5+6.25,ranks.indexOf(Number(sq[1]))*12.5+6.25];
    let arrow=null;
    if(hint?.from) {
      const [x1,y1]=positionOf(hint.from),[x2,y2]=hint.to?positionOf(hint.to):[x1,y1];
      arrow=h('svg',{className:'gb-arrow',viewBox:'0 0 100 100','aria-hidden':true},
        hint.to ? [h('defs',{key:'defs'},h('marker',{id:'gb-arrow-'+sid,markerWidth:4,markerHeight:4,refX:2.4,refY:2,orient:'auto'},h('path',{d:'M0 0 L4 2 L0 4 Z',fill:'#1758d9'}))),
          h('line',{key:'line',x1,y1,x2,y2,stroke:'#1758d9',strokeWidth:1.5,opacity:.8,markerEnd:`url(#gb-arrow-${sid})`})] :
          h('circle',{cx:x1,cy:y1,r:5.7,fill:'none',stroke:'#1758d9',strokeWidth:1.5}));
    }
    const status = !board ? 'Ready to play' : replay ? (coachingWait?'Hermes is responding in chat':board.position_result!=='*'?'End of match':board.turn===board.human?'Your move · replay':'Play from here') : board.result!=='*' ? (board.result==='1/2-1/2'?'Draw':'Game over') :
      board.pending ? `Hermes is thinking · ${Math.min(60,Math.max(0,Math.ceil(board.pending.deadline-now/1000)))}s` : 'Your move';
    const topName = board ? (reversed?board.white:board.black) : 'Hermes';
    const bottomName = board ? (reversed?board.black:board.white) : 'You';
    const match=board?.match;
    const platform=match?.platform==='chess.com'?'Chess.com':match?.platform==='lichess'?'Lichess':'Imported match';
    const sourceLabel=platform+(match?.username?' · @'+match.username:'');
    const opponent=match?(match.colour==='black'?match.white:match.black):'';
    const dateLabel=formatGameDate(match);
    const matchDetails=match?['vs '+opponent,dateLabel,match.result&&match.result!=='*'?match.result:null].filter(Boolean).join(' · '):'';
    const matchTitle=match?[sourceLabel,match.white+' (White) vs '+match.black+' (Black)',dateLabel,match.result?'Original result: '+match.result:null,match.source_id?'Game: '+match.source_id:null].filter(Boolean).join('\n'):'';
    let sourceUrl=null;
    if(match?.url){try{const url=new URL(match.url);const hosts=match.platform==='chess.com'?['chess.com','www.chess.com']:match.platform==='lichess'?['lichess.org','www.lichess.org']:[];if(url.protocol==='https:'&&hosts.includes(url.hostname)&&!url.username&&!url.password)sourceUrl=url.href;}catch{}}

    const modeLabel=board?.play_mode==='normal'?'Normal':'Coach';
    const ended=board?.mode==='play'&&board.result!=='*';
    const menuItem=(label,glyph,fn,title,danger=false)=>h('button',{type:'button',role:'menuitem',title,onClick:fn,disabled:!!requesting,className:danger?'gb-danger':''},icon(glyph),label);

    return h('div',{className:'gambit-board-root',onKeyDown:event=>{if(event.key==='Escape'){setMenu(false);setConfirm(false);setPromotion(null);if(importOpen)closeImport();}}},
      h('style',null,css),
      h('div',{className:'gb-header'},h('div',{className:'gb-brand'},icon('knight',18),'GAMBIT'),
        h('div',{className:'gb-header-actions'},h('button',{ref:importTrigger,type:'button',className:'gb-control',title:'Find and replay a completed Chess.com or Lichess game by username',onClick:showImport,disabled:!!requesting||!!finish},icon('folder',14),'Import game'),
        board?h('button',{type:'button',className:'gb-new',disabled:!!requesting||!!finish,
          title:replay?'Play this match yourself from the selected position':'Start a fresh game against Hermes. You play White.',
          onClick:()=>replay?beginPractice():startGame()},icon(replay?'play':'knight',14),requesting==='start'?'Starting…':replay?'Play from here':'New game'):null)),
      match?h('div',{className:'gb-match',role:'group','aria-label':'Selected match'},
        h('div',{className:'gb-match-heading'},h(sourceUrl?'a':'span',{className:'gb-match-source',title:matchTitle,...(sourceUrl?{href:sourceUrl,target:'_blank',rel:'noopener noreferrer','aria-label':'Open original '+sourceLabel+' match'}:{})},h('span',null,sourceLabel),sourceUrl?icon('external',12):null),
          h('span',{className:'gb-match-type'},board.practice?'Practice · original match':'Recorded match')),
        h('div',{className:'gb-match-details',title:matchTitle},matchDetails)):null,
      h('div',{className:'gb-stage',ref:stage},h('div',{className:'gb-position',style:{width:size}},
        h('div',{className:'gb-bar'},h('span',{className:'gb-name'},topName),
          board?.last_reply?.origin==='recorded'?h('span',{className:'gb-fallback',title:'This is the opponent’s recorded move from the original match.'},'Recorded reply'):
          board?.last_reply&&board.last_reply.origin!=='hermes'?h('span',{className:'gb-fallback',title:board.last_reply.explanation},'Engine-assisted'):null),
        h('div',{className:'gb-board',style:{width:size,height:size},role:'group','aria-label':'Chessboard'},
        ...ranks.flatMap((rank,row)=>[...files].map((file,col)=>{
          const sq=file+rank,piece=pieces[sq],light=((file.charCodeAt(0)-97)+rank)%2===0;
          const target=targets.some(m=>m.to===sq),last=board?.last_move;
          return h('button',{key:sq,type:'button',className:'gb-square '+(light?'light':'dark')+(selected===sq?' chosen':'')+
            ((last?.slice(0,2)===sq||last?.slice(2,4)===sq)?' last':'')+(board?.check_square===sq?' checked':''),
            ref:el=>{squares.current[sq]=el;},'aria-label':sq+(piece?', '+(piece===piece.toUpperCase()?'white ':'black ')+NAMES[piece.toLowerCase()]:', empty'),
            title:piece?((piece===piece.toUpperCase())===(board?.human==='white')?(replay?'Play from this position with this piece':ended?'Start a new game to play again':playable?'Select this '+NAMES[piece.toLowerCase()]:'Wait for the opponent’s reply'):'The opponent’s '+NAMES[piece.toLowerCase()]):target?'Move to '+sq:sq,
            'aria-pressed':selected===sq,onClick:()=>clickSquare(sq),
            draggable:playable&&legal.some(m=>m.from===sq),
            onDragStart:event=>{event.dataTransfer.setData('text/plain',sq);event.dataTransfer.effectAllowed='move';setSelected(sq);},
            onDragOver:event=>{if(playable)event.preventDefault();},
            onDrop:event=>{event.preventDefault();if(playable)attempt(event.dataTransfer.getData('text/plain'),sq);},
            onKeyDown:event=>{
              const offsets={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]};
              const delta=offsets[event.key];if(delta){event.preventDefault();const r=ranks[row+delta[0]],f=files[col+delta[1]];if(r&&f)squares.current[f+r]?.focus();}
              if(event.key==='Escape')setSelected(null);
            }},
            piece?h('span',{className:'gb-piece',dangerouslySetInnerHTML:{__html:PIECES[piece]}}):null,
            target?h('span',{className:piece?'gb-ring':'gb-dot'}):null,
            col===0?h('span',{className:'gb-coord gb-rank'},rank):null,
            row===7?h('span',{className:'gb-coord gb-file'},file):null);
        })),arrow,
        !board?h('div',{className:'gb-overlay'},h('div',{className:'gb-message'},h('strong',null,sid&&!state&&!error?'Loading your board…':'Ready to play?'),
          !(sid&&!state&&!error)?h('span',null,'You move, then Hermes replies. Coaching and hints stay in chat.'):null,
          !(sid&&!state&&!error)?h('button',{type:'button',className:'gb-new',style:{marginTop:14},title:'Start a normal chess game against Hermes. You play White.',onClick:startGame,disabled:!!requesting},icon('knight',15),requesting?'Starting…':'Play Hermes'):null)):null),
        h('div',{className:'gb-bar'},h('span',{className:'gb-name'},bottomName),h('span',{className:'gb-status'+(board?.pending?' pending':replay?' replay':''),role:'status'},status)))),
      replay?h('div',{className:'gb-replay-note'},coachingWait?'Waiting for chat coaching. Turn off guided coaching to browse freely.':'Move your pieces to play. The opponent replies once.'):null,
      h('div',{className:'gb-controls'},
        replay ? [
          iconButton('First move','first',()=>{setAutoplay(false);step(0);},board.ply===0||coachingWait,{key:'first',title:'Return to the beginning of the recorded match'}),
          iconButton('Previous move','previous',()=>{setAutoplay(false);step(board.ply-1);},board.ply===0||coachingWait,{key:'prev',title:'Step back one recorded move'}),
          iconButton(autoplay?'Pause replay':'Play replay',autoplay?'pause':'play',()=>setAutoplay(v=>!v),board.ply===board.total_plies,{key:'play',title:autoplay?'Pause automatic replay':'Watch the recorded moves automatically'}),
          iconButton('Next move','next',()=>{setAutoplay(false);step(board.ply+1);},board.ply>=board.total_plies||coachingWait,{key:'next',title:'Step forward one recorded move'}),
          iconButton('Last move','last',()=>{setAutoplay(false);step(board.total_plies);},board.ply===board.total_plies||coachingWait,{key:'last',title:'Jump to the final recorded position'}),
          h('span',{key:'count',className:'gb-count'},`${board.ply} / ${board.total_plies}`),
          iconButton('Replay speed',speed+'×',()=>setSpeed(v=>v===1?2:v===2?.5:1),false,{key:'speed',title:'Cycle replay speed: half speed, normal, or double speed'}),
          iconButton(guided?'Guided coaching on':'Guided coaching off',guided?'◉':'○',()=>setGuided(v=>!v),false,{key:'guide','aria-pressed':guided,title:guided?'Turn off automatic explanations while watching the replay':'Ask Hermes to explain your recorded moves during replay'})
        ] : board?[
          board.practice?iconButton('Back to recorded match','back',()=>act('replay_source'),false,{key:'back',title:'Return to the original match; your practice game remains saved'}):null,
          h('button',{key:'mode',type:'button',className:'gb-control',title:modeLabel==='Normal'?'Normal mode: hints only when requested. Click for game options.':'Coach mode: feedback after your moves. Click for game options.',onClick:()=>setMenu(v=>!v),'aria-label':'Game mode: '+modeLabel},modeLabel),
          iconButton('Ask for a hint','hint',()=>sendPrompt('Give me a hint for this chess position.'),!!board.pending||ended,{key:'hint',title:'Ask Hermes for a hint in chat'}),
          h('span',{key:'count',className:'gb-count'},board.practice?'Replay practice':`Move ${Math.floor(board.ply/2)+1}`)
        ]:null,
        iconButton('Flip board','flip',()=>setFlipped(v=>!v),false,{title:'Rotate the board to the other side'}),
        iconButton('Chess actions','more',()=>setMenu(v=>!v),false,{title:'Game options: mode, saved matches, undo, and resign','aria-expanded':menu})),
      menu?h('div',{style:{position:'absolute',inset:0,zIndex:19},onClick:()=>setMenu(false),'aria-hidden':true}):null,
      menu?h('div',{className:'gb-menu',role:'menu','aria-label':'Game options',style:{width:224,maxWidth:'calc(100% - 32px)',left:'auto',right:16,bottom:52,background:'#151e2c',opacity:1}},
        h('div',{className:'gb-menu-heading'},'GAME OPTIONS'),
        menuItem('New game','knight',startGame,'Start a fresh game against Hermes as White'),
        menuItem('Import game','folder',showImport,'Choose a Chess.com or Lichess username and select a match'),
        menuItem('Saved matches','folder',()=>{setMenu(false);sendPrompt('Show my saved chess matches.');},'Choose a saved match in Hermes chat'),
        board?.mode==='play'?h('div',null,h('div',{className:'gb-menu-separator'}),h('div',{className:'gb-menu-heading'},'PLAY MODE'),
          h('div',{className:'gb-mode-switch'},...['normal','coach'].map(mode=>h('button',{key:mode,type:'button',role:'menuitemradio','aria-checked':board.play_mode===mode,'aria-label':'Switch to '+(mode==='normal'?'Normal':'Coach')+' mode',title:mode==='normal'?'Play without automatic coaching. Hints are available on request.':'Get feedback in chat after each of your turns.',className:board.play_mode===mode?'selected':'',disabled:!!requesting,onClick:()=>act('set_mode',{mode})},mode==='normal'?'Normal':'Coach'))),
          h('div',{className:'gb-menu-note'},modeLabel==='Normal'?'Hints when you ask':'Feedback after your moves'),h('div',{className:'gb-menu-separator'}),
          menuItem('Undo last turn','undo',()=>act('undo'),'Take back your last move and the opponent’s reply'),
          board.claimable_draw?menuItem('Claim draw','flag',()=>act('claim_draw'),'Claim a draw allowed by the current chess position'):null,
          !ended?menuItem('Resign game','flag',()=>{setMenu(false);setConfirm(true);},'Resign, see GG fireworks, and start fresh',true):null):null):null,
      error&&!importOpen?h('div',{className:'gb-error',role:'alert'},error):null,
      promotion?h('div',{className:'gb-modal'},h('div',{className:'gb-dialog',role:'dialog','aria-modal':true,'aria-label':'Promote pawn'},
        'Choose a promotion',h('div',{className:'gb-promotions'},...promotion.map(m=>h('button',{type:'button',key:m.uci,'aria-label':'Promote to '+NAMES[m.promotion],
          title:'Promote your pawn to a '+NAMES[m.promotion],onClick:()=>{setPromotion(null);act(replay?'practice_move':'move',{move:m.uci,view_revision:board.view_revision,mode:'coach'});},dangerouslySetInnerHTML:{__html:PIECES[board.human==='white'?m.promotion.toUpperCase():m.promotion]}}))),
        h('button',{type:'button',className:'gb-control',title:'Keep your pawn move unplayed',style:{marginTop:10},onClick:()=>setPromotion(null)},'Cancel'))):null,
      confirm?h('div',{className:'gb-modal'},h('div',{className:'gb-dialog',role:'alertdialog','aria-modal':true,'aria-label':'Resign game'},
        h('strong',null,'Resign this game?'),h('div',{style:{fontSize:11,color:'#97aac4',marginTop:6}},'Your match stays saved. A fresh board follows.'),h('div',{style:{display:'flex',gap:8,justifyContent:'center',marginTop:14}},
          h('button',{type:'button',className:'gb-control',title:'Return to your current game',onClick:()=>setConfirm(false)},'Keep playing'),
          h('button',{type:'button',className:'gb-control',title:'Confirm resignation and start a fresh game',onClick:()=>{setConfirm(false);act('resign');}},'Resign')))):null,
      importOpen?h('div',{className:'gb-import-overlay',onClick:event=>{if(event.target===event.currentTarget)closeImport();}},h('div',{className:'gb-import-dialog',role:'dialog','aria-modal':true,'aria-label':'Import a chess game',onKeyDown:event=>{
        if(event.key==='Tab'){const items=[...event.currentTarget.querySelectorAll('button:not(:disabled), input:not(:disabled), a[href]')],first=items[0],last=items[items.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
      }},
        h('div',{className:'gb-import-heading'},h('h2',null,'Replay a match'),h('button',{ref:importClose,type:'button',className:'gb-control',title:'Close game import','aria-label':'Close game import',onClick:closeImport},icon('close',14))),
        h('p',{className:'gb-import-description'},'Choose a completed public game. No sign-in needed.'),
        h('form',{className:'gb-import-form',onSubmit:searchGames},
          h('div',{className:'gb-platforms',role:'group','aria-label':'Chess platform'},...['chess.com','lichess'].map(platform=>h('button',{key:platform,type:'button','aria-pressed':importPlatform===platform,title:'Search '+(platform==='chess.com'?'Chess.com':'Lichess')+' games',disabled:!!requesting,onClick:()=>{setImportPlatform(platform);setImportResults(null);setError('');}},platform==='chess.com'?'Chess.com':'Lichess'))),
          h('label',{className:'gb-input-label',htmlFor:'gb-username'},'Username'),h('div',{className:'gb-search-row'},h('input',{id:'gb-username',className:'gb-username',value:importUsername,onChange:event=>{setImportUsername(event.target.value.trim());setImportResults(null);setError('');},placeholder:(importPlatform==='chess.com'?'Chess.com':'Lichess')+' username',minLength:2,maxLength:50,pattern:'[A-Za-z0-9_\\-]{2,50}',required:true,autoComplete:'off',autoCapitalize:'none',spellCheck:false,autoFocus:true,disabled:!!requesting}),
            h('button',{type:'submit',className:'gb-new',title:importResults?'Check the site again for new completed games':'Find recent completed games for this username',disabled:!!requesting||!importUsername.trim()},requesting==='find_games'?'Searching…':importResults?'Refresh games':'Search games'))),
        error?h('div',{className:'gb-import-error',role:'alert'},error):null,
        importResults?.notice?h('p',{className:'gb-import-notice'},importResults.notice):null,
        importResults?h('div',{className:'gb-import-results','aria-label':'Matches for '+importResults.username},
          h('div',{className:'gb-results-label',role:'status'},importResults.games.length?'Choose a match · @'+importResults.username:'No published matches yet for @'+importResults.username),
          !importResults.games.length?h('p',{className:'gb-import-notice'},importResults.platform==='chess.com'?'New accounts and just-finished games can take time to appear on Chess.com’s public archive. Use Refresh games to check again. Private bot and Coach games are not included.':'Only completed public standard games appear here. A just-finished game may still be updating; use Refresh games to check again.'):null,
          ...importResults.games.map((game,index)=>h('button',{key:game.source_id,type:'button',className:'gb-import-game',disabled:!!requesting,title:'Replay game '+(game.number||index+1)+': '+game.white+' vs '+game.black+' · '+formatGameDate(game)+' · '+game.result+' · '+game.source_id,onClick:()=>openImported(game)},
            h('span',{className:'gb-game-number'},game.number||index+1),h('span',{className:'gb-game-info'},h('strong',null,game.white+' vs '+game.black),h('small',null,[formatGameDate(game),game.colour?game.colour==='white'?'White':'Black':null,game.result].filter(Boolean).join(' · '))),icon('play',13))),
          importResults.games.length&&importResults.older_than?h('button',{type:'button',className:'gb-control',style:{width:'calc(100% - 16px)',margin:'6px 8px 3px'},title:'Find games played before the oldest match in this list',disabled:!!requesting,onClick:()=>findImported(importResults.older_than)},'Older games'):null):null)):null,
      finish?h(Celebration,{result:finish.result,onNewGame:startGame}):null);
  };
}
