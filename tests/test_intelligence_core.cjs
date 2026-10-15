'use strict';
const assert=require('node:assert/strict'),C=require('../static/v16-core.js');
const head='Unified Name,Unified ID,Category,Downloads (Absolute),Downloads (PoP Growth),Platform,Date,Granularity,Currency,Revenue (Absolute),UA Spend,CPI,Retention (%),ROAS (%),ROAS Target (%),Cohort Window,Cohort Start,Cohort End,Measurement Date\n';
const row='ASMR,42,Games,1000,100,iOS,2026/10/13,,USD,500,100,0.5,35,120,110,D7,2026/09/16,2026/10/13,2026/10/20\n';
const monthly=C.parseFileText(head+row,'TEST Apps (Sep 14, 2026 - Oct 13, 2026, US).csv').records[0];assert.equal(monthly.period_start,'2026-09-14');assert.equal(monthly.period_end,'2026-10-13');assert.equal(monthly.roas_target_percent,110);assert.equal(monthly.currency,'USD');
const daily=C.parseFileText(head+row.replace('2026/10/13,,USD','2026/10/13,daily,USD'),'TEST Apps (Sep 14, 2026 - Oct 13, 2026, US).csv').records[0];assert.equal(daily.period_start,'2026-10-13');assert.equal(daily.period_end,'2026-10-13');assert.equal(daily.cohort_window,'D7');
console.log('v1.9.1 CSV day/period/currency/cohort parser tests PASS');
