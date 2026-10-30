# Modified for POV+ by kudykam · 2026-10-30 · GPL-3.0-only
"""POV+ Kodi menus, catalogue checks and clearly attributed ratings."""
import hashlib
import json
import re
import time
from threading import RLock
from datetime import date, timedelta
from urllib.parse import urlencode
from modules import kodi_utils as ku, settings
from modules.povplus_csfd import Client, Unavailable, film_id, text
from modules.povplus_policy import best_stream, meets_rating, number, stars
from modules.povplus_store import Store

_csfd_lock=RLock()

SOURCES = [('Domácí digitální / disková vydání · 31 dnů', 'digital'),
           ('TMDb · trendy týdne', 'tmdb'), ('Trakt · nejsledovanější týdne', 'trakt'),
           ('TMDb · populární filmy', 'popular')]

def store():
    return Store(ku.translate_path(ku.databases_path+'povplus.db'))


def config():
    try: minimum=(720,1080,2160)[max(0,min(2,int(ku.get_setting('povplus.minimum','1'))))]
    except (ValueError,IndexError): minimum=1080
    return {'minimum':minimum, 'budget':ku.get_setting('povplus.budget','40'),
            'rating':number(ku.get_setting('povplus.catalog_min_rating','0')) or 0,
            'quality':ku.get_setting('povplus.catalog_quality','true')=='true'}


def csfd_info(meta, force=False):
    with _csfd_lock:
        return _csfd_info(meta,force)


def _csfd_info(meta, force=False):
    cache=store()
    api=ku.get_setting('povplus.csfd_api','').strip()
    prefix=hashlib.sha256(api.encode()).hexdigest()[:12]
    key='csfd:%s:%s' % (prefix,meta['tmdb_id'])
    if not force:
        result=cache.get(key)
        if result is not None:return result
    try:
        if cache.get('csfd-blocked:'+prefix) and not force:
            return {'error':'ČSFD dočasně odmítá čtení. Hodnocení není známé.'}
        client=Client(api)
        mapping=cache.get('csfd-link:'+str(meta['tmdb_id']))
        result=client.movie(mapping['id']) if mapping else client.lookup(meta)
        if mapping:result['matchedBy']='user_confirmation'
        result['checkedAt']=time.time()
        cache.put(key,result,86400)
        return result
    except Unavailable as error:
        result={'error':str(error),'checkedAt':time.time()}
        cache.put(key,result,1800)
        if 'blokuje' in str(error):cache.put('csfd-blocked:'+prefix,True,1800)
        return result
    except Exception:
        result={'error':'ČSFD údaje nejsou dostupné.','checkedAt':time.time()}
        cache.put(key,result,1800)
        return result


def _quality_key(meta):
    # Invalidate checks after filters/providers/accounts change, without storing secrets.
    names=('povplus.minimum','povplus.budget','results_quality_movie','filter_hdr','filter_dv','filter_hevc','filter_av1',
           'provider.external','provider.aiostreams','provider.rd_cloud','provider.torrentio','provider.torz',
           'rd.token','rd.enabled','trakt.token')
    fingerprint=hashlib.sha256(json.dumps({k:ku.get_setting(k,'') for k in names},sort_keys=True).encode()).hexdigest()
    return 'quality:%s:%s' % (meta['tmdb_id'],fingerprint)


def quality_info(meta, probe=False):
    cache=store()
    key=_quality_key(meta)
    result=cache.get(key)
    if result is not None or not probe:return result
    from modules.sources import Sources
    source=Sources()
    try:
        source.config_loader.apply(source,{'tmdb_id':str(meta['tmdb_id']),'background':'true','prescrape':'false','autoplay':'false','meta':json.dumps(meta)})
        source.meta=source.meta_builder.build(source)
        source.full_screen=False
        # get_sources searches providers only. It does not call play_source,
        # play_file, resolve_sources, or start the TV player.
        results=source.get_sources()
        cfg=config()
        best=best_stream(results,meta.get('duration'),cfg['minimum'],cfg['budget'])
        result={'best':best,'checkedAt':time.time(),'state':'source_reported' if best else 'no_eligible_result',
                'notice':'Parametry hlásí poskytovatel; přehrání a bitrate špičky nejsou ověřené.'}
        cache.put(key,result,3600 if best else 900)
    except Exception:
        result={'best':None,'checkedAt':time.time(),'state':'unknown','notice':'Vyhledávání se nepodařilo dokončit.'}
        cache.put(key,result,300)
    finally:
        ku.hide_busy_dialog()
    return result


