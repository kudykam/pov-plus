"""TMDb pairing failures must explain the next step without exposing tokens."""
import ast
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


class TMDbPairingTests(unittest.TestCase):
    def service(self, token='', response=None):
        self.messages = []
        self.http = Mock()
        self.connection = self.http.connection_from_url.return_value
        self.connection.request.return_value = response
        settings = {'tmdb_read_token': token}
        tree = ast.parse((ROOT / 'plugin.video.povplus/resources/lib/modules/myservices.py').read_text())
        tree.body = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TMDbList']
        namespace = {'get_setting': settings.get, 'http': self.http,
                     'kodi_utils': types.SimpleNamespace(dialog=lambda: types.SimpleNamespace(
                         ok=lambda *args: self.messages.append(args)))}
        exec(compile(tree, 'TMDbList', 'exec'), namespace)
        return namespace['TMDbList']()

    def test_missing_read_token_explains_setup_without_network(self):
        service = self.service()
        self.assertFalse(service.set())
        self.http.connection_from_url.assert_not_called()
        self.assertIn('Metadata', self.messages[0][1])
        self.assertIn('API Read Access Token', self.messages[0][1])

    def test_rejected_token_is_visible_and_never_echoed(self):
        response = Mock(status=401)
        response.json.return_value = {'success': False}
        service = self.service('private-test-token', response)
        self.assertFalse(service.set())
        self.assertIn('HTTP 401', self.messages[0][1])
        self.assertNotIn('private-test-token', str(self.messages))

    def test_malformed_response_or_network_failure_is_visible(self):
        for response in (Mock(status=200), Mock(status=200)):
            with self.subTest(response=response):
                response.json.side_effect = ValueError('non-JSON response')
                service = self.service('private-test-token', response)
                self.assertFalse(service.set())
                self.assertIn('připojení', self.messages[0][1])
        service = self.service('private-test-token')
        self.connection.request.side_effect = OSError('network failed')
        self.assertFalse(service.set())
        self.assertIn('připojení', self.messages[0][1])


if __name__ == '__main__':
    unittest.main()
