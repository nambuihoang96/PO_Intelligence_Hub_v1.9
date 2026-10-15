"""v1.7 integrated research studio: user-owned imported evidence and public store snapshots.
No embedded market data, fabricated downloads or model-generated conclusions.
"""
import datetime as dt
import json
import re
import hashlib
from collections import Counter, defaultdict

FIELDS = ('downloads','delta_pop','growth_pop','delta_yoy','growth_yoy','revenue','dau','ua_spend','ua_cpi','retention_percent','roas_percent','roas_target_percent')

def init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS studio_imports (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), filename TEXT NOT NULL,
      fingerprint TEXT NOT NULL, kind TEXT NOT NULL, period_start TEXT NOT NULL DEFAULT '',
      period_end TEXT NOT NULL DEFAULT '', geo TEXT NOT NULL DEFAULT 'Unknown',
      state TEXT NOT NULL DEFAULT 'uploading', row_count INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL, UNIQUE(project_id,fingerprint)
    );
    CREATE TABLE IF NOT EXISTS studio_rows (
      id INTEGER PRIMARY KEY, import_id INTEGER NOT NULL REFERENCES studio_imports(id) ON DELETE CASCADE,
      line INTEGER NOT NULL, unified_id TEXT NOT NULL, payload TEXT NOT NULL,
      UNIQUE(import_id,line)
    );
    CREATE INDEX IF NOT EXISTS idx_studio_rows_import ON studio_rows(import_id);
    CREATE TABLE IF NOT EXISTS studio_public (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
      source TEXT NOT NULL, platform TEXT NOT NULL, geo TEXT NOT NULL,
      store_id TEXT NOT NULL, url TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL,
      collected_at TEXT NOT NULL, UNIQUE(project_id,platform,geo,store_id)
    );
    CREATE TABLE IF NOT EXISTS studio_news (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
      title TEXT NOT NULL, source TEXT NOT NULL, url TEXT NOT NULL,
      published TEXT NOT NULL DEFAULT '', collected_at TEXT NOT NULL,
      UNIQUE(project_id,url)
    );
    CREATE TABLE IF NOT EXISTS studio_public_history (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
      platform TEXT NOT NULL, geo TEXT NOT NULL, store_id TEXT NOT NULL,
      reviews REAL, rating REAL, payload TEXT, collected_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_studio_history ON studio_public_history(project_id,platform,geo,store_id,collected_at);
    CREATE TABLE IF NOT EXISTS studio_collections (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
      status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', error TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS studio_analyses (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
      question TEXT NOT NULL, mode TEXT NOT NULL, packet TEXT NOT NULL,
      result_json TEXT, state TEXT NOT NULL DEFAULT 'awaiting_ai',
      error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    ''')
    if 'payload' not in {r[1] for r in c.execute('PRAGMA table_info(studio_public_history)')}:
        c.execute('ALTER TABLE studio_public_history ADD COLUMN payload TEXT')

def _now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def _json(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def _project(c,pid):
    p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
    if not p:raise ValueError('Research Project không tồn tại')
    return dict(p)
def _num(v):
    if v is None or v=='':return None
    try:
        n=float(v)
        if not (-1e15<n<1e15):return None
        return n
    except (ValueError,TypeError):return None

def start_import(c,p):
    pid=int(p.get('project_id',0));_project(c,pid)
    name=str(p.get('filename','')).strip()[:240]
    digest=str(p.get('fingerprint','')).lower()
    if not name or not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('File name hoặc SHA-256 không hợp lệ')
    kind=str(p.get('kind',''))
    if kind not in ('pop','yoy'):raise ValueError('Chưa hỗ trợ loại CSV này')
    period=p.get('period') or {}
    row=c.execute('SELECT * FROM studio_imports WHERE project_id=? AND fingerprint=?',(pid,digest)).fetchone()
    if row:
        return {'id':row['id'],'existing':row['state']=='complete','state':row['state'],'rows':row['row_count']}
    c.execute('INSERT INTO studio_imports(project_id,filename,fingerprint,kind,period_start,period_end,geo,created_at) VALUES(?,?,?,?,?,?,?,?)',
      (pid,name,digest,kind,str(period.get('start',''))[:10],str(period.get('end',''))[:10],str(period.get('geo','Unknown'))[:70],_now()))
    return {'id':c.execute('SELECT last_insert_rowid()').fetchone()[0],'existing':False,'state':'uploading','rows':0}

def import_batch(c,p):
    fid=int(p.get('import_id',0));meta=c.execute('SELECT * FROM studio_imports WHERE id=?',(fid,)).fetchone()
    if not meta or meta['state']!='uploading':raise ValueError('Import không ở trạng thái uploading')
    rows=p.get('rows')
    if not isinstance(rows,list) or len(rows)>150:raise ValueError('Batch tối đa 150 dòng')
    existing=c.execute('SELECT COUNT(*) FROM studio_rows WHERE import_id=?',(fid,)).fetchone()[0]
    if existing+len(rows)>30000:raise ValueError('Tối đa 30.000 dòng/file')
    saved=0
    for r in rows:
        if not isinstance(r,dict):continue
        rid=str(r.get('id','')).strip()[:140];line=int((r.get('source') or {}).get('line',0))
        if not rid or line<2:continue
        clean={k:r.get(k) for k in ('id','name','publisher','category','publisher_country','platform','geo','period_start','period_end','release','store_id','currency','cohort_window','cohort_start','cohort_end','measurement_date')}
        for k in FIELDS:clean[k]=_num(r.get(k))
        clean['currency']=str(r.get('currency') or 'Unknown')[:10]
        clean['source']={'filename':meta['filename'],'line':line,'kind':meta['kind'],'import_id':fid}
        c.execute('INSERT OR IGNORE INTO studio_rows(import_id,line,unified_id,payload) VALUES(?,?,?,?)',(fid,line,rid,_json(clean)))
        saved+=1
    return {'accepted':saved}

def finish_import(c,p):
    fid=int(p.get('import_id',0));row=c.execute('SELECT * FROM studio_imports WHERE id=?',(fid,)).fetchone()
    if not row:raise ValueError('Import không tồn tại')
    n=c.execute('SELECT COUNT(*) FROM studio_rows WHERE import_id=?',(fid,)).fetchone()[0]
    expected=int(p.get('expected',n))
    if n!=expected:raise ValueError(f'Import thiếu dữ liệu: nhận {n}/{expected} dòng. Hãy thử lại.')
    c.execute("UPDATE studio_imports SET state='complete',row_count=? WHERE id=?",(n,fid))
    c.execute("UPDATE studio_analyses SET state='stale',updated_at=? WHERE project_id=? AND state='ready'",(_now(),row['project_id']))
    return {'id':fid,'rows':n,'state':'complete'}

def delete_import(c,p):
    pid=int(p.get('project_id',0));fid=int(p.get('import_id',0));_project(c,pid)
    c.execute('DELETE FROM studio_rows WHERE import_id=? AND import_id IN (SELECT id FROM studio_imports WHERE project_id=?)',(fid,pid))
    c.execute('DELETE FROM studio_imports WHERE id=? AND project_id=?',(fid,pid))
    c.execute("UPDATE studio_analyses SET state='stale',updated_at=? WHERE project_id=? AND state='ready'",(_now(),pid))
    return {'success':True}

def list_imports(c,pid):
    _project(c,pid)
    return [dict(r) for r in c.execute('SELECT * FROM studio_imports WHERE project_id=? ORDER BY id DESC',(pid,))]

def records(c,pid):
    _project(c,pid)
    result=[]
    for row in c.execute("SELECT r.payload FROM studio_rows r JOIN studio_imports i ON i.id=r.import_id WHERE i.project_id=? AND i.state='complete' ORDER BY i.id,r.line",(pid,)):
        result.append(json.loads(row['payload']))
    return result

def merge_records(raw):
    merged={}; warnings=[]
    for r in raw:
        r={**{field:None for field in FIELDS},**r}
        key=(r['id'],r['platform'],r['geo'],r['period_start'],r['period_end'])
        if key not in merged:
            x=dict(r);x['sources']={};x['field_sources']={}
            for field in FIELDS:
                if x[field] is not None:x['field_sources'][field]=r['source']
            merged[key]=x
        else:
            x=merged[key]
            if x['downloads'] is not None and r['downloads'] is not None and abs(x['downloads']-r['downloads'])>1:
                warnings.append('Downloads không khớp: '+r['id'])
            for field in FIELDS:
                if r[field] is not None and (x[field] is None or field.startswith(('growth_','delta_'))):
                    x[field]=r[field];x['field_sources'][field]=r['source']
        x['sources'][r['source']['kind']]=r['source']
    result=list(merged.values())
    for x in result:
        try:
            x['age']=(dt.date.fromisoformat(x['period_end'])-dt.date.fromisoformat(x['release'])).days
            if x['age']<0:x['age']=None
        except (ValueError,TypeError):x['age']=None
        x['evidence_ids']=['CSV:'+str(src['import_id'])+':'+str(src['line']) for src in x['sources'].values()]
        x['evidence_id']=x['evidence_ids'][0]
    return result,warnings[:30]

def public_list(c,pid):
    _project(c,pid)
    sql='''SELECT p.*, (SELECT h.id FROM studio_public_history h WHERE h.project_id=p.project_id
      AND h.platform=p.platform AND h.geo=p.geo AND h.store_id=p.store_id ORDER BY h.id DESC LIMIT 1) AS history_id
      FROM studio_public p WHERE p.project_id=? ORDER BY p.id DESC'''
    return [dict(id=r['id'],**json.loads(r['payload']),evidence_id='STOREH:'+str(r['history_id']) if r['history_id'] else 'STORE:'+str(r['id']),collected_at=r['collected_at']) for r in c.execute(sql,(pid,))]

def save_public(c,pid,items):
    _project(c,pid)
    for a in items:
        platform=str(a.get('platform',''))[:20];geo=str(a.get('country',''))[:10];store_id=str(a.get('store_id',''))[:160]
        if not platform or not geo or not store_id:continue
        url=str(a.get('url') or a.get('store_url') or '')[:800]
        clean={k:a.get(k) for k in ('name','platform','country','store_id','rating','reviews','description','release_date','released','installs','developer','publisher','price','genres','relevance_score')}
        clean['url']=url
        clean['category']=a.get('category') or a.get('primary_genre') or ''
        clean['release_date']=a.get('release_date') or a.get('releaseDate') or a.get('released')
        clean['installs']=a.get('installs') or a.get('installs_label')
        clean['source']='Apple Search/Lookup' if platform=='iOS' else 'Google Play public listing'
        c.execute('''INSERT INTO studio_public(project_id,source,platform,geo,store_id,url,payload,collected_at)
          VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(project_id,platform,geo,store_id)
          DO UPDATE SET payload=excluded.payload,url=excluded.url,collected_at=excluded.collected_at''',
          (pid,clean['source'],platform,geo,store_id,url,_json(clean),_now()))
        c.execute('INSERT INTO studio_public_history(project_id,platform,geo,store_id,reviews,rating,payload,collected_at) VALUES(?,?,?,?,?,?,?,?)',
          (pid,platform,geo,store_id,_num(clean.get('reviews')),_num(clean.get('rating')),_json(clean),_now()))
    c.execute("UPDATE studio_analyses SET state='stale',updated_at=? WHERE project_id=? AND state='ready'",(_now(),pid))

def save_news(c,pid,items):
    _project(c,pid)
    for a in items:
        url=str(a.get('url',''))[:800]
        if not url.startswith('https://'):continue
        c.execute('''INSERT OR IGNORE INTO studio_news(project_id,title,source,url,published,collected_at)
          VALUES(?,?,?,?,?,?)''',
          (pid,str(a.get('title',''))[:250],str(a.get('source',''))[:150],url,str(a.get('published',''))[:100],_now()))
    c.execute("UPDATE studio_analyses SET state='stale',updated_at=? WHERE project_id=? AND state='ready'",(_now(),pid))

def public_news(c,pid):
    _project(c,pid)
    return [dict(r,evidence_id='NEWS:'+str(r['id'])) for r in c.execute('SELECT * FROM studio_news WHERE project_id=? ORDER BY id DESC LIMIT 60',(pid,))]

def public_momentum(c,pid):
    _project(c,pid)
    rows=c.execute('''SELECT h.*,p.url,p.payload FROM studio_public_history h
      LEFT JOIN studio_public p ON p.project_id=h.project_id AND p.platform=h.platform AND p.geo=h.geo AND p.store_id=h.store_id
      WHERE h.project_id=? ORDER BY h.platform,h.geo,h.store_id,h.collected_at''',(pid,)).fetchall()
    groups=defaultdict(list)
    for r in rows:groups[(r['platform'],r['geo'],r['store_id'])].append(r)
    result=[]
    for (platform,geo,sid),entries in groups.items():
        # At least two separate dates are needed for a meaningful time delta.
        usable=[r for r in entries if r['reviews'] is not None]
        if len(usable)<2:continue
        first,last=usable[0],usable[-1]
        try:days=(dt.datetime.fromisoformat(last['collected_at'])-dt.datetime.fromisoformat(first['collected_at'])).total_seconds()/86400
        except ValueError:continue
        if days<0.5:continue
        item=json.loads(last['payload']) if last['payload'] else {}
        result.append({'name':item.get('name'), 'platform':platform,'geo':geo,'store_id':sid,'url':last['url'],
          'review_delta':last['reviews']-first['reviews'],'days':round(days,2),
          'start_reviews':first['reviews'],'end_reviews':last['reviews'],
          'evidence_ids':['STOREH:'+str(first['id']),'STOREH:'+str(last['id'])]})
    return sorted(result,key=lambda x:x['review_delta'],reverse=True)[:40]

def create_collection(c,pid):
    _project(c,pid)
    c.execute("INSERT INTO studio_collections(project_id,status,created_at,updated_at) VALUES(?,'running',?,?)",(pid,_now(),_now()))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]

def update_collection(c,collection_id,status,meta=None,error=''):
    c.execute('UPDATE studio_collections SET status=?,metadata_json=?,error=?,updated_at=? WHERE id=?',
       (status,_json(meta or {}),str(error)[:2000],_now(),collection_id))

def latest_collection(c,pid):
    r=c.execute('SELECT * FROM studio_collections WHERE project_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    if not r:return None
    d=dict(r);d['metadata']=json.loads(d.pop('metadata_json'));return d

def _market_match(row,category):
    """Conservative broad market filter. Never call this a verified subgenre classifier."""
    cat=str(row.get('category') or '').lower()
    if category=='All':return True
    if category=='Games':return 'game' in cat
    if category=='Utilities':return any(s in cat for s in ('utilit','tools','productivity'))
    return category.lower() in cat

def deterministic_overview(rows,public,market,question,news=None,momentum=None):
    matched=[r for r in rows if _market_match(r,market)]
    scopes=Counter((r.get('platform'),r.get('geo'),r.get('period_start'),r.get('period_end')) for r in matched)
    categories=Counter(str(r.get('category') or 'Unknown') for r in matched)
    candidates=[r for r in matched if r.get('downloads') is not None]
    by_download=sorted(candidates,key=lambda x:x['downloads'],reverse=True)[:35]
    by_delta=sorted([r for r in matched if r.get('delta_pop') is not None],key=lambda x:x['delta_pop'],reverse=True)[:35]
    new=sorted([r for r in matched if r.get('age') is not None and r['age']<=90 and r.get('downloads') is not None],key=lambda x:x['downloads'],reverse=True)[:35]
    # Each item carries evidence reference; no AI interpretation generated here.
    def card(r):
        return {k:r.get(k) for k in ('id','name','category','platform','geo','period_start','period_end','release','age','downloads','delta_pop','growth_pop','growth_yoy','evidence_id','evidence_ids','sources','field_sources')}
    pub=[a for a in public if market=='All' or market=='Games' and ('game' in str(a.get('category','')).lower()) or market=='Utilities' and (not a.get('category') or any(t in str(a.get('category','')).lower() for t in ('utilit','tools','productivity'))) or market.lower() in str(a.get('category','')).lower()]
    return {'market':market,'question':question,'records_total':len(rows),'records_market':len(matched),'public_count':len(pub),
      'scopes':[{'platform':k[0],'geo':k[1],'start':k[2],'end':k[3],'count':v} for k,v in scopes.most_common(20)],
      'categories':[{'category':k,'count':v} for k,v in categories.most_common(30)],
      'top_downloads':[card(r) for r in by_download], 'top_delta':[card(r) for r in by_delta],
      'new_releases':[card(r) for r in new],
      'public_candidates':[{k:a.get(k) for k in ('evidence_id','name','platform','country','store_id','url','rating','reviews','release_date','released','category','description','source','collected_at')} for a in pub[:70]],
      'public_news':(news or [])[:40], 'public_momentum':(momentum or [])[:40],
      'limitations':[
        'Sensor Tower downloads/revenue are estimates, not publisher actuals.',
        'CSV categories are broad store categories, not verified mechanic/subgenre taxonomy.',
        'Unified Worldwide cannot be split into iOS/Android or country downloads.',
        'A single 30-day export is not a daily timeline; PoP/YoY are comparisons, not daily observations.',
        'Public listing search is discovery, not a statistically representative market sample.',
        'Growth/scale in downloads does not prove profitable UA, retention, CPI, ROAS or ad revenue.',
        'No evidence for a market is a coverage gap, not proof of no growth.'
      ]}

def prepare(c,p):
    pid=int(p.get('project_id',0));proj=_project(c,pid)
    question=str(p.get('question') or proj.get('brief') or '').strip()[:1500]
    if len(question)<10:raise ValueError('Nhập câu hỏi nghiên cứu ít nhất 10 ký tự')
    market=str(p.get('market') or proj.get('category') or 'All')[:60]
    mode=str(p.get('mode','public'))
    if mode not in ('public','hybrid'):raise ValueError('Research mode không hợp lệ')
    rows,_=merge_records(records(c,pid)) if mode=='hybrid' else ([],[])
    if p.get('view'):
        from hub_workflows import filter_rows
        rows=filter_rows(rows,p['view'])
    public=public_list(c,pid)
    overview=deterministic_overview(rows,public,market,question,public_news(c,pid),public_momentum(c,pid))
    refs=set()
    for key in ('top_downloads','top_delta','new_releases','public_candidates','public_news','public_momentum'):
        refs.update(ev for r in overview[key] for ev in r.get('evidence_ids',[r.get('evidence_id')]) if ev)
    if not refs:
        raise ValueError('Chưa có evidence phù hợp. Hãy chạy Public Discovery hoặc import CSV đúng thị trường trước.')
    # Avoid accidentally sending full user dataset to AI; only scoped, selected evidence packet.
    instruction={
      'role':'Bạn là Market Research Analyst cho Product Owner. Viết tiếng Việt.',
      'task':'Trả lời research question theo toàn thị trường, subcategory, new/rising apps và scale hypothesis.',
      'rules':[
        'Chỉ dựa trên evidence trong packet, không bịa app, metrics, trend hay URL.',
        'Mọi factual finding/insight phải dẫn evidence_ids thuộc allowed_evidence_ids.',
        'Tách observed facts, inference/hypothesis, unknowns; không kết luận UA profitability nếu thiếu spend/ROAS.',
        'Không kết luận subgenre đang trending nếu chưa xác minh taxonomy, sample coverage và lịch sử.',
        'Nếu nguồn public và CSV không match được app, không tự tuyên bố đã đối chiếu 2 nguồn.',
        'Tuyệt đối không gán số Unified WW cho iOS, Android hoặc GEO cụ thể.',
        'Nêu rõ số liệu thiếu và đề xuất research actions (không tự tạo Product Experiment).',
        'Không coi ứng viên search listing là bằng chứng app đang scale.'
      ],
      'required_json':{'executive_summary':'string','market_findings':[{'title':'string','observation':'string','interpretation':'string','confidence':'low|medium|high','evidence_ids':['CSV:... or STORE:...'],'limitations':'string'}],
          'subcategory_assessments':[{'subcategory':'string','assessment':'string','confidence':'low|medium|high','evidence_ids':['...']}],
          'rising_apps':[{'name':'string','assessment':'string','evidence_ids':['...']}],
          'research_gaps':['string'], 'suggested_research_actions':[{'title':'string','reason':'string','evidence_ids':['...']}]}
    }
    packet='PO INTELLIGENCE HUB — RESEARCH PACKET (NOT A MARKET REPORT)\n'+_json({'instructions':instruction,'project_id':pid,'project_name':proj['name'],'question':question,'mode':mode,'view':p.get('view') or {},'evidence':overview,'allowed_evidence_ids':sorted(refs)})
    c.execute('INSERT INTO studio_analyses(project_id,question,mode,packet,created_at,updated_at) VALUES(?,?,?,?,?,?)',(pid,question,mode,packet,_now(),_now()))
    aid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
    return {'id':aid,'packet':packet,'overview':overview,'state':'awaiting_ai'}

def validate_result(packet,result):
    try:obj=json.loads(result) if isinstance(result,str) else result
    except json.JSONDecodeError:raise ValueError('AI result không phải JSON hợp lệ')
    if not isinstance(obj,dict):raise ValueError('AI result phải là object')
    required=('executive_summary','market_findings','subcategory_assessments','rising_apps','research_gaps','suggested_research_actions')
    for k in required:
        if k not in obj:raise ValueError('AI result thiếu '+k)
    if not isinstance(obj['executive_summary'],str) or len(obj['executive_summary'])>5000:raise ValueError('Executive summary không hợp lệ')
    allowed=set(json.loads(packet.split('\n',1)[1])['allowed_evidence_ids'])
    for key in ('market_findings','subcategory_assessments','rising_apps','suggested_research_actions'):
        entries=obj[key]
        if not isinstance(entries,list) or len(entries)>40:raise ValueError(key+' phải là list tối đa 40 phần tử')
        for item in entries:
            if not isinstance(item,dict):raise ValueError('Finding không hợp lệ')
            refs=item.get('evidence_ids')
            if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or v not in allowed for v in refs):
                raise ValueError('AI insight thiếu evidence hoặc tham chiếu ngoài nguồn đã thu thập: '+key)
            if item.get('confidence','low') not in ('low','medium','high'):raise ValueError('Confidence không hợp lệ')
    if not isinstance(obj['research_gaps'],list):raise ValueError('research_gaps phải là list')
    return obj

def import_ai(c,p):
    aid=int(p.get('analysis_id',0));row=c.execute('SELECT * FROM studio_analyses WHERE id=?',(aid,)).fetchone()
    if not row:raise ValueError('AI analysis không tồn tại')
    result=validate_result(row['packet'],p.get('result',''))
    c.execute("UPDATE studio_analyses SET result_json=?,state='ready',updated_at=? WHERE id=?",(_json(result),_now(),aid))
    return {'id':aid,'state':'ready','success':True}

def latest_analysis(c,pid):
    row=c.execute('SELECT * FROM studio_analyses WHERE project_id=? ORDER BY id DESC LIMIT 1',(pid,)).fetchone()
    if not row:return None
    d=dict(row)
    if d['result_json']:d['result']=json.loads(d.pop('result_json'))
    else:d.pop('result_json')
    return d

def get_analysis(c,aid):
    row=c.execute('SELECT * FROM studio_analyses WHERE id=?',(aid,)).fetchone()
    if not row:raise ValueError('Không có analysis')
    d=dict(row);d['result']=json.loads(d['result_json']) if d['result_json'] else None
    return d

def send_action_for_review(c,p):
    """Explicit PO action: bridge validated Studio AI draft into v1.5 Action Registry."""
    aid=int(p.get('analysis_id',0));index=int(p.get('index',-1))
    a=c.execute('SELECT * FROM studio_analyses WHERE id=?',(aid,)).fetchone()
    if not a or a['state']!='ready' or not a['result_json']:
        raise ValueError('Cần AI analysis hợp lệ, không stale, trước khi chuyển Action')
    result=json.loads(a['result_json']);actions=result.get('suggested_research_actions',[])
    if index<0 or index>=len(actions):raise ValueError('Research action index không hợp lệ')
    action=actions[index]
    # Validate again against the exact packet snapshot, not current sources.
    allowed=set(json.loads(a['packet'].split('\n',1)[1])['allowed_evidence_ids'])
    refs=action.get('evidence_ids',[])
    if not refs or any(ref not in allowed for ref in refs):raise ValueError('Action thiếu evidence hợp lệ')
    source_index=aid*1000+index
    existing=c.execute("SELECT id FROM action_registry WHERE project_id=? AND source_type='studio_ai' AND source_index=?",(a['project_id'],source_index)).fetchone()
    if existing:return {'id':existing['id'],'existing':True}
    title=str(action.get('title','')).strip()[:220]
    reason=str(action.get('reason','')).strip()[:2500]
    if not title or not reason:raise ValueError('Action title/reason không hợp lệ')
    packet_evidence=json.loads(a['packet'].split('\n',1)[1])['evidence']
    lookup={}
    for group in ('public_candidates','public_news','top_downloads','top_delta','new_releases'):
        for item in packet_evidence.get(group,[]):
            for ref in item.get('evidence_ids',[item.get('evidence_id')]):
                lookup[ref]=item
    evidence=[{'type':'studio_evidence','id':ref,'analysis_id':aid,
      'name':lookup.get(ref,{}).get('name') or lookup.get(ref,{}).get('title') or ref,
      'url':lookup.get(ref,{}).get('url',''),'source':lookup.get(ref,{}).get('field_sources',{})} for ref in refs]
    t=_now()
    c.execute('''INSERT INTO action_registry(project_id,run_id,insight_id,source_type,source_index,title,description,priority,state,evidence_json,notes,is_demo,created_at,updated_at)
      VALUES(?,NULL,NULL,'studio_ai',?,?,?,?,'new',?,?,0,?,?)''',
      (a['project_id'],source_index,title,reason,'medium',_json(evidence),f'Studio AI analysis #{aid} · PO approved research action',t,t))
    return {'id':c.execute('SELECT last_insert_rowid()').fetchone()[0],'existing':False}
