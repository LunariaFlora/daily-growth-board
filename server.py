"""Private, dependency-free local daily board. Bind only to loopback."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import copy, hashlib, json, mimetypes, os, re, secrets, socket, subprocess, sys, threading, time
from urllib.parse import urlsplit, parse_qs, quote

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('BOARD_DATA', str(ROOT / 'data')))
VAULT = Path(os.environ.get('BOARD_VAULT', str(DATA/'notes')))
QUOTES = DATA / '个人金句.md'
TZ = timezone(timedelta(hours=8))
APP_ID = 'lunaria-growth-board-v1'
LOCK = threading.RLock()
TOKEN = secrets.token_urlsafe(32)
COLUMNS = {'tech': '技术栈积累', 'project': '实习 / 项目', 'school': '学校课业'}
STATE_FILE = DATA / 'state.json'
STATE = None
LAST_EDIT = {}
SYNC_ERRORS = {}
DISPLAY_DEFAULTS = {'motto': '把今天，写进长期。', 'quoteMode': 'daily', 'fixedQuote': '让每一天，都留下一点积累。', 'quoteLayout': 'poster', 'appIcon':'01', 'goalTitle':'', 'goalDate':''}

def now(): return datetime.now(TZ)
def today(): return (now() - timedelta(hours=4)).date().isoformat()
def tomorrow(day): return (date.fromisoformat(day) + timedelta(days=1)).isoformat()
def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def init():
    global STATE, QUOTES
    DATA.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        STATE = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    else:
        STATE = {'version': 1, 'settings': {'style': '01', 'times': ['21:00'], 'enabled': True},
                 'days': {}, 'synced': {}, 'quoteDays': {}}
        atomic(STATE_FILE, STATE)
    defaults_file=DATA/'local-defaults.json'
    local_defaults=json.loads(defaults_file.read_text(encoding='utf-8-sig')) if defaults_file.exists() else {}
    for key, value in DISPLAY_DEFAULTS.items(): STATE['settings'].setdefault(key, local_defaults.get(key,value))
    STATE['settings'].setdefault('columnNames', dict(COLUMNS))
    STATE['settings'].setdefault('obsidianPath', local_defaults.get('notesPath',str(VAULT)))
    if 'quotesPath' not in STATE['settings']:
        candidate=Path(STATE['settings']['obsidianPath'])/'个人金句.md'
        STATE['settings']['quotesPath']=str(candidate if candidate.is_file() else QUOTES)
    QUOTES=Path(STATE['settings']['quotesPath'])
    if VAULT==DATA/'notes':VAULT.mkdir(parents=True,exist_ok=True)
    if QUOTES==DATA/'个人金句.md' and not QUOTES.exists():
        QUOTES.write_text((ROOT/'default-quotes.md').read_text(encoding='utf-8-sig'),encoding='utf-8')
    persist()

def persist():
    # Daily local backup; all writes use atomic replacement.
    backup = DATA / 'backups' / (today() + '.json')
    if STATE_FILE.exists() and not backup.exists():
        backup.parent.mkdir(exist_ok=True)
        backup.write_bytes(STATE_FILE.read_bytes())
    atomic(STATE_FILE, STATE)

def blank(): return {'revision': 0, 'review': {k: '' for k in COLUMNS}, 'tasks': {k: [] for k in COLUMNS}}
def daydata(day): return STATE['days'].get(day, blank())
def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError('日期格式无效')
    date.fromisoformat(value)
    return value

def parse_quotes():
    if not QUOTES.exists(): return []
    records = []
    for section in re.split(r'^##\s+', re.sub(r'<!--.*?-->', '', QUOTES.read_text(encoding='utf-8-sig'), flags=re.S), flags=re.M)[1:]:
        lines = section.splitlines()
        text = '\n'.join(re.sub(r'^> ?', '', s) for s in lines[1:] if s.startswith('>')).strip()
        source = next((s[len('来源：'):].strip() for s in lines if s.startswith('来源：')), '')
        if text: records.append({'id': hashlib.sha256(text.encode()).hexdigest()[:16], 'text': text, 'source': source})
    return records

def daily_quote(day):
    quotes = parse_quotes()
    if not quotes: return {'text': '在「个人金句.md」中写下第一句想提醒自己的话。', 'source': ''}
    chosen = STATE['quoteDays'].get(day)
    found = next((q for q in quotes if q['id'] == chosen), None)
    if not found:
        previous = STATE['quoteDays'].get((date.fromisoformat(day) - timedelta(days=1)).isoformat())
        pool = [q for q in quotes if q['id'] != previous] or quotes
        found = secrets.choice(pool)
        STATE['quoteDays'][day] = found['id']; persist()
    return found

def diary_path(day):
    from diary_routing import resolve_diary
    path = resolve_diary(STATE['settings'].get('obsidianPath', str(VAULT)), day)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def sync_snapshot(day):
    current = daydata(day); nxt = daydata(tomorrow(day))
    return {'review': current['review'], 'todayTasks': current['tasks'], 'tomorrowTasks': nxt['tasks']}

def nonempty(snapshot):
    return any(v.strip() for v in snapshot['review'].values()) or any(snapshot['todayTasks'].values()) or any(snapshot['tomorrowTasks'].values())

def sync_day(day):
    with LOCK:
        snapshot = copy.deepcopy(sync_snapshot(day))
        previous = STATE['synced'].get(day, {})
        if not nonempty(snapshot) and not previous: return {'status': 'empty'}
        path = diary_path(day)
        names = STATE['settings'].get('columnNames', COLUMNS)
        sections = []
        for col, title in names.items():
            bits = []
            if snapshot['review'][col].strip(): bits += ['**今日复盘**', snapshot['review'][col]]
            for key, label in [('todayTasks', '今日任务'), ('tomorrowTasks', f'明日任务 · {tomorrow(day)}')]:
                if snapshot[key][col]:
                    bits += ['**' + label + '**', '\n'.join(f"- [{'x' if t['done'] else ' '}] {t['text']}" for t in snapshot[key][col])]
            if bits: sections.append('### ' + title + '\n\n' + '\n\n'.join(bits))
        body = ('\n## 成长看板 · ' + day + '\n\n' + ('\n\n'.join(sections) or '（看板内容已清空）') + '\n').encode('utf-8')
        # Markers delimit only the generated section, never the surrounding diary.
        prefix = f'<!-- growth-board:start:{day}:'.encode()
        end = f'<!-- growth-board:end:{day} -->'.encode()
        digest = hashlib.sha256(body).hexdigest()
        block = prefix + digest.encode() + b' -->' + body + end
        path.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0)), 'r+b') as f:
            f.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 0x7fffffff)
            try:
                f.seek(0); existing = f.read()
                starts = list(re.finditer(re.escape(prefix) + rb'([a-f0-9]{64}) -->', existing))
                if prefix in existing and not starts: raise ValueError('看板区域标记被修改，请恢复标记后再同步')
                if len(starts)>1 or existing.count(end)>1: raise ValueError('日记中存在重复的看板区域，请检查后重试')
                if starts:
                    start = starts[0]; stop = existing.find(end, start.end())
                    if stop<0: raise ValueError('看板区域结束标记缺失，请恢复后再同步')
                    current = existing[start.end():stop]
                    if hashlib.sha256(current).hexdigest().encode()!=start.group(1):
                        raise ValueError('看板同步区域被手动修改。请先把手写内容移到区域外，并恢复区域内容后再同步；原文未改动')
                    updated = existing[:start.start()] + block + existing[stop+len(end):]
                else:
                    if end in existing: raise ValueError('看板区域开始标记缺失，请恢复后再同步')
                    if previous.get('managed') and previous.get('path')==str(path):
                        raise ValueError('原来的看板区域已被移除，请恢复标记，避免重复创建到文末')
                    # Keep legacy generated history; anchor new updates beside its first marker.
                    legacy = re.search(rb'<!-- growth-board:' + day.encode() + rb':\d+:[a-f0-9]+ -->', existing)
                    pos = legacy.end() if legacy else len(existing)
                    updated = existing[:pos] + b'\n\n' + block + b'\n' + existing[pos:]
                if updated != existing:
                    if existing:
                        backup = DATA/'diary-backups'/(day+'-'+str(time.time_ns())+'.md')
                        backup.parent.mkdir(parents=True, exist_ok=True); backup.write_bytes(existing)
                    f.seek(0)
                    if f.read()!=existing: raise ValueError('日记正在被其他程序修改，请稍后同步')
                    f.seek(0);f.write(updated);f.truncate();f.flush();os.fsync(f.fileno())
            finally:
                if os.name == 'nt':
                    f.seek(0);msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 0x7fffffff)
        STATE['synced'][day] = {'snapshot':snapshot, 'path':str(path), 'at':now().isoformat(), 'managed':True}
        persist();SYNC_ERRORS.pop(day, None)
        return {'status':'synced' if updated!=existing else 'unchanged', 'path':str(path)}


def validate_entry(body):
    day = valid_day(body['day']); col = body['column']; field = body['field']
    if col not in COLUMNS or field not in ('review', 'tasks'): raise ValueError('栏目无效')
    value = body['value']
    if field == 'review':
        if not isinstance(value, str) or len(value) > 40000: raise ValueError('复盘内容过长')
    else:
        if not isinstance(value, list) or len(value) > 100: raise ValueError('任务数量过多')
        ids = set()
        for t in value:
            if set(t) != {'id', 'text', 'done'} or not isinstance(t['id'], str) or not re.fullmatch(r'[\w-]{1,80}', t['id']): raise ValueError('任务格式无效')
            if not isinstance(t['text'], str) or not 0 < len(t['text']) <= 1000 or '\n' in t['text'] or type(t['done']) is not bool: raise ValueError('任务内容无效')
            if t['id'] in ids: raise ValueError('任务编号重复')
            ids.add(t['id'])
    return day, col, field, value

def save_entry(body):
    with LOCK:
        day, col, field, value = validate_entry(body)
        current = daydata(day)
        # Compare exact field base, so independent edits in other columns never conflict.
        if current[field][col] != body.get('base'):
            return 409, {'error': '此栏已在另一个窗口修改。你的草稿已保留，请刷新后对照。', 'current': current[field][col]}
        owner = valid_day(body.get('owner', day))
        if owner not in (day, (date.fromisoformat(day)-timedelta(days=1)).isoformat()): raise ValueError('记录日期不匹配')
        entry = copy.deepcopy(current); entry[field][col] = value; entry['revision'] += 1
        STATE['days'][day] = entry; persist()
        LAST_EDIT[owner] = time.time()
        # Persist pending so closing the browser or restarting cannot drop diary synchronization.
        STATE.setdefault('pending', {})[owner] = time.time(); persist()
        return 200, {'saved': True, 'entry': entry}

def apply_schedule(settings):
    if os.environ.get('BOARD_TEST') == '1': return
    settings_file = DATA / 'schedule-request.json'; atomic(settings_file, settings)
    run = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'schedule.ps1'), '-Config', str(settings_file)], capture_output=True, creationflags=0x08000000, timeout=45)
    if run.returncode: raise RuntimeError('Windows 提醒任务更新失败，原设置仍保留。请查看本地日志。')

def display_settings(body):
    settings=copy.deepcopy(STATE['settings'])
    settings.update({k:body[k] for k in ('times','enabled','style','columnNames','obsidianPath','quotesPath',*DISPLAY_DEFAULTS) if k in body})
    if settings['style'] not in ['01','02','03','04','05'] or type(settings['enabled']) is not bool: raise ValueError('设置无效')
    for key,limit in [('motto',120),('fixedQuote',3000)]:
        if not isinstance(settings[key],str) or len(settings[key])>limit: raise ValueError('展示文字过长')
    if settings['quoteMode'] not in ('daily','fixed') or settings['quoteLayout'] not in ('poster','type','hidden'): raise ValueError('展示方式无效')
    if settings['appIcon'] not in ('01','02','03','04','05'):raise ValueError('请选择有效的应用图标')
    if settings['quoteMode']=='fixed' and not settings['fixedQuote'].strip(): raise ValueError('请填写固定展示的那句话')
    if not isinstance(settings['goalTitle'],str) or len(settings['goalTitle'])>80: raise ValueError('近期目标请填写 80 字以内')
    if not isinstance(settings['goalDate'],str): raise ValueError('请选择有效的目标日期')
    if bool(settings['goalTitle'].strip()) != bool(settings['goalDate']): raise ValueError('请同时填写目标和日期，或同时清空')
    if settings['goalDate']:
        import datetime
        try:
            parsed=datetime.date.fromisoformat(settings['goalDate'])
            if parsed.isoformat()!=settings['goalDate']: raise ValueError()
        except ValueError: raise ValueError('请选择有效的目标日期')
    settings['goalTitle']=settings['goalTitle'].strip()
    names=settings['columnNames']
    if not isinstance(names,dict) or set(names)!=set(COLUMNS) or any(not isinstance(v,str) or not v.strip() or len(v)>30 or '\n' in v or '\r' in v for v in names.values()): raise ValueError('请为三个栏目填写 1–30 字名称')
    settings['columnNames']={k:names[k].strip() for k in COLUMNS}
    raw_quote=settings.get('quotesPath','')
    if not isinstance(raw_quote,str): raise ValueError('请填写金句 Markdown 文件路径')
    quote_path=Path(raw_quote.strip().strip(chr(34))) if raw_quote.strip() else DATA/'个人金句.md'
    if not quote_path.is_absolute() or quote_path.suffix.lower()!='.md': raise ValueError('金句路径须为完整的 .md 文件路径')
    if not quote_path.parent.is_dir(): raise ValueError('金句所在文件夹不存在，请先创建文件夹')
    if quote_path.exists():
        if not quote_path.is_file(): raise ValueError('金句路径必须指向文件')
        try: quote_path.read_text(encoding='utf-8-sig')
        except UnicodeError: raise ValueError('金句文档请保存为 UTF-8 编码')
    settings['quotesPath']=str(quote_path)
    raw=settings['obsidianPath']
    if not isinstance(raw,str) or not raw.strip(): raise ValueError('请填写 Obsidian 文件夹或 Markdown 文件的完整路径')
    target=Path(raw.strip().strip('"'))
    if not target.is_absolute() or '..' in target.parts: raise ValueError('请使用完整的本地绝对路径')
    if target.exists() and not target.is_dir() and target.suffix.lower()!='.md': raise ValueError('请选择文件夹或 .md 文件')
    if not target.exists() and target.suffix.lower()!='.md' and str(target)!=STATE['settings']['obsidianPath']: raise ValueError('文件夹不存在，请先创建或检查路径')
    if target.suffix.lower()=='.md' and not target.parent.is_dir(): raise ValueError('Markdown 文件的上级文件夹不存在')
    settings['obsidianPath']=str(target)
    times=settings['times']
    if not isinstance(times,list) or not 1<=len(times)<=8 or any(not isinstance(t,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',t) for t in times): raise ValueError('请输入 1–8 个有效的提醒时间')
    settings['times']=sorted(set(times))
    return settings

def worker():
    while True:
        time.sleep(3)
        with LOCK: pending = dict(STATE.get('pending', {}))
        for day, changed in pending.items():
            if time.time() - changed < 25: continue
            try:
                sync_day(day)
                with LOCK: STATE.get('pending', {}).pop(day, None); persist()
            except Exception as e: SYNC_ERRORS[day] = str(e)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send(self, code, data, ctype='application/json; charset=utf-8'):
        raw = json.dumps(data, ensure_ascii=False).encode() if 'application/json' in ctype else data
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'")
        self.end_headers(); self.wfile.write(raw)
    def local(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
    def do_GET(self):
        if not self.local(): return self.send(403, {'error':'仅限本机访问'})
        u = urlsplit(self.path)
        try:
            if u.path == '/api/health': return self.send(200, {'app': APP_ID, 'version':6})
            if u.path == '/favicon.ico':
                name=STATE['settings'].get('appIcon','01')
                return self.send(200,(ROOT/'public'/'icons'/('icon-'+name+'.ico')).read_bytes(),'image/x-icon')
            if u.path == '/api/diary-target':
                from diary_routing import resolve_diary
                query=parse_qs(u.query);raw=query.get('path',[''])[0].strip().strip('"');target=Path(raw)
                if not raw or not target.is_absolute() or '..' in target.parts:raise ValueError('请填写完整的本地路径')
                if target.exists() and not target.is_dir() and target.suffix.lower()!='.md':raise ValueError('请选择文件夹或 .md 文件')
                if not target.exists() and target.suffix.lower()!='.md':raise ValueError('文件夹不存在，请检查路径')
                if target.suffix.lower()=='.md' and not target.parent.is_dir():raise ValueError('文件的上级文件夹不存在')
                result=resolve_diary(target, valid_day(query.get('day',[today()])[0]))
                return self.send(200,{'path':str(result),'exists':result.exists()})
            if u.path == '/api/state':
                day = valid_day(parse_qs(u.query).get('day', [today()])[0])
                with LOCK:
                    payload = {'capabilities':['anchored-sync','custom-columns'], 'token':TOKEN, 'today':today(), 'day':day, 'next':tomorrow(day), 'entry':copy.deepcopy(daydata(day)), 'nextEntry':copy.deepcopy(daydata(tomorrow(day))), 'settings':STATE['settings'], 'quote':daily_quote(day), 'sync':STATE['synced'].get(day,{}).get('at'), 'syncError':SYNC_ERRORS.get(day), 'pending':day in STATE.get('pending',{}), 'quotesPath':str(QUOTES)}
                    return self.send(200,payload)
            if u.path == '/api/quotes':
                with LOCK: return self.send(200, {'quotes':parse_quotes(), 'path':str(QUOTES)})
            if u.path == '/api/export':
                with LOCK: return self.send(200,STATE)
            if u.path == '/':
                self.send_response(302); self.send_header('Location',f"/styles/v{STATE['settings']['style']}/index.html"); self.end_headers(); return
            decoded = __import__('urllib.parse', fromlist=['unquote']).unquote(u.path)
            path = (ROOT/'public'/decoded.lstrip('/')).resolve()
            if not path.is_relative_to((ROOT/'public').resolve()) or not path.is_file(): return self.send(404,{'error':'页面不存在'})
            return self.send(200, path.read_bytes(), (mimetypes.guess_type(str(path))[0] or 'application/octet-stream') + ('; charset=utf-8' if path.suffix in ('.html','.css','.js','.svg') else ''))
        except (ValueError,KeyError) as e: self.send(400,{'error':str(e)})
        except Exception: self.send(500,{'error':'本地文件读取失败，请检查文件权限或数据文件'})
    def do_POST(self):
        global QUOTES
        if not self.local() or self.headers.get('X-Board-Token') != TOKEN or self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}'):
            return self.send(403,{'error':'请求来源无效，请刷新页面'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length > 600000: return self.send(413,{'error':'内容过长'})
            body=json.loads(self.rfile.read(length))
            if self.path == '/api/entry':
                code,data=save_entry(body); return self.send(code,data)
            if self.path == '/api/open-quotes':
                if os.name=='nt' and os.environ.get('BOARD_TEST')!='1':
                    try:os.startfile(str(QUOTES))
                    except OSError:subprocess.Popen(['notepad.exe',str(QUOTES)])
                return self.send(200,{'opened':True})
            if self.path == '/api/sync':
                day=valid_day(body['day']); result=sync_day(day)
                with LOCK: STATE.get('pending',{}).pop(day,None);persist()
                return self.send(200,result)
            if self.path == '/api/settings':
                with LOCK:
                    settings=display_settings(body)
                    if settings['times']!=STATE['settings']['times'] or settings['enabled']!=STATE['settings']['enabled']: apply_schedule(settings)
                    quote_path=Path(settings['quotesPath'])
                    if not quote_path.exists():
                        with quote_path.open('x',encoding='utf-8') as f: f.write((ROOT/'default-quotes.md').read_text(encoding='utf-8-sig'))
                    QUOTES=quote_path
                    STATE['settings']=settings
                    if nonempty(sync_snapshot(today())): STATE.setdefault('pending',{})[today()]=time.time()
                    persist()
                    return self.send(200,settings)
            return self.send(404,{'error':'操作不存在'})
        except (ValueError,KeyError,TypeError) as e: self.send(400,{'error':str(e)})
        except Exception as e: self.send(500,{'error':str(e)})

class ExclusiveServer(ThreadingHTTPServer):
    allow_reuse_address = False
    def server_bind(self):
        if os.name == 'nt': self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def serve():
    DATA.mkdir(parents=True,exist_ok=True)
    # One process per installation, even when two launchers run simultaneously.
    lockfile=(DATA/'server.lock').open('a+b'); lockfile.seek(0);lockfile.write(b'1');lockfile.flush();lockfile.seek(0)
    if os.name=='nt':
        import msvcrt
        try: msvcrt.locking(lockfile.fileno(),msvcrt.LK_NBLCK,1)
        except OSError: return
    init()
    runtime=DATA/'runtime.json'; preferred=47831
    if runtime.exists():
        try: preferred=int(json.loads(runtime.read_text())['port'])
        except Exception: pass
    server=None
    for port in dict.fromkeys([preferred]+list(range(47831,47852))):
        try: server=ExclusiveServer(('127.0.0.1',port),Handler);break
        except OSError: continue
    if server is None: raise RuntimeError('本地端口暂不可用')
    atomic(runtime,{'port':server.server_port,'pid':os.getpid(),'app':APP_ID,'url':f'http://127.0.0.1:{server.server_port}'})
    threading.Thread(target=worker,daemon=True).start()
    server.serve_forever()

if __name__=='__main__':
    try: serve()
    except Exception:
        import traceback
        DATA.mkdir(parents=True,exist_ok=True)
        with (DATA/'server-error.log').open('a',encoding='utf-8') as f: traceback.print_exc(file=f)
        raise
