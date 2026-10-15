"""No-internet API smoke tests for a fresh local installation."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

class LocalHttpTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.mock=patch.object(server,'DBPATH',Path(self.dir.name)/'http.sqlite3')
        self.mock.start()
        server.init()
        self.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.mock.stop()
        self.dir.cleanup()

    def request(self,path,method='GET',payload=None,headers=None):
        hd={'Content-Type':'application/json', **(headers or {})}
        body=json.dumps(payload).encode() if payload is not None else None
        with urlopen(Request(self.url+path, data=body, headers=hd,method=method),timeout=8) as r:
            return json.load(r)

    def test_end_to_end_json(self):
        before=self.request('/api/bootstrap')
        self.assertEqual(len(before['projects']),3)
        scan=self.request('/api/scan','POST',{'mode':'demo','project_id':1})
        self.assertEqual(scan['new_signals'],1)
        latest=self.request('/api/bootstrap')['tasks'][0]
        sample=self.request(f'/api/task/{latest["id"]}/sample')
        self.assertTrue(self.request(f'/api/task/{latest["id"]}/result','POST',{'result':sample})['success'])
        insight=self.request('/api/bootstrap')['insights'][0]
        self.assertTrue(self.request(f'/api/insight/{insight["id"]}/state','POST',{'state':'investigating'})['success'])
        self.assertEqual(self.request('/api/bootstrap')['insights'][0]['state'],'investigating')

    def test_research_planner_api_and_project_filters(self):
        p=self.request('/api/planner','POST',{'brief':'Research AI Photo Editor in US and Japan for subscription analysis','mode':'manual'})
        self.assertIn('profile',p['proposal'])
        draft_id=p['id']
        self.assertEqual(len(self.request('/api/bootstrap')['projects']),3)
        proposal={**p['proposal'],'planner_id':f'PL-{draft_id:04d}'}
        imported=self.request(f'/api/planner/{draft_id}/import','POST',{'result':proposal})
        profile=imported['proposal']['profile']
        profile['competitor_filters']={'min_rating':4.6,'min_reviews':500,'pricing':'free','genre':'Photo'}
        created=self.request('/api/projects','POST',{'name':'AI Photo Research US/JP','brief':proposal['brief'],'profile':profile})
        self.assertEqual(created['profile']['competitor_filters']['min_reviews'],500)
        revised=self.request(f'/api/projects/{created["id"]}/update','POST',{'name':'AI Photo Research Updated','profile':{**profile,'keywords_exclude':['wallpaper']}})
        self.assertEqual(revised['profile']['keywords_exclude'],['wallpaper'])
        with urlopen(self.url+'/wizard.js',timeout=8) as r:
            self.assertIn(b'function wizardView',r.read())

    def test_initial_research_endpoints(self):
        import time
        with urlopen(self.url+'/reports.js',timeout=8) as r:
            self.assertIn(b'function reports()',r.read())
        initial=self.request('/api/research/start','POST',{'project_id':3,'mode':'demo'})
        self.assertEqual(initial['status'],'running')
        for _ in range(50):
            row=next(x for x in self.request('/api/bootstrap')['research_runs'] if x['id']==initial['id'])
            if row['status']=='ready':break
            time.sleep(.02)
        self.assertEqual(row['status'],'ready',row['error'])
        report=json.loads(row['report_json'])
        self.assertEqual(report['coverage'],{'iOS':3,'Android':3})
        expected={'run_id':f'MR-{initial["id"]:04d}', 'executive_summary':'Demo sample for PO to review; no external evidence has been collected.',
          'market_insights':[{'finding':'Only a demo test','evidence_urls':[],'confidence':'low','type':'hypothesis'}],
          'opportunities':[],'limitations':['demo']}
        done=self.request(f'/api/research/{initial["id"]}/import','POST',{'result':expected})
        self.assertTrue(done['success'])
        stored=next(x for x in self.request('/api/bootstrap')['research_runs'] if x['id']==initial['id'])
        self.assertEqual(json.loads(stored['ai_result'])['run_id'],expected['run_id'])

    def test_v13_market_action_deep_investigation_and_source_approval(self):
        import time
        with urlopen(self.url+'/market.js',timeout=8) as r:
            self.assertIn(b'function market()',r.read())
        run=self.request('/api/research/start','POST',{'project_id':3,'mode':'demo'})
        for _ in range(100):
            row=next(x for x in self.request('/api/bootstrap')['research_runs'] if x['id']==run['id'])
            if row['status']!='running':break
            time.sleep(.02)
        self.assertEqual(row['status'],'ready',row['error'])
        action=self.request('/api/actions/create','POST',{'run_id':run['id'],'source_type':'baseline_insight','index':0})
        self.assertEqual(action['project_id'],3)
        updated=self.request(f'/api/actions/{action["id"]}/update','POST',{'state':'approved','notes':'PO approved investigate'})
        self.assertEqual(updated['state'],'approved')
        inv=self.request('/api/investigations/start','POST',{'action_id':action['id'],'mode':'manual'})
        self.assertIn('action_id',inv)
        result={'action_id':action['id'],'executive_summary':'Demo verification is not market evidence',
                'findings':[{'claim':'Need to validate game UX','type':'hypothesis','confidence':'low','evidence_urls':[]}],
                'next_steps':[{'title':'Test','priority':'medium','validation_step':'In-app walkthrough'}],
                'missing_evidence':['Game recordings'],'limitations':['Demo']}
        self.assertTrue(self.request(f'/api/investigations/{inv["id"]}/import','POST',{'result':result})['success'])
        candidates=self.request('/api/source-discovery/3')
        self.assertTrue(any(s['id']=='techcrunch_apps' for s in candidates['candidates']))
        analyzed=self.request('/api/source-discovery/3/import','POST',{'result':{'recommended_ids':['techcrunch_apps']}})
        self.assertEqual(analyzed['recommended_ids'],['techcrunch_apps'])
        approved=self.request('/api/source-discovery/3/approve','POST',{'ids':['techcrunch_apps','meta_library']})
        self.assertEqual(len(approved['added_rss']),1)
        d=self.request('/api/bootstrap')
        self.assertEqual(d['action_registry'][0]['state'],'investigating')
        self.assertEqual(d['investigations'][0]['status'],'completed')
        self.assertEqual(len([x for x in d['source_registry'] if x['project_id']==3]),2)

    def test_cross_site_blocked(self):
        with self.assertRaises(HTTPError) as e:
            self.request('/api/settings','POST',{'auto_scan':True},{'Origin':'https://untrusted.example'})
        self.assertEqual(e.exception.code,403)
        self.assertFalse(self.request('/api/bootstrap')['settings']['auto_scan'])

    def test_bad_content_type_blocked(self):
        with self.assertRaises(HTTPError) as e:
            self.request('/api/settings','POST',{'auto_scan':True},{'Content-Type':'text/plain'})
        self.assertEqual(e.exception.code,415)

if __name__=='__main__': unittest.main()