def quality_label(check):
    if not check:return 'kvalita nezjištěna'
    best=check.get('best')
    if not best:return 'bez doloženého zdroje v limitu'
    return ' · '.join(x for x in ['4K' if best['resolution']==2160 else str(best['resolution'])+'p',best.get('hdr'),best.get('audio'),
                                  '%.1f GiB' % best['sizeGiB'],'≈ %.1f Mbit/s' % best['averageMbps']] if x)


def decorate_movie(listitem, meta, display):
    """Called at the end of original movie list building; safe on missing data."""
    try:
        if ku.get_setting('povplus.csfd','true')!='true':return
        data=csfd_info(meta)
        percent=data.get('rating')
        listitem.setLabel('%s  %s' % (display,stars(percent)))
        if percent is not None:
            listitem.setProperty('povplus.csfd.percent',str(percent))
            listitem.setProperty('povplus.csfd.url',data['url'])
            if ku.get_kodi_version()>=20:
                listitem.getVideoInfoTag(offscreen=True).setRating(float(percent)/10,0,'csfd',True)
            else:listitem.setRating('csfd',float(percent)/10,0,True)
        listitem.addContextMenuItems([('POV+ · Detail, kvalita a recenze','RunPlugin(%s)' % ku.build_url({'mode':'povplus_detail','tmdb_id':str(meta['tmdb_id'])}))])
    except Exception:pass


def _meta(mid):
    from indexers.metadata import movie_meta
    from modules.utils import get_datetime
    return movie_meta('tmdb_id',str(mid),settings.metadata_user_info(),get_datetime())


def _tmdb(path):
    from indexers.tmdb_api import get_tmdb
    data=get_tmdb(path)
    if not isinstance(data,dict):raise RuntimeError('Filmový katalog není dostupný.')
    return data


def genre_data():
    cache=store();data=cache.get('genres')
    if data:return data
    cs=_tmdb('/3/genre/movie/list?language=cs-CZ').get('genres',[])
    en=_tmdb('/3/genre/movie/list?language=en-US').get('genres',[])
    eng={g['id']:g['name'] for g in en}
    data=[{'id':g['id'],'name':g['name'],'aliases':[g['name'],eng.get(g['id'],g['name'])]} for g in cs]
    cache.put('genres',data,86400*7)
    return data


def selected_genres():
    try:
        value=json.loads(ku.get_setting('povplus.genres','[]'))
        return [int(x) for x in value] if isinstance(value,list) else []
    except (ValueError,TypeError):return []


def choose_genres(_params=None):
    try:
        genres=genre_data();selected=selected_genres()
        indices=ku.dialog().multiselect('POV+ · Žánry (prázdné = všechny)',[g['name'] for g in genres],preselect=[i for i,g in enumerate(genres) if g['id'] in selected])
        if indices is not None:ku.set_setting('povplus.genres',json.dumps([genres[i]['id'] for i in indices]));ku.execute_builtin('Container.Refresh')
    except Exception:ku.dialog().ok('POV+','Žánry se nepodařilo načíst z TMDb.')


def filters(_params=None):
    choice=ku.dialog().select('POV+ · Filtry',['ČSFD alespoň','Žánry','Nejnižší kvalita','Jen nalezené zdroje v limitu','Datový limit','Všechna nastavení POV+'])
    if choice==0:
        values=list(range(0,101,5));index=ku.dialog().select('ČSFD alespoň (%)',[str(x)+' %' if x else 'Bez filtru' for x in values])
        if index>=0:ku.set_setting('povplus.catalog_min_rating',str(values[index]))
    elif choice==1:return choose_genres()
    elif choice==2:
        index=ku.dialog().select('Nejnižší kvalita',['720p','1080p','4K'])
        if index>=0:ku.set_setting('povplus.minimum',str(index))
    elif choice==3:ku.set_setting('povplus.catalog_quality','false' if config()['quality'] else 'true')
    elif choice==4:
        values=[25,30,35,40];index=ku.dialog().select('Limit průměrného datového toku',[str(x)+' Mbit/s' for x in values])
        if index>=0:ku.set_setting('povplus.budget',str(values[index]))
    elif choice==5:return ku.open_settings(None)
    if choice>=0:ku.execute_builtin('Container.Refresh')


def choose_source(_params=None):
    selected=ku.dialog().select('POV+ · Zdroj přehledu',[x[0] for x in SOURCES])
    if selected>=0:
        ku.set_setting('povplus.catalog_source',str(selected))
        ku.execute_builtin('Container.Update(%s)' % ku.build_url({'mode':'povplus_catalog'}))


