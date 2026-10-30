"""Run new Kodi menu code against a small, explicit Kodi/provider double."""
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugin.video.povplus/resources/lib'))

class Item:
    def __init__(self):self.label='';self.context=[];self.rating=None
    def setLabel(self,v):self.label=v
    def setInfo(self,*a):pass
    def setArt(self,*a):pass
    def addContextMenuItems(self,v):self.context+=v
    def setRating(self,*a):self.rating=a

class Dialog:
    def __init__(self,choice=-1):self.choice=choice;self.messages=[]
    def create(self,*a):pass
    def iscanceled(self):return False
    def update(self,*a):pass
    def close(self):pass
    def select(self,*a):return self.choice
    def ok(self,*a):self.messages.append(a)
    def textviewer(self,*a):self.messages.append(a)

class MenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.added=[];self.dirs=[];self.dialog=Dialog()
        self.settings={'tmdb_read_token':'test-only-not-a-real-token','povplus.catalog_quality':'true','povplus.catalog_min_rating':'70'}
        self.ku=types.ModuleType('modules.kodi_utils')
        self.ku.translate_path=lambda p:str(Path(self.tmp.name)/Path(p).name)
        self.ku.databases_path='special://profile/addon_data/plugin.video.povplus/'
        self.ku.get_setting=lambda k,d=None:self.settings.get(k,d)
        self.ku.set_setting=lambda k,v:self.settings.__setitem__(k,v)
        self.ku.argv1=lambda:'1';self.ku.media_path=lambda p:p
        self.ku.add_dir=lambda *a,**kw:self.dirs.append(a)
        self.ku.add_item=lambda *a:self.added.append(a)
        self.ku.make_listitem=Item;self.ku.progressDialog=lambda:self.dialog;self.ku.dialog=lambda:self.dialog
        self.ku.set_category=lambda *a:None;self.ku.set_content=lambda *a:None;self.ku.end_directory=lambda *a:None
        self.ku.build_url=lambda d:'plugin://plugin.video.povplus/?'+str(d)
        self.ku.hide_busy_dialog=lambda:None
        self.ku.open_settings=lambda query:self.dialog.messages.append(('settings',query))
        fake_settings=types.ModuleType('modules.settings');fake_settings.metadata_user_info=lambda:{}
        self.patch=patch.dict(sys.modules,{'modules.kodi_utils':self.ku,'modules.settings':fake_settings})
        self.patch.start()
        self.module=importlib.import_module('modules.povplus_catalog')
        self.module.ku=self.ku
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def test_missing_metadata_setup_is_explained_without_network(self):
        self.settings['tmdb_read_token']=''
        with patch.object(self.module,'_page',side_effect=AssertionError('network called')):
            self.module.catalog({})
        self.assertIn('TMDb API Read Access Token',self.dialog.messages[0][1])

    def test_catalog_keeps_only_csfd_and_quality_matches(self):
        metas={i:{'tmdb_id':i,'title':'Film '+str(i),'year':2026,'duration':7200,'genre':'Drama','plot':'Popis'} for i in [1,2,3]}
        def rating(meta):return {'rating':{1:75,2:69,3:80}[meta['tmdb_id']]}
        def quality(meta,probe=False):return {'best':{'resolution':2160,'hdr':'HDR','audio':'Atmos','sizeGiB':20,'averageMbps':24},'checkedAt':1} if meta['tmdb_id']==1 else {'best':None}
        with patch.object(self.module,'_page',return_value=([1,2,3],True)),patch.object(self.module,'_meta',side_effect=lambda mid:metas[mid]),patch.object(self.module,'csfd_info',side_effect=rating),patch.object(self.module,'quality_info',side_effect=quality):
            self.module.catalog({})
        self.assertEqual(len(self.added),1)
        self.assertIn('ČSFD 75%',self.added[0][2].label)
        self.assertIn('4K',self.added[0][2].label)
        self.assertEqual(self.added[0][2].rating,('csfd',7.5,0,True))
        self.assertTrue(any('Další stránka' in str(d) for d in self.dirs))
        self.assertEqual(self.dialog.messages,[])

    def test_empty_page_is_explained_not_filled_with_unknown(self):
        with patch.object(self.module,'_page',return_value=([],False)):self.module.catalog({})
        self.assertTrue(any('Žádný doložený film' in str(d) for d in self.dirs))

    def test_details_open_settings_with_existing_kodi_contract(self):
        self.dialog.choice=6
        with patch.object(self.module,'_meta',return_value={'tmdb_id':1,'title':'Film'}),patch.object(self.module,'csfd_info',return_value={}),patch.object(self.module,'quality_info',return_value=None):self.module.detail({'tmdb_id':'1'})
        self.assertEqual(self.dialog.messages,[('settings',None)])

    def test_genres_are_or_and_missing_data_does_not_pass(self):
        genres=[{'id':1,'aliases':['Drama']},{'id':2,'aliases':['Komedie','Comedy']}]
        self.assertTrue(self.module._keep_genre({'genre':'Drama, Thriller'},[1,2],genres))
        self.assertFalse(self.module._keep_genre({'genre':'Thriller'},[1,2],genres))
        self.assertFalse(self.module._keep_genre({},[1],genres))

    def test_provider_check_does_not_start_playback_or_persist_urls(self):
        fake=types.ModuleType('modules.sources')
        class Sources:
            config_loader=types.SimpleNamespace(apply=lambda s,p:None)
            meta_builder=types.SimpleNamespace(build=lambda s:{'duration':7200})
            def get_sources(self):return [{'quality':'4K','size':20,'name':'Film.2026.4K.DV.Atmos','url':'https://private/secret'}]
            def play_source(self,*a):raise AssertionError('playback called')
            def play_file(self,*a):raise AssertionError('playback called')
        fake.Sources=Sources
        with patch.dict(sys.modules,{'modules.sources':fake}):
            result=self.module.quality_info({'tmdb_id':77,'duration':7200},probe=True)
        self.assertEqual(result['state'],'source_reported')
        self.assertNotIn('secret',json.dumps(result))
        self.assertEqual(self.module.quality_info({'tmdb_id':77}),result)

if __name__=='__main__':unittest.main()
