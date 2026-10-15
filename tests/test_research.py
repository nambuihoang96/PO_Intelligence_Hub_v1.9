import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
import research_engine

class MarketResearchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.dbp=patch.object(server,'DBPATH',Path(self.tmp.name)/'research.sqlite3')
  self.dbp.start();server.init()
 def tearDown(self):
  self.dbp.stop();self.tmp.cleanup()
 def await_run(self,rid):
  for _ in range(100):
   r=next(x for x in server.bootstrap()['research_runs'] if x['id']==rid)
   if r['status']!='running':return r
   time.sleep(.02)
  self.fail('Background research did not complete')
 def test_sample_generates_meaningful_report_without_apis(self):
  result=server.launch_initial_research({'project_id':3,'mode':'demo'})
  r=self.await_run(result['id'])
  self.assertEqual(r['status'],'ready',r['error'])
  report=json.loads(r['report_json'])
  self.assertEqual(report['coverage'],{'iOS':3,'Android':3})
  self.assertEqual(report['sample_count'],6)
  self.assertGreater(len(report['features']),0)
  self.assertGreater(len(report['insights']),1)
  self.assertEqual(len(report['recommendations']),0)  # rule engine must not invent generic action items
  self.assertTrue(all(x['is_demo'] for x in report['top_competitors']))
  self.assertIn('MR-',r['ai_packet'])
  with server.con() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM competitors WHERE project_id=3 AND is_demo=0').fetchone()[0],0)
 def test_live_cross_platform_initial_research_builds_watchlist_and_baseline(self):
  proj=server.new_project({'name':'Cross Platform AI Photo','profile':{'category':'Photo & Video','geos':['US'], 'platforms':['iOS','Android'],
     'keywords_include':['photo enhancer'],'sources':['apple','google_play'],'discovery_depth':1}})
  ios={'store_id':'98989898','name':'Photo Fix iOS','platform':'iOS','country':'US','store_url':'https://apps.apple.com/us/app/id98989898',
       'rating':4.5,'reviews':520,'description':'AI photo enhancer with templates and background remover','price':0,'source_type':'Apple iTunes Search API'}
  android={'store_id':'com.test.photo','name':'Photo Fix Android','platform':'Android','country':'US',
       'store_url':'https://play.google.com/store/apps/details?id=com.test.photo', 'rating':4.2,'reviews':1100, 'description':'Photo enhancer and portrait generator','price':0}
  found={'results':[ios,android],'rejected':[],'terms':['photo enhancer'],'geos':['US'],'errors':[]}
  with patch.object(server,'guided_discover',return_value=found),patch.object(server,'android_detail',return_value=android),patch.object(server.time,'sleep'):
   run=server.launch_initial_research({'project_id':proj['id'],'mode':'live'})
   r=self.await_run(run['id'])
  self.assertEqual(r['status'],'ready',r['error'])
  report=json.loads(r['report_json'])
  self.assertEqual(report['coverage'],{'iOS':1,'Android':1})
  self.assertTrue(any('Background removal'==x['feature'] for x in report['features']))
  with server.con() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM competitors WHERE project_id=?',(proj['id'],)).fetchone()[0],2)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0],2)
  self.assertTrue(all(x['url'].startswith('https://') for x in report['top_competitors']))
 def test_research_import_requires_existing_evidence_and_run_id(self):
  r=self.await_run(server.launch_initial_research({'project_id':3,'mode':'demo'})['id'])
  id=r['id']
  valid={'run_id':f'MR-{id:04d}','executive_summary':'Đây là báo cáo mẫu cần xác minh thêm trước khi áp dụng.',
    'market_insights':[{'finding':'Đây chỉ là demo','evidence_urls':[],'confidence':'low','type':'hypothesis'}],
    'opportunities':[{'title':'Tìm hiểu','why':'Thử nghiệm','priority':'low','validation_step':'Xem app'}], 'limitations':['SAMPLE']}
  self.assertTrue(server.import_research_analysis(id,{'result':valid})['success'])
  valid['run_id']='MR-9999'
  with self.assertRaises(ValueError):server.import_research_analysis(id,{'result':valid})
  valid['run_id']=f'MR-{id:04d}'
  valid['market_insights'][0]['evidence_urls']=['https://evil.example/unverified']
  with self.assertRaises(ValueError):server.import_research_analysis(id,{'result':valid})
 def test_android_optional_connector_not_silently_faked(self):
  with patch.object(server,'android_available',return_value=False):
   with self.assertRaisesRegex(ValueError,'connector'):server.android_search('photo','US')
  proj=server.new_project({'name':'Android-only Market','profile':{'category':'Game','geos':['US'], 'platforms':['Android'],
    'keywords_include':['casual game'],'sources':['google_play']}})
  with patch.object(server,'android_available',return_value=False),patch.object(server.time,'sleep'):
   r=server.guided_discover({'project_id':proj['id']})
  self.assertEqual(r['results'],[])
  self.assertTrue(r['errors'])
  self.assertIn('connector',r['errors'][0])
 def test_research_engine_does_not_make_up_monetization(self):
  app={'name':'Free Photo Tool','store_id':'123','platform':'iOS','country':'US','store_url':'https://apps.apple.com/app/id123',
   'description':'Photo enhancer with background remover','price':0,'rating':4.3,'reviews':500}
  report=research_engine.build_baseline({'name':'P','category':'Photo','geo':'US'},[app])
  self.assertEqual(report['coverage']['Android'],0)
  self.assertTrue(any('Ads/IAP/Subscription' in x for x in report['limitations']))
  self.assertFalse(any('subscription' in t.lower() for t in report['top_competitors'][0]['tags']))

if __name__=='__main__':unittest.main()
