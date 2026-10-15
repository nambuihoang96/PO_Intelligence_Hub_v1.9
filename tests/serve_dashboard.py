"""Synthetic fixtures ONLY. This module is not imported by the production server."""
import json,sys,time,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w
import market_intelligence as mi
s.DBPATH=s.ROOT/'tmp'/('dashboard-e2e-'+str(time.time_ns())+'.sqlite3')
s.init()
scope=w.scope_for('ASMR games')
def save(name,scope,rows,status='ready',sources=None):
    pid=s.new_project(dict(name=name,brief='TEST FIXTURE — không phải dữ liệu thị trường thực. '+scope['topic']))['id']
    packet=mi.enrich(dict(evidence=rows,signals=[],warnings=[],coverage={},gaps=['TEST FIXTURE; hiệu quả UA chưa được đánh giá.'],sources=sources or []),scope)
    result=mi.decorate(dict(trend=dict(status='insufficient_evidence',answer='TEST FIXTURE: chỉ kết luận tăng trưởng trong tập CSV giả lập, không suy rộng thị trường.',confidence='low',classification='insufficient_evidence',evidence_ids=[]),scale_candidates=[],research_gaps=['Thiếu dữ liệu UA.'],next_steps=[dict(title='TEST Xác minh UA',reason='Cần dữ liệu cohort và mục tiêu UA.',evidence_ids=[rows[0]['evidence_id']] if rows else [])],data_at=s.now(),preliminary=False,question=name,scope=scope,signals=[]),packet,scope)
    with s.con() as c:
        c.execute('INSERT INTO workspace_runs(research_id,question,mode,status,scope_json,packet_json,result_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(pid,'TEST FIXTURE '+name,'manual',status,json.dumps(scope),json.dumps(packet),json.dumps(result),s.now(),s.now()))
        rid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
    return pid,rid
def row(id,name,current,delta,line=2):
    return dict(kind='csv',id=id,name=name,platform='iOS',geo='US',category='Games',relevance='relevant',relevance_reasons=['TEST topic verified'],period_start=scope['start'],period_end=scope['end'],downloads=current,delta_pop=delta,evidence_id='CSV:TEST:'+str(line),evidence_ids=['CSV:TEST:'+str(line)],sources={'pop':dict(import_id=1,line=line,filename='TEST_SYNTHETIC_ASMR.csv')},field_sources={})
rows=[row('fixture42','ASMR Game A · TEST',145000,45000),row('fixture43','ASMR Game B · TEST',72000,-8000,3)]
for i,value in zip((0,1,3,4),(1000,1200,900,1500)):
    day=str(dt.date.fromisoformat(scope['start'])+dt.timedelta(days=i))
    rows.append(dict(row('fixture44','ASMR Daily · TEST',value,None,i+4),period_start=day,period_end=day))
pid,rid=save('ASMR · TEST fixture',scope,rows,sources=[dict(source='Apple Store · TEST',status='ready',count=2),dict(source='Android · TEST',status='error',error='TEST missing connector')])
w.create_action(s,rid,dict(index=0))
utility=w.scope_for('Thị trường Utilities có đang trending không?');save('Utilities · TEST fixture',utility,[],sources=[dict(source='History · TEST',status='missing_history',note='TEST no comparable history')])
s.discover=lambda p:dict(results=[])
s.android_search=lambda *a:[]
s.research_news_context=lambda *a:([],[])
s.main()
