"""Build a clean Windows ZIP from the checked-out source, without private backups."""
import hashlib,json,sqlite3,tempfile,zipfile,subprocess,time,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=Path('C:/Users/Admin/Documents/Codex/2026-10-15/ti-p-t-c-tri-n/outputs');out.mkdir(parents=True,exist_ok=True)
stage=Path(tempfile.mkdtemp(prefix='po-release-'));db=stage/'research.sqlite3'
source=sqlite3.connect('file:'+str(root/'data/research.sqlite3').replace('\\','/')+'?mode=ro',uri=True)
c=sqlite3.connect(db)
for kind in ('table','index'):
 for (sql,) in source.execute("SELECT sql FROM sqlite_master WHERE type=? AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'",(kind,)):c.execute(sql)
rows=list(source.execute('SELECT * FROM studio_rows ORDER BY id LIMIT 10'));imports=sorted({r[1] for r in rows})
parents=list(source.execute('SELECT DISTINCT project_id FROM studio_imports WHERE id IN ('+','.join('?'*len(imports))+')',imports))
for table,records in [('projects',[source.execute('SELECT * FROM projects WHERE id=?',(r[0],)).fetchone() for r in parents]),('studio_imports',[source.execute('SELECT * FROM studio_imports WHERE id=?',(i,)).fetchone() for i in imports]),('studio_rows',rows)]:
 for row in records:c.execute('INSERT INTO '+table+' VALUES('+','.join('?'*len(row))+')',row)
for key,value in [('auto_scan','false'),('scan_hours','24'),('default_mode','manual'),('codex_allowed','false')]:c.execute('INSERT INTO settings(key,value) VALUES(?,?)',(key,value))
c.commit();assert not list(c.execute('PRAGMA foreign_key_check'));c.close();source.close()
files=[p for p in root.iterdir() if p.is_file() and (p.suffix in ('.py','.json') or p.name in ('RUN_WINDOWS.bat','DESIGN.md','README_RECOVERY.md','README_V193.md','IMPLEMENTATION_REPORT_V193.md')) and p.name!='RELEASE_MANIFEST.json']
files+=list((root/'static').rglob('*'));files+=list((root/'runtime').rglob('*'))
files=[p for p in files if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log')]
manifest={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest['data/research.sqlite3']=hashlib.sha256(db.read_bytes()).hexdigest()
zip_path=out/'PO_Intelligence_Hub_v1.9.3_Windows.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'PO_Intelligence_Hub/'+p.relative_to(root).as_posix())
 z.write(db,'PO_Intelligence_Hub/data/research.sqlite3')
 z.writestr('PO_Intelligence_Hub/RELEASE_MANIFEST.json',json.dumps(manifest,indent=2))
extract=stage/'extracted'
with zipfile.ZipFile(zip_path) as z:z.extractall(extract)
app=extract/'PO_Intelligence_Hub'
p=subprocess.Popen([str(app/'runtime/python.exe'),str(app/'server.py'),'--port','8903','--no-browser'],cwd=app,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
 for _ in range(60):
  try:
   body=urllib.request.urlopen('http://127.0.0.1:8903/',timeout=2).read().decode();assert 'v1.9.3' in body
   for asset in ('product.css','product.js'):
    assert len(urllib.request.urlopen('http://127.0.0.1:8903/'+asset,timeout=2).read())>100
   break
  except Exception:time.sleep(.2)
 else:raise RuntimeError('Extracted ZIP server failed')
 with sqlite3.connect(app/'data/research.sqlite3') as c:
  assert c.execute('select count(*) from studio_rows').fetchone()[0]==10
  assert not list(c.execute('PRAGMA foreign_key_check'))
 print('ZIP SMOKE PASS',zip_path,zip_path.stat().st_size,flush=True)
finally:p.terminate();p.wait(timeout=10)
(out/'release-checks-v193.json').write_text(json.dumps(dict(zip=str(zip_path),sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest(),files=len(manifest),sample_rows=10,zip_smoke='pass',private_backups_included=False),indent=2),encoding='utf-8')
