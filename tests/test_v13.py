import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class V13WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.mock=patch.object(server,'DBPATH',Path(self.tmp.name)/'research.sqlite3');self.mock.start();server.init()
  self.rid=server.launch_initial_research({'project_id':3,'mode':'demo'})['id']
  for i in range(150):
   row=next(x for x in server.bootstrap()['research_runs'] if x['id']==self.rid)
   if row['status']!='running':break
   time.sleep(.02)
  self.assertEqual(row['status'],'ready',row['error'])
 def tearDown(self):self.mock.stop();self.tmp.cleanup()
 def test_report_action_creates_global_registry_and_is_idempotent(self):
  a=server.create_research_action({'run_id':self.rid,'source_type':'baseline_insight','index':0})
  b=server.create_research_action({'run_id':self.rid,'source_type':'baseline_insight','index':0})
  self.assertEqual(a['id'],b['id'])
  data=server.bootstrap()
  self.assertEqual(len(data['action_registry']),1)
  self.assertEqual(data['action_registry'][0]['run_id'],self.rid)
  self.assertTrue(data['action_registry'][0]['is_demo'])
  self.assertEqual(data['action_registry'][0]['evidence_json'],'[]')  # DEMO never invents external links
 def test_state_notes_and_end_to_end_deep_investigation(self):
  a=server.create_research_action({'run_id':self.rid,'source_type':'baseline_insight','index':0})
  updated=server.update_action_record(a['id'],{'state':'in_progress','notes':'Đã giao cho researcher'})
  self.assertEqual(updated['state'],'in_progress')
  inv=server.start_investigation({'action_id':a['id'],'mode':'manual'})
  self.assertIn('evidence',inv['packet'])
  self.assertEqual(server.bootstrap()['action_registry'][0]['state'],'investigating')
  self.assertEqual(json.loads(a['evidence_json']),[])
  url=None
  result={'action_id':a['id'],'executive_summary':'This is only simulated content.',
     'findings':[{'claim':'Store listing mentions capability','type':'hypothesis','confidence':'low','evidence_urls':[]}],
     'next_steps':[{'title':'Validate','priority':'high','validation_step':'Capture in-app walkthrough'}],
     'missing_evidence':['Gameplay screenshot'],'limitations':['Demo data']}
  self.assertTrue(server.import_investigation_result(inv['id'],{'result':result})['success'])
  self.assertEqual(server.bootstrap()['investigations'][0]['status'],'completed')
  result['findings'][0]['evidence_urls']=['https://evil.example/unsupported']
  with self.assertRaisesRegex(ValueError,'Evidence URL'):server.import_investigation_result(inv['id'],{'result':result})
  with self.assertRaises(ValueError):server.update_action_record(a['id'],{'state':'invalid'})
 def test_research_import_action_ai_opportunity(self):
  result={'run_id':f'MR-{self.rid:04d}','executive_summary':'Not a verified market trend',
          'market_insights':[{'finding':'May be interesting','evidence_urls':[],'confidence':'low','type':'hypothesis'}],
          'opportunities':[{'title':'Compare products','why':'Validate hypothesis','priority':'medium','validation_step':'Test in-app'}],
          'limitations':['Sample']}
  server.import_research_analysis(self.rid,{'result':result})
  a=server.create_research_action({'run_id':self.rid,'source_type':'ai_opportunity','index':0})
  self.assertEqual(a['title'],'Compare products')
  with self.assertRaises(ValueError):server.create_research_action({'run_id':self.rid,'source_type':'ai_opportunity','index':1})
 def test_source_discovery_approval_is_controlled_and_deduplicated(self):
  r=server.discover_sources_for_project(3)
  ids=[x['id'] for x in r['candidates']]
  self.assertIn('techcrunch_apps',ids)
  self.assertIn('meta_library',ids)
  ai=server.import_source_suggestion(3,{'result':{'recommended_ids':['techcrunch_apps'],'rationale':'Candidate','gaps':['Not monetization estimates']}})
  self.assertEqual(ai['recommended_ids'],['techcrunch_apps'])
  with self.assertRaises(ValueError):server.import_source_suggestion(3,{'result':{'recommended_ids':['unknown.example']}})
  approved=server.approve_source_suggestions(3,{'ids':['techcrunch_apps','meta_library']})
  self.assertIn('TechCrunch Apps',approved['added_rss'])
  self.assertTrue(any('Meta Ad Library' in x for x in approved['manual_or_existing']))
  server.approve_source_suggestions(3,{'ids':['techcrunch_apps']})
  feeds=[x for x in server.bootstrap()['sources'] if x['project_id']==3 and 'techcrunch' in x['url']]
  self.assertEqual(len(feeds),1)
  with self.assertRaises(ValueError):server.approve_source_suggestions(3,{'ids':['random_url']})
 def test_codex_gate_rejects_without_approval(self):
  a=server.create_research_action({'run_id':self.rid,'source_type':'baseline_insight','index':0})
  i=server.start_investigation({'action_id':a['id']})
  with self.assertRaises(ValueError):server.run_codex_investigation(i['id'],False)
  with self.assertRaises(ValueError):server.run_codex_investigation(i['id'],True)
 def test_google_play_keyword_counters_do_not_read_previous_platform(self):
  from research_engine import build_baseline
  app=[{'name':'Android A','platform':'Android','store_id':'com.a','country':'US',
      'store_url':'https://play.google.com/store/apps/details?id=com.a','description':'Photo editor','contains_ads':True,'offers_iap':False},
      {'name':'iOS B','platform':'iOS','store_id':'123','country':'US',
      'store_url':'https://apps.apple.com/app/id123','description':'Photo editor'}]
  report=build_baseline({'name':'X','category':'Photo','geo':'US'},app)
  self.assertEqual(report['monetization_metadata']['android_with_ad_flag'],1)
  self.assertEqual(report['monetization_metadata']['android_flag_observed'],1)

if __name__=='__main__':unittest.main()
