"""Ship handoff gates. Instructions + post-checks, NOT a sandbox or auto-runner."""
import argparse
import contextlib
import datetime as dt
import difflib
import hashlib
import json
import ntpath
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import uuid
import tomllib

ROLES = ('planner', 'coder', 'tester', 'reviewer')
REPORTS = dict(zip(ROLES, ('ke-hoach.md', 'thay-doi.md', 'ket-qua-test.md', 'danh-gia.md')))
PROTECTED = ('.git', '.bangiao', '.codex', 'data', 'runtime', '.env')
class GateError(Exception):
    pass

def git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if p.returncode:
        raise GateError(p.stderr.decode('utf-8', 'replace').strip() or 'Git command failed')
    return p.stdout

def repo(root):
    root = Path(root).resolve()
    top = Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if top != root:
        raise GateError('ROOT must be the Git repository root')
    try:
        branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()
    except GateError:
        raise GateError('Detached HEAD: stop before any writes')
    if branch.casefold() in ('main', 'master'):
        raise GateError('Protected branch: stop before any writes')
    head = git(root, 'rev-parse', '--verify', 'HEAD').decode().strip()
    return root, branch, head

def safe(root, relative):
    if not isinstance(relative, str) or not relative or '\x00' in relative:
        raise GateError('Invalid path')
    name = relative.replace('\\', '/')
    parts = PurePosixPath(name).parts
    if ntpath.splitdrive(name)[0] or name.startswith('/') or '..' in parts or not parts:
        raise GateError('Path escapes ROOT: ' + relative)
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root):
        raise GateError('Resolved path escapes ROOT: ' + relative)
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
            raise GateError('Symlink/junction is not allowed: ' + relative)
    return path

def keypath(root, value):
    p = safe(root, value)
    if p.is_dir():
        raise GateError('Expected an exact file, not directory: ' + value)
    name = p.relative_to(root).as_posix()
    if name.casefold().startswith('.agents/skills/ship/'):
        raise GateError('Protected pipeline skill path: ' + name)
    if name.split('/')[0].casefold() in PROTECTED or any(x.casefold().startswith('.env') for x in PurePosixPath(name).parts):
        raise GateError('Protected pipeline/data/config path: ' + name)
    return name

def digest(path):
    if path.is_symlink():
        return 'LINK:' + str(path.readlink())
    if getattr(path, 'is_junction', lambda: False)():
        return 'JUNCTION:' + str(path.resolve())
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def profiles(root):
    """Read the sole configuration source; no model/effort defaults."""
    result = {}
    for role in ROLES:
        path = safe(root, '.codex/agents/' + role + '.toml')
        try:
            config = tomllib.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as e:
            raise GateError('Invalid agent profile ' + role + ': ' + str(e))
        for key in ('name', 'description', 'model', 'model_reasoning_effort', 'developer_instructions'):
            if not isinstance(config.get(key), str) or not config[key].strip():
                raise GateError('Missing profile field: ' + role + '.' + key)
        if config['name'] != role:
            raise GateError('Profile name mismatch: ' + role)
        result[role] = dict(config=config, sha256=digest(path))
    return result

def preflight(root):
    root, branch, head = repo(root)
    selected = profiles(root)
    if safe(root, '.bangiao/.ship.lock').exists():
        raise GateError('Another guard operation is active; do not remove its lock')
    statefile = safe(root, '.bangiao/luot-chay.json')
    if statefile.exists() and load(root).get('next_role'):
        raise GateError('Previous run is still active; do not halt or overwrite it')
    return dict(root=str(root), branch=branch, head=head, profiles={
        role: dict(sha256=item['sha256'], config={key: item['config'][key]
                   for key in ('name', 'model', 'model_reasoning_effort')})
        for role, item in selected.items()})

def dispatch(root):
    """Read-only spawn payload tied to the current run and frozen profiles."""
    root, _, _ = repo(root)
    state = load(root)
    identity(root, state)
    role = state.get('next_role')
    if role not in ROLES:
        raise GateError('No pending agent')
    config = profiles(root)[role]['config']
    return dict(root=str(root), run_id=state['run_id'], branch=state['branch'],
                role=role, profile=config, request=state['request'],
                guard_python=sys.executable, report='.bangiao/' + REPORTS[role])


