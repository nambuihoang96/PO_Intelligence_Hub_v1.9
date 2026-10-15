import sys, tempfile, unittest, json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class PlannerTests(unittest.TestCase):
  def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.dbp=patch.object(server,'DBPATH',Path(self.tmp.name)/'test.sqlite3')
    self.dbp.start();server.init()
  def tearDown(self):
    self.dbp.stop();self.tmp.cleanup()
  def test_rule_draft_from_natural_language_without_ai(self):
    r=server.create_planner({'brief':'Tôi muốn nghiên cứu AI Photo Editor tại Mỹ và Nhật, tập trung subscription','mode':'manual'})
    self.assertGreater(r['id'],0)
    self.assertEqual(r['proposal']['planner_source'],'rule_based')
    self.assertIn('JP',r['proposal']['profile']['geos'])
    self.assertIn('US',r['proposal']['profile']['geos'])
    self.assertIn('photo',r['proposal']['name'].lower())
    self.assertEqual(len(server.bootstrap()['projects']),3) # Draft does not create project.
  def test_import_planner_json_validated(self):
    draft=server.create_planner({'brief':'I want to research fitness workout apps for US market','mode':'manual'})
    good={**draft['proposal'],'planner_id':f'PL-{draft["id"]:04d}','name':'Fitness Intelligence','profile':{**draft['proposal']['profile'],'keywords_include':['workout trainer'],'competitor_filters':{'min_rating':4.4,'min_reviews':2500,'pricing':'free','genre':'Health'}}}
    bad={**good,'planner_id':'PL-0000'}
    with self.assertRaises(ValueError):server.import_planner(draft['id'],{'result':json.dumps(bad)})
    imported=server.import_planner(draft['id'],{'result':'```json\n'+json.dumps(good)+'\n```'})
    self.assertEqual(imported['proposal']['profile']['competitor_filters']['min_reviews'],2500)
    self.assertEqual(server.bootstrap()['planner_drafts'][0]['status'],'imported')
  def test_create_update_profile_and_sources(self):
    p={ 'name':'My IPTV Research', 'brief':'Compare IPTV players in Vietnam',
      'profile':{'category':'Entertainment','subcategory':'IPTV','geos':['VN','US'],'platforms':['iOS','Android'],
        'keywords_include':['iptv','tv player'],'keywords_exclude':['wallpaper'],
        'monetization':['Ads','Subscription'], 'competitor_filters':{'min_rating':4,'min_reviews':100,'pricing':'free'},
        'cadence_hours':48, 'research_goals':['competitors','pricing'], 'sources':['apple','trends']}}
    r=server.new_project(p)
    profile=r['profile'];self.assertEqual(profile['geos'],['VN','US'])
    self.assertEqual(profile['competitor_filters']['min_reviews'],100)
    feeds=[x for x in server.bootstrap()['sources'] if x['project_id']==r['id']]
    self.assertEqual(len(feeds),2)
    up=server.update_project(r['id'],{'name':'My IPTV Research Updated','brief':'new brief','profile':{**profile,'keywords_exclude':['tv box'],'cadence_hours':72}})
    self.assertEqual(up['profile']['cadence_hours'],72)
    proj=next(p for p in server.bootstrap()['projects'] if p['id']==r['id'])
    self.assertEqual(proj['name'],'My IPTV Research Updated')
    self.assertEqual(json.loads(proj['profile_json'])['keywords_exclude'],['tv box'])
  def test_guided_discovery_applies_filters(self):
    project=server.new_project({'name':'Demo Discovery','profile':{
      'geos':['US'],'platforms':['iOS'], 'keywords_include':['photo enhancer','photo editor'],
      'keywords_exclude':['wallpaper'], 'competitor_filters':{'min_rating':4.2,'min_reviews':150,'pricing':'free','genre':'Photo'},'sources':['apple'], 'discovery_depth':2}})
    def apple_results(url,timeout=11):
      return {'results':[
         {'kind':'software','trackId':100,'trackName':'Good Photo Editor','sellerName':'Maker','averageUserRating':4.8,'userRatingCount':250,'price':0,'primaryGenreName':'Photo & Video','genres':['Photo & Video']},
         {'kind':'software','trackId':101,'trackName':'Bad Wallpaper Editor','sellerName':'Maker','averageUserRating':4.9,'userRatingCount':300,'price':0,'primaryGenreName':'Photo & Video','genres':['Photo & Video']},
         {'kind':'software','trackId':102,'trackName':'Paid Photo Editor','sellerName':'Maker','averageUserRating':4.8,'userRatingCount':300,'price':6.99,'primaryGenreName':'Photo & Video','genres':['Photo & Video']},
         {'kind':'software','trackId':103,'trackName':'Low-Rated Photo','sellerName':'Maker','averageUserRating':3.9,'userRatingCount':100,'price':0,'primaryGenreName':'Photo & Video','genres':['Photo & Video']}
       ]}
    with patch.object(server,'request_json',side_effect=apple_results),patch.object(server.time,'sleep'):
      r=server.guided_discover({'project_id':project['id']})
    self.assertEqual(r['requests'],2)
    self.assertEqual(len(r['results']),1)
    self.assertEqual(r['results'][0]['name'],'Good Photo Editor')
    self.assertEqual(len(r['rejected']),3)
  def test_codex_gate_requires_confirmation(self):
    draft=server.create_planner({'brief':'Research apps for photo editor market','mode':'codex'})
    with self.assertRaises(ValueError):server.start_planner_codex(draft['id'],False)
    with self.assertRaises(ValueError):server.start_planner_codex(draft['id'],True) # disabled in settings
  def test_legacy_schema_upgrade(self):
    legacy=Path(self.tmp.name)/'legacy.sqlite3'
    import sqlite3
    c=sqlite3.connect(legacy)
    c.execute('CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, geo TEXT NOT NULL, keywords TEXT NOT NULL, created_at TEXT NOT NULL)')
    c.execute("INSERT INTO projects(name,category,geo,keywords,created_at) VALUES('Old project','IPTV','US','iptv','2026')")
    c.commit();c.close()
    with patch.object(server,'DBPATH',legacy):
      server.init()
      proj=server.bootstrap()['projects'][0]
      self.assertIn('profile_json',proj)
      self.assertEqual(server.get_project_profile(proj)['keywords_include'],['iptv'])
if __name__=='__main__':unittest.main()
