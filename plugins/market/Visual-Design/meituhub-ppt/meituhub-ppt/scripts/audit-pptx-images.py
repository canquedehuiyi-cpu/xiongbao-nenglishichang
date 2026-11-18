#!/usr/bin/env python3
"""Read-only raster geometry checks; never a visual-quality verdict. Requires Pillow."""
import io, json, posixpath, sys, zipfile
from xml.etree import ElementTree as E
from PIL import Image
N={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def audit(file):
    result={'images_checked':0,'issues':[],'review':[],'render_verified':False}
    with zipfile.ZipFile(file) as z:
        if sum(i.file_size for i in z.infolist())>1024**3: raise ValueError('Archive exceeds inspection limit')
        for name in z.namelist():
            if not name.startswith('ppt/slides/slide') or not name.endswith('.xml'):continue
            rel='ppt/slides/_rels/'+posixpath.basename(name)+'.rels'
            links={r.get('Id'):r.attrib for r in E.fromstring(z.read(rel))} if rel in z.namelist() else {}
            root=E.fromstring(z.read(name)); parents={c:p for p in root.iter() for c in p}
            for idx,pic in enumerate(root.findall('.//p:pic',N),1):
                row={'slide':name,'picture':idx}
                ancestor=parents.get(pic);grouped=False
                while ancestor is not None:
                    grouped |= ancestor.tag=='{'+N['p']+'}grpSp';ancestor=parents.get(ancestor)
                if grouped:
                    result['review'].append(dict(row,reason='Grouped picture transforms require rendered review'));continue
                blip=pic.find('.//a:blip',N);ext=pic.find('./p:spPr/a:xfrm/a:ext',N)
                if blip is None or ext is None:
                    result['review'].append(dict(row,reason='Missing direct raster geometry'));continue
                relation=links.get(blip.get('{'+N['r']+'}embed'),{})
                if not relation or relation.get('TargetMode')=='External':
                    result['review'].append(dict(row,reason='Linked or unresolved image'));continue
                target=relation['Target'];media=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('ppt/slides',target))
                if media not in z.namelist():
                    result['issues'].append(dict(row,reason='Missing embedded image'));continue
                try:
                    with Image.open(io.BytesIO(z.read(media))) as im:w,h=im.size
                except OSError:
                    result['review'].append(dict(row,reason='Unsupported image encoding, including vector images'));continue
                crop=pic.find('./p:blipFill/a:srcRect',N);c={} if crop is None else crop.attrib
                cw=1-(float(c.get('l',0))+float(c.get('r',0)))/100000
                ch=1-(float(c.get('t',0))+float(c.get('b',0)))/100000
                dx,dy=float(ext.get('cx','0')),float(ext.get('cy','0'))
                if min(cw,ch,dx,dy,w,h)<=0:
                    result['issues'].append(dict(row,reason='Invalid crop or display extent'));continue
                error=abs((dx/dy)/((w*cw)/(h*ch))-1);result['images_checked']+=1
                if error>.025:result['issues'].append(dict(row,reason='Aspect ratio mismatch',media=media,relative_error=round(error,4)))
    return result
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: audit-pptx-images.py FILE.pptx')
    result=audit(sys.argv[1]);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(2 if result['issues'] else 0)
