import json
import sqlite3
import unittest
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import studio

class StudioTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE projects(id INTEGER PRIMARY KEY,name TEXT,brief TEXT,category TEXT)')
        self.db.execute("INSERT INTO projects VALUES(1,'Utilities','Utilities trending and scaling','Utilities')")
        studio.init(self.db)

    def add_file(self,kind='pop',name='Top Apps (Sep 14, 2026 - Oct 13, 2026, Worldwide).csv',category='Games',id='one',downloads=1000,delta=300):
        fingerprint=('a' if kind=='pop' else 'b')*64
        imp=studio.start_import(self.db,{'project_id':1,'filename':name,'fingerprint':fingerprint,'kind':kind,'period':{'start':'2026-09-14','end':'2026-10-13','geo':'Worldwide'}})
        rec={'id':id,'name':'Example '+id,'publisher':'Example Publisher','category':category,'platform':'Unified','geo':'Worldwide','period_start':'2026-09-14','period_end':'2026-10-13','release':'2026-09-15','downloads':downloads,'delta_pop':delta if kind=='pop' else None,'growth_pop':.428 if kind=='pop' else None,'delta_yoy':400 if kind=='yoy' else None,'growth_yoy':.5 if kind=='yoy' else None,'revenue':None,'dau':None,'source':{'line':2}}
        studio.import_batch(self.db,{'import_id':imp['id'],'rows':[rec]})
        studio.finish_import(self.db,{'import_id':imp['id'],'expected':1})
        return imp

    def test_merge_and_provenance(self):
        self.add_file('pop');self.add_file('yoy')
        rows,w=studio.merge_records(studio.records(self.db,1))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['downloads'],1000)
        self.assertEqual(rows[0]['delta_pop'],300)
        self.assertEqual(rows[0]['growth_yoy'],.5)
        self.assertEqual(len(rows[0]['evidence_ids']),2)
        self.assertEqual(rows[0]['age'],28)
        self.assertFalse(w)

    def test_utilities_rejects_games_csv(self):
        self.add_file()
        rows,_=studio.merge_records(studio.records(self.db,1))
        o=studio.deterministic_overview(rows,[],'Utilities','Which utilities are trending?')
        self.assertEqual(o['records_market'],0)
        with self.assertRaisesRegex(ValueError,'Chưa có evidence phù hợp'):
            studio.prepare(self.db,{'project_id':1,'market':'Utilities','mode':'hybrid','question':'Which utilities are trending?'})

    def test_public_only_and_ai_evidence_validation(self):
        studio.save_public(self.db,1,[{'name':'Real Store App','platform':'iOS','country':'US','store_id':'12345','url':'https://apps.apple.com/app/id12345','rating':4.5,'reviews':10}])
        packet=studio.prepare(self.db,{'project_id':1,'market':'Utilities','mode':'public','question':'Which utilities are trending now?'})
        evidence=packet['overview']['public_candidates'][0]['evidence_id']
        obj={'executive_summary':'Store listing exists; cannot conclude trending or scaling.',
             'market_findings':[{'title':'Listing','observation':'Listing exists','interpretation':'Not growth','confidence':'low','evidence_ids':[evidence],'limitations':'No history'}],
             'subcategory_assessments':[],'rising_apps':[],'research_gaps':['No history'],'suggested_research_actions':[]}
        self.assertEqual(studio.import_ai(self.db,{'analysis_id':packet['id'],'result':json.dumps(obj)})['state'],'ready')
        obj['market_findings'][0]['evidence_ids']=['STORE:999999']
        with self.assertRaisesRegex(ValueError,'evidence'):
            studio.validate_result(packet['packet'],obj)

    def test_public_source_fields_preserved(self):
        studio.save_public(self.db,1,[{'name':'Scanner','platform':'iOS','country':'US','store_id':'42','store_url':'https://apps.apple.com/app/id42','primary_genre':'Productivity','release_date':'2026-10-01'}])
        item=studio.public_list(self.db,1)[0]
        self.assertEqual(item['url'],'https://apps.apple.com/app/id42')
        self.assertEqual(item['category'],'Productivity')
        self.assertEqual(item['release_date'],'2026-10-01')

    def test_action_requires_approval_and_validated_ai(self):
        self.db.executescript('''CREATE TABLE action_registry (
            id INTEGER PRIMARY KEY,project_id INTEGER,run_id INTEGER,insight_id INTEGER,source_type TEXT,source_index INTEGER,
            title TEXT,description TEXT,priority TEXT,state TEXT,evidence_json TEXT,notes TEXT,is_demo INTEGER,
            created_at TEXT,updated_at TEXT);''')
        studio.save_public(self.db,1,[{'name':'Scanner','platform':'iOS','country':'US','store_id':'42','store_url':'https://apps.apple.com/app/id42'}])
        a=studio.prepare(self.db,{'project_id':1,'market':'Utilities','mode':'public','question':'Which utility apps are scaling?'})
        with self.assertRaisesRegex(ValueError,'AI analysis'):
            studio.send_action_for_review(self.db,{'analysis_id':a['id'],'index':0})
        ev=a['overview']['public_candidates'][0]['evidence_id']
        result={'executive_summary':'Unknown','market_findings':[],'subcategory_assessments':[],'rising_apps':[],'research_gaps':[],
            'suggested_research_actions':[{'title':'Benchmark Scanner','reason':'Investigate listing','evidence_ids':[ev]}]}
        studio.import_ai(self.db,{'analysis_id':a['id'],'result':result})
        first=studio.send_action_for_review(self.db,{'analysis_id':a['id'],'index':0})
        self.assertFalse(first['existing'])
        self.assertEqual(first['id'],studio.send_action_for_review(self.db,{'analysis_id':a['id'],'index':0})['id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM action_registry').fetchone()[0],1)

    def test_dedupe_file_and_stale_ai(self):
        imp=self.add_file(category='Utilities')
        again=studio.start_import(self.db,{'project_id':1,'filename':'duplicate.csv','fingerprint':'a'*64,'kind':'pop','period':{}})
        self.assertTrue(again['existing']);self.assertEqual(imp['id'],again['id'])
        p=studio.prepare(self.db,{'project_id':1,'market':'Utilities','mode':'hybrid','question':'Which utilities are trending now?'})
        evidence=p['overview']['top_downloads'][0]['evidence_id']
        obj={'executive_summary':'No verified trends','market_findings':[{'title':'Observed downloads','observation':'1000 downloads estimated','interpretation':'Not enough','confidence':'low','evidence_ids':[evidence]}],'subcategory_assessments':[],'rising_apps':[],'research_gaps':[],'suggested_research_actions':[]}
        studio.import_ai(self.db,{'analysis_id':p['id'],'result':obj})
        studio.delete_import(self.db,{'project_id':1,'import_id':imp['id']})
        self.assertEqual(studio.latest_analysis(self.db,1)['state'],'stale')

if __name__=='__main__':unittest.main()
