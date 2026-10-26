"""Typeset reviewed Korean over original manual art; no generated prose."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'work/ui_images'
OUT = ROOT / 'artwork/ui/manual_ko'
FONT = SOURCE / 'fonts/Jua.ttf'
BODY = SOURCE / 'fonts/GamjaFlower.ttf'

def wrap(text, font, width):
    lines = []
    for para in text.split('\n'):
        if not para:
            lines.append(''); continue
        line = ''
        for char in para:
            if font.getlength(line + char) > width and line:
                lines.append(line.rstrip()); line = char.lstrip()
            else:
                line += char
        lines.append(line.rstrip())
    return lines

def render_region(canvas, region, metrics):
    x0, y0, x1, y1 = region['box']
    assert 0 <= x0 < x1 <= 1920 and 0 <= y0 < y1 <= 1080
    # Erase just the specified original text area. Artwork outside it is exact.
    crop = np.array(canvas.crop((x0,y0,x1,y1)).convert('RGB'))
    mode = region.get('erase', 'cream')
    if mode in ('cream','black','pink','cyan','green','yellow'):
        if mode == 'cream':
            pixels = crop[(crop[:,:,0] > 200) & (crop[:,:,1] > 190) & (crop[:,:,2] > 180)]
            color = tuple(np.median(pixels,axis=0).astype(int)) if len(pixels) else (247,235,225)
        elif mode == 'black': color=(6,6,6)
        else: color=tuple(np.median(crop.reshape(-1,3),axis=0).astype(int))
        ImageDraw.Draw(canvas).rectangle((x0,y0,x1-1,y1-1), fill=color)
    elif mode == 'white_ink':
        mask = ((crop[:,:,0]>190)&(crop[:,:,1]>175)&(crop[:,:,2]>150)).astype('uint8')*255
        mask=cv2.dilate(mask,np.ones((5,5),np.uint8))
        clean=cv2.inpaint(crop,mask,7,cv2.INPAINT_TELEA)
        canvas.paste(Image.fromarray(clean),(x0,y0))
    elif mode == 'pink_ink':
        mask=((crop[:,:,0]>160)&(crop[:,:,1]<155)&(crop[:,:,2]>60)).astype('uint8')*255
        mask=cv2.dilate(mask,np.ones((5,5),np.uint8))
        canvas.paste(Image.fromarray(cv2.inpaint(crop,mask,7,cv2.INPAINT_TELEA)),(x0,y0))
    elif mode == 'dark_ink':
        mask=(crop.max(axis=2)<125).astype('uint8')*255
        mask=cv2.dilate(mask,np.ones((3,3),np.uint8))
        canvas.paste(Image.fromarray(cv2.inpaint(crop,mask,5,cv2.INPAINT_TELEA)),(x0,y0))
    else: raise ValueError(mode)
    text=region['text'].replace('『','"').replace('』','"').replace('‘','"').replace('’','"'); max_size=region.get('size',36); min_size=region.get('min_size',18 if y1-y0<140 else 24)
    for size in range(max_size,min_size-1,-1):
        font=ImageFont.truetype(str(FONT if region.get('font')=='header' else BODY),size)
        lines=wrap(text,font,x1-x0-(4 if max_size<=24 else 12))
        line_h=round(size*region.get('leading',1.08 if y1-y0<140 else 1.18))
        if len(lines)*line_h <= y1-y0-(4 if y1-y0<40 else 8): break
    else: raise ValueError(f'Text does not fit: {region}')
    draw=ImageDraw.Draw(canvas); y=y0+3
    for line in lines:
        if line:
            x=x0+(2 if max_size<=24 else 6) if region.get('align')!='center' else (x0+x1-font.getlength(line))/2
            draw.text((x,y),line,font=font,fill=region.get('color','#111111'),stroke_width=0)
        y+=line_h
    metrics.append({'box':region['box'],'font_size':size,'lines':len(lines),'text':text})

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    doc=json.loads((ROOT/'artwork/ui/manual_ko.json').read_text(encoding='utf-8'))
    report=[]
    for page in doc['pages']:
        name=page['name']; original=Image.open(SOURCE/(name+'.png')).convert('RGB'); canvas=original.copy(); metrics=[]
        for region in page['regions']: render_region(canvas,region,metrics)
        canvas.save(OUT/(name+'.png'))
        report.append({'name':name,'regions':metrics,'size':list(canvas.size)})
    (OUT/'layout_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('MANUAL',len(report),'pages; all text fits; min font',min(r['font_size'] for p in report for r in p['regions']))

if __name__=='__main__':main()
