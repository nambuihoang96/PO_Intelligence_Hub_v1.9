"""Deterministic gate tests; all Git writes are confined to temporary fixture repos."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import tomllib
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ship_guard', HERE/'ship_guard.py')
g = importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class Gates(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        subprocess.run(['git','init','-b','feature/fixture',str(self.root)],check=True,capture_output=True)
        shutil.copytree(HERE.parent/'agents', self.root/'.codex/agents')
        self.models={role: item['config']['model'] for role,item in g.profiles(self.root).items()}
        (self.root/'app.py').write_text('value = 1\n',encoding='utf-8')
        self.cmd=['{python}','-c','print("fixture test passed")']
        self.git('add','app.py');self.git('-c','user.name=Fixture','-c','user.email=fixture@local.invalid','commit','-qm','Fixture seed')
    def tearDown(self):self.tmp.cleanup()
    def git(self,*args):return g.git(self.root,*args)
    def start(self):g.start(self.root,'Add a fixture feature');return g.load(self.root)
    def report(self,role,status,scope=None,run=None):
        state=g.load(self.root);first=('PHAN QUYET' if role=='reviewer' else 'TRANG_THAI')+': '+status
        body=first+'\n'+ '\n'.join(k+': '+str(v) for k,v in dict(LUOT_CHAY=run or state['run_id'],NHANH=state['branch'],VAI_TRO=role,MODEL=self.models[role]).items())+'\n'
        if role=='planner' and status=='SAN_SANG':body+='PHAM_VI_JSON: '+json.dumps(scope or dict(code=['app.py'],tests=['tests/test_app.py'],commands=[self.cmd]))+'\n'
        body+='\nFixture report with concrete behavior and limits.\n'
        (self.root/'.bangiao'/g.REPORTS[role]).write_text(body,encoding='utf-8')
    def through_coder(self):
        self.start();self.report('planner','SAN_SANG');g.check(self.root,'planner')
        (self.root/'app.py').write_text('value = 2\n',encoding='utf-8');self.report('coder','HOAN_THANH');g.check(self.root,'coder')
    def test_native_profiles(self):
        for role,model in self.models.items():
            value=tomllib.loads((HERE.parent/'agents'/(role+'.toml')).read_text(encoding='utf-8'))
            self.assertEqual(value['name'],role);self.assertEqual(value['model'],model);self.assertIn('developer_instructions',value)
    def test_protected_branches_write_nothing(self):
        for branch in ('main','master'):
            self.git('branch','-m',branch)
            with self.assertRaises(g.GateError):self.start()
            self.assertFalse((self.root/'.bangiao').exists())
    def test_detached_writes_nothing(self):
        self.git('checkout','--detach','HEAD')
        with self.assertRaises(g.GateError):self.start()
        self.assertFalse((self.root/'.bangiao').exists())
    def test_success_with_real_test_log(self):
        self.through_coder();self.assertEqual(g.run_test(self.root,self.cmd)['_exit'],0)
        self.report('tester','DAT');self.assertEqual(g.check(self.root,'tester')['next_role'],'reviewer')
        self.report('reviewer','CHOT');self.assertEqual(g.check(self.root,'reviewer')['status'],'CHOT')
    def test_questions_stop_before_coder(self):
        self.start();self.report('planner','CAN_LAM_RO');r=g.check(self.root,'planner');self.assertIsNone(r['next_role']);self.assertEqual(r['status'],'CAN_LAM_RO')
    def test_empty_questions_heading_does_not_stop(self):
        self.start();self.report('planner','SAN_SANG')
        with (self.root/'.bangiao/ke-hoach.md').open('a',encoding='utf-8') as f:f.write('CÂU HỎI CÒN BỎ NGỎ\nKhông.\n')
        self.assertEqual(g.check(self.root,'planner')['next_role'],'coder')
    def test_missing_empty_and_stale_reports(self):
        self.start()
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
        (self.root/'.bangiao/ke-hoach.md').write_text('',encoding='utf-8')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
        self.report('planner','SAN_SANG',run='old-run')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
        self.assertEqual(g.load(self.root)['next_role'],'planner')
    def test_cannot_skip_stage(self):
        self.start()
        with self.assertRaises(g.GateError):g.check(self.root,'coder')
    def test_failed_tests_still_reach_reviewer(self):
        self.cmd=['{python}','-c','raise SystemExit(1)'];self.through_coder();self.assertEqual(g.run_test(self.root,self.cmd)['_exit'],1)
        self.report('tester','KHONG_DAT');self.assertEqual(g.check(self.root,'tester')['next_role'],'reviewer')
        self.report('reviewer','CAN SUA');self.assertEqual(g.check(self.root,'reviewer')['status'],'CAN SUA')
    def test_failed_tests_never_chot(self):
        self.cmd=['{python}','-c','raise SystemExit(1)'];self.through_coder();g.run_test(self.root,self.cmd);self.report('tester','KHONG_DAT');g.check(self.root,'tester');self.report('reviewer','CHOT')
        with self.assertRaises(g.GateError):g.check(self.root,'reviewer')
        self.assertEqual(g.load(self.root)['status'],'CHAN')
    def test_no_faked_green_or_rerun_after_failure(self):
        self.through_coder();self.report('tester','DAT');r=g.check(self.root,'tester');self.assertTrue(r['violations']);self.assertEqual(r['checks']['tester'],'KHONG_DAT')
    def test_model_mismatch_does_not_advance(self):
        self.start();self.report('planner','SAN_SANG');p=self.root/'.bangiao/ke-hoach.md';p.write_text(p.read_text(encoding='utf-8').replace('gpt-6.1-sol','different-model'),encoding='utf-8')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
        self.assertEqual(g.load(self.root)['next_role'],'planner')
    def test_outside_scope_is_preserved_and_reviewed(self):
        self.start();self.report('planner','SAN_SANG');g.check(self.root,'planner');p=self.root/'unexpected.py';p.write_text('user must inspect this\n',encoding='utf-8');self.report('coder','HOAN_THANH');r=g.check(self.root,'coder');self.assertEqual(r['next_role'],'reviewer');self.assertEqual(r['violations'][0]['path'],'unexpected.py');self.assertTrue(p.exists())
    def test_tester_cannot_edit_product(self):
        self.through_coder();(self.root/'app.py').write_text('bad change\n',encoding='utf-8');self.report('tester','KHONG_DAT');r=g.check(self.root,'tester');self.assertTrue(any(v['path']=='app.py' for v in r['violations']))
    def test_dirty_baseline_not_reset_or_mixed_with_new_diff(self):
        (self.root/'app.py').write_text('prior user change\n',encoding='utf-8');self.start();self.report('planner','SAN_SANG');g.check(self.root,'planner');state=g.load(self.root);copy=self.root/'.bangiao/nen'/state['run_id']/'files/app.py';self.assertEqual(copy.read_text(encoding='utf-8'),'prior user change\n');(self.root/'app.py').write_text('new feature\n',encoding='utf-8');text=g.diff(self.root);self.assertIn('-prior user change',text);self.assertNotIn('-value = 1',text)
    def test_path_traversal_and_protected_data(self):
        for path in ('../outside.py','C:/outside.py','data/research.sqlite3','.codex/agents/coder.toml','.agents/skills/ship/SKILL.md'):
            with self.assertRaises(g.GateError):g.keypath(self.root,path)
    def test_only_four_old_reports_deleted(self):
        self.start();g.halt(self.root,'fixture stop');folder=self.root/'.bangiao';(folder/'keep.txt').write_text('keep',encoding='utf-8');self.report('planner','CAN_LAM_RO');self.start();self.assertTrue((folder/'keep.txt').exists());self.assertFalse((folder/'ke-hoach.md').exists())
    def test_active_run_cannot_be_overwritten(self):
        first=self.start()
        with self.assertRaises(g.GateError):self.start()
        self.assertEqual(g.load(self.root)['run_id'],first['run_id'])
    def test_branch_head_or_index_change_blocks(self):
        self.start();self.git('checkout','-b','feature/other');self.report('planner','SAN_SANG')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
    def test_model_or_permission_failure_can_halt_without_fallback(self):
        self.start();r=g.halt(self.root,'Selected model unavailable / permission denied');self.assertEqual(r['status'],'DUNG');self.assertIsNone(r['next_role'])
    def test_required_command_only_and_stop_after_failure(self):
        self.cmd=['{python}','-c','raise SystemExit(1)'];self.through_coder()
        with self.assertRaises(g.GateError):g.run_test(self.root,['{python}','-c','print(1)'])
        g.run_test(self.root,self.cmd)
        with self.assertRaises(g.GateError):g.run_test(self.root,self.cmd)
    def test_baseline_tamper_detected(self):
        self.through_coder();state=g.load(self.root);p=self.root/'.bangiao/nen'/state['run_id']/'files/app.py';p.write_text('tampered\n',encoding='utf-8')
        with self.assertRaises(g.GateError):g.check(self.root,'tester')

    def test_header_only_report_is_rejected(self):
        self.start();self.report('planner','SAN_SANG');p=self.root/'.bangiao/ke-hoach.md';p.write_text(p.read_text(encoding='utf-8').split('\n\n')[0]+'\n',encoding='utf-8')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
    def test_index_change_blocks_without_revert(self):
        self.start();(self.root/'app.py').write_text('staged change\n',encoding='utf-8');self.git('add','app.py');self.report('planner','SAN_SANG')
        with self.assertRaises(g.GateError):g.check(self.root,'planner')
        self.assertEqual((self.root/'app.py').read_text(encoding='utf-8'),'staged change\n')
    def test_protected_store_metadata_flags_changes_without_reading_payload(self):
        data=self.root/'data';data.mkdir();db=data/'research.sqlite3';db.write_bytes(b'fixture');self.through_coder();db.write_bytes(b'fixture has changed');self.report('tester','KHONG_DAT');r=g.check(self.root,'tester');self.assertTrue(any(v['path']=='data/research.sqlite3' for v in r['violations']))
    def test_modified_test_log_blocks_reviewer(self):
        self.through_coder();g.run_test(self.root,self.cmd);self.report('tester','DAT');g.check(self.root,'tester');state=g.load(self.root);(self.root/state['tests'][0]['log']).write_text('forged',encoding='utf-8');self.report('reviewer','CHOT')
        with self.assertRaises(g.GateError):g.check(self.root,'reviewer')

    def test_nested_handoff_edit_outside_role_is_detected(self):
        folder=self.root/'.bangiao/notes';folder.mkdir(parents=True);p=folder/'keep.txt';p.write_text('existing note',encoding='utf-8');self.start();self.report('planner','SAN_SANG');g.check(self.root,'planner');p.write_text('unexpected edit',encoding='utf-8');self.report('coder','HOAN_THANH');r=g.check(self.root,'coder');self.assertEqual(r['next_role'],'reviewer');self.assertTrue(any(v['path']=='.bangiao/notes/keep.txt' for v in r['violations']))


    def test_preflight_read_only_and_dynamic_dispatch(self):
        self.assertFalse((self.root/'.bangiao').exists())
        config=g.preflight(self.root)
        self.assertFalse((self.root/'.bangiao').exists())
        self.assertEqual(config['profiles']['coder']['config']['model'],self.models['coder'])
        self.start()
        payload=g.dispatch(self.root)
        self.assertEqual(payload['role'],'planner')
        self.assertEqual(payload['profile']['model'],config['profiles']['planner']['config']['model'])
        self.assertNotIn('developer_instructions',config['profiles']['planner']['config'])
        self.assertEqual(payload['run_id'],g.load(self.root)['run_id'])

    def test_profile_changes_stop_existing_run(self):
        self.start()
        path=self.root/'.codex/agents/coder.toml'
        path.write_text(path.read_text(encoding='utf-8')+'\n# changed during run\n',encoding='utf-8')
        with self.assertRaises(g.GateError):g.dispatch(self.root)
        self.assertEqual(g.load(self.root)['next_role'],'planner')

    def test_invalid_profile_cannot_clear_handoffs(self):
        handoff=self.root/'.bangiao';handoff.mkdir()
        report=handoff/'ke-hoach.md';report.write_text('keep old report',encoding='utf-8')
        (self.root/'.codex/agents/coder.toml').write_text('invalid = [',encoding='utf-8')
        with self.assertRaises(g.GateError):self.start()
        self.assertEqual(report.read_text(encoding='utf-8'),'keep old report')

    def test_model_is_read_from_repo_not_module_constant(self):
        path=self.root/'.codex/agents/planner.toml'
        path.write_text(path.read_text(encoding='utf-8').replace(self.models['planner'],'fixture-model'),encoding='utf-8')
        self.start()
        self.report('planner','CAN_LAM_RO')
        report=self.root/'.bangiao/ke-hoach.md'
        report.write_text(report.read_text(encoding='utf-8').replace(self.models['planner'],'fixture-model'),encoding='utf-8')
        self.assertEqual(g.dispatch(self.root)['profile']['model'],'fixture-model')
        self.assertEqual(g.check(self.root,'planner')['status'],'CAN_LAM_RO')

    def test_preflight_keeps_active_run_and_lock(self):
        self.start()
        before=(self.root/'.bangiao/luot-chay.json').read_bytes()
        with self.assertRaises(g.GateError):g.preflight(self.root)
        self.assertEqual((self.root/'.bangiao/luot-chay.json').read_bytes(),before)
        lock=self.root/'.bangiao/.ship.lock';lock.write_text('owned by another process',encoding='utf-8')
        with self.assertRaises(g.GateError):g.preflight(self.root)
        self.assertTrue(lock.exists())



    def test_missing_model_or_effort_has_no_default(self):
        path=self.root/'.codex/agents/coder.toml'
        original=path.read_text(encoding='utf-8')
        for field in ('model', 'model_reasoning_effort'):
            path.write_text('\n'.join(line for line in original.splitlines()
                                      if not line.startswith(field+' =')),encoding='utf-8')
            with self.assertRaises(g.GateError):g.preflight(self.root)
            self.assertFalse((self.root/'.bangiao').exists())
        path.write_text(original.replace('name = "coder"','name = "unknown"'),encoding='utf-8')
        with self.assertRaises(g.GateError):g.preflight(self.root)

    def test_legacy_active_state_is_preserved(self):
        self.start();state=g.load(self.root);state.pop('profile_hashes',None);g.save(self.root,state)
        before=(self.root/'.bangiao/luot-chay.json').read_bytes()
        with self.assertRaises(g.GateError):g.preflight(self.root)
        self.assertEqual(g.dispatch(self.root)['run_id'],state['run_id'])
        self.assertEqual((self.root/'.bangiao/luot-chay.json').read_bytes(),before)


if __name__=='__main__':unittest.main(verbosity=2)