def inventory(root, extra=()):
    raw = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    names = {os.fsdecode(x).replace('\\', '/') for x in raw.split(b'\x00') if x}
    names.update(extra)
    result = {}
    for name in names:
        # Never read datasets/runtime/secrets; pipeline profiles ARE checked for changes.
        first = name.split('/')[0].casefold()
        if first in ('.git', '.bangiao', 'data', 'runtime') or any(x.casefold().startswith('.env') for x in PurePosixPath(name).parts):
            continue
        path = root / name
        if not path.resolve().is_relative_to(root):
            result[name] = 'ESCAPING_LINK'
            continue
        result[name] = digest(path)
    for name in ('data', 'data/research.sqlite3', 'data/research.sqlite3-wal', 'data/research.sqlite3-shm'):
        path = root / name
        if path.exists():
            stat = path.stat()
            result[name] = 'PROTECTED_META:' + str(stat.st_mtime_ns) + ':' + str(stat.st_size)
    handoff = safe(root, '.bangiao')
    if handoff.exists():
        for directory, dirs, files in os.walk(handoff, followlinks=False):
            parent = Path(directory)
            if parent == handoff:
                dirs[:] = [name for name in dirs if name != 'nen']
            for name in list(dirs):
                path = parent / name
                key = path.relative_to(root).as_posix()
                if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                    result[key] = 'LINK_OR_JUNCTION'
                    dirs.remove(name)
                else:
                    result[key] = 'DIRECTORY'
            for name in files:
                if parent == handoff and (name in ('luot-chay.json', '.ship.lock') or name.startswith('.ship-state-')):
                    continue
                path = parent / name
                result[path.relative_to(root).as_posix()] = digest(path)
    return result

def save(root, state):
    target = safe(root, '.bangiao/luot-chay.json')
    tmp = target.with_name('.ship-state-' + uuid.uuid4().hex)
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(target)

def load(root):
    path = safe(root, '.bangiao/luot-chay.json')
    if not path.exists():
        raise GateError('No active run; call start first')
    return json.loads(path.read_text(encoding='utf-8'))

@contextlib.contextmanager
def lock(root):
    directory = safe(root, '.bangiao')
    directory.mkdir(exist_ok=True)
    path = safe(root, '.bangiao/.ship.lock')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise GateError('Another guard operation is active; do not remove its lock')
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()

def identity(root, state):
    _, branch, head = repo(root)
    index = hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest()
    if 'profile_hashes' in state and {role: item['sha256'] for role, item in profiles(root).items()} != state['profile_hashes']:
        raise GateError('Agent profiles changed during run; stop without fallback')
    for name, info in state.get('baseline_files', {}).items():
        if info['exists'] and digest(safe(root, '.bangiao/nen/' + state['run_id'] + '/files/' + name)) != info['sha256']:
            raise GateError('Baseline snapshot changed: ' + name)
    for item in state.get('tests', []):
        if digest(safe(root, item['log'])) != item['sha256']:
            raise GateError('Recorded test log changed: ' + item['log'])
    if (branch, head, index) != (state['branch'], state['head'], state['index']):
        raise GateError('Branch, HEAD or index changed; stop without reset')

def start(root, request):
    root, branch, head = repo(root)  # Crucially before mkdir/delete/lock.
    if not request.strip():
        raise GateError('Missing feature request')
    selected = profiles(root)  # Validate before touching handoffs.
    with lock(root):
        statefile = safe(root, '.bangiao/luot-chay.json')
        if statefile.exists() and load(root).get('next_role'):
            raise GateError('Previous run is still active; halt only if user requests it')
        paths = [safe(root, '.bangiao/' + name) for name in REPORTS.values()]
        if any(p.exists() and not p.is_file() for p in paths):
            raise GateError('A report path is not a regular file')
        for p in paths:
            if p.exists():
                p.unlink()
        state = dict(run_id=uuid.uuid4().hex, branch=branch, head=head,
                     index=hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest(),
                     request=request, profile_hashes={role: item['sha256'] for role, item in selected.items()}, started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                     next_role='planner', status='DANG_CHAY', checks={}, violations=[], tests=[])
        state['checkpoint'] = inventory(root)
        safe(root, '.bangiao/nen/' + state['run_id']).mkdir(parents=True, exist_ok=True)
        save(root, state)
        return public(state)

def public(state):
    return {k: state.get(k) for k in ('run_id', 'branch', 'next_role', 'status', 'checks', 'violations', 'reason')}