def _page(source,page):
    if source=='trakt':
        from indexers.trakt_api import trakt_movies_most_watched
        data,total=trakt_movies_most_watched(page)
        return [i['movie']['ids']['tmdb'] for i in data if i.get('movie',{}).get('ids',{}).get('tmdb')],page<total
    if source=='tmdb':data=_tmdb('/3/trending/movie/week?'+urlencode({'page':page,'language':'cs-CZ'}))
    elif source=='popular':data=_tmdb('/3/movie/popular?'+urlencode({'page':page,'language':'cs-CZ'}))
    else:
        params={'language':'cs-CZ','region':'US','page':page,'with_release_type':'4|5','release_date.gte':str(date.today()-timedelta(days=31)),
                'release_date.lte':str(date.today()),'sort_by':'popularity.desc','include_adult':'false'}
        data=_tmdb('/3/discover/movie?'+urlencode(params))
    return [i['id'] for i in data.get('results',[])],page<int(data.get('total_pages',page))


def _keep_genre(meta,selected,genres):
    if not selected:return True
    names={n.strip().casefold() for n in str(meta.get('genre','')).split(',')}
    return any(g['id'] in selected and any(a.casefold() in names for a in g['aliases']) for g in genres)


def catalog(params=None):
    params=params or {};handle=int(ku.argv1());cfg=config()
    if not ku.get_setting('tmdb_read_token','').strip():
        ku.dialog().ok('POV+ · Nastavení katalogu','Nejprve vlož vlastní TMDb API Read Access Token v nastavení Metadata.')
        ku.end_directory(handle,False)
        return
    try:page=max(1,int(params.get('page','1')))
    except ValueError:page=1
    try:source_index=max(0,min(len(SOURCES)-1,int(ku.get_setting('povplus.catalog_source','0'))))
    except ValueError:source_index=0
    source_name,source=SOURCES[source_index]
    ku.add_dir(handle,{'mode':'povplus_filters'},'⚙ Filtry · ČSFD ≥ %s %% · %sp · %s Mbit/s' % (cfg['rating'],cfg['minimum'],cfg['budget']),ku.media_path('settings.png'),isFolder=False)
    ku.add_dir(handle,{'mode':'povplus_source'},'Zdroj: '+source_name,ku.media_path('trending.png'),isFolder=False)
    progress=ku.progressDialog();progress.create('POV+','Načítání filmů a dostupných zdrojů…')
    visible=0;has_more=False;cancelled=False;unknown_csfd=0
    try:
        selected=selected_genres();genres=genre_data() if selected else []
        ids,has_more=_page(source,page)
        for index,mid in enumerate(ids):
            if progress.iscanceled():cancelled=True;break
            progress.update(int(index*100/max(1,len(ids))),'Film %s/%s · lze zrušit' % (index+1,len(ids)))
            meta=_meta(mid)
            if not meta or meta.get('blank_entry') or not _keep_genre(meta,selected,genres):continue
            rating=csfd_info(meta) if ku.get_setting('povplus.csfd','true')=='true' or cfg['rating']>0 else {}
            if not meets_rating(rating.get('rating'),cfg['rating']):
                if rating.get('rating') is None:unknown_csfd+=1
                continue
            check=quality_info(meta,probe=cfg['quality'])
            if cfg['quality'] and not (check or {}).get('best'):continue
            label='%s  %s  ·  %s' % (text(meta['title']),stars(rating.get('rating')),quality_label(check))
            item=ku.make_listitem();item.setLabel(label)
            item.setInfo('video',{'title':text(meta['title']),'plot':text(meta.get('plot'))+'\n\n'+quality_label(check),'mediatype':'movie','year':meta.get('year')})
            poster=meta.get('poster') or meta.get('poster_path')
            if poster:
                if str(poster).startswith('/'):poster='https://image.tmdb.org/t/p/w500'+poster
                item.setArt({'thumb':poster,'poster':poster})
            if rating.get('rating') is not None:item.setRating('csfd',rating['rating']/10,0,True)
            item.addContextMenuItems([('Vyhledat zdroje a přehrát','RunPlugin(%s)' % ku.build_url({'mode':'play_media','tmdb_id':str(mid)})),
                ('Propojit ČSFD ručně','RunPlugin(%s)' % ku.build_url({'mode':'povplus_link','tmdb_id':str(mid)}))])
            ku.add_item(handle,ku.build_url({'mode':'povplus_detail','tmdb_id':str(mid)}),item,False)
            visible+=1
        if not visible:
            ku.add_dir(handle,{'mode':'povplus_filters'},'Žádný doložený film v těchto filtrech · upravit filtry',ku.media_path('settings.png'),isFolder=False)
        if unknown_csfd:
            ku.add_dir(handle,{'mode':'povplus_filters'},'ČSFD nedostupné / nepřiřazené u %s filmů · filtr je nepropouští' % unknown_csfd,ku.media_path('settings.png'),isFolder=False)
        if has_more:
            ku.add_dir(handle,{'mode':'povplus_catalog','page':str(page+1)},'Další stránka kandidátů →',ku.media_path('item_next.png'))
        ku.set_category(handle,source_name+(' · částečná kontrola' if cancelled else ''))
    except Exception:
        ku.dialog().ok('POV+','Přehled se nepodařilo načíst. Ověř připojení, účty a nastavení katalogu.')
    finally:
        progress.close();ku.set_content(handle,'movies');ku.end_directory(handle,False)


