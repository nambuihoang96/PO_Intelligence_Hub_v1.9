import unittest
import tempfile
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.orig=(s.DATA,s.DBPATH)
        s.DATA=Path(self.tmp.name);s.DBPATH=s.DATA/'research.sqlite3';s.init()
        self.pid=s.new_project({'name':'ASMR study','brief':'Thị trường game ASMR có đang trending không, game nào đang scale tốt?','category':'Games'})['id']
        self.collect=patch.object(s,'discover',return_value={'results':[dict(store_id='42',name='ASMR Craft',description='ASMR sensory game for relaxation',platform='iOS',country='US',primary_genre='Games',reviews=400,url='https://apps.apple.com/us/app/id42')]});self.collect.start()
        self.android=patch.object(s,'android_search',side_effect=ValueError('connector missing'));self.android.start()
        self.news=patch.object(s,'research_news_context',return_value=([],[]));self.news.start()
    def tearDown(self):
        for t in list(w.THREADS.values()):t.join(timeout=3)
        self.collect.stop();self.android.stop();self.news.stop();s.DATA,s.DBPATH=self.orig;self.tmp.cleanup()
    def start(self,**kw):
        p=dict(research_id=self.pid,question='Thị trường game ASMR có đang trending không, game nào đang scale tốt?',mode='manual');p.update(kw)
        with s.LOCK:r=w.launch(s,p)
        return r
    def wait(self,rid):
        for _ in range(100):
            with s.LOCK,s.con() as c:r=w.get(c,rid)
            if r['status'] not in ('queued','planning','collecting','assessing','analyzing'):return r
            time.sleep(.03)
        self.fail('timeout')
    def answer(self,r):
        e=next(e for e in r['packet']['evidence'] if e['relevance']=='relevant')
        return dict(trend=dict(status='insufficient_evidence',answer='Chưa đủ bằng chứng trend: chỉ có listing hiện tại tại US.',confidence='low',classification='insufficient_evidence',evidence_ids=[e['evidence_id']]),scale_candidates=[dict(name=e['name'],app_id=e['store_id'],reason='Ứng viên ASMR cần xác minh.',evidence_ids=[e['evidence_id']],signal_ids=[],unknowns='Thiếu spend/CPI/retention/ROAS.',classification='insufficient_evidence')],research_gaps=['Thiếu kỳ so sánh.'],next_steps=[dict(title='Xác minh ASMR Craft',reason='Thu thập thêm kỳ so sánh.',evidence_ids=[e['evidence_id']])])
    def test_asmr_no_puzzle(self):
        scope=w.scope_for('Thị trường game ASMR có đang trending không, game nào đang scale tốt?')
        self.assertEqual(scope['topic'],'ASMR');self.assertEqual(scope['product_type'],'games');self.assertNotIn('puzzle',json.dumps(scope).lower())
    def test_utilities_and_all_apps(self):
        self.assertEqual(w.scope_for('Thị trường Utilities có đang trending không?')['product_type'],'utilities')
        self.assertEqual(w.scope_for('All mobile apps đang trending?')['product_type'],'all_apps')
    def test_explicit_scope_wins(self):
        sc=w.scope_for('ASMR games Android tại Việt Nam 60 ngày',{'geo':'US','days':30,'platforms':['iOS']})
        self.assertEqual((sc['geo'],sc['days'],sc['platforms']),('VN',60,['Android']))
    def test_manual_single_handoff_and_partial_failure(self):
        r=self.wait(self.start()['id']);self.assertEqual(r['status'],'awaiting_manual');self.assertIn('SCHEMA:',r['packet']['prompt'])
        self.assertTrue(any(e['source']=='google_play' and e['status']=='error' for e in r['packet']['sources']))
        self.assertTrue(r['packet']['evidence']);self.assertTrue(r['result']['preliminary'])
    def test_deduplicates(self):
        r=self.start();r2=self.start();self.assertEqual(r['id'],r2['id'])
    def test_manual_invalid_json_preserves_packet(self):
        r=self.wait(self.start()['id'])
        with self.assertRaisesRegex(ValueError,'JSON'):w.import_result(s,r['id'],{'result':'broken'})
        with s.con() as c:self.assertEqual(w.get(c,r['id'])['status'],'awaiting_manual')
    def test_false_trend_rejected(self):
        r=self.wait(self.start()['id']);a=self.answer(r);a['trend']['status']='rising'
        with self.assertRaisesRegex(ValueError,'signals'):w.validate(a,r['packet'])
    def test_unknown_evidence_rejected(self):
        r=self.wait(self.start()['id']);a=self.answer(r);a['trend']['evidence_ids']=['STOREH:999999']
        with self.assertRaisesRegex(ValueError,'Evidence ID'):w.validate(a,r['packet'])
    def test_wrong_app_identity_rejected(self):
        r=self.wait(self.start()['id']);a=self.answer(r);a['scale_candidates'][0]['app_id']='wrong'
        with self.assertRaisesRegex(ValueError,'định danh'):w.validate(a,r['packet'])
    def test_result_action_opportunity_and_snapshot(self):
        r=self.wait(self.start()['id']);w.import_result(s,r['id'],{'result':self.answer(r)})
        a=w.create_action(s,r['id'],{'index':0});a2=w.create_action(s,r['id'],{'index':0});self.assertEqual(a['id'],a2['id'])
        o=w.create_action(s,r['id'],{'index':0,'kind':'opportunity'});self.assertEqual(o['action_id'],a['id'])
        with s.con() as c:
            report=s.hub_workflows.action_report(c,dict(c.execute('SELECT * FROM action_registry WHERE id=?',(a['id'],)).fetchone()))
            self.assertEqual(report['coverage']['workspace_run_id'],r['id'])
        next_run=self.wait(self.start()['id']);self.assertNotEqual(r['id'],next_run['id'])
        with s.con() as c:self.assertEqual(w.get(c,r['id'])['status'],'ready')
    def test_recover_keeps_manual(self):
        r=self.wait(self.start()['id']);w.recover(s)
        with s.con() as c:self.assertEqual(w.get(c,r['id'])['status'],'awaiting_manual')
    def test_cancel(self):
        r=self.wait(self.start()['id']);w.cancel(s,r['id'])
        with s.con() as c:self.assertEqual(w.get(c,r['id'])['status'],'cancelled')
    def test_auto_not_silent_fallback(self):
        with self.assertRaisesRegex(ValueError,'Settings'):self.start(mode='auto')
    def test_auto_end_to_end_mock_cli(self):
        with s.con() as c:c.execute("UPDATE settings SET value='true' WHERE key='codex_allowed'")
        def mock(srv,rid,prompt,schema):
            if 'seeds' in schema['properties']:return {'seeds':['ASMR game','puzzle'],'reason':'Exact topic'}
            with s.con() as c:r=w.get(c,rid)
            return self.answer(r)
        with patch.object(w,'check_cli',return_value={'ok':True}),patch.object(w,'call_ai',side_effect=mock):
            r=self.wait(self.start(mode='auto')['id']);self.assertEqual(r['status'],'ready');self.assertNotIn('puzzle',r['scope']['seeds'])
    def test_auto_error_retry_keeps_evidence(self):
        with s.con() as c:c.execute("UPDATE settings SET value='true' WHERE key='codex_allowed'")
        def mock(srv,rid,prompt,schema):
            if 'seeds' in schema['properties']:return {'seeds':['ASMR'],'reason':'Exact topic'}
            raise ValueError('AI offline')
        with patch.object(w,'check_cli',return_value={'ok':True}),patch.object(w,'call_ai',side_effect=mock):
            r=self.wait(self.start(mode='auto')['id']);self.assertEqual(r['status'],'error');self.assertTrue(r['packet'])
        with patch.object(w,'call_ai',side_effect=lambda srv,rid,prompt,schema:self.answer(r)):
            w.retry(s,r['id']);r=self.wait(r['id']);self.assertEqual(r['status'],'ready')
    def test_auto_repairs_invalid_evidence_once(self):
        with s.con() as c:c.execute("UPDATE settings SET value='true' WHERE key='codex_allowed'")
        attempts=[]
        def mock(srv,rid,prompt,schema):
            if 'seeds' in schema['properties']:return dict(seeds=['ASMR'],reason='Exact topic')
            with s.con() as c:r=w.get(c,rid)
            result=self.answer(r);attempts.append(prompt)
            if len(attempts)==1:result['next_steps'][0]['evidence_ids']=[]
            return result
        with patch.object(w,'check_cli',return_value={'ok':True}),patch.object(w,'call_ai',side_effect=mock):
            r=self.wait(self.start(mode='auto')['id'])
        self.assertEqual(r['status'],'ready');self.assertEqual(len(attempts),2);self.assertTrue(r['packet']['ai_validation_errors'])
    def test_cancel_terminates_auto_process(self):
        import subprocess
        with s.con() as c:c.execute("UPDATE settings SET value='true' WHERE key='codex_allowed'")
        original=subprocess.Popen
        def popen(args,**kw):return original([sys.executable,'-c','import time;time.sleep(30)'],**kw)
        with patch.object(w,'check_cli',return_value={'ok':True}),patch.object(w,'cli_path',return_value=sys.executable),patch.object(w.subprocess,'Popen',side_effect=popen):
            r=self.start(mode='auto')
            for _ in range(100):
                if r['id'] in w.PROCESSES:break
                time.sleep(.02)
            proc=w.PROCESSES[r['id']];w.cancel(s,r['id']);w.THREADS[r['id']].join(timeout=5)
            self.assertIsNotNone(proc.poll())
        with s.con() as c:self.assertEqual(w.get(c,r['id'])['status'],'cancelled')
    def test_name_only_possible_not_proof(self):
        status,_=w.relevance(dict(name='ASMR',category='Games',platform='iOS',country='US'),w.scope_for('ASMR games'))
        self.assertEqual(status,'possible')
    def test_unrelated_and_mismatched_csv(self):
        sc=w.scope_for('ASMR games')
        for row in [dict(name='Puzzle',category='Games',platform='iOS',geo='US',period_start=sc['start'],period_end=sc['end']),dict(name='ASMR',category='Games',platform='Unified',geo='Worldwide',period_start=sc['start'],period_end=sc['end'])]:
            self.assertEqual(w.relevance(row,sc,True)[0],'unrelated')
    def test_all_candidates_assessed_not_seventy(self):
        with s.con() as c:
            studio=s.studio;studio.save_public(c,self.pid,[dict(store_id=str(i),name='ASMR '+str(i),description='ASMR game',platform='iOS',country='US',primary_genre='Games') for i in range(203)])
            p=w.assess(c,self.pid,w.scope_for('ASMR games'));self.assertEqual(p['coverage']['total'],203);self.assertEqual(p['coverage']['assessed'],203)
    def test_top_n_cannot_change_analysis(self):
        r=self.wait(self.start()['id'])
        with s.con() as c:
            p=w.assess(c,self.pid,r['scope']);q=w.assess(c,self.pid,r['scope'])
        self.assertEqual(p,q);self.assertNotIn('top',r['scope'])
    def test_selected_evidence_is_explicit_scope(self):
        r=self.wait(self.start()['id']);w.cancel(s,r['id'])
        eid=next(e['evidence_id'] for e in r['packet']['evidence'] if e['relevance']=='relevant')
        nxt=self.wait(self.start(selected_evidence_ids=[eid])['id'])
        self.assertEqual(nxt['scope']['selected_evidence_ids'],[eid])
        self.assertTrue(all(e['relevance']=='unrelated' or e['evidence_id']==eid for e in nxt['packet']['evidence']))
    def test_csv_signal_has_file_line_and_period(self):
        scope=w.scope_for('ASMR games')
        with s.con() as c:
            imp=s.studio.start_import(c,dict(project_id=self.pid,filename='ASMR.csv',fingerprint='b'*64,kind='pop',period={'start':scope['start'],'end':scope['end'],'geo':'US'}))
            s.studio.import_batch(c,dict(import_id=imp['id'],rows=[dict(id='csv42',name='ASMR Test',category='Games',platform='iOS',geo='US',period_start=scope['start'],period_end=scope['end'],downloads=1000,delta_pop=200,source={'line':2})]))
            s.studio.finish_import(c,dict(import_id=imp['id'],expected=1));p=w.assess(c,self.pid,scope)
        self.assertEqual(p['signals'][0]['value'],200);self.assertEqual(p['signals'][0]['evidence_ids'],['CSV:'+str(imp['id'])+':2'])
        self.assertEqual(p['signals'][0]['period_start'],scope['start']);self.assertEqual(p['evidence'][0]['sources']['pop']['filename'],'ASMR.csv')
    def test_snapshot_comparison_requires_two_periods(self):
        scope=w.scope_for('ASMR games');item=dict(store_id='42',name='ASMR',description='ASMR game',platform='iOS',country='US',primary_genre='Games',reviews=10,url='https://example.com/app')
        with s.con() as c:
            s.studio.save_public(c,self.pid,[item]);c.execute('UPDATE studio_public_history SET collected_at=?',(scope['comparison_start']+'T12:00:00+00:00',))
            self.assertFalse(w.assess(c,self.pid,scope)['signals'])
            item['reviews']=20;s.studio.save_public(c,self.pid,[item]);c.execute('UPDATE studio_public_history SET collected_at=? WHERE id=(SELECT MAX(id) FROM studio_public_history)',(scope['start']+'T12:00:00+00:00',))
            p=w.assess(c,self.pid,scope)
        self.assertEqual(p['signals'][0]['value'],10);self.assertEqual(len(p['signals'][0]['evidence_ids']),2)
    def test_no_sources_still_honest_manual_answer(self):
        r=self.wait(self.start(scope={'sources':[]})['id'])
        self.assertEqual(r['status'],'awaiting_manual');self.assertFalse(r['packet']['evidence']);self.assertEqual(r['result']['trend']['status'],'insufficient_evidence')
    def test_typed_json_and_classification_enforced(self):
        r=self.wait(self.start()['id']);a=self.answer(r);a['trend']['classification']='observed'
        with self.assertRaises(ValueError):w.validate(a,r['packet'])
        a=self.answer(r);a['research_gaps']='not a list'
        with self.assertRaises(ValueError):w.validate(a,r['packet'])
    def test_long_title_capped(self):
        self.assertLessEqual(len(w.title_for(w.scope_for('ASMR games'),'x'*500)),80)
    def test_restart_interrupts_running_not_results(self):
        r=self.wait(self.start()['id'])
        with s.con() as c:c.execute("UPDATE workspace_runs SET status='collecting' WHERE id=?",(r['id'],))
        w.recover(s)
        with s.con() as c:after=w.get(c,r['id'])
        self.assertEqual(after['status'],'interrupted');self.assertEqual(after['packet'],r['packet'])

if __name__=='__main__':unittest.main()