def headers(root, state, role):
    path = safe(root, '.bangiao/' + REPORTS[role])
    if not path.exists() or path.stat().st_size > 256000:
        raise GateError('Missing or oversized report: ' + path.name)
    text = path.read_text(encoding='utf-8-sig').strip()
    if not text:
        raise GateError('Empty report: ' + path.name)
    fields = {}
    for line in text.splitlines():
        if ': ' in line and not line.startswith((' ', '#', '-', '`')):
            key, value = line.split(': ', 1)
            if key in ('LUOT_CHAY', 'NHANH', 'VAI_TRO', 'MODEL', 'TRANG_THAI', 'PHAN QUYET', 'PHAM_VI_JSON'):
                if key in fields:
                    raise GateError('Duplicate report header: ' + key)
                fields[key] = value.strip()
    expected = dict(LUOT_CHAY=state['run_id'], NHANH=state['branch'], VAI_TRO=role, MODEL=profiles(root)[role]['config']['model'])
    if any(fields.get(k) != v for k, v in expected.items()):
        raise GateError('Stale run, wrong role/model or branch in ' + path.name)
    body_lines = [line for line in text.splitlines() if not any(line.startswith(k + ': ') for k in fields)]
    if len(''.join(body_lines).strip()) < 30:
        raise GateError('Report has headers only; include concrete handoff content')
    return fields, text

def scope(root, fields):
    try:
        data = json.loads(fields['PHAM_VI_JSON'])
        if set(data) != {'code', 'tests', 'commands'}:
            raise ValueError()
        for key in ('code', 'tests'):
            if not isinstance(data[key], list):
                raise ValueError()
            data[key] = [keypath(root, p) for p in data[key]]
        allpaths = data['code'] + data['tests']
        if len({p.casefold() for p in allpaths}) != len(allpaths):
            raise ValueError('Overlapping code/test paths')
        if not isinstance(data['commands'], list) or not data['commands'] or any(not isinstance(c, list) or not c or not all(isinstance(v, str) and v for v in c) for c in data['commands']):
            raise ValueError('Commands must be nonempty argv lists')
        return data
    except (KeyError, TypeError, ValueError) as e:
        raise GateError('Invalid PHAM_VI_JSON: ' + str(e))

def check(root, role):
    root, _, _ = repo(root)
    with lock(root):
        state = load(root)
        identity(root, state)
        if state['next_role'] != role:
            raise GateError('Wrong stage; expected ' + str(state['next_role']))
        fields, text = headers(root, state, role)
        now = inventory(root, state.get('scope', {}).get('code', []) + state.get('scope', {}).get('tests', []))
        changed = {p for p in set(now) | set(state['checkpoint']) if now.get(p) != state['checkpoint'].get(p)}
        allowed = {'.bangiao/' + REPORTS[role]}
        if role in ('coder', 'tester'):
            allowed.update(state['scope']['code' if role == 'coder' else 'tests'])
        outside = sorted(changed - allowed)
        state['violations'].extend(dict(role=role, path=p) for p in outside)
        status = fields.get('TRANG_THAI')
        if role == 'planner':
            if status not in ('SAN_SANG', 'CAN_LAM_RO'):
                raise GateError('Planner status must be SAN_SANG or CAN_LAM_RO')
            if status == 'CAN_LAM_RO':
                state.update(next_role=None, status='CAN_LAM_RO')
            else:
                state['scope'] = scope(root, fields)
                snapshots = {}
                for name in state['scope']['code'] + state['scope']['tests']:
                    original = safe(root, name)
                    snapshots[name] = dict(exists=original.exists(), sha256=digest(original))
                    if original.exists():
                        copy = safe(root, '.bangiao/nen/' + state['run_id'] + '/files/' + name)
                        copy.parent.mkdir(parents=True, exist_ok=True)
                        copy.write_bytes(original.read_bytes())
                state['baseline_files'] = snapshots
                state['next_role'] = 'coder'
        elif role == 'coder':
            if status not in ('HOAN_THANH', 'CHUA_HOAN_THANH'):
                raise GateError('Invalid Coder status')
            state['next_role'] = 'tester' if status == 'HOAN_THANH' else 'reviewer'
        elif role == 'tester':
            if status not in ('DAT', 'KHONG_DAT', 'CHUA_KIEM_TRA'):
                raise GateError('Invalid Tester status')
            complete = all(any(t['argv'] == cmd and t['exit_code'] == 0 for t in state['tests']) for cmd in state['scope']['commands'])
            if status == 'DAT' and (not complete or any(t['exit_code'] for t in state['tests'])):
                state['violations'].append(dict(role=role, path='.bangiao/ket-qua-test.md', reason='DAT without all successful test logs'))
                status = 'KHONG_DAT'
            state['next_role'] = 'reviewer'
        else:
            verdict = fields.get('PHAN QUYET')
            if text.splitlines()[0] not in ('PHAN QUYET: CHOT', 'PHAN QUYET: CAN SUA', 'PHAN QUYET: CHAN'):
                raise GateError('Reviewer first line must contain one exact verdict')
            if verdict == 'CHOT' and (state['violations'] or outside or state['checks'].get('tester') != 'DAT' or state['checks'].get('coder') != 'HOAN_THANH'):
                state.update(next_role=None, status='CHAN', reason='Reviewer CHOT rejected: required gates did not pass')
                state['checks'][role] = 'CHAN'
                save(root, state)
                raise GateError(state['reason'])
            state.update(next_role=None, status=verdict)
            status = verdict
        state['checks'][role] = status
        if state['violations'] and role != 'reviewer':
            state['next_role'] = 'reviewer'
        state['checkpoint'] = inventory(root, state.get('scope', {}).get('code', []) + state.get('scope', {}).get('tests', []))
        save(root, state)
        return public(state)