def link_csfd(params):
    meta=_meta(params['tmdb_id'])
    value=ku.dialog().input('ČSFD ID nebo veřejný odkaz na film')
    if not value:return
    mid=value.strip() if value.strip().isdigit() else film_id(value.strip())
    try:
        if not mid:raise Unavailable('Neplatné ID nebo odkaz ČSFD.')
        result=Client(ku.get_setting('povplus.csfd_api','')).movie(mid)
        if result['imdbIds'] and meta.get('imdb_id') not in result['imdbIds']:raise Unavailable('ČSFD odkaz patří jinému IMDb filmu.')
        if not ku.dialog().yesno('Potvrdit propojení','%s (%s) ↔ %s (%s)' % (meta['title'],meta['year'],result['title'],result['year'])):return
        store().put('csfd-link:'+str(meta['tmdb_id']),{'id':mid},86400*3650)
        csfd_info(meta,force=True);ku.execute_builtin('Container.Refresh')
    except Unavailable as error:ku.dialog().ok('ČSFD',str(error))


def _reviews(meta,rating):
    reviews=rating.get('reviews',[])[:3]
    if reviews:return reviews
    try:
        data=_tmdb('/3/movie/%s/reviews?language=cs-CZ' % int(meta['tmdb_id']))
        return [{'source':'TMDb','author':text(r.get('author')),'text':text(r.get('content'))[:900],'url':r.get('url','')} for r in data.get('results',[])[:3]]
    except Exception:return []


def detail(params):
    meta=_meta(params['tmdb_id']);rating=csfd_info(meta);check=quality_info(meta)
    choices=['Popis, kvalita a hodnocení','Vyhledat zdroje a přehrát','Obnovit kontrolu zdrojů','Recenze / komentáře','Propojit ČSFD ručně','Uložit / spravovat Trakt','Nastavení POV+']
    choice=ku.dialog().select(text(meta['title'])+' · '+stars(rating.get('rating')),choices)
    if choice==0:
        age=time.strftime('%d.%m.%Y %H:%M',time.localtime(check['checkedAt'])) if check else 'dosud neproběhla'
        ku.dialog().textviewer(text(meta['title']),text(meta.get('plot'))+'\n\n'+stars(rating.get('rating'))+'\n'+rating.get('url','')+'\n'+rating.get('error','')+'\n\n'+quality_label(check)+'\nKontrola: '+age+'\nParametry hlásí zdroj. Nejde o ověření přehrání na TV ani špiček datového toku.\n\nŽánry: '+text(meta.get('genre')))
    elif choice==1:ku.execute_builtin('RunPlugin(%s)' % ku.build_url({'mode':'play_media','tmdb_id':str(meta['tmdb_id'])}))
    elif choice==2:
        # Invalidate only this quality check, not the rest of the add-on cache.
        store().put(_quality_key(meta),None,0)
        result=quality_info(meta,probe=True)
        ku.dialog().ok('POV+ · Zdroje',quality_label(result))
    elif choice==3:
        reviews=_reviews(meta,rating)
        if not reviews:ku.dialog().ok('Recenze','ČSFD ani TMDb neposkytlo dostupnou recenzi. '+rating.get('error',''))
        else:ku.dialog().textviewer('Recenze · původ je uveden u každé', '\n\n'.join('%s · %s\n%s\n%s' % (r['source'],r['author'],r['text'],r.get('url','')) for r in reviews))
    elif choice==4:return link_csfd(params)
    elif choice==5:
        from menus.trakt import TraktManager
        TraktManager({'mediatype':'movie','tmdb_id':str(meta['tmdb_id']),'imdb_id':meta.get('imdb_id'),'tvdb_id':'None'}).manage()
    elif choice==6:ku.open_settings(None)
