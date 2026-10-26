"""Composite generated Korean lettering into original texture regions."""
from pathlib import Path
import json
from PIL import Image, ImageOps
from build_manual_images import render_region

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'work/ui_images'; GEN=ROOT/'artwork/ui/generated'; OUT=ROOT/'artwork/ui/final'

def rgba(p): return Image.open(p).convert('RGBA')
def cropped(key,box): return rgba(GEN/(key+'.png')).crop(box)
def fit_alpha(im,size):
    bbox=im.getchannel('A').getbbox(); assert bbox
    im=im.crop(bbox); im.thumbnail(size,Image.Resampling.LANCZOS)
    layer=Image.new('RGBA',size);layer.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2));return layer
def paste(canvas,patch,box,alpha=False,contain=False):
    size=(box[2]-box[0],box[3]-box[1])
    if contain: patch=fit_alpha(patch,size)
    else: patch=patch.resize(size,Image.Resampling.LANCZOS)
    if alpha:
        # Flatten only edge transparency over the target's paper color before
        # reinstating its exact original silhouette.
        base=canvas.crop(box); base.alpha_composite(patch);patch=base
        patch.putalpha(canvas.crop(box).getchannel('A'))
    canvas.paste(patch,box[:2])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inv=json.loads((SRC/'inventory.json').read_text(encoding='utf-8'))
    regions=json.loads((SRC/'sprite_regions.json').read_text(encoding='utf-8'))
    textures=[];audit=[]
    def save(im,file,pid,regions_changed):
        row=next(r for r in inv if r['file']==file and r['id']==pid and r['type']=='Texture2D')
        dest=OUT/(file+'_'+str(pid)+'.png');im.save(dest)
        textures.append({'texture':row['name'],'image':str(dest.relative_to(ROOT)).replace('\\','/')})
        audit.append({'texture':row['name'],'file':file,'id':pid,'regions':regions_changed})
    # Translated comic genre cards, including the variants revealed by play.
    selected={17:['SpaceOpera_Unlocked','Artsy_Unlocked','MagicalGirls_Unlocked','Domino_Unlocked','Harem_Unlocked','Noir_Unlocked','Superheroes_Unlocked','Period_Unlocked'],12:['Sports_Unlocked'],14:['Shonen_Unlocked'],15:['Fantasy_Unlocked','ComicStrip_Unlocked']}
    canvases={n:rgba(SRC/f'sharedassets4.assets_{n}.png') for n in [8,10,12,14,15,16,17]};changed={n:[] for n in canvases}
    for pid,ends in selected.items():
        im=rgba(GEN/('gen17.png' if pid==17 else f'atlas_{pid}.png'))
        for r in regions:
            if r['texture_id']!=pid or r['sprite'].removeprefix('ComicType_') not in ends:continue
            b=r['box'];srcbox=tuple(round(v*im.width/2048) for v in b)
            paste(canvases[pid],im.crop(srcbox),b,alpha=True);changed[pid].append(b)
    # Difficulty labels: replace lettering areas, leaving all original car art.
    difficulty_sources={'Hard':('atlas_12',[966,546,1225,640]),'Hard_Highlight':('atlas_12',[964,856,1242,954]),'Medium':('atlas_15',[374,477,615,573]),'Medium_Highlight':('atlas_15',[374,477,615,573]),'Easy':('atlas_15',[752,510,966,606]),'Easy_Highlight':('atlas_15',[752,818,966,914])}
    for r in regions:
        if not r['sprite'].startswith('DifficultyMode_'):continue
        key,srcbox=difficulty_sources[r['sprite'].removeprefix('DifficultyMode_')];x0,y0,x1,y1=r['box'];b=[x0,y0+388,x1,y1]
        paste(canvases[r['texture_id']],cropped(key,srcbox),b,contain=True);changed[r['texture_id']].append(b)
    # Paper cassette labels. The cassette illustrations remain original.
    music_sources={'Kawaii':('music16',[89,480,257,575]),'Kawaii_Highlight':('atlas_14',[1012,1150,1190,1242]),'Fantasy':('music16',[48,818,217,915]),'Fantasy_Highlight':('music16',[645,1151,808,1240]),'Retro':('music16',[61,1148,221,1242]),'Retro_Highlight':('music8',[58,326,225,421]),'SurfRock':('music16',[370,1152,541,1241]),'SurfRock_Highlight':('music10',[1008,508,1172,588]),'LoFi':('music10',[988,830,1156,916]),'LoFi_Highlight':('music16',[943,1150,1125,1242])}
    for r in regions:
        if not r['sprite'].startswith('MusicVariation_'):continue
        im=rgba(r['crop']);local=im.crop((0,390,im.width,im.height)).getchannel('A').getbbox();assert local
        x,y=r['box'][:2];b=[x+local[0],y+390+local[1],x+local[2],y+390+local[3]]
        key,s=music_sources[r['sprite'].removeprefix('MusicVariation_')]
        paste(canvases[r['texture_id']],cropped(key,s),b,alpha=True);changed[r['texture_id']].append(b)
    for pid,im in canvases.items():save(im,'sharedassets4.assets',pid,changed[pid])
    # FRIEND-O-MAT text only: preserve bird mascot, machine and shelves.
    im=rgba(SRC/'sharedassets5.assets_15.png');gen=rgba(GEN/'friendomat.png').resize(im.size,Image.Resampling.LANCZOS)
    boxes=[[155,855,1355,1115],[1375,925,1685,1080]]
    for b in boxes:paste(im,gen.crop(b),b,alpha=True)
    save(im,'sharedassets5.assets',15,boxes)
    # Gallery NEW tag and insufficient-funds message, preserving other sprites.
    im=rgba(SRC/'sharedassets2.assets_12.png');b=[403,26,507,96];paste(im,rgba(GEN/'newtag.png'),b,contain=True);save(im,'sharedassets2.assets',12,[b])
    im=rgba(SRC/'sharedassets9.assets_5.png');b=[1575,1537,1879,1841];paste(im,cropped('gallery',[985,965,1130,1115]),b,contain=True);save(im,'sharedassets9.assets',5,[b])
    for pid in [17,26,31,32,21,20,33]:
        im=rgba(SRC/f'sharedassets2.assets_{pid}.png');key={21:'franchise',20:'firstlaunch',33:'crossover'}.get(pid,f'promo{pid}')
        gen=rgba(GEN/(key+'.png'))
        if pid in [17,26,31,32,21]:
            bbox=gen.getchannel('A').getbbox();gen=gen.crop(bbox).resize((im.width,im.getchannel('A').getbbox()[3]),Image.Resampling.LANCZOS)
            padded=Image.new('RGBA',im.size);padded.paste(gen,(0,0));gen=padded
        else:gen=gen.resize(im.size,Image.Resampling.LANCZOS)
        boxes=([[35,15,285,66],[30,72,420,140]] if pid in [17,26,31,32] else [[238,85,580,128]] if pid==21 else [[210,170,670,260],[1330,170,1750,260],[1270,335,1660,490],[810,650,1265,885],[1315,895,1665,945]] if pid==20 else [[220,180,800,305],[1360,830,1620,925]])
        if pid in [17,26,31,32]:
            gen.putalpha(im.getchannel('A'));im=gen
        else:
            for b in boxes:paste(im,gen.crop(b),b,alpha=True)
        save(im,'sharedassets2.assets',pid,boxes)
    # Keep all generated manual designs; correct only the three known mistranslated bodies.
    doc=json.loads((ROOT/'artwork/ui/manual_ko.json').read_text(encoding='utf-8'))
    fixes={0:[([100,315,655,1010],1)],2:[([115,375,910,1020],2)],4:[([350,450,900,975],3),([1245,450,1800,975],4)],5:[([370,440,955,975],3),([1240,450,1800,975],4)]}
    for n in range(31):
        im=rgba(GEN/f'manual_{n}.png').resize((1920,1080),Image.Resampling.LANCZOS)
        if n in fixes:
            page=next(p for p in doc['pages'] if p['name']==f'info_manual_{n}')
            metrics=[]
            for box,index in fixes[n]:
                render_region(im,{'box':box,'text':page['regions'][index]['text'],'size':34,'min_size':27,'font':'header','erase':'cream','leading':1.35},metrics)
        if n==0:
            for region in [
                {'box':[738,378,834,415],'text':'일차','size':22,'min_size':18,'font':'header','erase':'cyan','align':'center'},
                {'box':[1698,929,1828,978],'text':'블루','size':32,'min_size':22,'font':'header','erase':'black','color':'#00d8e8','align':'center'}]:render_region(im,region,[])
        if n==22:
            for region in [
                {'box':[1035,741,1178,766],'text':'지능 없는 스미스','size':16,'min_size':12,'font':'header','erase':'black','color':'#fff0e7','align':'center'},
                {'box':[1025,808,1182,855],'text':'모든 능력치가\n크게 내려갑니다.','size':17,'min_size':12,'font':'header','erase':'black','color':'#fff0e7','align':'center'}]:render_region(im,region,[])
        if n==2:
            render_region(im,{'box':[75,280,1100,340],'text':'몬스터콘에서는 여러 방법으로 성공 엔딩을 볼 수 있어요!','size':34,'min_size':28,'font':'header','erase':'cyan'},[])
        if n==21:
            page=next(p for p in doc['pages'] if p['name']=='info_manual_21')
            render_region(im,{'box':[60,305,675,470],'text':page['regions'][1]['text'],'size':35,'min_size':27,'font':'header','erase':'dark_ink'},[])
        if n==28:
            render_region(im,{'box':[1605,748,1745,795],'text':'이어하기','size':25,'min_size':19,'font':'header','erase':'white_ink','color':'#fff0e7','align':'center'},[])
        dest=OUT/f'info_manual_{n}.png';im.save(dest)
        textures.append({'texture':f'info_manual_{n}','image':str(dest.relative_to(ROOT)).replace('\\','/')})
    im=rgba(ROOT/'artwork/ui/manual_ko/info_manual_cover.png');dest=OUT/'info_manual_cover.png';im.save(dest)
    textures.append({'texture':'info_manual_cover','image':str(dest.relative_to(ROOT)).replace('\\','/')})
    (ROOT/'artwork/ui/texture_patch.json').write_text(json.dumps({'textures':textures},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'compositing_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print('ASSEMBLED',len(textures),'texture names')

if __name__=='__main__':main()