def run_test(root, argv, timeout=180):
    root, _, _ = repo(root)
    with lock(root):
        state = load(root)
        identity(root, state)
        if state['next_role'] != 'tester' or any(t['exit_code'] for t in state['tests']):
            raise GateError('Tests only during Tester; stop after first failed command')
        if argv not in state['scope']['commands']:
            raise GateError('Test argv is not declared by Planner')
        actual = [sys.executable if x == '{python}' else x for x in argv]
        try:
            p = subprocess.run(actual, cwd=root, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            code, output = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            code, output = 124, (e.stdout or b'') + (e.stderr or b'') + b'\nTIMEOUT'
        except OSError as e:
            code, output = 127, str(e).encode('utf-8')
        name = '.bangiao/nen/' + state['run_id'] + '/test-' + uuid.uuid4().hex + '.log'
        safe(root, name).write_bytes(output)
        item = dict(argv=argv, exit_code=code, log=name, sha256=hashlib.sha256(output).hexdigest())
        state['tests'].append(item)
        save(root, state)
        return dict(item, _exit=0 if code == 0 else 1)

def halt(root, reason):
    root, _, _ = repo(root)
    with lock(root):
        state = load(root)
        state.update(next_role=None, status='DUNG', reason=reason)
        save(root, state)
        return public(state)

def diff(root):
    root, _, _ = repo(root)
    state = load(root)
    identity(root, state)
    output = []
    for name, baseline in state.get('baseline_files', {}).items():
        before = safe(root, '.bangiao/nen/' + state['run_id'] + '/files/' + name)
        after = safe(root, name)
        a = before.read_text(encoding='utf-8', errors='replace').splitlines(True) if baseline['exists'] else []
        b = after.read_text(encoding='utf-8', errors='replace').splitlines(True) if after.exists() else []
        output.extend(difflib.unified_diff(a, b, fromfile='baseline/' + name, tofile='current/' + name))
    return ''.join(output)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('start');p.add_argument('--request');p.add_argument('--request-file', type=Path)
    p = sub.add_parser('check');p.add_argument('role', choices=ROLES)
    p = sub.add_parser('test');p.add_argument('--timeout', type=int, default=180);p.add_argument('argv', nargs=argparse.REMAINDER)
    p = sub.add_parser('halt');p.add_argument('--reason', required=True)
    sub.add_parser('status');sub.add_parser('diff');sub.add_parser('preflight');sub.add_parser('dispatch')
    args = parser.parse_args()
    try:
        root, _, _ = repo(args.root)
        if args.command == 'preflight':data = preflight(root)
        elif args.command == 'dispatch':data = dispatch(root)
        elif args.command == 'start':
            request = args.request_file.read_text(encoding='utf-8') if args.request_file else args.request or ''
            data = start(root, request)
        elif args.command == 'check':data = check(root, args.role)
        elif args.command == 'test':data = run_test(root, args.argv[1:] if args.argv[:1] == ['--'] else args.argv, args.timeout)
        elif args.command == 'halt':data = halt(root, args.reason)
        elif args.command == 'diff':print(diff(root));return 0
        else:data = public(load(root))
        code = data.pop('_exit', 0)
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return code
    except (GateError, ValueError, OSError) as e:
        print(json.dumps(dict(error=str(e)), ensure_ascii=True), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
