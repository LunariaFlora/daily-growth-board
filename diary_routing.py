"""Infer supported monthly diary conventions without guessing between duplicate notes."""
import re
from datetime import date
from pathlib import Path

MONTHS = [
    (re.compile(r'^(\d{2})\.(\d{1,2})复盘$'), 'review'),
    (re.compile(r'^(\d{4})-(\d{2})$'), 'iso'),
    (re.compile(r'^(\d{4})年(\d{1,2})月$'), 'chinese'),
]

def month_info(name):
    for pattern, style in MONTHS:
        m=pattern.fullmatch(name)
        if m:
            y,n=map(int,m.groups());y=y+2000 if style=='review' else y
            if 1<=n<=12:return (y,n,style)
    return None

def month_name(d, style):
    return {'review':f'{d.year%100:02}.{d.month}复盘','iso':f'{d.year:04}-{d.month:02}','chinese':f'{d.year}年{d.month}月'}[style]

def note_info(p, year):
    m=re.match(r'^(\d{4})-(\d{2})-(\d{2})(?!\d)',p.stem)
    style='iso'
    if m:y,mo,da=map(int,m.groups())
    else:
        m=re.match(r'^(\d{1,2})\.(\d{1,2})(?!\d)',p.stem)
        if not m:return None
        y=year;mo,da=map(int,m.groups());style='short'
    try:return date(y,mo,da),style
    except ValueError:return None

def dated_notes(folder, year):
    return [(p,info) for p in folder.glob('*.md') if (info:=note_info(p,year))]

def resolve_diary(root, day):
    root=Path(root);d=date.fromisoformat(day)
    if root.suffix.lower()=='.md':return root
    own=month_info(root.name)
    monthly=[(p,info) for p in root.iterdir() if p.is_dir() and (info:=month_info(p.name))] if root.exists() else []
    if own:
        if own[:2]!=(d.year,d.month):raise ValueError('选择的是其他月份文件夹。请改选日记根目录，以便自动跨月创建')
        folder=root;reference=root;style=own[2]
    elif monthly:
        matches=[(p,m) for p,m in monthly if m[:2]==(d.year,d.month)]
        if len(matches)>1:raise ValueError('同一个月份有多个日记文件夹，请选择唯一的月份目录')
        latest=max(m[:2] for _,m in monthly)
        refs=[(p,m) for p,m in monthly if m[:2]==latest]
        if not matches and len(refs)>1:raise ValueError('月份目录命名存在歧义，请保留唯一的分类格式')
        reference,info=matches[0] if matches else refs[0];style=info[2]
        folder=reference if matches else root/month_name(d,style)
        if dated_notes(root,d.year):raise ValueError('根目录和月份目录都有日记，请明确选择对应的月份文件夹')
    elif dated_notes(root,d.year):
        folder=root;reference=root;style='iso'
    else:
        # Empty/new diary root defaults to the user's established month convention.
        if root.exists() and any(p.is_dir() and not p.name.startswith('.') for p in root.iterdir()):
            raise ValueError('未识别到月份分类。支持 26.10复盘、2026-10、2026年10月；也可直接选择月份文件夹或具体 .md 文件')
        style='review';folder=root/month_name(d,style);reference=folder
    entries=dated_notes(folder,d.year)
    matches=[p for p,(value,_) in entries if value==d]
    if len(matches)>1:raise ValueError(f'{day} 有多篇日记，请保留唯一的当天日记名称后重试')
    if matches:return matches[0]
    examples=entries or dated_notes(reference,d.year)
    if examples:
        latest=max(value for _,(value,_) in examples)
        formats={kind for _,(value,kind) in examples if value==latest}
        if len(formats)>1:raise ValueError('最近日记存在两种日期格式，请统一命名后重试')
        naming=formats.pop()
    else:naming='short' if style=='review' else 'iso'
    name=f'{d.month}.{d.day}.md' if naming=='short' else d.isoformat()+'.md'
    return folder/name
