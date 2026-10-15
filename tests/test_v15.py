"""Regression tests: AI provenance, real lifecycle operations, no canned recommendations."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from decision_workflows import (create_subtask,update_subtask,delete_subtask,restore_subtask,
                                draft_ai_opportunities,update_opportunity)
from research_engine import build_baseline

class V15IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(server,'DBPATH',Path(self.tmp.name)/'research.sqlite3')
        self.patch.start();server.init()
        self.url='https://apps.apple.com/us/app/legitimate-editor/id12345678'
        apps=[{'name':'Legitimate Photo Tool', 'store_id':'12345678', 'country':'US','platform':'iOS',
               'developer':'Example Studio', 'store_url':self.url,
               'description':'Photo editor with background eraser and portraits', 'rating':4.5,'reviews':250}]
        with server.con() as c:
            project=dict(c.execute('SELECT * FROM projects WHERE id=3').fetchone())
            report=build_baseline(project,apps,mode='live')
            c.execute('INSERT INTO research_runs(project_id,mode,status,report_json,ai_packet,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                (3,'live','ready',server.dumps(report),'local evidence packet',server.now(),server.now()))
            self.rid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        self.action=server.create_research_action({'run_id':self.rid,'source_type':'baseline_insight','index':0})
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def test_rule_engine_only_observations_not_canned_actions(self):
        with server.con() as c:
            report=json.loads(c.execute('SELECT report_json FROM research_runs WHERE id=?',(self.rid,)).fetchone()[0])
        self.assertEqual(report['recommendations'],[])
        self.assertTrue(report['insights'])
        with self.assertRaisesRegex(ValueError,'không tồn tại'):
            server.create_research_action({'run_id':self.rid,'source_type':'baseline','index':0})

    def test_invalid_research_brief_rejected(self):
        with self.assertRaisesRegex(ValueError,'Chưa xác định'):
            server.create_planner({'brief':'Tôi muốn thử xem action của bạn có fix cứng hay không'})

    def test_subtasks_edit_delete_restore_and_progress_exclusion(self):
        id=self.action['id']
        a=create_subtask({'action_id':id,'title':'Evidence check'},server.con,server.LOCK,server.now,server.dumps)
        b=update_subtask(a['id'],{'title':'Validate onboarding path','description':'Capture screenshot','priority':'high','owner':'PO','state':'in_progress','due_date':'2026-10-31'},server.con,server.LOCK,server.now)
        self.assertEqual((b['title'],b['priority'],b['state']),('Validate onboarding path','high','in_progress'))
        with self.assertRaises(ValueError):server.update_action_record(id,{'state':'done'})
        deleted=delete_subtask(a['id'],server.con,server.LOCK,server.now)
        self.assertTrue(deleted['deleted'])
        self.assertEqual(server.update_action_record(id,{'state':'done'})['state'],'done')
        with self.assertRaises(ValueError):update_subtask(a['id'],{'title':'Secretly revived'},server.con,server.LOCK,server.now)
        with self.assertRaises(ValueError):restore_subtask(a['id'],server.con,server.LOCK,server.now)
        server.update_action_record(id,{'state':'in_progress'})
        self.assertTrue(restore_subtask(a['id'],server.con,server.LOCK,server.now)['restored'])
        self.assertFalse(next(x for x in server.bootstrap()['action_subtasks'] if x['id']==a['id'])['is_deleted'])

    def test_ai_opportunity_with_verified_source_is_draft_and_editable(self):
        inv=server.start_investigation({'action_id':self.action['id'],'mode':'manual'})
        ai={'action_id':self.action['id'],'executive_summary':'Potential product opportunity requiring validation',
            'findings':[{'claim':'Listing describes eraser','type':'fact','confidence':'medium','evidence_urls':[self.url]}],
            'next_steps':[{'title':'Validate feature','priority':'medium','validation_step':'Run in-app session'}],
            'opportunity_drafts':[{'title':'Streamline background removal flow','user_problem':'Users may spend time retrying extraction','hypothesis':'Shorter extraction flow may improve first-session task completion','confidence':'low','impact':'unknown','validation_step':'Interview users then run task-completion usability test','evidence_urls':[self.url]}],
            'missing_evidence':['User interviews'],'limitations':['Only store description']}
        self.assertTrue(server.import_investigation_result(inv['id'],{'result':ai})['success'])
        one=draft_ai_opportunities(inv['id'],server.con,server.LOCK,server.now,server.dumps,server.safejson)
        two=draft_ai_opportunities(inv['id'],server.con,server.LOCK,server.now,server.dumps,server.safejson)
        self.assertEqual(one['draft_count'],1)
        self.assertEqual(one['drafts'][0]['id'],two['drafts'][0]['id'])
        draft=one['drafts'][0]
        self.assertEqual((draft['state'],draft['investigation_id']),('proposed',inv['id']))
        self.assertEqual(json.loads(draft['evidence_json'])[0]['url'],self.url)
        updated=update_opportunity(draft['id'],{'title':'New improved title','validation_step':'Run prototype'},server.con,server.LOCK,server.now)
        self.assertEqual(updated['title'],'New improved title')
        with self.assertRaisesRegex(ValueError,'bằng chứng'):
            update_opportunity(draft['id'],{'state':'validated'},server.con,server.LOCK,server.now)

    def test_invalid_ai_evidence_rejected_instead_of_creating_opp(self):
        inv=server.start_investigation({'action_id':self.action['id']})
        fake={'action_id':self.action['id'],'executive_summary':'Should never be imported',
            'findings':[],'next_steps':[],'missing_evidence':[],'limitations':[],
            'opportunity_drafts':[{'title':'Fake opportunity','user_problem':'Claim','hypothesis':'Hyp','confidence':'high','impact':'high',
             'validation_step':'Test','evidence_urls':['https://evil.invalid/made-up-source']} ]}
        with self.assertRaisesRegex(ValueError,'Opportunity AI'):
            server.import_investigation_result(inv['id'],{'result':fake})
        self.assertEqual(server.bootstrap()['opportunities'],[])

    def test_no_ai_result_does_not_fabricate_proposal(self):
        inv=server.start_investigation({'action_id':self.action['id']})
        ai={'action_id':self.action['id'],'executive_summary':'Not enough evidence',
            'findings':[],'next_steps':[],'opportunity_drafts':[], 'missing_evidence':['Users'], 'limitations':['Limited data']}
        server.import_investigation_result(inv['id'],{'result':ai})
        result=draft_ai_opportunities(inv['id'],server.con,server.LOCK,server.now,server.dumps,server.safejson)
        self.assertEqual(result['draft_count'],0)
        self.assertEqual(server.bootstrap()['opportunities'],[])

    def test_demo_scope_guard(self):
        with self.assertRaisesRegex(ValueError,'chỉ mô phỏng AI Photo Editor'):
            server.launch_initial_research({'project_id':1,'mode':'demo'})

if __name__=='__main__':unittest.main()
