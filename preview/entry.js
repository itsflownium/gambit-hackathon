import * as React from 'react';
import {createRoot} from 'react-dom/client';
import {createBoard} from '../src/board.js';

const api=async(path,options={})=>{
  const response=await fetch('/api/plugins/gambit'+path,{...options,headers:{'Content-Type':'application/json'},body:options.body?JSON.stringify(options.body):undefined});
  if(!response.ok)throw new Error('Board request failed ('+response.status+')');
  return response.json();
};
const Board=createBoard(React);
createRoot(document.getElementById('root')).render(React.createElement(Board,{
  api,sessionId:'preview',onPrompt:()=>false,chatBusy:false
}));
