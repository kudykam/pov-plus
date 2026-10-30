#!/usr/bin/env python3
"""Build deterministic Kodi ZIPs and repository metadata without network calls."""
import argparse
import hashlib
import html
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
ADDON_ID='plugin.video.povplus'
REPOSITORY_ID='repository.kudykam.povplus'


def zip_tree(folder,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(destination,'w',ZIP_DEFLATED,compresslevel=9) as archive:
        for file in sorted(folder.rglob('*')):
            if not file.is_file() or '__pycache__' in file.parts or file.suffix=='.pyc':continue
            item=ZipInfo(folder.name+'/'+file.relative_to(folder).as_posix(),(2026,10,30,0,0,0))
            item.compress_type=ZIP_DEFLATED;item.external_attr=0o100644<<16
            archive.writestr(item,file.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)


def build(owner='kudykam',repository='pov-plus',ref='main'):
    if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',value) for value in (owner,repository,ref)):
        raise ValueError('Invalid GitHub path component')
    docs=ROOT/'docs';dist=ROOT/'dist';docs.mkdir(exist_ok=True);dist.mkdir(exist_ok=True)
    addon=ET.parse(ROOT/ADDON_ID/'addon.xml').getroot()
    version=addon.attrib['version']
    base='https://raw.githubusercontent.com/%s/%s/%s/docs/' % (owner,repository,ref)
    repo_dir=ROOT/REPOSITORY_ID;repo_dir.mkdir(exist_ok=True)
    repo=ET.Element('addon',{'id':REPOSITORY_ID,'version':'0.1.0','name':'POV+ Repository','provider-name':owner})
    ext=ET.SubElement(repo,'extension',{'point':'xbmc.addon.repository','name':'POV+ Repository'})
    directory=ET.SubElement(ext,'dir',{'minversion':'19.0.0'})
    ET.SubElement(directory,'info',{'compressed':'false'}).text=base+'addons.xml'
    ET.SubElement(directory,'checksum').text=base+'addons.xml.md5'
    ET.SubElement(directory,'datadir',{'zip':'true'}).text=base
    metadata=ET.SubElement(repo,'extension',{'point':'xbmc.addon.metadata'})
    ET.SubElement(metadata,'summary',{'lang':'en_GB'}).text='Personal POV+ update repository'
    ET.SubElement(metadata,'description',{'lang':'en_GB'}).text='Independent GPL-3.0 fork. Experimental build; not affiliated with upstream POV.'
    ET.SubElement(metadata,'license').text='GPL-3.0-only'
    ET.indent(repo)
    (repo_dir/'addon.xml').write_bytes(ET.tostring(repo,encoding='utf-8',xml_declaration=True))
    shutil.copyfile(ROOT/'LICENSE',repo_dir/'LICENSE')
    for folder,ver in [(ROOT/ADDON_ID,version),(repo_dir,'0.1.0')]:
        destination=docs/folder.name/(folder.name+'-'+ver+'.zip')
        zip_tree(folder,destination);shutil.copyfile(destination,dist/destination.name)
    addons=ET.Element('addons');addons.append(addon);addons.append(repo);ET.indent(addons)
    data=ET.tostring(addons,encoding='utf-8',xml_declaration=True)+b'\n'
    (docs/'addons.xml').write_bytes(data)
    # Kodi uses this legacy checksum to detect repository index changes.
    (docs/'addons.xml.md5').write_text(hashlib.md5(data).hexdigest(),encoding='ascii')
    paths=sorted(p for p in docs.rglob('*.zip'))
    (docs/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(docs).as_posix()+'\n' for p in paths))
    links=''.join('<li><a href="%s">%s</a></li>' % (html.escape(p.relative_to(docs).as_posix()),html.escape(p.name)) for p in paths)
    (docs/'index.html').write_text('''<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>POV+ · Kodi</title><style>body{max-width:780px;margin:50px auto;padding:20px;background:#101820;color:#eaf0f5;font:20px system-ui;line-height:1.6}a{color:#7cd3ec}li{margin:20px 0}</style><h1>POV+ · Kodi</h1><p>Experimentální samostatný fork POV. Instaluje se vedle původního doplňku.</p><p>ČSFD může automatické čtení odmítnout. Hodnocení a recenze se zobrazují pouze při dostupných datech. TV přehrávání dosud není ověřené.</p><ul>'''+links+'</ul><p><a href="addons.xml">addons.xml</a> · <a href="SHA256SUMS">SHA256</a></p>',encoding='utf-8')
    (docs/'.nojekyll').touch()
    print('Built',version,'for',owner+'/'+repository,'at',docs)
    return paths

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--owner',default='kudykam');parser.add_argument('--repository',default='pov-plus');parser.add_argument('--ref',default='main')
    args=parser.parse_args();build(args.owner,args.repository,args.ref)
