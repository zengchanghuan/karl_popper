from pathlib import Path
import re,html,zipfile,uuid,xml.etree.ElementTree as ET,posixpath
ROOT=Path(__file__).resolve().parents[1]
FILES=[('前言','foreword'),('哈维尔序言','havel-preface'),('贡布里希出版回忆（部分）','gombrich-recollections'),('致谢与第一版序言','acknowledgements-and-first-preface'),('第二版序言','second-preface'),('导论','introduction'),('第一卷题辞及第1章','ch01'),('第2章 赫拉克利特','ch02'),('第3章 理念理论','ch03'),('第6章 极权主义的正义','ch06'),('第7章 领导原则','ch07'),('第8章 哲学王','ch08'),('第9章 唯美主义、完美主义与乌托邦主义','ch09'),('第10章 开放社会及其敌人','ch10'),('第一卷补遗Ⅰ—Ⅳ','vol1-addenda')]
assets={};report=[]
def clean(slug):
 s=(ROOT/'translations'/f'open-society-{slug}-zh.md').read_text()
 if slug=='foreword':s=s[s.index('## 前言：原文完整翻译'):]
 elif slug not in ['havel-preface','vol1-addenda','ch09','ch10','second-preface']:
  ix=s.find('\n## ')
  if ix>=0:s=s[ix+1:]
 # Remove repository metadata and per-turn progress only; keep translator uncertainty separately.
 lines=[]
 for l in s.splitlines():
  if l.startswith(('〔','原文：','来源：','已译：','用户最新要求','本章共','下一位置：')):continue
  lines.append(l)
 s='\n'.join(lines)
 if slug.startswith('ch') and slug!='ch01':
  blocks=re.split(r'(?m)^(#{1,3} .*)$',s)
  main=[blocks[0]];notes=[];isnote=False;seen=set()
  for i in range(1,len(blocks),2):
   h,b=blocks[i],blocks[i+1]
   isnote=bool(re.search('原注',h))
   if isnote:notes.extend([h,b]);continue
   h=re.sub(r'（(?:续[^）]*|第\d+[^）]*)）','',h)
   if h in seen:main.append(b)
   else:main.extend([h,b]);seen.add(h)
  s='\n'.join(main)+ '\n\n# 本章原注\n'+'\n'.join(notes)
 return s.strip()
def inline(s):
 s=html.escape(s)
 def im(m):
  target=html.unescape(m[2]);p=(ROOT/'translations'/target).resolve()
  if not p.is_file():raise ValueError('Missing image '+str(p))
  name='assets/'+p.name;assets[name]=p.read_bytes()
  return '<img src="'+name+'" alt="'+m[1]+'" />'
 s=re.sub(r'!\[([^]]*)\]\(([^)]+)\)',im,s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 s=s.replace('\\*','&#42;')
 s=re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)',r'<em>\1</em>',s)
 return s

def render(s):
 out=[];heads=[];serial=0
 for block in re.split(r'\n\s*\n',s):
  if not block.strip():continue
  lines=block.splitlines()
  if lines[0].startswith('#'):
   # Treat multiple adjacent headings individually.
   for l in lines:
    m=re.match(r'^(#{1,6})\s+(.*)',l)
    if m:
     serial+=1;aid='h'+str(serial);level=min(len(m[1])+1,6);t=m[2]
     out.append(f'<h{level} id="{aid}">{inline(t)}</h{level}>');heads.append((aid,t))
    else:out.append('<p>'+inline(l)+'</p>')
  elif all(l.startswith('>') for l in lines):out.append('<blockquote><p>'+'<br />'.join(inline(l.lstrip('> ')) for l in lines)+'</p></blockquote>')
  elif all(l.startswith('|') for l in lines):
   rows=[]
   for l in lines:
    if re.fullmatch(r'[| :\-]+',l):continue
    rows.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in l.strip('|').split('|'))+'</tr>')
   out.append('<table>'+''.join(rows)+'</table>')
  else:out.append('<p>'+'<br />'.join(inline(l) for l in lines)+'</p>')
 body='\n'.join(out)
 # Anchors for author notes. Headings provide anchor when number was only in heading.
 notes={}
 for m in re.finditer(r'<p><strong>(\d+)[.．](?:</strong>|（)',body):
  n=m[1];notes.setdefault(n,'n'+n)
 for n,aid in notes.items():body=re.sub(r'(<p>)(<strong>'+n+r'[.．])',r'<p id="'+aid+r'">\2',body,count=1)
 for aid,t in heads:
  m=re.fullmatch(r'(?:对应)?原注(\d+)',t)
  if m and m[1] not in notes:
   notes[m[1]]=aid
 refs={}
 def ref(m):
  n=m[1]
  if n not in notes:return m[0]
  k=refs.get(n,0)+1;refs[n]=k
  return f'<a id="r{n}-{k}" href="#{notes[n]}" epub:type="noteref">〔{n}〕</a>'
 body=re.sub(r'〔(\d+)〕',ref,body)
 for n,k in refs.items():
  back=' '.join(f'<a href="#r{n}-{i}">返回正文{(" "+str(i)) if k>1 else ""}</a>' for i in range(1,k+1))
  body=body.replace(f'id="{notes[n]}">',f'id="{notes[n]}"><span class="back">{back}</span> ',1)
 return body,heads,len(refs)
