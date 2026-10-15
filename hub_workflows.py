"""Additive unified research identity and immutable report snapshots."""
import json
import hashlib
import studio


def init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS hub_research (
      research_id INTEGER PRIMARY KEY REFERENCES projects(id), planner_id INTEGER,
      scope_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS hub_reports (
      report_id INTEGER PRIMARY KEY, research_id INTEGER NOT NULL REFERENCES projects(id),
      analysis_id INTEGER REFERENCES studio_analyses(id), collection_id INTEGER,
      snapshot_json TEXT NOT NULL, fingerprint TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(research_id,fingerprint));
    CREATE TABLE IF NOT EXISTS hub_action_links (
      action_id INTEGER PRIMARY KEY REFERENCES action_registry(id),
      research_id INTEGER NOT NULL REFERENCES projects(id), analysis_id INTEGER NOT NULL,
      finding_index INTEGER NOT NULL);
    ''')
    c.execute("INSERT OR IGNORE INTO hub_action_links SELECT a.id,a.project_id,s.id,a.source_index % 1000 FROM action_registry a JOIN studio_analyses s ON s.id=CAST(a.source_index / 1000 AS INTEGER) AND s.project_id=a.project_id WHERE a.source_type='studio_ai'")


def config(c,p):
    pid=int(p.get('research_id',0)); studio._project(c,pid)
    scope=p.get('scope') or {}
    if not isinstance(scope,dict): raise ValueError('Scope phải là object')
    planner=p.get('planner_id')
    if planner and not c.execute('SELECT id FROM planner_drafts WHERE id=?',(int(planner),)).fetchone():
        raise ValueError('Planner không tồn tại')
    previous=c.execute('SELECT scope_json FROM hub_research WHERE research_id=?',(pid,)).fetchone()
    if previous and json.loads(previous['scope_json'])!=scope:
        c.execute("UPDATE studio_analyses SET state='stale',updated_at=? WHERE project_id=? AND state='ready'",(studio._now(),pid))
    c.execute('INSERT INTO hub_research VALUES(?,?,?,?) ON CONFLICT(research_id) DO UPDATE SET planner_id=excluded.planner_id,scope_json=excluded.scope_json,updated_at=excluded.updated_at',
      (pid,planner,studio._json(scope),studio._now()))
    return {'research_id':pid,'scope':scope,'planner_id':planner}


def overview(c):
    projects=[]
    for p in c.execute('SELECT * FROM projects ORDER BY id DESC').fetchall():
        pid=p['id']; a=studio.latest_analysis(c,pid); col=studio.latest_collection(c,pid)
        imports=studio.list_imports(c,pid)
        cfg=c.execute('SELECT * FROM hub_research WHERE research_id=?',(pid,)).fetchone()
        pub=c.execute('SELECT COUNT(*) FROM studio_public WHERE project_id=?',(pid,)).fetchone()[0]
        reports=c.execute('SELECT COUNT(*) FROM hub_reports WHERE research_id=?',(pid,)).fetchone()[0]
        old=c.execute('SELECT COUNT(*) FROM research_runs WHERE project_id=?',(pid,)).fetchone()[0]
        actions=c.execute('SELECT COUNT(*) FROM action_registry WHERE project_id=?',(pid,)).fetchone()[0]
        stage='question'
        if cfg:stage='plan'
        if col or imports:stage='assessment'
        if a:stage='report' if a['state']=='ready' else 'analysis'
        if actions and a and a['state']=='ready':stage='decision'
        projects.append({'research_id':pid,'name':p['name'],'question':p['brief'],
          'category':p['category'],'geo':p['geo'],'scope':json.loads(cfg['scope_json']) if cfg else {},
          'planner_id':cfg['planner_id'] if cfg else None,'stage':stage,
          'collection_id':col['id'] if col else None,'collection_status':col['status'] if col else None,
          'analysis_id':a['id'] if a else None,'analysis_state':a['state'] if a else None,
          'summary':a['result']['executive_summary'] if a and a['state']=='ready' and a.get('result') else None,
          'public_count':pub,'dataset_ids':[x['id'] for x in imports if x['state']=='complete'],
          'dataset_rows':sum(x['row_count'] for x in imports if x['state']=='complete'),
          'reports':reports,'legacy_reports':old,'actions':actions})
    return {'projects':projects,'reports':[dict(r) for r in c.execute('SELECT report_id,research_id,analysis_id,created_at FROM hub_reports ORDER BY report_id DESC')],
      'action_links':[dict(r) for r in c.execute('SELECT * FROM hub_action_links')]}


def save_report(c,p):
    pid=int(p.get('research_id',0)); project=studio._project(c,pid)
    aid=p.get('analysis_id'); a=studio.get_analysis(c,int(aid)) if aid else None
    if a and a['project_id']!=pid:raise ValueError('Analysis không thuộc research này')
    rows,_=studio.merge_records(studio.records(c,pid))
    wanted=set(p.get('evidence_ids') or [])
    available={r['evidence_id']:r for r in rows}
    if wanted-set(available):raise ValueError('Evidence không thuộc research hiện tại')
    col=studio.latest_collection(c,pid)
    snapshot={'research_id':pid,'project':project,'analysis':a,
      'collection':col,'dataset_ids':[x['id'] for x in studio.list_imports(c,pid) if x['state']=='complete'],
      'view':p.get('view') or {},'records':[available[k] for k in sorted(wanted)],
      'public':studio.public_list(c,pid),'news':studio.public_news(c,pid),
      'imports':studio.list_imports(c,pid)}
    view=snapshot['view']
    snapshot['overview']=studio.deterministic_overview(snapshot['records'] if view.get('mode')=='hybrid' else [],snapshot['public'],view.get('market','All'),project.get('brief',''),snapshot['news'],studio.public_momentum(c,pid))
    raw=studio._json(snapshot); digest=hashlib.sha256(raw.encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO hub_reports(research_id,analysis_id,collection_id,snapshot_json,fingerprint,created_at) VALUES(?,?,?,?,?,?)',
      (pid,aid,col['id'] if col else None,raw,digest,studio._now()))
    row=c.execute('SELECT report_id FROM hub_reports WHERE research_id=? AND fingerprint=?',(pid,digest)).fetchone()
    return {'report_id':row['report_id'],'research_id':pid,'analysis_id':aid}


def get_report(c,rid):
    row=c.execute('SELECT * FROM hub_reports WHERE report_id=?',(rid,)).fetchone()
    if not row:raise ValueError('Report không tồn tại')
    result=dict(row);result['snapshot']=json.loads(result.pop('snapshot_json'));return result


def filter_rows(rows,view):
    """Match the explorer controls so AI receives the selected dataset view."""
    f=view.get('filters') or {}
    def contains(value,term):return str(term or '').strip().lower() in str(value or '').lower()
    def keep(r):
        if f.get('search') and not any(contains(r.get(k),f['search']) for k in ('name','publisher','id','category')):return False
        for k in ('name','category','release'):
            if f.get(k) and not contains(r.get(k),f[k]):return False
        for k in ('platform','geo','period_end'):
            if f.get(k) and f[k]!='all' and r.get(k)!=f[k]:return False
        for k in ('downloads','delta_pop','growth_pop','growth_yoy'):
            v=f.get(k+'Min')
            if v is not None and v!='':
                if r.get(k) is None or r[k]<float(v)/(100 if k.startswith('growth_') else 1):return False
        return True
    selected=[r for r in rows if keep(r)]
    key=view.get('sort','downloads'); reverse=view.get('direction','desc')=='desc'
    nonnull=[r for r in selected if r.get(key) is not None]
    nonnull.sort(key=lambda r:(r[key],str(r.get('id',''))),reverse=reverse)
    selected=nonnull+[r for r in selected if r.get(key) is None]
    top=view.get('top','all')
    if top!='all':selected=selected[:max(0,min(30000,int(top)))]
    return selected


def action_report(c,action):
    """Use the exact source analysis packet for Studio actions; keep v1.5 reports intact."""
    link=c.execute('SELECT * FROM workspace_links WHERE action_id=?',(action['id'],)).fetchone()
    if link:
        import research_workspace
        run=research_workspace.get(c,link['run_id']);packet=run['packet'] or {}
        return {'top_competitors':[e for e in packet.get('evidence',[]) if e.get('kind')=='public'],
          'market_news':packet.get('news',[]),'dataset_evidence':[e for e in packet.get('evidence',[]) if e.get('kind')=='csv'],
          'coverage':{'research_id':run['research_id'],'workspace_run_id':run['id'],'scope':run['scope']},
          'limitations':packet.get('gaps',[]),'market_findings':[run.get('result',{}).get('trend',{})]}
    if action['run_id']:
        run=c.execute('SELECT * FROM research_runs WHERE id=?',(action['run_id'],)).fetchone()
        if not run or run['status']!='ready':raise ValueError('Thiếu report nguồn')
        return json.loads(run['report_json'])
    link=c.execute('SELECT * FROM hub_action_links WHERE action_id=?',(action['id'],)).fetchone()
    if not link:raise ValueError('Thiếu liên kết analysis nguồn')
    a=studio.get_analysis(c,link['analysis_id'])
    packet=json.loads(a['packet'].split('\n',1)[1]);e=packet['evidence']
    return {'top_competitors':e.get('public_candidates',[]),'market_news':e.get('public_news',[]),
      'coverage':{'research_id':action['project_id'],'analysis_id':a['id'],'scopes':e.get('scopes',[])},
      'limitations':e.get('limitations',[]),'dataset_evidence':e.get('top_downloads',[]),
      'market_findings':(a.get('result') or {}).get('market_findings',[])}
