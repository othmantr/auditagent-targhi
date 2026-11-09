"""Meaningful installation safety and repeatability tests; no host account changes."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('auditagent_installer', ROOT / 'installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # macOS exposes temporary directories through /var -> /private/var.
        # Use the canonical fixture root; retain explicit symlink rejection tests.
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.target = self.base / 'target'
        self.target.mkdir()
        skill = self.source / 'plugins/auditagent-targhi/skills/auditagent-targhi'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: auditagent-targhi\ndescription: Audit.\n---\nAudit.')
        (skill / 'scripts').mkdir()
        (skill / 'scripts/auditagent.py').write_text('print("ok")\n')
        for host, path, suffix in [('codex','adapters/codex/agents','.toml'), ('claude','plugins/auditagent-targhi/agents','.md')]:
            folder = self.source / path
            folder.mkdir(parents=True)
            (folder / ('auditagent-security' + suffix)).write_text(host)

    def run_install(self, hosts=None, **kwargs):
        return installer.install(self.source, self.target, hosts or ['codex','claude'], **kwargs)

    def test_install_both_and_repeat_then_uninstall(self):
        self.run_install()
        codex = self.target / '.agents/skills/auditagent-targhi/SKILL.md'
        claude = self.target / '.claude/skills/auditagent-targhi/SKILL.md'
        self.assertTrue(codex.is_file())
        self.assertTrue(claude.is_file())
        self.assertTrue((self.target / '.codex/agents/auditagent-security.toml').is_file())
        again = self.run_install()
        self.assertTrue(all(c['action']=='unchanged' for c in again['changes']))
        self.run_install(uninstall=True)
        self.assertFalse(codex.exists())
        self.assertFalse(claude.exists())
        self.assertFalse(installer.manifest_path(self.target,'codex').exists())
        self.assertFalse((self.target / '.auditagent-targhi-install.lock').exists())

    def test_preflight_all_hosts_refuses_unowned_without_partial_install(self):
        existing = self.target / '.claude/agents/auditagent-security.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('my own agent')
        with self.assertRaises(installer.InstallError):
            self.run_install()
        self.assertEqual(existing.read_text(), 'my own agent')
        self.assertFalse((self.target / '.agents').exists())

    def test_refuses_even_identical_unowned_file(self):
        existing = self.target / '.codex/agents/auditagent-security.toml'
        existing.parent.mkdir(parents=True)
        existing.write_text('codex')
        with self.assertRaises(installer.InstallError):
            self.run_install(['codex'])

    def test_modified_owned_file_blocks_update_and_uninstall(self):
        self.run_install(['codex'])
        path = self.target / '.agents/skills/auditagent-targhi/SKILL.md'
        path.write_text('local customization')
        for kwargs in [{}, {'uninstall':True}]:
            with self.assertRaises(installer.InstallError):
                self.run_install(['codex'], **kwargs)
        self.assertEqual(path.read_text(), 'local customization')

    def test_update_replaces_unchanged_owned_files_removes_obsolete(self):
        self.run_install(['codex'])
        source = self.source / 'plugins/auditagent-targhi/skills/auditagent-targhi'
        (source / 'SKILL.md').write_text('updated')
        (source / 'scripts/auditagent.py').unlink()
        self.run_install(['codex'])
        self.assertEqual((self.target / '.agents/skills/auditagent-targhi/SKILL.md').read_text(), 'updated')
        self.assertFalse((self.target / '.agents/skills/auditagent-targhi/scripts/auditagent.py').exists())

    def test_symlink_destination_and_ancestor_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.target / '.agents').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            self.run_install(['codex'])
        self.assertEqual(list(outside.iterdir()), [])

    def test_dry_run_is_read_only(self):
        result = self.run_install(dry_run=True)
        self.assertTrue(result['dry_run'])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_uninstall_preserves_unknown_files_and_other_host(self):
        self.run_install()
        custom = self.target / '.agents/skills/auditagent-targhi/custom.txt'
        custom.write_text('preserve')
        self.run_install(['codex'], uninstall=True)
        self.assertEqual(custom.read_text(), 'preserve')
        self.assertTrue((self.target / '.claude/skills/auditagent-targhi/SKILL.md').exists())

    def test_manifest_cannot_delete_arbitrary_file(self):
        self.run_install(['codex'])
        victim = self.target / 'important.txt'
        victim.write_text('do not delete')
        meta = installer.manifest_path(self.target,'codex')
        data = json.loads(meta.read_text())
        data['files']['important.txt'] = installer.digest(victim.read_bytes())
        meta.write_text(json.dumps(data))
        with self.assertRaises(installer.InstallError):
            self.run_install(['codex'],uninstall=True)
        self.assertTrue(victim.exists())

    def test_lock_blocks_concurrent_installer(self):
        (self.target / '.auditagent-targhi-install.lock').write_text('busy')
        with self.assertRaises(installer.InstallError):
            self.run_install(['codex'])
        self.assertFalse((self.target / '.agents').exists())

    def test_reloads_ownership_under_lock_after_intervening_install(self):
        from contextlib import contextmanager
        self.run_install(['codex'])
        extra_relative = '.agents/skills/auditagent-targhi/obsolete.txt'
        extra = self.target / extra_relative
        original_lock = installer.installation_lock
        @contextmanager
        def concurrent_install_before_lock(root):
            # A cooperating installer completed after our first preflight.
            extra.write_text('previous package version')
            meta = installer.manifest_path(root, 'codex')
            doc = json.loads(meta.read_text())
            doc['files'][extra_relative] = installer.digest(extra.read_bytes())
            meta.write_text(json.dumps(doc))
            with original_lock(root):
                yield
        with patch.object(installer, 'installation_lock', concurrent_install_before_lock):
            result = self.run_install(['codex'])
        self.assertFalse(extra.exists())
        self.assertIn({'host':'codex','action':'remove','path':extra_relative}, result['changes'])

    def test_best_effort_rollback_restores_written_files(self):
        original = installer.atomic_write
        calls = 0
        def injected_failure(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('simulated disk error')
            return original(path, data)
        with patch.object(installer, 'atomic_write', side_effect=injected_failure):
            with self.assertRaises(OSError):
                self.run_install(['codex'])
        self.assertFalse((self.target / '.codex/agents/auditagent-security.toml').exists())
        self.assertFalse((self.target / '.auditagent-targhi-install.lock').exists())

    def test_native_definitions_are_valid_toml_and_claude_read_only(self):
        import tomllib
        for path in (ROOT / 'adapters/codex/agents').glob('*.toml'):
            doc = tomllib.loads(path.read_text())
            self.assertEqual(set(doc), {'name','description','developer_instructions'})
            self.assertIn('Do not edit',doc['developer_instructions'])
        for path in (ROOT / 'plugins/auditagent-targhi/agents').glob('*.md'):
            text = path.read_text()
            self.assertIn('tools: Read, Grep, Glob\n',text)
            self.assertNotIn('Bash',text.split('---')[1])

if __name__ == '__main__':
    unittest.main()