CSS='body{font-family:serif;line-height:1.75;margin:5%;}p{text-indent:2em;margin:.8em 0;}h1,h2,h3{line-height:1.35;}blockquote{margin:1em 1.5em;}blockquote p{text-indent:0;}img{max-width:100%;height:auto;}table{border-collapse:collapse;width:100%;}td{border:1px solid #aaa;padding:.4em;}a{color:#315a89;text-decoration:none;}.back{font-size:.75em;}code{overflow-wrap:anywhere;}'
def xhtml(title,body):return '<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN"><head><title>'+html.escape(title)+'</title><link rel="stylesheet" href="style.css" /></head><body>'+body+'</body></html>'
intro='''# 开放社会及其敌人：中文学习译文合集

作者：卡尔·波普尔。前置文字分别保留原作者署名。本书是依据用户提供的2011年Routledge Classics英文EPUB逐段生成的中文学习译文，供个人复习，不是已出版的中文译本。

本合集尚非全书。已包含：前言、哈维尔序言、贡布里希出版回忆已译部分、致谢和第一、第二版序言、导论、第1—2章、第3章全部正文及原注、第6—10章及对应已译原注、第一卷补遗Ⅰ—Ⅳ。

未包含：第4—5章及原注、第二卷第11—25章及其原注与补遗。贡布里希回忆剩余18段按用户要求省略。译文生成与电子书整理不代表用户已读或掌握。

阅读版将已译正文的连续片段合并，将第2—10章的原注集中到各章末。注号提供跳转及返回链接。原有图示保留。章目中的缺失不作隐瞒，也不以概述补写。

待核查：第10章注27的页码“III”；注59（2）的“the known”；补遗原注1中的“1932年”；补遗B节希腊动词词形“archōn”。均按本地文件记录，不将未核实修正冒充原文。各处页码为原作者引用的版本页码，不能当作本EPUB页码。
'''
items=[]
b,h,r=render(intro);items.append(('about','编制说明与覆盖范围',b,h))
for title,slug in FILES:
 s=clean(slug);b,h,r=render(s);items.append((slug,title,b,h));report.append({'file':slug,'characters':len(s),'headings':len(h),'linked_note_numbers':r})
uid='urn:uuid:'+str(uuid.uuid4());payload={'OEBPS/style.css':CSS.encode()}
nav=[]
for slug,title,b,heads in items:
 name=slug+'.xhtml';payload['OEBPS/'+name]=xhtml(title,b).encode()
 sub=''.join('<li><a href="'+name+'#'+a+'">'+html.escape(t)+'</a></li>' for a,t in heads)
 nav.append('<li><a href="'+name+'">'+html.escape(title)+'</a><ol>'+sub+'</ol></li>')
payload['OEBPS/nav.xhtml']=xhtml('目录','<nav epub:type="toc" id="toc"><h1>目录</h1><ol>'+''.join(nav)+'</ol></nav>').encode()
manifest=['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>','<item id="css" href="style.css" media-type="text/css"/>'];spine=[]
for i,(slug,title,b,h) in enumerate(items):manifest.append(f'<item id="s{i}" href="{slug}.xhtml" media-type="application/xhtml+xml"/>');spine.append(f'<itemref idref="s{i}"/>')
for i,(n,data) in enumerate(assets.items()):
 payload['OEBPS/'+n]=data;manifest.append(f'<item id="a{i}" href="{n}" media-type="image/jpeg"/>')
payload['OEBPS/content.opf']=('''<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">'''+uid+'''</dc:identifier><dc:title>开放社会及其敌人 · 中文学习译文合集（尚非全书）</dc:title><dc:creator>卡尔·波普尔</dc:creator><dc:language>zh-CN</dc:language><meta property="dcterms:modified">2026-10-13T00:00:00Z</meta></metadata><manifest>'''+''.join(manifest)+'</manifest><spine>'+''.join(spine)+'</spine></package>').encode()
payload['META-INF/container.xml']=b'<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
out=ROOT/'exports/open-society-zh-study-collected.epub'
with zipfile.ZipFile(out,'w') as z:
 z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
 for n,d in payload.items():z.writestr(n,d,compress_type=zipfile.ZIP_DEFLATED)
# Validate XML and every internal hyperlink/image target including fragments.
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 roots={n:ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith(('.xhtml','.opf','.xml'))}
 ids={n:{e.attrib['id'] for e in r.iter() if 'id' in e.attrib} for n,r in roots.items()}
 links=0
 for n,r in roots.items():
  for e in r.iter():
   for attr in ['href','src']:
    link=e.attrib.get(attr)
    if not link or '://' in link:continue
    path,sep,frag=link.partition('#');target=posixpath.normpath(posixpath.join(posixpath.dirname(n),path)) if path else n
    assert target in z.namelist(),(n,link)
    if frag:assert frag in ids.get(target,set()),(n,link)
    links+=1
report={'output':str(out),'size_bytes':out.stat().st_size,'documents':len(items),'assets':len(assets),'validated_internal_links':links,'sources':report}
(ROOT/'exports/open-society-epub-validation.json').write_text(__import__('json').dumps(report,ensure_ascii=False,indent=2))
print(__import__('json').dumps({k:v for k,v in report.items() if k!='sources'},ensure_ascii=False))
