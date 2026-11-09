"""Controller authorization and evidence contracts using isolated local projects."""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = (Path(__file__).resolve().parents[1] / 'plugins' / 'auditagent-targhi' /
          'skills' / 'auditagent-targhi' / 'scripts' / 'auditagent.py')
spec = importlib.util.spec_from_file_location('auditagent_controller_under_test', SCRIPT)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'project'
        self.root.mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'app.py').write_text('value = 1\n')
        (self.root / 'README.md').write_text('Fixture project\n')
        self.ledger = controller.Ledger(self.root)
        self.call('init')
        finding = {'id': 'F1', 'title': 'Fixture defect', 'domain': 'correctness',
                   'impact': 'Incorrect fixture result', 'recommendation': 'Correct the result',
                   'verification': 'Run the fixture check', 'severity': 'medium',
                   'classification': 'confirmed', 'confidence': 'high',
                   'evidence': [{'path': 'src/app.py', 'detail': 'Fixture value is 1'}]}
        self.call('add_finding', self.input_file('finding.json', finding))
        self.plan = {'version': 1, 'summary': 'Repair fixture in reviewed phases',
                     'phases': [self.phase('P1'), self.phase('P2', ['P1'])]}
        self.load_plan()

    def phase(self, pid, dependencies=None):
        return {'id': pid, 'title': 'Repair ' + pid, 'objective': 'Correct fixture',
                'rollback': 'Restore previous fixture', 'allowed_paths': ['src/*'],
                'tasks': ['Update fixture'], 'acceptance': ['Fixture is correct'],
                'checks': ['unit'], 'finding_ids': ['F1'],
                'depends_on': dependencies or [], 'risks': [],
                'max_attempts': 2, 'max_minutes': 5}

    def input_file(self, name, value):
        path = self.base / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def call(self, method, *args):
        with self.ledger.lock():
            return getattr(self.ledger, method)(*args)

    def load_plan(self):
        self.plan_hash = self.call('plan', self.input_file('plan.json', self.plan))['plan_hash']

    def approve(self, phases=None, risks=None):
        return self.call('approve', phases or ['P1'], self.plan_hash,
                         'Explicit authorization from test fixture', risks or [])

    def start(self):
        self.approve()
        self.call('start', 'P1')

    def check(self, code=0):
        return self.call('check', 'P1', 'unit',
                         [sys.executable, '-c', 'raise SystemExit(%d)' % code], 10)

    def report(self, verdict='pass', **overrides):
        report = {'phase_id': 'P1', 'plan_hash': self.plan_hash,
                  'snapshot_hash': controller.digest(controller.snapshot(self.root)),
                  'reviewer': 'Separate verifier test fixture', 'independent': True,
                  'limitations': 'Synthetic local fixture only', 'verdict': verdict,
                  'acceptance': [{'criterion': 'Fixture is correct',
                                  'status': 'pass' if verdict == 'pass' else 'fail',
                                  'evidence': 'Independent fixture review evidence'}]}
        report.update(overrides)
        return self.input_file('report.json', report)

    def test_execution_requires_approval_and_never_launches_command(self):
        with mock.patch.object(controller.subprocess, 'run') as run:
            for method, args in [('start', ('P1',)),
                                 ('check', ('P1', 'unit', [sys.executable, '-c', 'pass'], 10)),
                                 ('handoff', ('P1',)),
                                 ('verify', ('P1', self.report()))]:
                with self.subTest(method=method), self.assertRaises(controller.Refused):
                    self.call(method, *args)
            run.assert_not_called()
        self.assertEqual(self.ledger.load()['phases']['P1']['status'], 'pending')

    def test_approval_requires_exact_plan_hash(self):
        with self.assertRaisesRegex(controller.Refused, 'exact displayed plan hash'):
            self.call('approve', ['P1'], '0' * 64, 'User approved fixture', [])
        self.assertEqual(self.ledger.load()['approvals'], {})

    def test_tampered_plan_is_rejected_on_load(self):
        state = self.ledger.load()
        state['plan']['summary'] = 'Unreviewed revision'
        controller.write_json(self.ledger.statefile, state)
        with self.assertRaisesRegex(controller.Refused, 'Plan changed outside controller'):
            self.call('start', 'P1')

    def test_project_drift_prevents_approval(self):
        (self.root / 'src' / 'app.py').write_text('value = 2\n')
        with self.assertRaisesRegex(controller.Refused, 'Project changed since plan'):
            self.approve()

    def test_project_drift_after_approval_prevents_start(self):
        self.approve()
        (self.root / 'README.md').write_text('Unreviewed user edit\n')
        with self.assertRaisesRegex(controller.Refused, 'Project drift'):
            self.call('start', 'P1')
        self.assertIsNone(self.ledger.load()['active'])

    def test_batches_must_be_consecutive_and_execute_in_order(self):
        for ids in [['P2'], ['P2', 'P1'], ['P1', 'P1']]:
            with self.subTest(ids=ids), self.assertRaises(controller.Refused):
                self.approve(ids)
        self.approve(['P1', 'P2'])
        with self.assertRaisesRegex(controller.Refused, 'Earlier phase'):
            self.call('start', 'P2')
        self.call('start', 'P1')
        self.check()
        self.call('verify', 'P1', self.report())
        self.assertEqual(self.call('start', 'P2')['phase']['id'], 'P2')

    def test_narrower_approval_replaces_previous_batch(self):
        self.approve(['P1', 'P2'])
        self.approve(['P1'])
        state = self.ledger.load()
        self.assertEqual(set(state['approvals']), {'P1'})
        self.assertEqual(state['phases']['P2']['status'], 'pending')

    def test_success_records_check_and_independent_verification(self):
        self.start()
        (self.root / 'src' / 'app.py').write_text('value = 2\n')
        result = self.check()
        self.assertEqual(result['check']['exit_code'], 0)
        self.assertFalse(result['check']['modified_project'])
        outcome = self.call('verify', 'P1', self.report())
        self.assertEqual(outcome['status'], 'verified')
        state = self.ledger.load()
        self.assertIsNone(state['active'])
        self.assertEqual(state['phases']['P1']['changed_paths'], ['src/app.py'])
        self.assertEqual(state['phases']['P1']['checks'][0]['snapshot_hash'],
                         controller.digest(controller.snapshot(self.root)))
        self.assertTrue(state['phases']['P1']['reviews'][0]['independent'])
        self.assertEqual(self.call('status', True)['changed_paths'], [])
        self.assertTrue((self.ledger.directory / 'P1-verification.json').exists())

    def test_verification_requires_independent_reviewer(self):
        self.start()
        self.check()
        with self.assertRaisesRegex(controller.Refused, 'separate reviewer'):
            self.call('verify', 'P1', self.report(independent=False))
        self.assertEqual(self.ledger.load()['phases']['P1']['attempts'], 0)

    def test_stale_verifier_report_is_rejected(self):
        self.start()
        self.check()
        path = self.report()
        (self.root / 'src' / 'app.py').write_text('value = 3\n')
        with self.assertRaisesRegex(controller.Refused, 'report is stale'):
            self.call('verify', 'P1', path)

    def test_stale_check_is_rejected_even_with_current_report(self):
        self.start()
        self.check()
        (self.root / 'src' / 'app.py').write_text('value = 3\n')
        with self.assertRaisesRegex(controller.Refused, 'Missing, failed or stale check'):
            self.call('verify', 'P1', self.report())
        self.check()
        self.assertEqual(self.call('verify', 'P1', self.report())['status'], 'verified')

    def test_pass_needs_all_checks_and_latest_result_must_pass(self):
        self.start()
        with self.assertRaisesRegex(controller.Refused, 'Missing, failed or stale check'):
            self.call('verify', 'P1', self.report())
        self.check()
        self.check(3)
        with self.assertRaisesRegex(controller.Refused, 'Missing, failed or stale check'):
            self.call('verify', 'P1', self.report())

    def test_out_of_scope_edit_blocks_check_before_launch_and_verification(self):
        self.start()
        (self.root / 'README.md').write_text('Outside scope\n')
        with mock.patch.object(controller.subprocess, 'run') as run:
            with self.assertRaisesRegex(controller.Refused, 'Out-of-scope changes: README.md'):
                self.check()
            run.assert_not_called()
        with self.assertRaisesRegex(controller.Refused, 'Out-of-scope changes'):
            self.call('verify', 'P1', self.report())

    def test_deletion_requires_explicit_plan_risk_and_risk_approval(self):
        self.start()
        (self.root / 'src' / 'app.py').unlink()
        with self.assertRaisesRegex(controller.Refused, 'File deletion requires'):
            self.check()
        self.call('stop', 'Need explicit deletion approval')
        (self.root / 'src' / 'app.py').write_text('value = 1\n')
        self.plan['phases'][0]['risks'] = ['delete_files']
        self.load_plan()
        with self.assertRaisesRegex(controller.Refused, 'explicitly include phase risk'):
            self.approve()
        self.approve(risks=['delete_files'])
        self.call('start', 'P1')
        (self.root / 'src' / 'app.py').unlink()
        self.check()
        self.assertEqual(self.call('verify', 'P1', self.report())['status'], 'verified')

    def test_retry_exhaustion_revokes_entire_batch(self):
        self.approve(['P1', 'P2'])
        self.call('start', 'P1')
        first = self.call('verify', 'P1', self.report('fail'))
        self.assertEqual((first['status'], first['attempts']), ('running', 1))
        second = self.call('verify', 'P1', self.report('fail'))
        self.assertEqual((second['status'], second['attempts']), ('blocked', 2))
        state = self.ledger.load()
        self.assertIsNone(state['active'])
        self.assertEqual(state['approvals'], {})
        self.assertEqual(state['phases']['P2']['status'], 'pending')
        with self.assertRaises(controller.Refused):
            self.call('start', 'P1')

    def test_stop_revokes_active_and_future_approvals(self):
        self.approve(['P1', 'P2'])
        self.call('start', 'P1')
        self.call('stop', 'User requested pause')
        state = self.ledger.load()
        self.assertEqual(state['approvals'], {})
        self.assertEqual(state['phases']['P1']['status'], 'blocked')
        self.assertEqual(state['phases']['P2']['status'], 'pending')
        with self.assertRaises(controller.Refused):
            self.call('start', 'P2')

    def test_copied_ledger_cannot_reuse_root_bound_approvals(self):
        self.approve()
        other = self.base / 'copied-project'
        shutil.copytree(self.root, other)
        with self.assertRaisesRegex(controller.Refused, 'another root'):
            controller.Ledger(other).load()

    def test_lock_prevents_concurrent_cli_and_preserves_owner_lock(self):
        with self.ledger.lock():
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = controller.main(['--project', str(self.root), 'status'])
            self.assertEqual(code, 2)
            self.assertIn('owns the ledger lock', json.loads(error.getvalue())['error'])
            self.assertTrue((self.ledger.directory / 'LOCK').exists())
        self.assertFalse((self.ledger.directory / 'LOCK').exists())

    def test_lock_releases_after_exception(self):
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with self.ledger.lock():
                raise RuntimeError('fixture')
        with self.ledger.lock():
            self.assertTrue((self.ledger.directory / 'LOCK').exists())

    def test_invalid_input_is_reported_without_state_change(self):
        invalid = self.base / 'invalid.json'
        invalid.write_text('{broken json')
        before = self.ledger.statefile.read_bytes()
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = controller.main(['--project', str(self.root), 'plan', str(invalid)])
        self.assertEqual(code, 2)
        self.assertIn('error', json.loads(error.getvalue()))
        self.assertEqual(self.ledger.statefile.read_bytes(), before)
        self.assertFalse((self.ledger.directory / 'LOCK').exists())

    def test_invalid_scope_and_plan_fields_are_rejected(self):
        for path in ['../outside', '/tmp/outside', '.auditagent/state.json',
                     '.git/config', '**/*', 'src/../README.md', 'src\\app.py']:
            with self.subTest(path=path), self.assertRaises(controller.Refused):
                controller.safe_rel(path, glob=True)
        for field, value in [('max_attempts', True), ('max_minutes', 0),
                             ('depends_on', ['P2']), ('finding_ids', ['missing']),
                             ('allowed_paths', ['node_modules/*'])]:
            plan = copy.deepcopy(self.plan)
            plan['phases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(controller.Refused):
                controller.validate_plan(plan, self.ledger.load()['findings'])

    def test_malformed_verifier_rows_return_cli_error_and_preserve_state(self):
        self.start()
        self.check()
        for row in [None, 'not an object', 7, []]:
            with self.subTest(row=row):
                report = self.report(acceptance=[row])
                before = self.ledger.statefile.read_bytes()
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    code = controller.main(['--project', str(self.root), 'verify',
                                            'P1', str(report)])
                self.assertEqual(code, 2)
                self.assertIn('acceptance criterion', json.loads(error.getvalue())['error'])
                self.assertEqual(self.ledger.statefile.read_bytes(), before)
                self.assertFalse((self.ledger.directory / 'LOCK').exists())

    def test_checkpoint_note_survives_scan_and_subsequent_state_save(self):
        note = 'Continue from the reviewed fixture; preserve user edits.'
        self.call('note', note)
        self.call('scan')
        self.approve()
        self.assertEqual(self.ledger.load()['resume_note'], note)
        summary = (self.ledger.directory / 'SUMMARY.md').read_text()
        self.assertIn('## Current handoff note', summary)
        self.assertEqual(summary.count(note), 1)

    def test_verified_phase_content_is_immutable_during_plan_revision(self):
        self.start()
        self.check()
        self.call('verify', 'P1', self.report())
        before = self.ledger.statefile.read_bytes()
        revised = copy.deepcopy(self.plan)
        revised['phases'][0]['objective'] = 'Unreviewed replacement objective'
        with self.assertRaisesRegex(controller.Refused, 'Verified phases are immutable'):
            self.call('plan', self.input_file('revised.json', revised))
        self.assertEqual(self.ledger.statefile.read_bytes(), before)
        revised = copy.deepcopy(self.plan)
        revised['phases'][1]['objective'] = 'Refine unfinished phase only'
        self.call('plan', self.input_file('revised.json', revised))
        self.assertEqual(self.ledger.load()['phases']['P1']['status'], 'verified')

    def test_verified_prefix_cannot_be_removed_reordered_or_preceded(self):
        self.start()
        self.check()
        self.call('verify', 'P1', self.report())
        before = self.ledger.statefile.read_bytes()
        removed = copy.deepcopy(self.plan)
        removed['phases'] = [self.phase('P2')]
        reordered = copy.deepcopy(self.plan)
        reordered['phases'] = [self.phase('P2'), self.phase('P1')]
        prepended = copy.deepcopy(self.plan)
        prepended['phases'].insert(0, self.phase('P0'))
        for revised in [removed, reordered, prepended]:
            with self.subTest(ids=[p['id'] for p in revised['phases']]):
                with self.assertRaisesRegex(controller.Refused, 'original leading order'):
                    self.call('plan', self.input_file('revised.json', revised))
                self.assertEqual(self.ledger.statefile.read_bytes(), before)

    def test_check_that_modifies_source_requires_unchanged_source_rerun(self):
        self.start()
        command = ('from pathlib import Path; p = Path("src/app.py"); '
                   'assert p.read_text() == "value = 1\\n"; '
                   'p.write_text("value = 2\\n")')
        recorded = self.call('check', 'P1', 'unit', [sys.executable, '-c', command], 10)
        self.assertEqual(recorded['check']['exit_code'], 0)
        self.assertTrue(recorded['check']['modified_project'])
        self.assertEqual(recorded['check']['snapshot_hash'],
                         controller.digest(controller.snapshot(self.root)))
        with self.assertRaisesRegex(controller.Refused, 'Missing, failed or stale check'):
            self.call('verify', 'P1', self.report())
        self.assertEqual(self.ledger.load()['phases']['P1']['status'], 'running')
        command = ('from pathlib import Path; '
                   'assert Path("src/app.py").read_text() == "value = 2\\n"')
        rerun = self.call('check', 'P1', 'unit', [sys.executable, '-c', command], 10)
        self.assertEqual(rerun['check']['exit_code'], 0)
        self.assertFalse(rerun['check']['modified_project'])
        self.assertEqual(self.call('verify', 'P1', self.report())['status'], 'verified')

    def test_check_outside_scope_blocks_and_revokes_batch_immediately(self):
        self.approve(['P1', 'P2'])
        self.call('start', 'P1')
        command = ('from pathlib import Path; '
                   'Path("README.md").write_text("Command edited outside approved scope")')
        with self.assertRaisesRegex(controller.Refused, 'Out-of-scope changes: README.md'):
            self.call('check', 'P1', 'unit', [sys.executable, '-c', command], 10)
        state = self.ledger.load()
        self.assertEqual((self.root / 'README.md').read_text(),
                         'Command edited outside approved scope')
        self.assertIsNone(state['active'])
        self.assertEqual(state['approvals'], {})
        self.assertEqual(state['phases']['P1']['status'], 'blocked')
        self.assertEqual(state['phases']['P2']['status'], 'pending')
        self.assertEqual(state['phases']['P1']['checks'][-1]['exit_code'], 0)
        self.assertTrue(state['phases']['P1']['checks'][-1]['modified_project'])
        self.assertEqual(state['events'][-1]['event'],
                         'check_scope_violation_approvals_revoked')
        with self.assertRaisesRegex(controller.Refused, 'Phase is not running'):
            self.call('verify', 'P1', self.report())
        with self.assertRaisesRegex(controller.Refused, 'Explicit approval required'):
            self.call('start', 'P2')

    def test_expired_deadline_prevents_command_execution(self):
        self.start()
        state = self.ledger.load()
        state['phases']['P1']['deadline'] = 0
        controller.write_json(self.ledger.statefile, state)
        with mock.patch.object(controller.subprocess, 'run') as run:
            with self.assertRaisesRegex(controller.Refused, 'time budget reached'):
                self.check()
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
