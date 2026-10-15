"""Local, evidence-aware PO decision records. No network calls and no model invocation."""
from __future__ import annotations
import datetime as dt
import json
import re
import urllib.parse

SUBTASK_STATES={'proposed','todo','in_progress','blocked','done','rejected'}
OPPORTUNITY_STATES={'proposed','investigating','validated','rejected'}
EXPERIMENT_STATES={'draft','approved','running','completed','cancelled'}
PRIORITIES={'low','medium','high'}
CONFIDENCES={'low','medium','high'}

def required(data,key,maxlen=250):
    value=data.get(key)
    if not isinstance(value,str) or not value.strip() or len(value.strip())>maxlen:
        raise ValueError(f'{key}: cần văn bản 1–{maxlen} ký tự')
    return value.strip()

def one_of(value,allowed,name):
    if value not in allowed:raise ValueError(f'{name} không hợp lệ: {value}')
    return value

def date_or_none(x):
    if not x:return None
    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x):raise ValueError('due_date phải YYYY-MM-DD')
    dt.date.fromisoformat(x)
    return x

def action_row(c,aid):
    a=c.execute('SELECT * FROM action_registry WHERE id=?',(aid,)).fetchone()
    if not a:raise ValueError('Action không tồn tại')
    return a

def create_subtask(p,con,lock,now,dumps):
    aid=int(p.get('action_id',0));title=required(p,'title')
    priority=one_of(p.get('priority','medium'),PRIORITIES,'priority')
    desc=str(p.get('description',''))[:2400]
    owner=str(p.get('owner',''))[:120]
    due=date_or_none(p.get('due_date'))
    with lock,con() as c:
        a=action_row(c,aid)
        if a['state'] in ('done','rejected'):raise ValueError('Action đã đóng')
        nowt=now()
        c.execute('INSERT INTO action_subtasks(action_id,title,description,priority,state,owner,due_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                  (aid,title,desc,priority,'proposed',owner,due,nowt,nowt))
        return dict(c.execute('SELECT * FROM action_subtasks WHERE id=last_insert_rowid()').fetchone())

def update_subtask(sid,p,con,lock,now):
    allowed={'state','title','description','priority','owner','due_date'}
    updates={k:v for k,v in p.items() if k in allowed}
    if not updates:raise ValueError('Không có thay đổi hợp lệ')
    with lock,con() as c:
        row=c.execute('SELECT * FROM action_subtasks WHERE id=?',(sid,)).fetchone()
        if not row or row['is_deleted']:raise ValueError('Subtask không tồn tại hoặc đã xóa')
        a=action_row(c,row['action_id'])
        if a['state']=='done' and updates.get('state') not in ('done','rejected'):
            raise ValueError('Hãy mở lại Action trước khi sửa task')
        for k,v in list(updates.items()):
            if k=='state':one_of(v,SUBTASK_STATES,k)
            elif k=='priority':one_of(v,PRIORITIES,k)
            elif k=='title':updates[k]=required(p,k)
            elif k=='description':
                if not isinstance(v,str) or len(v)>2400:raise ValueError('description không hợp lệ')
            elif k=='owner':
                if not isinstance(v,str) or len(v)>120:raise ValueError('owner không hợp lệ')
            elif k=='due_date':updates[k]=date_or_none(v)
        updates['updated_at']=now()
        columns=', '.join(k+'=?' for k in updates)
        c.execute('UPDATE action_subtasks SET '+columns+' WHERE id=?',list(updates.values())+[sid])
        return dict(c.execute('SELECT * FROM action_subtasks WHERE id=?',(sid,)).fetchone())

def draft_investigation_steps(iid,con,lock,now,dumps,safejson):
    with lock,con() as c:
        inv=c.execute('SELECT * FROM investigations WHERE id=?',(iid,)).fetchone()
        if not inv or inv['status']!='completed':raise ValueError('Investigation chưa hoàn thành')
        result=safejson(inv['result_json'],{})
        steps=result.get('next_steps',[])
        created=[]
        for idx,st in enumerate(steps[:15]):
            if not isinstance(st,dict) or not st.get('title'):continue
            title=str(st['title'])[:250]
            detail=str(st.get('validation_step',''))[:2400]
            priority=st.get('priority') if st.get('priority') in PRIORITIES else 'medium'
            t=now()
            c.execute('INSERT OR IGNORE INTO action_subtasks(action_id,investigation_id,source_index,title,description,priority,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                      (inv['action_id'],iid,idx,title,detail,priority,'proposed',t,t))
            row=c.execute('SELECT * FROM action_subtasks WHERE investigation_id=? AND source_index=?',(iid,idx)).fetchone()
            created.append(dict(row))
        return {'action_id':inv['action_id'],'draft_count':len(created),'drafts':created,'note':'Chưa phê duyệt. Các task có trạng thái proposed, PO cần duyệt từng task.'}

def create_opportunity(p,con,lock,now,dumps):
    aid=int(p.get('action_id',0))
    title=required(p,'title');problem=required(p,'user_problem',2000);hypothesis=required(p,'hypothesis',2000)
    confidence=one_of(p.get('confidence','low'),CONFIDENCES,'confidence')
    impact=one_of(p.get('impact','unknown'),{'unknown','low','medium','high'},'impact')
    with lock,con() as c:
        a=action_row(c,aid)
        ev=a['evidence_json'] or '[]';t=now()
        c.execute('INSERT INTO opportunities(project_id,action_id,title,user_problem,hypothesis,confidence,impact,evidence_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (a['project_id'],aid,title,problem,hypothesis,confidence,impact,ev,t,t))
        return dict(c.execute('SELECT * FROM opportunities WHERE id=last_insert_rowid()').fetchone())

def update_opportunity(oid,p,con,lock,now):
    editable={'state','title','user_problem','hypothesis','validation_step','impact','confidence'}
    values={k:v for k,v in p.items() if k in editable}
    if not values:raise ValueError('Không có dữ liệu thay đổi')
    for key in ('title','user_problem','hypothesis','validation_step'):
        if key in values:
            values[key]=required(p,key,250 if key=='title' else 2000) if key!='validation_step' or p[key] else ''
    if 'state' in values:one_of(values['state'],OPPORTUNITY_STATES,'state')
    if 'impact' in values:one_of(values['impact'],{'unknown','low','medium','high'},'impact')
    if 'confidence' in values:one_of(values['confidence'],CONFIDENCES,'confidence')
    with lock,con() as c:
        row=c.execute('SELECT * FROM opportunities WHERE id=?',(oid,)).fetchone()
        if not row:raise ValueError('Opportunity không tồn tại')
        st=values.get('state',row['state'])
        confidence=values.get('confidence',row['confidence'])
        if st=='validated' and (confidence=='low' or not any(e.get('status')=='po_verified' and e.get('type') in ('walkthrough','screenshot','review','test_result') for e in json.loads(row['evidence_json'] or '[]'))):
            raise ValueError('Cần bằng chứng in-app/review/test do PO xác minh và confidence medium/high')
        values['updated_at']=now()
        c.execute('UPDATE opportunities SET '+', '.join(k+'=?' for k in values)+' WHERE id=?',[*values.values(),oid])
        return dict(c.execute('SELECT * FROM opportunities WHERE id=?',(oid,)).fetchone())

def create_experiment(p,con,lock,now):
    oid=int(p.get('opportunity_id',0))
    values=[required(p,k,1600 if k!='title' else 250) for k in ('title','hypothesis','primary_metric','guardrails','success_criteria')]
    with lock,con() as c:
        opp=c.execute('SELECT * FROM opportunities WHERE id=?',(oid,)).fetchone()
        if not opp:raise ValueError('Opportunity không tồn tại')
        if opp['state']=='rejected':raise ValueError('Opportunity đã bị từ chối')
        t=now()
        c.execute('INSERT INTO experiments(project_id,opportunity_id,title,hypothesis,primary_metric,guardrails,success_criteria,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                  (opp['project_id'],oid,*values,t,t))
        return dict(c.execute('SELECT * FROM experiments WHERE id=last_insert_rowid()').fetchone())

def update_experiment(eid,p,con,lock,now):
    state=one_of(p.get('state'),EXPERIMENT_STATES,'state')
    notes=str(p.get('result_notes',''))[:3000]
    with lock,con() as c:
        row=c.execute('SELECT * FROM experiments WHERE id=?',(eid,)).fetchone()
        if not row:raise ValueError('Experiment không tồn tại')
        opp=c.execute('SELECT state FROM opportunities WHERE id=?',(row['opportunity_id'],)).fetchone()
        if state in ('running','completed') and opp['state']!='validated':
            raise ValueError('Phải xác minh Opportunity trước khi chạy Experiment')
        if state=='completed' and not notes and not row['result_notes']:
            raise ValueError('Cần ghi result_notes trước khi đóng Experiment')
        c.execute('UPDATE experiments SET state=?,result_notes=?,updated_at=? WHERE id=?',(state,notes or row['result_notes'],now(),eid))
        return dict(c.execute('SELECT * FROM experiments WHERE id=?',(eid,)).fetchone())

def add_opportunity_evidence(oid,p,con,lock,now,dumps):
    name=required(p,'name',160);url=required(p,'url',1000)
    kind=one_of(p.get('type'),{'walkthrough','screenshot','review','test_result'},'type')
    if p.get('po_confirmed') is not True:raise ValueError('Cần PO xác nhận đã kiểm tra evidence thực tế')
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Evidence cần HTTPS link hợp lệ, không chứa credentials')
    with lock,con() as c:
        o=c.execute('SELECT * FROM opportunities WHERE id=?',(oid,)).fetchone()
        if not o:raise ValueError('Opportunity không tồn tại')
        data=json.loads(o['evidence_json'] or '[]')
        if not any(e.get('url')==url and e.get('type')==kind for e in data):
            data.append({'name':name,'url':url,'type':kind,'status':'po_verified','verified_at':now()})
        c.execute('UPDATE opportunities SET evidence_json=?,updated_at=? WHERE id=?',(dumps(data),now(),oid))
        return dict(c.execute('SELECT * FROM opportunities WHERE id=?',(oid,)).fetchone())


def delete_subtask(sid,con,lock,now):
    """Soft delete keeps audit history while removing progress/UI impact."""
    with lock,con() as c:
        row=c.execute('SELECT * FROM action_subtasks WHERE id=?',(sid,)).fetchone()
        if not row or row['is_deleted']:raise ValueError('Subtask không tồn tại')
        action_row(c,row['action_id'])
        c.execute('UPDATE action_subtasks SET is_deleted=1, updated_at=? WHERE id=?',(now(),sid))
        return {'id':sid,'action_id':row['action_id'],'deleted':True}

def restore_subtask(sid,con,lock,now):
    with lock,con() as c:
        row=c.execute('SELECT * FROM action_subtasks WHERE id=?',(sid,)).fetchone()
        if not row or not row['is_deleted']:raise ValueError('Subtask không có trong thùng rác')
        a=action_row(c,row['action_id'])
        if a['state'] in ('done','rejected'):raise ValueError('Mở lại Action trước khi khôi phục')
        c.execute('UPDATE action_subtasks SET is_deleted=0,updated_at=? WHERE id=?',(now(),sid))
        return {'id':sid,'restored':True}

def draft_ai_opportunities(iid,con,lock,now,dumps,safejson):
    """Persist only genuine imported AI output, link evidence and provenance, never invent templates."""
    with lock,con() as c:
        inv=c.execute('SELECT * FROM investigations WHERE id=?',(iid,)).fetchone()
        if not inv or inv['status']!='completed':raise ValueError('Chưa có kết quả AI Investigation hoàn thành')
        result=safejson(inv['result_json'],{})
        ideas=result.get('opportunity_drafts',[])
        if not ideas:return {'draft_count':0,'drafts':[],'note':'AI không đề xuất Opportunity có đủ bằng chứng; không sinh template thay thế.'}
        action=action_row(c,inv['action_id'])
        source_evidence=safejson(action['evidence_json'],[])
        available={x.get('url'):x for x in source_evidence if isinstance(x,dict) and x.get('url')}
        if action['run_id']:
            reportrow=c.execute('SELECT report_json FROM research_runs WHERE id=?',(action['run_id'],)).fetchone()
            report=safejson(reportrow['report_json'],{}) if reportrow else {}
            for item in (report.get('top_competitors',[])+report.get('market_news',[])):
                url=item.get('url') if isinstance(item,dict) else None
                if url and url not in available:available[url]={'url':url,'name':item.get('name') or item.get('title') or 'Research source','status':'public_listing'}
        drafts=[]
        for idx,idea in enumerate(ideas[:8]):
            urls=idea.get('evidence_urls',[])
            if not urls or any(url not in available for url in urls):
                raise ValueError('Opportunity AI không có evidence nằm trong Action. Cần điều tra thêm, không tự tạo card.')
            evidence=[available[url] for url in dict.fromkeys(urls)]
            t=now()
            c.execute("""INSERT OR IGNORE INTO opportunities
                (project_id,action_id,title,user_problem,hypothesis,confidence,impact,evidence_json,investigation_id,source_index,validation_step,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (action['project_id'],action['id'],required(idea,'title'),required(idea,'user_problem',2000),
                 required(idea,'hypothesis',2000),one_of(idea['confidence'],CONFIDENCES,'confidence'),
                 one_of(idea['impact'],{'unknown','low','medium','high'},'impact'),dumps(evidence),iid,idx,
                 required(idea,'validation_step',2000),t,t))
            saved=c.execute('SELECT * FROM opportunities WHERE investigation_id=? AND source_index=?',(iid,idx)).fetchone()
            drafts.append(dict(saved))
        return {'action_id':action['id'],'draft_count':len(drafts),'drafts':drafts,'note':'AI suggestions; status proposed. PO must review and validate evidence.'}
