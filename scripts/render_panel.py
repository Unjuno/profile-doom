"""A GitHub-native-looking frame around a real captured replay, never a live feed.

Input durations are milliseconds. Desktop game pixels are not rescaled/cropped;
mobile preserves 4:3 with nearest-neighbour resampling. Rendering never writes
save data, injects input, invents activity, or changes the replay's duration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageSequence

PALETTES = {
    'dark': {'bg':'#0d1117','surface':'#151b23','border':'#3d444d',
             'fg':'#f0f6fc','muted':'#9198a1','accent':'#3fb950','button':'#238636'},
    'light': {'bg':'#ffffff','surface':'#f6f8fa','border':'#d1d9e0',
              'fg':'#1f2328','muted':'#59636e','accent':'#1a7f37','button':'#1f883d'},
}

@lru_cache(maxsize=24)
def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    suffix = '-Bold' if bold else ''
    roots = ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu')
    for root in roots:
        path = Path(root) / f'{family}{suffix}.ttf'
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    # Pillow's bundled scalable fallback; no font binaries are copied to outputs.
    return ImageFont.load_default(size=size)


def fit(value: str, face: ImageFont.FreeTypeFont, width: int) -> str:
    text = ' '.join(str(value).split())
    if face.getlength(text) <= width:
        return text
    while text and face.getlength(text + '…') > width:
        text = text[:-1]
    return text + '…' if text else ''


def saved_time(value: Any) -> str:
    if not value:
        return 'No saved input yet'
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            return 'Save time unavailable'
        return stamp.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except (ValueError, TypeError, OverflowError):
        return 'Save time unavailable'


def compose(game: Image.Image, state: dict[str, Any], theme: str,
            compact: bool, elapsed_ms: int, duration_ms: int) -> Image.Image:
    count = state.get('input_count', 0)
    if type(count) is not int or count < 0:
        raise ValueError('input_count must be a nonnegative integer')
    if theme not in PALETTES or duration_ms <= 0 or not 0 <= elapsed_ms <= duration_ms:
        raise ValueError('invalid theme or replay timing')
    if game.size != (480, 360):
        raise ValueError('expected the existing 480 by 360 replay format')
    c = PALETTES[theme]
    width, height = (320, 444) if compact else (800, 520)
    im = Image.new('RGB', (width, height), c['bg'])
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, width-1, height-1), radius=8,
                        fill=c['bg'], outline=c['border'], width=1)
    d.rounded_rectangle((1, 1, width-2, 50), radius=7, fill=c['surface'])
    d.rectangle((1, 34, width-2, 50), fill=c['surface'])
    d.line((1, 51, width-2, 51), fill=c['border'])

    def text(x, y, value, size=14, color='fg', bold=False, mono=False, available=None):
        face=font(size,bold,mono)
        content=fit(str(value),face,available or (width-x-16))
        d.text((x,y),content,font=face,fill=c.get(color,color),anchor='lt')

    # Terminal icon, not GitHub branding or a fake service-health indicator.
    d.rounded_rectangle((16,16,36,35),radius=4,outline=c['muted'],width=1)
    d.line((21,21,25,25,21,29),fill=c['fg'],width=1)
    d.line((27,30,31,30),fill=c['fg'],width=1)
    text(46,18,'runtime / 01',16,bold=True)
    tagx = width - (80 if compact else 160)
    d.rounded_rectangle((tagx,14,width-16,36),radius=11,
                        fill=c['bg'],outline=c['border'])
    text(tagx+10,19,'REPLAY' if compact else f'REPLAY  {elapsed_ms/1000:04.1f}s',
         11 if compact else 12,color='muted',mono=True)
    # The moving line is a replay playhead; it is never called uptime/CPU/health.
    d.line((1,51,1+int((width-3)*elapsed_ms/duration_ms),51),fill=c['accent'],width=2)

    actor = '@' + str(state.get('last_actor') or 'none')
    command = str(state.get('last_input') or 'none')
    stamp = saved_time(state.get('updated_at'))
    if compact:
        im.paste(game.convert('RGB').resize((288,216), Image.Resampling.NEAREST), (16,56))
        text(16,286,'LAST RECORDED INPUT',11,color='muted',mono=True)
        text(16,306,command,25,bold=True,mono=True,available=182)
        text(211,314,f'{count} inputs',14,color='muted',available=94)
        text(16,341,actor,15,available=288)
        text(16,366,stamp,13,color='muted',available=288)
        d.line((16,393,304,393),fill=c['border'])
        text(16,409,'Your move.',18,bold=True,available=142)
        bx,by,bw,bh=173,401,131,33
        label='Take a turn  →'
        label_size=12
    else:
        im.paste(game.convert('RGB'), (16,68))
        d.line((511,68,511,428),fill=c['border'])
        text(532,71,'LAST RECORDED INPUT',11,color='muted',mono=True)
        text(532,98,command,32,bold=True,mono=True,available=250)
        text(532,145,actor,16,available=248)
        text(532,188,f'{count:03d}',44,bold=True,mono=True,available=170)
        text(710,216,'inputs',13,color='muted',available=74)
        d.line((532,247,780,247),fill=c['border'])
        text(532,265,'THE UNLIKELY MACHINE',11,color='muted',mono=True)
        for y, left, right in [(291,'display','README'),(315,'input','Issues'),
                               (339,'compute','Actions'),(363,'memory','Git')]:
            text(532,y,left,13,color='muted',mono=True,available=115)
            text(670,y,right,13,mono=True,available=110)
        text(532,404,stamp,12,color='muted',available=248)
        d.line((16,448,784,448),fill=c['border'])
        text(20,464,'One save. Everyone plays.',19,bold=True,available=510)
        text(20,493,'Your next move becomes part of the history.',12,color='muted',available=560)
        bx,by,bw,bh=615,466,169,36
        label='Take a turn  →'
        label_size=14
    d.rounded_rectangle((bx,by,bx+bw,by+bh),radius=6,fill=c['button'])
    face=font(label_size,bold=True)
    d.text((bx+bw/2,by+bh/2),label,font=face,fill='#ffffff',anchor='mm')
    return im


def render_panels(source: Path, state: dict[str, Any], output: Path) -> dict:
    """Write four animated panels and matching final-frame stills, plus provenance."""
    source,output=Path(source),Path(output)
    # Validate all inputs before producing any replacement assets.
    with Image.open(source) as image:
        if image.format != 'GIF' or image.n_frames < 2 or image.n_frames > 150:
            raise ValueError('expected a 2-150-frame GIF replay, not a placeholder')
        frames=[]; durations=[]
        for frame in ImageSequence.Iterator(image):
            duration=frame.info.get('duration')
            if not isinstance(duration,int) or duration < 20 or duration % 10:
                raise ValueError('GIF frame duration must be at least 20 ms, in 10 ms units')
            frames.append(frame.convert('RGB'))
            durations.append(duration)
    total=sum(durations)
    if total > 15000:
        raise ValueError('replay exceeds 15-second presentation budget')
    compose(frames[0],state,'dark',False,0,total)
    output.mkdir(parents=True,exist_ok=True)
    manifest={'kind':'recorded-replay','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_frames':len(frames),'duration_ms':total,'input_count':state.get('input_count',0),
              'saved_at':state.get('updated_at'),'last_actor':state.get('last_actor'),
              'last_input':state.get('last_input'),'assets':{}}
    for compact in (False,True):
        layout='mobile' if compact else 'desktop'
        for theme in PALETTES:
            rendered=[]; elapsed=0
            for frame,dt in zip(frames,durations):
                rendered.append(compose(frame,state,theme,compact,elapsed,total))
                elapsed+=dt
            # A shared palette avoids per-frame flickering of type and panel borders.
            w,h=rendered[0].size
            samples=Image.new('RGB',(w,h*3))
            for y,index in enumerate((0,len(rendered)//2,len(rendered)-1)):
                samples.paste(rendered[index],(0,y*h))
            palette=samples.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
            encoded=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rendered]
            stem=f'panel-v4-{layout}-{theme}'
            gif=output/(stem+'.gif')
            encoded[0].save(gif,save_all=True,append_images=encoded[1:],
                            duration=durations,loop=0,optimize=True,disposal=1)
            # Derive the fallback from the actual encoded GIF, not a separate render.
            with Image.open(gif) as check:
                check.seek(check.n_frames-1)
                check.convert('RGB').save(output/(stem+'.png'))
            for ext in ('gif','png'):
                path=output/(stem+'.'+ext)
                manifest['assets'][path.name]={'width':w,'height':h,'bytes':path.stat().st_size,
                                              'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (output/'panel-v4.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    state=json.loads(args.state.read_text(encoding='utf-8'))
    if not isinstance(state,dict):raise ValueError('state must be a JSON object')
    render_panels(args.source,state,args.output)
