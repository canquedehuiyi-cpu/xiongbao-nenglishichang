import{useCallback as z,useEffect as y,useRef as k,useState as S}from"react";import*as v from"qoder/canvas";function E(e){return e?.status==="ready"&&typeof e.url=="string"&&e.url.length>0}function Y(e,t){let a=E(e)?e:t;return Object.freeze({displayedSurface:a,failed:e?.status==="failed",nextRetainedReady:a,recovering:a!==void 0&&e?.status!=="ready"})}function Q(e,t,a){if(!t||e?.status!=="stopped")return;let r=e.generation||e.updatedAt||"legacy-stopped";return r===a?void 0:r}import{jsx as s,jsxs as f}from"react";function Z({elapsedMs:e,isChinese:t,message:a,phase:r}){return f("div",{className:"canvas-simulator-skeleton",role:"status","aria-label":a,children:[s("style",{children:ie}),f("div",{className:"canvas-simulator-skeleton__layout","aria-hidden":"true",children:[f("div",{className:"canvas-simulator-skeleton__status-bar",children:[s(c,{className:"canvas-simulator-skeleton__time"}),f("div",{className:"canvas-simulator-skeleton__status-icons",children:[s(c,{className:"canvas-simulator-skeleton__signal"}),s(c,{className:"canvas-simulator-skeleton__signal"}),s(c,{className:"canvas-simulator-skeleton__battery"})]})]}),f("div",{className:"canvas-simulator-skeleton__app-bar",children:[s(c,{className:"canvas-simulator-skeleton__avatar"}),f("div",{className:"canvas-simulator-skeleton__app-title",children:[s(c,{className:"canvas-simulator-skeleton__title-line"}),s(c,{className:"canvas-simulator-skeleton__caption-line"})]}),s(c,{className:"canvas-simulator-skeleton__action"})]}),f("div",{className:"canvas-simulator-skeleton__hero",children:[s(c,{className:"canvas-simulator-skeleton__hero-media"}),f("div",{className:"canvas-simulator-skeleton__startup-copy",children:[s("strong",{children:a}),f("span",{children:[r?de(r):t?"\u6B63\u5728\u542F\u52A8":"Starting",` \xB7 ${le(e)}`]})]})]}),f("div",{className:"canvas-simulator-skeleton__chips",children:[s(c,{className:"canvas-simulator-skeleton__chip"}),s(c,{className:"canvas-simulator-skeleton__chip"}),s(c,{className:"canvas-simulator-skeleton__chip"})]}),s("div",{className:"canvas-simulator-skeleton__feed",children:Array.from({length:3},(o,i)=>f("div",{className:"canvas-simulator-skeleton__feed-row",children:[s(c,{className:"canvas-simulator-skeleton__thumbnail"}),f("div",{className:"canvas-simulator-skeleton__feed-copy",children:[s(c,{className:"canvas-simulator-skeleton__feed-title"}),s(c,{className:"canvas-simulator-skeleton__feed-line canvas-simulator-skeleton__feed-line--long"}),s(c,{className:"canvas-simulator-skeleton__feed-line canvas-simulator-skeleton__feed-line--short"})]})]},i))}),s("div",{className:"canvas-simulator-skeleton__tab-bar",children:Array.from({length:4},(o,i)=>f("div",{className:"canvas-simulator-skeleton__tab-item",children:[s(c,{className:"canvas-simulator-skeleton__tab-icon"}),s(c,{className:"canvas-simulator-skeleton__tab-label"})]},i))})]})]})}function c({className:e,style:t}){return s("span",{className:`canvas-simulator-skeleton__block ${e}`,style:t})}var ie=`
  @keyframes canvas-simulator-skeleton-pulse {
    0%,100% { opacity:.58; }
    50% { opacity:1; }
  }
  .canvas-simulator-skeleton {
    box-sizing:border-box;
    height:100%;
    min-height:280px;
    overflow:auto;
    padding:20px 24px 32px;
  }
  .canvas-simulator-skeleton *,
  .canvas-simulator-skeleton *::before,
  .canvas-simulator-skeleton *::after { box-sizing:border-box; }
  .canvas-simulator-skeleton__layout {
    display:flex;
    flex-direction:column;
    gap:14px;
    margin:0 auto;
    max-width:390px;
    min-height:100%;
    width:100%;
  }
  .canvas-simulator-skeleton__block {
    animation:canvas-simulator-skeleton-pulse 1.8s ease-in-out infinite;
    background:var(--vscode-aicoding-skeletonBackground, color-mix(in srgb, var(--vscode-foreground) 10%, transparent));
    border-radius:6px;
    display:block;
  }
  .canvas-simulator-skeleton__status-bar,
  .canvas-simulator-skeleton__app-bar,
  .canvas-simulator-skeleton__status-icons,
  .canvas-simulator-skeleton__chips,
  .canvas-simulator-skeleton__tab-bar,
  .canvas-simulator-skeleton__tab-item { align-items:center; display:flex; }
  .canvas-simulator-skeleton__status-bar { justify-content:space-between; min-height:12px; padding:0 6px; }
  .canvas-simulator-skeleton__time { height:8px; width:34px; }
  .canvas-simulator-skeleton__status-icons { gap:5px; }
  .canvas-simulator-skeleton__signal { border-radius:3px; height:8px; width:10px; }
  .canvas-simulator-skeleton__battery { border-radius:3px; height:9px; width:19px; }
  .canvas-simulator-skeleton__app-bar { gap:12px; }
  .canvas-simulator-skeleton__avatar { border-radius:50%; flex:0 0 40px; height:40px; }
  .canvas-simulator-skeleton__app-title { display:flex; flex:1 1 auto; flex-direction:column; gap:7px; }
  .canvas-simulator-skeleton__title-line { height:12px; width:42%; }
  .canvas-simulator-skeleton__caption-line { height:8px; width:27%; }
  .canvas-simulator-skeleton__action { border-radius:50%; flex:0 0 32px; height:32px; }
  .canvas-simulator-skeleton__hero {
    background:color-mix(in srgb, var(--vscode-foreground) 4%, transparent);
    border-radius:16px;
    display:flex;
    flex-direction:column;
    gap:10px;
    padding:12px 12px 16px;
  }
  .canvas-simulator-skeleton__hero-media { border-radius:12px; height:120px; width:100%; }
  .canvas-simulator-skeleton__startup-copy {
    align-items:center;
    color:var(--vscode-foreground);
    display:flex;
    flex-direction:column;
    gap:5px;
    min-height:38px;
    padding-top:2px;
    text-align:center;
  }
  .canvas-simulator-skeleton__startup-copy strong { font-size:13px; font-weight:600; line-height:18px; }
  .canvas-simulator-skeleton__startup-copy span {
    color:var(--vscode-descriptionForeground, var(--vscode-foreground));
    font-size:11px;
    line-height:15px;
  }
  .canvas-simulator-skeleton__chips { gap:8px; overflow:hidden; }
  .canvas-simulator-skeleton__chip { border-radius:999px; flex:0 0 82px; height:28px; }
  .canvas-simulator-skeleton__feed { display:flex; flex-direction:column; gap:10px; }
  .canvas-simulator-skeleton__feed-row {
    align-items:center;
    background:color-mix(in srgb, var(--vscode-foreground) 3%, transparent);
    border-radius:12px;
    display:flex;
    gap:12px;
    padding:8px;
  }
  .canvas-simulator-skeleton__thumbnail { border-radius:9px; flex:0 0 52px; height:52px; }
  .canvas-simulator-skeleton__feed-copy { display:flex; flex:1 1 auto; flex-direction:column; gap:7px; }
  .canvas-simulator-skeleton__feed-title { height:11px; width:58%; }
  .canvas-simulator-skeleton__feed-line { height:8px; }
  .canvas-simulator-skeleton__feed-line--long { width:88%; }
  .canvas-simulator-skeleton__feed-line--short { width:46%; }
  .canvas-simulator-skeleton__tab-bar {
    border-top:1px solid color-mix(in srgb, var(--vscode-foreground) 8%, transparent);
    justify-content:space-around;
    margin-top:auto;
    padding:14px 4px 0;
  }
  .canvas-simulator-skeleton__tab-item { flex-direction:column; gap:6px; width:48px; }
  .canvas-simulator-skeleton__tab-icon { border-radius:50%; height:20px; width:20px; }
  .canvas-simulator-skeleton__tab-label { height:6px; width:30px; }
  @media (max-width:640px) {
    .canvas-simulator-skeleton { padding:16px 18px 24px; }
    .canvas-simulator-skeleton__layout { gap:12px; }
    .canvas-simulator-skeleton__hero-media { height:112px; }
  }
  @media (prefers-reduced-motion:reduce) {
    .canvas-simulator-skeleton__block { animation:none; }
  }
`;function le(e){return`${(Math.max(0,e)/1e3).toFixed(1)}s`}function de(e){return e?`${e[0]?.toUpperCase()??""}${e.slice(1)}`:"Starting"}import{Fragment as _e,jsx as u,jsxs as H}from"react";var ce="mobileSimulatorSurface.v1",ue="simulator/compat-launcher.mjs";function ee(e){let t=v.CanvasSimulator,a=v.useHostLanguage(),r=v.useHostTheme(),o=e.hostLanguage??a,i=e.hostTheme??r;pe(!!t,o,i);let g={...e,hostLanguage:o,hostTheme:i};return t?u(t,{...g}):u(me,{...g})}function pe(e,t,a){let r=k(new Map),o=z((g,l)=>{g.postMessage(ye(t,a),l)},[t,a]),i=k(o);y(()=>{if(i.current=o,!!e)for(let[g,l]of r.current)o(g,l)},[e,o]),y(()=>{if(!e){r.current.clear();return}let g=l=>{if(l.data?.type!=="aicoding.canvas.hostContextReady"||!xe(l.origin)||!ke(l.source))return;let x=l.source;r.current.set(x,l.origin),i.current(x,l.origin)};return window.addEventListener("message",g),()=>{window.removeEventListener("message",g),r.current.clear()}},[e])}function me({targetFilePath:e,platform:t,hostLanguage:a,hostTheme:r,height:o="100%",className:i,style:g,fallback:l}){let x=v.useCanvasAction(),h=v.useHostLanguage(),P=v.useHostTheme(),w=a??h,d=r??P,[R]=v.useCanvasState(ce,void 0),[D,A]=S(0),[te,F]=S(0),[M,I]=S(),N=k(null),$=k(""),O=k(""),j=k(Date.now()),W=k(!1),[U,V]=S([]),[q,K]=S(),_=e.trim(),p=R?.schemaVersion===1&&R.targetFilePath===_&&R.platform===t?R:void 0,ae=`${t}\0${_}`;y(()=>{I(void 0),$.current=""},[ae]),y(()=>{E(p)&&I(p)},[p]),y(()=>{let n=Q(p,M,$.current);n&&($.current=n,A(m=>m+1))},[p,M]),y(()=>{if(!_)return;let n=`${t}\0${_}\0${D}`;O.current!==n&&(O.current=n,j.current=Date.now(),F(0),x({type:"aicoding.canvas.runScript",script:ue,args:{platform:t,targetFilePath:_}}))},[x,t,D,_]),y(()=>{if(p?.status==="ready"||p?.status==="failed")return;let n=window.setInterval(()=>F(Date.now()-j.current),250);return()=>window.clearInterval(n)},[p?.status]);let b=z(()=>{N.current?.contentWindow?.postMessage({type:"aicoding.canvas.annotationState",active:W.current},"*")},[]),C=z(()=>{N.current?.contentWindow?.postMessage({type:"aicoding.canvas.hostContext",language:w,theme:{kind:d.kind,colors:{accent:d.tokens.accent.control,accentHover:d.tokens.accent.controlHover,background:d.tokens.bg.editor,elevated:d.tokens.bg.elevated,fill:d.tokens.fill.tertiary,foreground:d.tokens.text.primary,foregroundSecondary:d.tokens.text.secondary,foregroundTertiary:d.tokens.text.tertiary,focus:d.tokens.accent.focus,onAccent:d.tokens.text.onAccent,stroke:d.tokens.stroke.tertiary}}},"*")},[w,d]);y(()=>{let n=m=>{!(m instanceof CustomEvent)||typeof m.detail?.active!="boolean"||(W.current=m.detail.active,m.detail.active||(V([]),K(void 0)),b())};return window.addEventListener("aicoding:canvas-annotation-state",n),()=>window.removeEventListener("aicoding:canvas-annotation-state",n)},[b]),y(()=>{C()},[C]),y(()=>{let n=m=>{if(m.source!==N.current?.contentWindow)return;if(m.data?.type==="aicoding.canvas.hostContextReady"){b(),C();return}if(m.data?.type!=="aicoding.canvas.deviceAxTargets")return;let re=Array.isArray(m.data.elements)?m.data.elements:[],X=m.data.context,J=m.data.active===!0;V(J?re:[]),K(J&&ve(X)?X:void 0)};return window.addEventListener("message",n),()=>window.removeEventListener("message",n)},[b,C]);let ne=typeof o=="number"?`${o}px`:o,oe=q?JSON.stringify(q):void 0,{displayedSurface:G,failed:T,recovering:se}=Y(p,M);return u("div",{className:i,"data-aicoding-canvas-simulator-surface":"compat",style:{display:"flex",flexDirection:"column",width:"100%",minHeight:280,height:ne,overflow:"hidden",color:d.tokens.text.primary,background:d.tokens.bg.editor,...g},children:u("div",{style:{flex:"1 1 auto",minHeight:0,position:"relative"},children:G?.url?H(_e,{children:[u("iframe",{ref:N,src:G.url,sandbox:"allow-scripts allow-same-origin allow-downloads",onLoad:()=>{b(),C()},style:{display:"block",width:"100%",height:"100%",border:0,background:d.tokens.bg.editor}}),U.length?u("div",{"aria-label":"Device accessibility annotation targets","data-aicoding-semantic-context":oe,style:{position:"absolute",inset:0,zIndex:2,pointerEvents:"none"},children:U.map(n=>u("div",{"aria-label":n.label,"data-aicoding-component-name":n.label,"data-aicoding-device-ax":JSON.stringify(n.selection),"data-device-ax-id":n.id,style:{position:"absolute",left:n.rect.left,top:n.rect.top,width:n.rect.width,height:n.rect.height,pointerEvents:"auto"}},n.id))}):null,se?u(ge,{error:T?p?.error||p?.progress?.message:void 0,hostLanguage:w,hostTheme:d,onRetry:()=>A(n=>n+1)}):null]}):T&&l?l:u(fe,{elapsedMs:Math.max(te,p?.progress?.elapsedMs??0),error:T?p?.error||p?.progress?.message:void 0,hostTheme:d,hostLanguage:w,platform:t,progress:p?.progress,onRetry:()=>A(n=>n+1)})})})}function ge({error:e,hostLanguage:t,hostTheme:a,onRetry:r}){let o=t.isChinese;return H("div",{role:"status",style:{position:"absolute",top:10,left:"50%",zIndex:3,display:"flex",alignItems:"center",gap:8,maxWidth:"min(680px, calc(100% - 24px))",padding:"7px 10px",border:`1px solid ${e?a.tokens.status.danger:a.tokens.stroke.tertiary}`,borderRadius:7,background:a.tokens.bg.elevated,color:e?a.tokens.status.danger:a.tokens.text.secondary,boxShadow:`0 4px 14px ${a.tokens.fill.tertiary}`,transform:"translateX(-50%)",fontSize:12},children:[u("span",{children:e||(o?"\u6B63\u5728\u6062\u590D\u8BBE\u5907\u8FDE\u63A5\u2026":"Restoring the device connection\u2026")}),e?u("button",{type:"button",onClick:r,style:{padding:"4px 8px",border:0,borderRadius:5,background:a.tokens.accent.control,color:a.tokens.text.onAccent,cursor:"pointer"},children:o?"\u91CD\u8BD5":"Retry"}):null]})}function fe({elapsedMs:e,error:t,hostTheme:a,hostLanguage:r,platform:o,progress:i,onRetry:g}){let l=r.isChinese,x=i?.status==="failed"&&!t?void 0:i?.message,h=t||x||(l?`\u6B63\u5728\u51C6\u5907 ${L(o)} \u8BBE\u5907\u2026`:`Preparing ${L(o)} device\u2026`);if(!t)return u(Z,{elapsedMs:Math.max(e,i?.elapsedMs??0),isChinese:l,message:h,phase:i?.phase});let P=i?.logs?.length?i.logs.slice(-8).join(`
`):l?`\u6CA1\u6709\u66F4\u591A ${L(o)} \u5BBF\u4E3B\u8F93\u51FA\u3002`:`No additional ${L(o)} host output.`;return u("div",{role:"status","aria-label":h,style:{display:"grid",placeItems:"center",boxSizing:"border-box",height:"100%",minHeight:280,padding:24},children:H("div",{style:{display:"flex",flexDirection:"column",alignItems:"center",gap:12,width:"min(620px, 100%)"},children:[u("div",{"aria-hidden":"true",style:{width:46,height:82,border:`2px solid ${t?a.tokens.status.danger:a.tokens.accent.control}`,borderRadius:12,boxShadow:`inset 0 0 0 4px ${a.tokens.fill.tertiary}`}}),u("strong",{style:{color:t?a.tokens.status.danger:a.tokens.text.primary,textAlign:"center"},children:h}),H("span",{style:{color:a.tokens.text.secondary,fontSize:12},children:[i?.phase||(l?"\u542F\u52A8\u4E2D":"Starting")," \xB7 ",(e/1e3).toFixed(1),"s"]}),u("pre",{style:{boxSizing:"border-box",width:"100%",maxHeight:180,overflow:"auto",margin:0,padding:"10px 12px",border:`1px solid ${a.tokens.stroke.tertiary}`,borderRadius:6,background:a.tokens.fill.tertiary,color:a.tokens.text.secondary,fontSize:11,lineHeight:1.55,whiteSpace:"pre-wrap"},children:P}),t?u("button",{type:"button",onClick:g,style:{padding:"6px 12px",border:0,borderRadius:6,background:a.tokens.accent.control,color:a.tokens.text.onAccent,cursor:"pointer"},children:l?"\u91CD\u8BD5":"Retry"}):null]})})}function ve(e){return e?.schemaVersion===1&&e.kind==="device-ui-tree"&&Number.isInteger(e.totalNodeCount)&&Number.isInteger(e.includedNodeCount)&&typeof e.truncated=="boolean"&&Array.isArray(e.elements)}function ye(e,t){return{type:"aicoding.canvas.hostContext",language:e,theme:{kind:t.kind,colors:{accent:t.tokens.accent.control,accentHover:t.tokens.accent.controlHover,background:t.tokens.bg.editor,elevated:t.tokens.bg.elevated,fill:t.tokens.fill.tertiary,foreground:t.tokens.text.primary,foregroundSecondary:t.tokens.text.secondary,foregroundTertiary:t.tokens.text.tertiary,focus:t.tokens.accent.focus,onAccent:t.tokens.text.onAccent,stroke:t.tokens.stroke.tertiary}}}}function xe(e){try{let t=new URL(e);return t.protocol==="http:"&&(t.hostname==="127.0.0.1"||t.hostname==="localhost")}catch{return!1}}function ke(e){if(!e)return!1;for(let t=0;t<window.frames.length;t+=1)if(window.frames[t]===e)return!0;return!1}function L(e){return e==="android"?"Android":e==="harmony"?"HarmonyOS":"iOS"}import{Banner as he,Stack as be,useCanvasTargetFilePath as Ce,useHostLanguage as Se,useHostTheme as we}from"qoder/canvas";import{jsx as B}from"react";function Re(){let e=Ce(),t=Se(),a=we(),{isChinese:r}=t,{tokens:o}=a;return e?B(ee,{targetFilePath:e,platform:"ios",hostLanguage:t,hostTheme:a,height:"100%",style:{position:"fixed",inset:0}}):B(be,{gap:0,style:{position:"fixed",inset:0,background:o.bg.editor},children:B(he,{tone:"info",children:r?"\u8BF7\u6253\u5F00 Xcode \u9879\u76EE\u7684 project.pbxproj\u3002":"Open the Xcode project's project.pbxproj."})})}export{Re as default};
