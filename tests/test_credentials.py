import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin.video.povplus/resources/lib'))
from modules.povplus_credentials import MAX_BYTES, parse_tmdb_token, import_tmdb_token

# Synthetic text only; no real credential is used in tests.
TOKEN = 'synthetic.header.synthetic_payload.synthetic_signature'


class CredentialTests(unittest.TestCase):
    def test_notepad_encodings_and_optional_bearer_prefix(self):
        for raw in (TOKEN, ('\ufeff' + TOKEN + '\r\n').encode('utf-8'),
                    (TOKEN + '\r\n').encode('utf-16'), 'Bearer ' + TOKEN):
            with self.subTest(raw_type=type(raw).__name__):
                self.assertEqual(parse_tmdb_token(raw), TOKEN)

    def test_invalid_file_never_includes_its_contents_in_error(self):
        for raw in ('', 'a' * 32, '"' + TOKEN + '"', TOKEN + '\n' + TOKEN,
                    b'\xff', 'x' * (MAX_BYTES + 1)):
            with self.subTest(size=len(raw)):
                with self.assertRaises(ValueError) as ctx:
                    parse_tmdb_token(raw)
                self.assertNotIn(TOKEN, str(ctx.exception))

    def fake_kodi(self, path='smb://server/share/tmdb-token.txt', raw=None):
        ku = types.ModuleType('modules.kodi_utils')
        ku.hide_busy_dialog = Mock()
        self.dialog = Mock()
        self.dialog.browseSingle.return_value = path
        ku.dialog = lambda: self.dialog
        class File(io.BytesIO):
            def readBytes(self, size): return self.read(size)
        ku.open_file = Mock(side_effect=lambda path: File(raw if raw is not None else TOKEN.encode()))
        ku.set_setting = Mock()
        ku.clear_property = Mock()
        ku.make_settings_dict = Mock()
        return ku

    def test_cancel_preserves_existing_settings(self):
        ku = self.fake_kodi(path='')
        with patch.dict(sys.modules, {'modules.kodi_utils': ku}), patch('modules.kodi_utils', ku, create=True):
            self.assertFalse(import_tmdb_token())
        ku.open_file.assert_not_called()
        ku.set_setting.assert_not_called()

    def test_import_uses_selected_vfs_file_and_keeps_token_out_of_ui(self):
        ku = self.fake_kodi()
        with patch.dict(sys.modules, {'modules.kodi_utils': ku}), patch('modules.kodi_utils', ku, create=True):
            self.assertTrue(import_tmdb_token())
        ku.open_file.assert_called_once_with('smb://server/share/tmdb-token.txt')
        ku.set_setting.assert_called_once_with('tmdb_read_token', TOKEN)
        ku.clear_property.assert_called_once_with('povplus_settings')
        ku.make_settings_dict.assert_called_once()
        self.assertNotIn(TOKEN, str(self.dialog.mock_calls))

    def test_bad_or_unreadable_file_does_not_replace_token(self):
        for unreadable in (False, True):
            ku = self.fake_kodi(raw=b'not a token')
            if unreadable: ku.open_file.side_effect = OSError('private path details')
            with patch.dict(sys.modules, {'modules.kodi_utils': ku}), patch('modules.kodi_utils', ku, create=True):
                self.assertFalse(import_tmdb_token())
            ku.set_setting.assert_not_called()
            self.assertNotIn('private path details', str(self.dialog.mock_calls))


if __name__ == '__main__':
    unittest.main()
