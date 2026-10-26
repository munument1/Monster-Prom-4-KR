"""Build, validate, install or restore the local Monster Con UI image patch."""
from pathlib import Path
from datetime import datetime
import argparse, base64, hashlib, json, re, shutil, subprocess, struct
import UnityPy
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Games\Steam\steamapps\common\Monster Prom 4 - Monster Con')
DATA=GAME/'MonsterCon_Data'
STAGE=ROOT/'build/image_patch'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def inside(root,relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError(relative)
    return path
def closed():
    tasklist=subprocess.run(['tasklist','/FI','IMAGENAME eq MonsterCon.exe','/FO','CSV','/NH'],capture_output=True,text=True).stdout
    if 'MonsterCon.exe' in tasklist: raise RuntimeError('Close Monster Con before changing its asset files.')

def build():
    specs=json.loads((ROOT/'artwork/ui/texture_patch.json').read_text(encoding='utf-8'))['textures']
    names={x['texture']:x for x in specs}; assert len(names)==len(specs)
    # Discover targets from the user's installed game, so a fresh clone does
    # not depend on the author's ignored extraction inventory.
    inventory=[]
    sources=sorted(DATA.glob('*.assets'))+sorted((DATA/'StreamingAssets/aa/StandaloneWindows').glob('*.bundle'))
    for source in sources:
        env=UnityPy.load(str(source))
        for o in env.objects:
            if o.type.name!='Texture2D':continue
            texture=o.read()
            if texture.m_Name in names:
                inventory.append({'type':'Texture2D','name':texture.m_Name,'id':o.path_id,'file':str(source.relative_to(DATA))})
    targets={}
    for row in inventory:
        if row['type']=='Texture2D' and row['name'] in names:
            targets.setdefault(row['file'],[]).append(row)
    catalog=json.loads((DATA/'StreamingAssets/aa/catalog.json').read_text(encoding='utf-8'))
    extra=base64.b64decode(catalog['m_ExtraDataString']);offset=0;options=[]
    while offset<len(extra):
        assert extra[offset]==7;offset+=1
        for _ in range(2):
            length=extra[offset];offset+=1+length
        length=struct.unpack_from('<i',extra,offset)[0];offset+=4
        options.append(json.loads(extra[offset:offset+length].decode('utf-16le')));offset+=length
    for option in options:
        if not option['m_Crc']:continue
        # This build has a single nonzero CRC, on the untouched hashed requirements bundle.
        matching=list((DATA/'StreamingAssets/aa/StandaloneWindows').glob('*'+option['m_Hash']+'*.bundle'))
        assert len(matching)==1 and matching[0].stat().st_size==option['m_BundleSize']
        if str(matching[0].relative_to(DATA)) in targets:raise RuntimeError('Target bundle has CRC validation: '+matching[0].name)
    records=[];seen=set()
    for relative,rows in sorted(targets.items()):
        source=inside(DATA,relative);env=UnityPy.load(str(source))
        objects={(o.assets_file.name,o.path_id):o for o in env.objects}
        before={k:o.get_raw_data() for k,o in objects.items()};changed={};expected={}
        for row in rows:
            matches=[o for o in env.objects if o.path_id==row['id'] and o.type.name=='Texture2D']
            assert len(matches)==1,(relative,row)
            o=matches[0];texture=o.read();spec=names[row['name']]
            im=Image.open(inside(ROOT,spec['image'])).convert('RGBA')
            assert im.size==(texture.m_Width,texture.m_Height),(relative,texture.m_Name,im.size)
            texture.set_image(im,target_format=4,mipmap_count=texture.m_MipCount);texture.save()
            key=(o.assets_file.name,o.path_id);assert o.data is not None
            changed[key]=o.data;expected[key]=im.tobytes();seen.add(texture.m_Name)
        dest=inside(STAGE,relative);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(env.file.save(packer='lz4') if source.suffix=='.bundle' else env.file.save())
        reread=UnityPy.load(str(dest));check={(o.assets_file.name,o.path_id):o for o in reread.objects}
        assert set(check)==set(before),(relative,'object identities changed')
        for key,o in check.items():
            assert o.get_raw_data()==changed.get(key,before[key]),(relative,key,'unrelated object changed')
            if key in expected: assert o.read().image.convert('RGBA').tobytes()==expected[key],(relative,key,'image mismatch')
        records.append({'file':relative,'before_sha256':sha(source),'after_sha256':sha(dest),'textures':[r['name'] for r in rows],'object_count':len(before)})
        print('VERIFIED',relative,len(rows),flush=True)
    assert seen==set(names),set(names)-seen
    dump(STAGE/'manifest.json',{'game':str(GAME),'files':records,'unique_textures':len(seen),'crc_catalog':{'entries':len(options),'nonzero_target_bundles':0,'nonzero_untouched_bundles':sum(bool(x['m_Crc']) for x in options)},'validation':'All object identities preserved; only named Texture2D objects changed; decoded RGBA pixels match final PNGs.'})
    print('READY',len(records),'files',len(seen),'unique texture names')

def install():
    closed();doc=json.loads((STAGE/'manifest.json').read_text(encoding='utf-8'))
    for r in doc['files']:
        assert sha(inside(DATA,r['file']))==r['before_sha256'],('Game changed since build',r['file'])
        assert sha(inside(STAGE,r['file']))==r['after_sha256']
    backup=ROOT/'work/backups'/('ui_images_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True,exist_ok=False)
    for r in doc['files']:
        target=inside(backup,r['file']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(inside(DATA,r['file']),target)
        assert sha(target)==r['before_sha256']
    dump(backup/'manifest.json',doc)
    installed=[]
    try:
        for r in doc['files']:
            shutil.copy2(inside(STAGE,r['file']),inside(DATA,r['file']));installed.append(r)
            assert sha(inside(DATA,r['file']))==r['after_sha256']
    except BaseException:
        for r in installed: shutil.copy2(inside(backup,r['file']),inside(DATA,r['file']))
        raise
    dump(ROOT/'work/install/ui_images.json',{'backup':str(backup),**doc})
    print('INSTALLED; verified hashes; backup:',backup)

def restore():
    closed();doc=json.loads((ROOT/'work/install/ui_images.json').read_text(encoding='utf-8'));backup=Path(doc['backup'])
    assert backup.resolve().is_relative_to((ROOT/'work/backups').resolve())
    for r in doc['files']:
        assert sha(inside(DATA,r['file']))==r['after_sha256'],('Refusing to overwrite later changes',r['file'])
        assert sha(inside(backup,r['file']))==r['before_sha256']
    for r in doc['files']:
        shutil.copy2(inside(backup,r['file']),inside(DATA,r['file']));assert sha(inside(DATA,r['file']))==r['before_sha256']
    print('RESTORED original image assets from',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','install','restore'])
    p.add_argument('--game',type=Path,default=GAME,help='Monster Con installation directory')
    a=p.parse_args();GAME=a.game.resolve();DATA=GAME/'MonsterCon_Data'
    globals()[a.action]()
