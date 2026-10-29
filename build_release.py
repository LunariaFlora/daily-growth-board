"""Build a clean Windows portable distribution from an explicit allowlist."""
from pathlib import Path
import zipfile, hashlib, json

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'日有所积-Windows便携版.zip'
FILES=['README.md','COPYRIGHT.md','THIRD_PARTY_NOTICES.md','default-quotes.md','server.py','diary_routing.py','open.ps1','schedule.ps1','install.ps1','bootstrap.ps1','restart.ps1','更新并打开.cmd','启动日有所积.cmd','日有所积.exe']
README='''日有所积 · Windows 10/11 64 位便携版

1. 完整解压到一个普通文件夹。
2. 双击「日有所积.exe」。无需安装 Python、Node 或 Obsidian。
3. 右上角设置可修改栏目、主题、应用图标和提醒时间。

默认记录保存在本文件夹的 data 中，笔记同步到 data/notes。
可以在「笔记同步」中选择自己的本地 Markdown 日记根目录。
点旁边的 i 查看月份识别规则与说明图。
个人金句位于 data/个人金句.md，可用任意文本编辑器修改。

首次启动会尝试设置当前用户的登录启动和每日提醒。若系统不允许注册计划任务，仍可手动打开；请检查 data/setup-warning.log。
优先使用 Chrome，未安装时使用 Windows 自带 Edge。
关闭窗口后，后台仍负责保存后的笔记同步。
复制或移动文件夹后再次启动，会更新提醒入口。

请勿在压缩包内部直接运行，不要单独移动 exe。
分享软件请分享原始便携包，不要连同自己的 data 文件夹一起发送。

运行环境：Python 3.13.17 Windows x64 embeddable package。
来源：https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip
Python 授权文件保留在 runtime/LICENSE.txt。
'''

def build():
    files=[ROOT/name for name in FILES]
    files += [p for folder in ['public','runtime','docs'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='icon-05-night.ico']
    if any(not p.exists() for p in files):raise RuntimeError('Required distribution file missing')
    if not (ROOT/'runtime'/'pythonw.exe').is_file():raise RuntimeError('Embedded runtime missing')
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'日有所积/'+str(p.relative_to(ROOT)).replace('\\','/'))
        z.writestr('日有所积/使用说明.txt',README)
        z.writestr('日有所积/文件校验.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    digest=hashlib.sha256(OUT.read_bytes()).hexdigest()
    OUT.with_suffix(OUT.suffix+'.sha256').write_text(digest+'  '+OUT.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(OUT),'files':len(files),'bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},ensure_ascii=False))
if __name__=='__main__':build()
