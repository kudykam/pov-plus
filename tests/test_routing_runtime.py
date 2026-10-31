"""Exercise the real URL helpers and router together without requiring Kodi."""
import ast
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'plugin.video.povplus/resources/lib'


def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(tree, str(path), 'exec'), namespace)
    return namespace


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.helpers = functions(LIB / 'modules/kodi_utils.py',
            {'build_url', 'parsed_query', 'skin_location'},
            {'urlencode': urlencode, 'urlparse': urlparse, 'parse_qsl': parse_qsl})

    def test_real_menu_urls_reach_povplus_router(self):
        called = []
        routes = {mode: lambda p, mode=mode: called.append((mode, p))
                  for mode in ('povplus_catalog', 'play_media', 'open_settings')}
        router = functions(LIB / 'modules/entry.py', {'routing'}, {
            'kodi_utils': types.SimpleNamespace(parsed_query=self.helpers['parsed_query']),
            'POVPLUS_ROUTES': routes})['routing']
        menu = {}
        exec((LIB / 'modules/menu_lists.py').read_text(), menu)
        item = next(i for i in menu['root_list'] if i.get('mode') == 'povplus_catalog')
        for params in (item, {'mode': 'play_media', 'tmdb_id': '42'},
                       {'mode': 'open_settings', 'query': 'Český výběr & účty'}):
            with self.subTest(mode=params['mode']):
                url = self.helpers['build_url'](params)
                parsed = urlparse(url)
                # Kodi chooses the add-on from the URL BEFORE invoking routing.
                self.assertEqual(parsed.netloc, 'plugin.video.povplus')
                router(types.SimpleNamespace(argv=[url.split('?')[0], '1', '?' + parsed.query]))
                self.assertEqual(called[-1], (params['mode'], {k: str(v) for k, v in params.items()}))

    def test_windows_use_installed_fork_assets(self):
        path = self.helpers['skin_location']()
        self.assertEqual(path, 'special://home/addons/plugin.video.povplus')
        self.assertTrue((ROOT / path.removeprefix('special://home/addons/') /
                         'resources/skins/Default').is_dir())


if __name__ == '__main__':
    unittest.main()
