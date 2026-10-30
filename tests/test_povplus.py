import ast
import importlib.util
import json
import math
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'plugin.video.povplus/resources/lib'
sys.path.insert(0,str(LIB))
from modules.povplus_policy import best_stream,evaluate,prerelease,stars,meets_rating,strict_results
from modules.povplus_csfd import Client,Unavailable,parse_movie,search_candidates,film_id
from modules.povplus_store import Store


def stream(name='Film.2026.2160p.WEB-DL.DV.Atmos',size=20,quality='4K'):
    return {'name':name,'size':size,'quality':quality,'url':'https://private.invalid/secret'}


def page(rating='73%',imdb='tt1234567'):
    return '''<html><div class="film-header-name"><h1>Zkušební film</h1><span>2026</span></div>
    <script type="application/ld+json">{"@type":"Movie","name":"Zkušební film","dateCreated":"2026"}</script>
    <div class="film-rating-average">%s</div><a href="https://www.imdb.com/title/%s/">IMDb</a>
    <div class="genres">Drama / Thriller</div><article class="article-comment"><a class="user-title">Autor</a><div class="comment">Krátká testovací recenze.</div></article></html>''' % (rating,imdb)


class PolicyTests(unittest.TestCase):
    def test_cam_and_ts_rejected_even_if_label_claims_4k(self):
        for marker in ['TS','HDCAM','TELESYNC','HDTC','DVDSCR','TC','HQCAM','CAM']:
            with self.subTest(marker=marker):
                self.assertFalse(evaluate(stream('Film.2026.2160p.'+marker),7200)['eligible'])

    def test_real_title_cam_is_not_a_camera_rip(self):
        self.assertFalse(prerelease(stream('Cam.2018.1080p.WEB-DL',quality='1080p')))
        self.assertTrue(prerelease(stream('Cam.2018.1080p.HDCAM',quality='1080p')))

    def test_unknown_and_nonfinite_values_cannot_pass(self):
        for size,duration in [(None,7200),(0,7200),(-1,7200),(float('nan'),7200),(20,None),(20,0),(20,float('inf'))]:
            self.assertFalse(evaluate(stream(size=size),duration)['eligible'])
        self.assertFalse(evaluate(stream(),7200,budget_mbps='nan')['eligible'])

    def test_gib_and_exact_bitrate_boundary(self):
        size=40*1000000*7200/8/1073741824
        self.assertTrue(evaluate(stream(size=size),7200)['eligible'])
        self.assertFalse(evaluate(stream(size=size+0.00001),7200)['eligible'])
        self.assertAlmostEqual(evaluate(stream(size=20),7200)['averageMbps'],23.8609294222)

    def test_best_quality_and_safe_summary(self):
        best=best_stream([stream(size=60),stream(size=20),stream('Film.2026.1080p.WEB',10,'1080p')],7200)
        self.assertEqual(best['resolution'],2160)
        self.assertEqual(best['hdr'],'Dolby Vision')
        self.assertNotIn('secret',json.dumps(best))

    def test_rating_threshold_never_uses_unknown_or_imdb(self):
        self.assertFalse(meets_rating(None,70))
        self.assertFalse(meets_rating(69,70))
        self.assertTrue(meets_rating(70,70))
        self.assertTrue(meets_rating(None,0))
        self.assertEqual(stars(None),'ČSFD —')
        self.assertEqual(stars(100),'★★★★★ ČSFD 100%')
        self.assertIn('ČSFD 73%',stars(73))


class CsfdTests(unittest.TestCase):
    def test_parse_rating_exact_imdb_review_and_genres(self):
        d=parse_movie(page(),'123')
        self.assertEqual(d['rating'],73)
        self.assertEqual(d['imdbIds'],['tt1234567'])
        self.assertEqual(d['reviews'][0]['source'],'ČSFD')
        self.assertEqual(d['year'],2026)
        self.assertEqual(d['genres'],['Drama','Thriller'])

    def test_siky_349_page_fields_origin_and_review_content_attribute(self):
        html='<div class="film-header-name"><h1>Zkušební film</h1></div><div class="origin"><span>2026</span>, 120 min</div><div class="rating-average">81%</div><article class="article"><a class="user-title-name">Testovací autor</a><div data-review-content>Vlastní krátká testovací recenze.<span class="review-date">datum</span></div></article>'
        data=parse_movie(html,'123')
        self.assertEqual(data['rating'],81)
        self.assertEqual(data['year'],2026)
        self.assertEqual(data['reviews'][0]['author'],'Testovací autor')
        self.assertEqual(data['reviews'][0]['text'],'Vlastní krátká testovací recenze.')

    def test_block_page_is_not_treated_as_film_or_zero_rating(self):
        with self.assertRaises(Unavailable):parse_movie("Making sure you're not a bot!",'1')
        self.assertIsNone(parse_movie(page('bez hodnocení'),'1')['rating'])
        self.assertIsNone(parse_movie(page('173%'),'1')['rating'])

    def test_search_and_identity(self):
        html='<article><a class="film-title-name" href="/film/123-film/">Zkušební film</a><div class="film-title-info"><span class="info">(2026)</span></div></article>'
        c=search_candidates(html);self.assertEqual(c[0]['year'],2026)
        fetch=lambda url,as_json=False:html if 'hledat' in url else page()
        result=Client(fetch=fetch).lookup({'title':'Zkušební film','year':2026,'imdb_id':'tt1234567'})
        self.assertEqual(result['matchedBy'],'imdb')
        with self.assertRaises(Unavailable):Client(fetch=fetch).lookup({'title':'Zkušební film','year':2026,'imdb_id':'tt9999999'})

    def test_ambiguous_or_wrong_year_never_select_first_result(self):
        def fetch(url,as_json=False):
            return {'movies':[{'id':1,'title':'Film','year':2026},{'id':2,'title':'Film','year':2026}]}
        with self.assertRaises(Unavailable):Client('http://localhost:3000',fetch).lookup({'title':'Film','year':2026})
        with self.assertRaises(Unavailable):Client('http://localhost:3000',fetch).lookup({'title':'Film','year':2025})

    def test_node_api_documents_are_normalized_and_not_misidentified(self):
        def fetch(url,as_json=False):
            return {'movies':[{'id':123,'title':'Film','year':2026}]} if '/search/' in url else {'id':123,'title':'Film','year':2026,'rating':74}
        d=Client('http://localhost:3000',fetch).lookup({'title':'Film','year':2026})
        self.assertEqual(d['rating'],74)
        self.assertEqual(d['source'],'ČSFD')
        for url in ['http://user:secret@host/','javascript:bad','https://host/?token=secret']:
            with self.assertRaises(Unavailable):Client(url)
        self.assertIsNone(film_id('https://evil.example/film/123/'))


