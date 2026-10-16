"""Explicit maintenance only: back up then retain 10 CSV rows, never run at startup."""
import datetime,json,sqlite3
from pathlib import Path

def reset(root):
 db=Path(root)/'data/research.sqlite3'
 backup=db.with_name('research-before-reset-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
 c=sqlite3.connect(db,timeout=30)
 with sqlite3.connect(backup) as b:c.backup(b)
 c.execute('PRAGMA foreign_keys=OFF');c.execute('BEGIN IMMEDIATE')
 try:
  samples=list(c.execute('SELECT id,import_id FROM studio_rows ORDER BY import_id,line LIMIT 10'))
  if len(samples)!=10:raise RuntimeError('Không đủ 10 dòng mẫu; giữ nguyên database')
  imports=sorted({r[1] for r in samples})
  projects=[r[0] for r in c.execute('SELECT DISTINCT project_id FROM studio_imports WHERE id IN ('+','.join('?'*len(imports))+')',imports)]
  if c.execute('SELECT 1 FROM rss_sources WHERE project_id NOT IN ('+','.join('?'*len(projects))+') LIMIT 1',projects).fetchone():raise RuntimeError('Cấu hình RSS ngoài research mẫu cần quyết định riêng; rollback an toàn')
  keep={'projects','studio_rows','studio_imports','settings','rss_sources','source_registry','intelligence_versions'}
  tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  for table in tables:
   if table not in keep:c.execute('DELETE FROM "'+table+'"')
  ids=[r[0] for r in samples]
  c.execute('DELETE FROM studio_rows WHERE id NOT IN ('+','.join('?'*len(ids))+')',ids)
  c.execute('DELETE FROM studio_imports WHERE id NOT IN ('+','.join('?'*len(imports))+')',imports)
  c.execute('DELETE FROM projects WHERE id NOT IN ('+','.join('?'*len(projects))+')',projects)
  for pid in projects:c.execute("UPDATE projects SET name='CSV mẫu · 10 dòng',brief='Dữ liệu mẫu; không đại diện toàn thị trường.' WHERE id=?",(pid,))
  c.execute('UPDATE studio_imports SET row_count=(SELECT COUNT(*) FROM studio_rows WHERE import_id=studio_imports.id)')
  c.commit()
 except Exception:c.rollback();raise
 finally:c.close()
 return str(backup)
if __name__=='__main__':
 import sys
 if sys.argv[1:]!=['--confirm-reset']:raise SystemExit('Cần --confirm-reset để dọn database')
 print(reset(Path(__file__).resolve().parents[1]))
