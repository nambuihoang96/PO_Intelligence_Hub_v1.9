'use strict';
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const C=require('../static/v16-core.js');
const samples=process.argv.slice(2);
assert.equal(C.number(''),null);assert.equal(C.number('-0.018859'),-.018859);assert.equal(C.number('1,000'),1000);
assert.equal(C.date('2026/10/13'),'2026-10-13');
assert.equal(C.periodFromName('Unified Top Apps Downloads  (Sep 14, 2026 - Oct 13, 2026, Worldwide), Table Data.csv').end,'2026-10-13');
assert.equal(C.periodFromName('Top Apps (Sep 14, 2026 - Oct 13, 2026, US).csv').start,'2026-09-14');
assert.equal(C.periodFromName('Top Apps (Feb 30, 2026 - Mar 01, 2026, US).csv').start,'');
const testCSV='Unified Name,Unified ID,Downloads (Absolute),Downloads (PoP Growth),Downloads (PoP Growth %),Platform,Release Date (WW)\n"Game, A",id1,1000,200,0.25,iOS,2026/10/01\n';
const small=C.parseFileText(testCSV,'sample.csv');assert.equal(small.records.length,1);assert.equal(small.records[0].name,'Game, A');assert.equal(small.records[0].source.line,2);
assert.equal(C.getFiltered([{id:'1',name:'A',publisher:'X',category:'Games',platform:'iOS',geo:'US',release:'2026-10-01',age:10,downloads:1000,growth_pop:.25},{id:'2',name:'B',publisher:'X',category:'Games',platform:'Android',geo:'US',release:'2026-10-01',age:10,downloads:500,growth_pop:.02}],{sort:'downloads',direction:'desc',top:'10',columns:{growth_popMin:.1}}).view.length,1);
if(samples.length){const parsed=samples.map(f=>C.parseFileText(C.decode(fs.readFileSync(f)),path.basename(f)));assert.equal(parsed[0].records.length,10000);assert.equal(parsed[1].records.length,10000);const merged=C.mergeImports(parsed);assert.equal(merged.data.length,13852);const block=merged.data.find(x=>x.id==='622390aa2e0fa027dbdc26b8');assert(block);assert.equal(block.downloads,22103448);assert.equal(block.sources.pop.line,2);const meow=merged.data.find(x=>x.name==='Meowdoku: Brain Puzzle Games');assert(meow);assert.equal(meow.sources.yoy.line,2);assert.equal(meow.sources.pop.line,3);const top=C.getFiltered(merged.data,{sort:'downloads',direction:'desc',top:'10',columns:{}});assert.equal(top.view.length,10);assert.equal(top.view[0].name,'Block Blast!');const missing=C.getFiltered(merged.data,{sort:'growth_yoy',direction:'desc',top:'100',columns:{growth_yoyMin:1}});assert(missing.view.every(x=>x.growth_yoy!==null&&x.growth_yoy>=1));console.log('Real CSV import: 20,000 source rows,',merged.data.length,'distinct scope-specific records; filters/sort/evidence OK.');}
console.log('v1.6.1 core tests passed');
