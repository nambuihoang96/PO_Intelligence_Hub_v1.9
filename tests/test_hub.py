import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server,studio,hub_workflows as hub

class UnifiedHubTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(server,'DBPATH',Path(self.tmp.name)/'hub.sqlite3');self.patch.start()
        server.init()
        self.pid=server.new_project({'name':'All Mobile Research','brief':'Research all mobile apps and rising categories','profile':{'category':'Other','geos':['US'],'platforms':['iOS'],'keywords_include':['mobile apps']}})['id']
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def evidence(self):
        with server.con() as c:
            studio.save_public(c,self.pid,[{'name':'Test Utility','platform':'iOS','country':'US','store_id':'test1','url':'https://apps.apple.com/app/idtest1','category':'Utilities'}])
            imp=studio.start_import(c,{'project_id':self.pid,'filename':'test.csv','fingerprint':'a'*64,'kind':'pop','period':{'start':'2026-09-01','end':'2026-09-30','geo':'US'}})
            studio.import_batch(c,{'import_id':imp['id'],'rows':[{'id':'a','name':'Test Utility','platform':'iOS','geo':'US','category':'Utilities','period_start':'2026-09-01','period_end':'2026-09-30','downloads':100,'delta_pop':10,'source':{'line':2}},{'id':'b','name':'Test Game','platform':'Android','geo':'JP','category':'Games','period_start':'2026-09-01','period_end':'2026-09-30','downloads':200,'source':{'line':3}}]})
            studio.finish_import(c,{'import_id':imp['id'],'expected':2})
        return imp['id']
    def analysis(self):
        self.evidence()
        with server.con() as c:
            a=studio.prepare(c,{'project_id':self.pid,'market':'All','mode':'hybrid'})
            ev=a['overview']['public_candidates'][0]['evidence_id']
            result={'executive_summary':'TEST FIXTURE — no live market conclusion','market_findings':[{'title':'Listing exists','observation':'Test store listing','interpretation':'No UA conclusion','confidence':'low','evidence_ids':[ev]}],'subcategory_assessments':[],'rising_apps':[],'research_gaps':['Need retention and spend'],'suggested_research_actions':[{'title':'Verify utility workflow','reason':'Inspect the original source','evidence_ids':[ev]}]}
            studio.import_ai(c,{'analysis_id':a['id'],'result':result})
        return a
    def test_additive_migration_preserves_legacy_and_is_idempotent(self):
        before=server.bootstrap();server.init();server.init();after=server.bootstrap()
        self.assertEqual(before['projects'],after['projects']);self.assertEqual(before['tasks'],after['tasks'])
        with server.con() as c:self.assertEqual(len(hub.overview(c)['projects']),4)
    def test_upgrade_backup_is_consistent_and_only_created_once(self):
        with server.con() as c:c.execute('DROP TABLE hub_reports')
        server.init()
        backups=list(server.DBPATH.parent.glob('backups/*.sqlite3'))
        self.assertEqual(len(backups),1)
        b=sqlite3.connect(backups[0])
        try:
            self.assertEqual(b.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(b.execute('SELECT COUNT(*) FROM projects').fetchone()[0],4)
        finally:b.close()
        server.init();self.assertEqual(len(list(server.DBPATH.parent.glob('backups/*.sqlite3'))),1)
    def test_all_mobile_question_produces_editable_plan(self):
        p=server.create_planner({'brief':'Research all mobile apps for rising categories'})
        self.assertEqual(p['proposal']['profile']['subcategory'],'All Mobile Apps')
        self.assertEqual(p['proposal']['planner_source'],'rule_based')
        with server.con() as c:
            saved=hub.config(c,{'research_id':self.pid,'planner_id':p['id'],'scope':{'market':'All','timeframe':'Last 90 days'}})
            self.assertEqual(saved['research_id'],self.pid)
    def test_analysis_uses_filtered_dataset_and_public_evidence(self):
        self.evidence()
        with server.con() as c:
            a=studio.prepare(c,{'project_id':self.pid,'market':'All','mode':'hybrid','view':{'filters':{'platform':'iOS','geo':'US'},'top':'all'}})
            self.assertEqual(a['overview']['records_total'],1);self.assertEqual(a['overview']['public_count'],1)
            self.assertEqual(json.loads(a['packet'].split('\n',1)[1])['view']['filters']['geo'],'US')
    def test_public_only_without_csv_and_no_cross_market_leak(self):
        with server.con() as c:
            studio.save_public(c,self.pid,[{'name':'Utility','platform':'iOS','country':'US','store_id':'u','url':'https://example.com/u','category':'Utilities'},{'name':'Game','platform':'iOS','country':'US','store_id':'g','url':'https://example.com/g','category':'Games'}])
            a=studio.prepare(c,{'project_id':self.pid,'market':'Utilities','mode':'public'})
            self.assertEqual(a['overview']['public_count'],1)
            self.assertEqual(a['overview']['records_total'],0)
    def test_snapshot_immutable_and_deduplicated_after_source_deletion(self):
        a=self.analysis()
        with server.con() as c:
            rows,_=studio.merge_records(studio.records(c,self.pid));p={'research_id':self.pid,'analysis_id':a['id'],'evidence_ids':[rows[0]['evidence_id']],'view':{'mode':'hybrid','market':'All','filters':{'platform':'iOS'}}}
            r=hub.save_report(c,p);self.assertEqual(r,hub.save_report(c,p));snap=hub.get_report(c,r['report_id'])
            studio.delete_import(c,{'project_id':self.pid,'import_id':snap['snapshot']['dataset_ids'][0]})
            self.assertEqual(hub.get_report(c,r['report_id']),snap)
            self.assertEqual(len(snap['snapshot']['records']),1)
    def test_reject_cross_research_analysis_and_evidence(self):
        a=self.analysis()
        with server.con() as c:
            with self.assertRaisesRegex(ValueError,'không thuộc'):
                hub.save_report(c,{'research_id':1,'analysis_id':a['id']})
            with self.assertRaisesRegex(ValueError,'Evidence'):
                hub.save_report(c,{'research_id':self.pid,'evidence_ids':['CSV:invalid']})
    def test_studio_action_can_continue_to_investigation(self):
        a=self.analysis()
        with server.con() as c:
            action=studio.send_action_for_review(c,{'analysis_id':a['id'],'index':0})
            c.execute('INSERT INTO hub_action_links VALUES(?,?,?,?)',(action['id'],self.pid,a['id'],0))
        inv=server.start_investigation({'action_id':action['id'],'mode':'manual'})
        self.assertIn('https://apps.apple.com/app/idtest1',inv['packet'])
        self.assertIn('dataset_evidence',inv['packet'])
        result={'action_id':action['id'],'executive_summary':'TEST FIXTURE','findings':[{'claim':'Test listing','type':'fact','confidence':'low','evidence_urls':['https://apps.apple.com/app/idtest1']}],'next_steps':[],'missing_evidence':[],'limitations':['Test only'],'opportunity_drafts':[]}
        server.import_investigation_result(inv['id'],{'result':result})
    def test_csv_filter_handles_zero_null_and_percentage(self):
        rows=[{'id':'a','downloads':0,'growth_pop':None},{'id':'b','downloads':100,'growth_pop':.5}]
        self.assertEqual([r['id'] for r in hub.filter_rows(rows,{'filters':{'growth_popMin':40},'top':'all'})],['b'])
        self.assertEqual(len(hub.filter_rows(rows,{'filters':{'downloadsMin':0},'top':'all'})),2)

if __name__=='__main__':unittest.main()
