"""Revise one installed image while preserving the original patch restore point."""
import argparse,json,shutil
from datetime import datetime
import UnityPy
from PIL import Image
from manage_image_patch import ROOT,DATA,STAGE,sha,dump,inside,closed

def main(texture_name):
    closed()
    record_path=ROOT/'work/install/ui_images.json'
    doc=json.loads(record_path.read_text(encoding='utf-8'))
    specs=json.loads((ROOT/'artwork/ui/texture_patch.json').read_text(encoding='utf-8'))['textures']
    spec=next(s for s in specs if s['texture']==texture_name)
    image=Image.open(inside(ROOT,spec['image'])).convert('RGBA')
    targets=[r for r in doc['files'] if texture_name in r['textures']]
    assert targets
    revision=ROOT/'work/backups'/('ui_revision_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    revision.mkdir(parents=True,exist_ok=False)
    dump(revision/'installation_before.json',doc)
    prepared=[]
    for r in targets:
        source=inside(DATA,r['file']);assert sha(source)==r['after_sha256'],('Later game changes',r['file'])
        backup=inside(revision,r['file']);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        env=UnityPy.load(str(source));objects={(o.assets_file.name,o.path_id):o for o in env.objects}
        before={k:o.get_raw_data() for k,o in objects.items()};changed={}
        for key,o in objects.items():
            if o.type.name!='Texture2D':continue
            t=o.read()
            if t.m_Name!=texture_name:continue
            assert image.size==(t.m_Width,t.m_Height)
            t.set_image(image,target_format=4,mipmap_count=t.m_MipCount);t.save();changed[key]=o.data
        assert changed
        staged=inside(STAGE,r['file']);staged.parent.mkdir(parents=True,exist_ok=True)
        staged.write_bytes(env.file.save(packer='lz4') if source.suffix=='.bundle' else env.file.save())
        check={(o.assets_file.name,o.path_id):o for o in UnityPy.load(str(staged)).objects}
        assert set(check)==set(before)
        for key,o in check.items():
            assert o.get_raw_data()==changed.get(key,before[key]),('Unrelated object changed',key)
            if key in changed:assert o.read().image.convert('RGBA').tobytes()==image.tobytes()
        prepared.append((r,source,staged,backup,sha(staged)))
        print('VERIFIED',r['file'],flush=True)
    closed()
    try:
        for r,source,staged,backup,digest in prepared:
            assert sha(source)==r['after_sha256']
            shutil.copy2(staged,source);assert sha(source)==digest
        for r,source,staged,backup,digest in prepared:r['after_sha256']=digest
        doc.setdefault('revisions',[]).append({'texture':texture_name,'backup':str(revision)})
        dump(record_path,doc)
        manifest=json.loads((STAGE/'manifest.json').read_text(encoding='utf-8'))
        manifest['files']=doc['files'];dump(STAGE/'manifest.json',manifest)
    except BaseException:
        for r,source,staged,backup,digest in prepared:shutil.copy2(backup,source)
        raise
    print('UPDATED; installed hashes verified; original restore point retained:',doc['backup'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('texture');main(parser.parse_args().texture)
