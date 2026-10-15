"""Explicit synthetic fixtures for browser acceptance; never a production data source."""
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w
s.DBPATH=s.ROOT/'tmp'/('workspace-e2e-'+str(time.time_ns())+'.sqlite3')
def discover(p):
    time.sleep(.2)
    topic='ASMR' if 'asmr' in p['term'].lower() else 'Utility'
    return {'results':[dict(store_id='fixture-'+topic,name=topic+' Test App',platform='iOS',country=p['country'],primary_genre='Games' if topic=='ASMR' else 'Utilities',description=topic+' game or utility tools',reviews=123,store_url='https://apps.apple.com/us/app/id123'),dict(store_id='unrelated',name='Sudoku',platform='iOS',country=p['country'],primary_genre='Games',description='Number puzzles',reviews=500)]}
s.discover=discover;s.android_search=lambda *a:(_ for _ in ()).throw(ValueError('TEST FIXTURE: connector unavailable'));s.research_news_context=lambda *a:([],[])
def ai(srv,rid,prompt,schema,web=False):
    if web:return dict(sources=[],coverage=[dict(source='web research TEST',status='no_results',note='TEST no extra sources')])
    if 'seeds' in schema['properties']:return dict(seeds=['ASMR game'],reason='Exact question topic')
    with s.LOCK,s.con() as c:r=w.get(c,rid)
    e=next(e for e in r['packet']['evidence'] if e['relevance']=='relevant');eid=e['evidence_id']
    return dict(trend=dict(status='insufficient_evidence',answer='TEST FIXTURE: Chưa đủ kỳ so sánh để khẳng định ASMR trending tại US.',confidence='low',evidence_ids=[eid],classification='insufficient_evidence'),scale_candidates=[dict(name=e['name'],app_id=e['store_id'],reason='Ứng viên cần xác minh; chưa chứng minh scale.',evidence_ids=[eid],signal_ids=[],unknowns='Thiếu lịch sử và ROAS.',classification='insufficient_evidence')],research_gaps=['Thiếu lịch sử so sánh.'],next_steps=[dict(title='TEST Verify ASMR',reason='Thu thập thêm kỳ dữ liệu.',evidence_ids=[eid])])
w.check_cli=lambda:dict(ok=True,message='TEST CLI');w.call_ai=ai
s.main()
