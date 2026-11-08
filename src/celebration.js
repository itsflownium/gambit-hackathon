/**
 * A short, presentational end-of-game overlay. Mount after a successful resign;
 * the owner controls when the next game starts and when this is unmounted.
 * `onNewGame`, when supplied, lets the player start that next game immediately.
 */
export function createCelebration(React) {
  const h = React.createElement;
  const css = `
    .gambit-celebration{position:absolute;inset:0;z-index:30;isolation:isolate;container:gambit-gg / size;display:grid;place-items:center;overflow:hidden;padding:16px;background:radial-gradient(ellipse at 50% 42%,#203b63ed 0%,#101d32f2 48%,#0a1220f7 100%);color:#f3f6fc;text-align:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);animation:gambit-gg-arrive .3s ease-out both}
    .gambit-celebration,.gambit-celebration *{box-sizing:border-box}
    .gambit-celebration .gc-content{position:relative;z-index:2;display:flex;align-items:center;flex-direction:column;max-width:100%;animation:gambit-gg-rise .55s cubic-bezier(.16,1,.3,1) both}
    .gambit-celebration .gc-score{display:inline-flex;align-items:center;gap:7px;border:1px solid #b3ccf12b;background:#bdd7ff08;border-radius:20px;padding:5px 11px;color:#afc4e2;font-size:10px;font-weight:600;letter-spacing:.12em;line-height:1.2;text-transform:uppercase}
    .gambit-celebration .gc-score i{height:3px;width:3px;background:#c4d4eb;border-radius:50%}
    .gambit-celebration .gc-monogram{position:relative;margin:11px 0 0;font-size:clamp(82px,24vmin,142px);font-weight:850;line-height:1.02;letter-spacing:-.085em;padding-right:.085em;color:#eff5ff;text-shadow:0 2px 36px #91baff34}
    .gambit-celebration .gc-monogram:after{content:'';position:absolute;width:48%;height:1px;bottom:-7px;left:26%;background:linear-gradient(90deg,transparent,#c3d7f8b0,transparent)}
    .gambit-celebration .gc-heading{margin:21px 0 0;font-size:clamp(20px,5vmin,26px);font-weight:600;line-height:1.25;letter-spacing:-.025em}
    .gambit-celebration .gc-reason{margin:8px 0 0;color:#a8bad4;font-size:12px;line-height:1.5}
    .gambit-celebration .gc-next{margin-top:27px;color:#8299b9;font-size:10px;line-height:1.4;letter-spacing:.02em}
    .gambit-celebration .gc-track{height:2px;width:112px;max-width:100%;margin:10px auto 0;border-radius:4px;background:#aac9f21c;overflow:hidden}
    .gambit-celebration .gc-progress{display:block;width:100%;height:100%;border-radius:4px;background:linear-gradient(90deg,#6d9de3,#c3dbff);transform-origin:left;animation:gambit-gg-progress 3s linear both}
    .gambit-celebration .gc-again{margin-top:16px;border:1px solid #8eafd345;border-radius:6px;background:#a0c2f00b;padding:6px 13px;color:#c2d5ee;font:inherit;font-size:11px;cursor:pointer;transition:background .15s,border-color .15s}
    .gambit-celebration .gc-again:hover{background:#a0c2f01c;border-color:#8eafd388}
    .gambit-celebration .gc-again:focus-visible{outline:2px solid #b0d0ff;outline-offset:4px}
    .gambit-celebration .gc-fireworks{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:1}
    .gambit-celebration .gc-halo{position:absolute;left:50%;top:43%;width:260px;height:260px;border:1px solid #99c1ff0b;border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 90px 15px #6c9dea0a,inset 0 0 70px #8ebaff07}
    .gambit-celebration .gc-burst{position:absolute;left:var(--x);top:var(--y);height:1px;width:1px}
    .gambit-celebration .gc-spark{position:absolute;left:0;top:0;width:3px;height:3px;border-radius:50%;background:var(--spark);box-shadow:0 0 7px var(--spark);opacity:0;animation:gambit-gg-spark 1.35s cubic-bezier(.12,.55,.4,1) var(--delay) both}
    .gambit-celebration .gc-spark:after{content:'';position:absolute;inset:-1px;border-radius:50%;background:inherit;opacity:.3}
    @keyframes gambit-gg-arrive{from{opacity:0}to{opacity:1}}
    @keyframes gambit-gg-rise{from{opacity:0;transform:translateY(10px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}
    @keyframes gambit-gg-progress{from{transform:scaleX(0)}to{transform:scaleX(1)}}
    @keyframes gambit-gg-spark{0%{opacity:0;transform:translate(0,0) scale(.3)}12%{opacity:.95}65%{opacity:.65}100%{opacity:0;transform:translate(var(--dx),var(--dy)) scale(.25)}}
    @container gambit-gg (max-height:370px){.gambit-celebration .gc-monogram{font-size:78px;margin-top:9px}.gambit-celebration .gc-heading{font-size:20px;margin-top:15px}.gambit-celebration .gc-next{margin-top:16px}.gambit-celebration .gc-again{margin-top:12px}}
    @container gambit-gg (max-height:300px){.gambit-celebration .gc-score{font-size:9px;padding:4px 9px}.gambit-celebration .gc-monogram{font-size:62px;margin-top:6px}.gambit-celebration .gc-heading{font-size:18px;margin-top:12px}.gambit-celebration .gc-reason{margin-top:6px;font-size:11px}.gambit-celebration .gc-next{margin-top:13px}.gambit-celebration .gc-again{margin-top:10px}}
    @media(prefers-reduced-motion:reduce){.gambit-celebration,.gambit-celebration .gc-content,.gambit-celebration .gc-progress{animation:none}.gambit-celebration .gc-spark{animation:none;display:none}.gambit-celebration .gc-again{transition:none}}
  `;
  // Fixed trajectories keep mounts deterministic and avoid any animation timers.
  const bursts = [
    {x:'18%',y:'29%',colour:'#91baff',delay:.05,radius:59},
    {x:'83%',y:'24%',colour:'#e9c993',delay:.34,radius:48},
    {x:'80%',y:'68%',colour:'#8db4e9',delay:1.02,radius:52},
    {x:'21%',y:'72%',colour:'#e2ccaa',delay:1.38,radius:43},
  ];
  return function Celebration({result, onNewGame}) {
    const score = {'1-0':'1–0','0-1':'0–1','1/2-1/2':'½–½'}[result];
    return h('div',{className:'gambit-celebration'},
      h('style',null,css),
      h('div',{className:'gc-fireworks','aria-hidden':true},
        h('div',{className:'gc-halo'}),
        ...bursts.map((burst,index)=>h('div',{key:index,className:'gc-burst',style:{'--x':burst.x,'--y':burst.y,'--spark':burst.colour}},
          ...Array.from({length:12},(_,particle)=>{
            const angle=particle*Math.PI/6, radius=burst.radius*(particle%2?.76:1);
            return h('i',{key:particle,className:'gc-spark',style:{'--dx':`${Math.cos(angle)*radius}px`,'--dy':`${Math.sin(angle)*radius+12}px`,'--delay':`${burst.delay}s`}});
          })))),
      h('div',{className:'gc-content'},
        h('div',{role:'status','aria-live':'polite','aria-atomic':true},
          h('div',{className:'gc-score'},'Game complete',score?h('i',{'aria-hidden':true}):null,score||null),
          h('div',{className:'gc-monogram','aria-hidden':true},'GG'),
          h('h2',{className:'gc-heading'},'Good game.'),
          h('p',{className:'gc-reason'},'You resigned')),
        h('div',{className:'gc-next'},'A fresh board is coming up',
          h('div',{className:'gc-track','aria-hidden':true},h('span',{className:'gc-progress'}))),
        onNewGame?h('button',{type:'button',className:'gc-again',title:'Start the next game immediately',onClick:onNewGame},'Play again'):null));
  };
}
