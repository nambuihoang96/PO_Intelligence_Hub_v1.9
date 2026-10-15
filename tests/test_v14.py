"""Regression tests for v1.4 audit, Signal Explorer, and decision traceability."""
import json
import tempfile
import unittest
import time
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from decision_workflows import *
from research_engine import build_baseline

class DecisionV14Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patcher=patch.object(server,'DBPATH',Path(self.tmp.name)/'test.sqlite3');self.patcher.start()
        server.init()
        self.runid=server.launch_initial_research({'project_id':3,'mode':'demo'})['id']
        for _ in range(100):
            self.runrow=next(x for x in server.bootstrap()['research_runs'] if x['id']==self.runid)
            if self.runrow['status']!='running':break
            time.sleep(.01)
        self.assertEqual(self.runrow['status'],'ready',self.runrow.get('error'))
        self.action=server.create_research_action({'run_id':self.runid,'source_type':'baseline_insight','index':0})
    def tearDown(self):
        self.patcher.stop();self.tmp.cleanup()
    def test_signal_count_sql_not_frontend_cap(self):
        with server.con() as c:
            for i in range(350):
                c.execute("INSERT INTO signals(project_id,kind,title,description,fingerprint,is_demo,created_at) VALUES(?,?,?,?,?,?,?)",
                    (3,'Version changed',f'Real change {i}','Updated store description',f'signal-v14-{i}',0,server.now()))
        stats=server.bootstrap()['signal_stats']
        self.assertGreaterEqual(stats['total'],355)
        q=server.query_signals({'project_id':3,'source':'store','per_page':'40','page':'3'})
        self.assertEqual(q['total'],350)
        self.assertEqual(len(q['rows']),40)
        self.assertEqual(q['page'],3)
        self.assertTrue(all(x['analysis_status']=='new' for x in q['rows']))
        self.assertGreater(stats['by_project']['3'],300)
    def test_keyword_relevance_filter_and_over_120_report(self):
        apps=[{'name':f'Puzzle Game {i}', 'description':'Casual puzzle mechanic and levels', 'store_id':f'com.puzz.g{i}', 'platform':'Android','country':'US','store_url':f'https://play.google.com/store/apps/details?id=com.puzz.g{i}'} for i in range(158)]
        apps+=[{'name':'Unrelated Hotel','description':'Book cheap hotels', 'store_id':'com.hotel.app','platform':'Android','country':'US'}]
        profile=server.normalize_profile({'keywords_include':['puzzle'],'geos':['US'],'platforms':['Android']})
        chosen,rejected=server.discovery_filter(apps,profile)
        self.assertEqual(len(chosen),158);self.assertEqual(len(rejected),1)
        r=build_baseline({'name':'Puzzle','category':'Game','geo':'US'},chosen)
        self.assertEqual(r['sample_count'],158)
    def test_research_config_fingerprint_stale(self):
        self.assertFalse(next(x for x in server.bootstrap()['research_runs'] if x['id']==self.runid)['stale_config'])
        p=next(x for x in server.bootstrap()['projects'] if x['id']==3)
        server.update_project(3,{'name':p['name'],'profile':{'category':'Photo & Video','geos':['KR'], 'keywords_include':['korean ai filters']}})
        r=next(x for x in server.bootstrap()['research_runs'] if x['id']==self.runid)
        self.assertTrue(r['stale_config'])
    def test_subtask_approval_completion_and_parent_guard(self):
        st=create_subtask({'action_id':self.action['id'],'title':'Compare 3 puzzle loops'},server.con,server.LOCK,server.now,server.dumps)
        self.assertEqual(st['state'],'proposed')
        updated=update_subtask(st['id'],{'state':'in_progress','owner':'PO','due_date':'2026-10-31'},server.con,server.LOCK,server.now)
        self.assertEqual(updated['owner'],'PO')
        with self.assertRaises(ValueError):server.update_action_record(self.action['id'],{'state':'done'})
        update_subtask(st['id'],{'state':'done'},server.con,server.LOCK,server.now)
        self.assertEqual(server.update_action_record(self.action['id'],{'state':'done'})['state'],'done')
    def test_draft_ai_steps_idempotently(self):
        inv=server.start_investigation({'action_id':self.action['id']})
        result={'action_id':self.action['id'],'executive_summary':'DEMO simulated benchmark results',
            'findings':[{'claim':'Store listing says puzzle','type':'hypothesis','confidence':'low','evidence_urls':[]}],
            'next_steps':[{'title':'Capture walkthrough','priority':'high','validation_step':'Record session'},
                          {'title':'Validate metric','priority':'medium','validation_step':'Analyze level completion'}],
            'missing_evidence':['in-app flow'],'limitations':['DEMO']}
        server.import_investigation_result(inv['id'],{'result':result})
        one=draft_investigation_steps(inv['id'],server.con,server.LOCK,server.now,server.dumps,server.safejson)
        two=draft_investigation_steps(inv['id'],server.con,server.LOCK,server.now,server.dumps,server.safejson)
        self.assertEqual(one['draft_count'],2)
        self.assertEqual(two['draft_count'],2)
        self.assertTrue(all(x['state']=='proposed' for x in one['drafts']))
        self.assertEqual(len(server.bootstrap()['action_subtasks']),2)
    def test_opportunity_experiment_guardrails_and_history(self):
        a=self.action
        o=create_opportunity({'action_id':a['id'],'title':'Puzzle progression opportunity','user_problem':'Users may not see enough goals','hypothesis':'Progression increases retention'},server.con,server.LOCK,server.now,server.dumps)
        self.assertEqual(o['state'],'proposed')
        with self.assertRaises(ValueError):update_opportunity(o['id'],{'state':'validated'},server.con,server.LOCK,server.now)
        x=create_experiment({'opportunity_id':o['id'],'title':'Progression MVP','hypothesis':'D1 grows if goals exist',
            'primary_metric':'D1 retention','guardrails':'Crash free, eCPM','success_criteria':'>2pp improvement with planned power'},server.con,server.LOCK,server.now)
        self.assertEqual(x['state'],'draft')
        with self.assertRaises(ValueError):update_experiment(x['id'],{'state':'running'},server.con,server.LOCK,server.now)
        # Add explicit evidence for an actual (non-demo) verified source, and explicitly validate by PO.
        with server.con() as c:
            c.execute("UPDATE opportunities SET confidence='medium' WHERE id=?",(o['id'],))
        add_opportunity_evidence(o['id'],{'name':'Observed gameplay video','url':'https://example.org/gameplay/evidence','type':'walkthrough','po_confirmed':True},server.con,server.LOCK,server.now,server.dumps)
        update_opportunity(o['id'],{'state':'validated'},server.con,server.LOCK,server.now)
        self.assertEqual(update_experiment(x['id'],{'state':'running'},server.con,server.LOCK,server.now)['state'],'running')
        with self.assertRaises(ValueError):update_experiment(x['id'],{'state':'completed'},server.con,server.LOCK,server.now)
        update_experiment(x['id'],{'state':'completed','result_notes':'No significant gain under agreed criteria'},server.con,server.LOCK,server.now)
        data=server.bootstrap()
        self.assertEqual(data['experiments'][0]['opportunity_id'],o['id'])
        self.assertEqual(data['opportunities'][0]['action_id'],a['id'])

if __name__=='__main__':unittest.main()