class StorageTests(unittest.TestCase):
    def test_expiration_and_namespaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'povplus.db');s.put('csfd:1',{'rating':70},60)
            self.assertEqual(s.get('csfd:1')['rating'],70)
            self.assertIsNone(s.get('quality:1'))
            s.put('csfd:1',{},-1);self.assertIsNone(s.get('csfd:1'))


class PlaybackBoundaryTests(unittest.TestCase):
    @staticmethod
    def source_class(settings):
        # Compile actual modified methods without importing Kodi or providers.
        tree=ast.parse((LIB/'modules/sources.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Sources')
        names={'povplus_restrict','play_source','_process_post_results','_process_ignore_filters'}
        body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names]
        mod=ast.Module(body=[ast.ClassDef(name='Boundary',bases=[],keywords=[],body=body,decorator_list=[])],type_ignores=[])
        env={'strict_results':strict_results,'get_setting':lambda k,d=None:settings.get(k,d),'notification':lambda *a:None}
        exec(compile(ast.fix_missing_locations(mod),'<actual Sources boundary>','exec'),env)
        obj=env['Boundary']();obj.meta={'duration':7200};obj.autoplay=False;obj.background=False;obj.ignore_results_filter=True
        obj.orig_results=[stream('Film.2026.4K.HDCAM')]
        obj.results_processor=types.SimpleNamespace(sort_results=lambda r:r,sort_first=lambda r:r)
        obj._no_results=lambda:'no-results';obj.display_results=lambda r:('display',r);obj.play_file=lambda r:('autoplay',r)
        return obj

    def test_ignore_all_filters_cannot_reintroduce_cam(self):
        s=self.source_class({});self.assertEqual(s._process_post_results(),'no-results')
        self.assertTrue(s.filters_ignored)

    def test_direct_aio_and_autoplay_paths_obey_boundary(self):
        s=self.source_class({});s.autoplay=True
        self.assertEqual(s.play_source([stream('Film.2026.4K.TS')]),'no-results')
        result=s.play_source([stream()]);self.assertEqual(result[0],'autoplay')

    def test_explicitly_disabling_strict_filter_keeps_upstream_behavior(self):
        s=self.source_class({'povplus.strict':'false'})
        self.assertEqual(s._process_post_results()[0],'display')


class PackagingTests(unittest.TestCase):
    def test_addon_routes_settings_and_isolation(self):
        import xml.etree.ElementTree as ET
        addon=ET.parse(ROOT/'plugin.video.povplus/addon.xml').getroot()
        self.assertEqual(addon.attrib['id'],'plugin.video.povplus')
        tree=ET.parse(ROOT/'plugin.video.povplus/resources/settings.xml')
        keys={s.get('id') for s in tree.iter('setting') if s.get('id')}
        credentials={n.get('id'):n.get('default') for n in tree.iter('setting')}
        for key in ['tmdb_read_token','trakt.client_id','trakt.client_secret']:self.assertEqual(credentials[key],'')
        self.assertIn('povplus.csfd',keys);self.assertIn('povplus.catalog_source',keys)
        for file in (ROOT/'plugin.video.povplus').rglob('*.py'):
            source=file.read_text();ast.parse(source)
            self.assertNotIn('plugin.video.pov/',source,str(file))
            self.assertNotIn('plugin.video.pov\'',source,str(file))
        namespace={}
        exec((LIB/'modules/menu_lists.py').read_text(),namespace)
        self.assertEqual(namespace['main_menu_items']['MovieList']['action'],'MovieList')
        self.assertEqual(namespace['main_menu_items']['TVShowList']['action'],'TVShowList')
        entry=(LIB/'modules/entry.py').read_text()
        for route in ['povplus_catalog','povplus_filters','povplus_detail','povplus_link']:self.assertIn("'"+route+"'",entry)

if __name__=='__main__':unittest.main()
