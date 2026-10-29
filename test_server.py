import os, tempfile, unittest, json, copy
from unittest.mock import patch
from pathlib import Path
os.environ['BOARD_TEST']='1'
import server as s

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        s.DATA=Path(self.temp.name)/'data'; s.VAULT=Path(self.temp.name)/'vault';s.QUOTES=s.DATA/'个人金句.md';s.STATE_FILE=s.DATA/'state.json';s.LAST_EDIT.clear();s.init()
    def save(self,day,field,value,base=None,owner=None):
        return s.save_entry({'day':day,'column':'tech','field':field,'value':value,'base':base if base is not None else ('' if field=='review' else []),'owner':owner or day})
    def test_same_month_different_years_stay_separate(self):
        from diary_routing import resolve_diary
        for y in [25,26]:
            folder=s.VAULT/f'{y}.8复盘';folder.mkdir(parents=True);(folder/'8.28.md').write_text(str(y))
        self.assertEqual(resolve_diary(s.VAULT,'2025-08-28'),s.VAULT/'25.8复盘'/'8.28.md')
        self.assertEqual(resolve_diary(s.VAULT,'2026-08-28'),s.VAULT/'26.8复盘'/'8.28.md')

    def test_single_goal_validation_and_clear(self):
        value=s.display_settings({'goalTitle':'完成项目','goalDate':'2026-11-16'})
        self.assertEqual(value['goalDate'],'2026-11-16')
        for body in [{'goalTitle':'目标','goalDate':''},{'goalTitle':'','goalDate':'2026-11-16'},{'goalTitle':'目标','goalDate':'2026-02-30'},{'goalTitle':'a'*81,'goalDate':'2026-11-16'}]:
            with self.assertRaises(ValueError):s.display_settings(body)
        value=s.display_settings({'goalTitle':'','goalDate':''})
        self.assertEqual(value['goalTitle'],'')

    def test_day_rolls_at_four_without_erasing_records(self):
        self.save('2026-10-27','review','深夜的记录')
        for moment,expected in [('2026-10-27T23:59:59+08:00','2026-10-27'),('2026-10-28T00:00:00+08:00','2026-10-27'),('2026-10-28T03:59:59+08:00','2026-10-27'),('2026-10-28T04:00:00+08:00','2026-10-28'),('2027-01-01T01:00:00+08:00','2026-12-31')]:
            with patch.object(s,'now',return_value=s.datetime.fromisoformat(moment)):
                self.assertEqual(s.today(),expected)
        self.assertEqual(s.daydata('2026-10-27')['review']['tech'],'深夜的记录')

    def test_empty_never_creates_diary(self):
        self.assertEqual(s.sync_day('2026-10-26')['status'],'empty'); self.assertFalse(s.VAULT.exists())
    def test_whitespace_does_not_create_diary(self):
        self.save('2026-10-26','review',' \n  ');self.assertEqual(s.sync_day('2026-10-26')['status'],'empty');self.assertFalse(s.VAULT.exists())
    def test_port_binding_is_exclusive(self):
        first=s.ExclusiveServer(('127.0.0.1',0),s.Handler)
        try:
            with self.assertRaises(OSError): s.ExclusiveServer(('127.0.0.1',first.server_port),s.Handler)
        finally:first.server_close()
    def test_append_preserves_bytes_and_repeated_sync_is_idempotent(self):
        p=s.diary_path('2026-10-26');original='原来的日记\r\n- [ ] 原任务\r\n'.encode();p.write_bytes(original)
        self.save('2026-10-26','review','今天理解了闭包');s.sync_day('2026-10-26');first=p.read_bytes()
        self.assertTrue(first.startswith(original));s.sync_day('2026-10-26');self.assertEqual(first,p.read_bytes())
        tail='\r\n## 后来手写\r\n这段不能移动。\r\n'.encode();p.write_bytes(first+tail)
        self.save('2026-10-26','review','今天理解了闭包和作用域','今天理解了闭包');s.sync_day('2026-10-26')
        result=p.read_bytes();self.assertTrue(result.startswith(original));self.assertTrue(result.endswith(tail));self.assertEqual(result.count(b'<!-- growth-board:start:'),1)
    def test_tomorrow_is_next_day_task_and_checkboxes_export(self):
        tasks=[{'id':'t1','text':'写一个闭包例子','done':False}]
        self.save('2026-10-27','tasks',tasks,owner='2026-10-26');s.sync_day('2026-10-26')
        text=s.diary_path('2026-10-26').read_text(encoding='utf-8');self.assertIn('明日任务 · 2026-10-27',text);self.assertIn('- [ ] 写一个闭包例子',text)
        self.assertEqual(s.daydata('2026-10-27')['tasks']['tech'],tasks)
    def test_conflicts_preserve_newer_edit(self):
        self.save('2026-10-26','review','窗口一');code,_=self.save('2026-10-26','review','窗口二');self.assertEqual(code,409);self.assertEqual(s.daydata('2026-10-26')['review']['tech'],'窗口一')
    def test_crash_after_append_does_not_duplicate(self):
        self.save('2026-10-26','review','一次即可');before=copy.deepcopy(s.STATE);s.sync_day('2026-10-26');p=s.diary_path('2026-10-26');raw=p.read_bytes();s.STATE=before;s.sync_day('2026-10-26');self.assertEqual(p.read_bytes(),raw)
    def test_existing_titled_diary_and_ambiguous_guard(self):
        p=s.diary_path('2026-10-26');titled=p.with_name('10.26 复盘.md');titled.write_text('旧文');self.assertEqual(s.diary_path('2026-10-26'),titled)
        p.write_text('另一篇');self.assertRaises(ValueError,s.diary_path,'2026-10-26')
    def test_default_quotes_are_public_and_format_comment_is_not_a_quote(self):
        self.assertEqual(len(s.parse_quotes()),4)
        self.assertTrue(all(q['source'] for q in s.parse_quotes()))
        self.assertTrue(any('千里之行' in q['text'] for q in s.parse_quotes()))

    def test_quote_path_validation_no_side_effects(self):
        target=s.DATA/'new-quotes.md'
        self.assertEqual(s.display_settings({'quotesPath':str(target)})['quotesPath'],str(target))
        self.assertFalse(target.exists())
        self.assertEqual(s.display_settings({'quotesPath':''})['quotesPath'],str(s.DATA/'个人金句.md'))
        for path in ['relative.md',str(s.DATA/'quotes.txt'),str(s.DATA/'missing'/'quotes.md')]:
            with self.assertRaises(ValueError):s.display_settings({'quotesPath':path})

    def test_quotes_verbatim_and_daily_stability(self):
        s.VAULT.mkdir();s.QUOTES.write_text('# 个人金句\n\n## 一\n\n> 这是原话。\n\n来源：[[日记]]\n\n## 二\n\n> 不要改写！\n',encoding='utf-8')
        q=s.daily_quote('2026-10-26');self.assertEqual(q,s.daily_quote('2026-10-26'));self.assertNotEqual(q['id'],s.daily_quote('2026-10-27')['id'])
    def test_display_settings_validation(self):
        settings=s.display_settings({'quoteMode':'fixed','fixedQuote':'这是原话。','motto':'','quoteLayout':'type'})
        self.assertEqual(settings['fixedQuote'],'这是原话。');self.assertEqual(settings['motto'],'')
        for patch in [{'quoteMode':'fixed','fixedQuote':' '},{'quoteLayout':'unknown'},{'motto':'长'*121}]:
            self.assertRaises(ValueError,s.display_settings,patch)
    def test_legacy_settings_keep_existing_reminders(self):
        state=copy.deepcopy(s.STATE);state['settings']={'style':'04','times':['08:30','21:15'],'enabled':False};s.atomic(s.STATE_FILE,state);s.init()
        self.assertEqual(s.STATE['settings']['times'],['08:30','21:15']);self.assertEqual(s.STATE['settings']['quoteLayout'],'poster');self.assertFalse(s.STATE['settings']['enabled'])

    def test_existing_personal_paths_and_motto_survive_portable_defaults(self):
        s.VAULT.mkdir();q=s.VAULT/'个人金句.md';q.write_text('原来的金句',encoding='utf-8')
        s.STATE['settings'].update({'obsidianPath':str(s.VAULT),'motto':'我自己的话'})
        s.STATE['settings'].pop('quotesPath',None);s.persist();s.init()
        self.assertEqual(s.QUOTES,q);self.assertEqual(q.read_text(encoding='utf-8'),'原来的金句');self.assertEqual(s.STATE['settings']['motto'],'我自己的话')
        self.assertEqual(s.STATE['settings']['appIcon'],'01')
        self.assertRaises(ValueError,s.display_settings,{'appIcon':'../unknown'})

    def test_local_legacy_migration_is_not_a_portable_default(self):
        s.atomic(s.DATA/'local-defaults.json',{'notesPath':str(s.VAULT),'motto':'原来的页眉'})
        s.STATE['settings'].pop('obsidianPath',None);s.STATE['settings'].pop('motto',None);s.persist();s.init()
        self.assertEqual(s.STATE['settings']['obsidianPath'],str(s.VAULT));self.assertEqual(s.STATE['settings']['motto'],'原来的页眉')
    def test_large_review_survives_sync_exactly(self):
        text=('长文本验证：理解、练习、记录。\n'*800)+'结尾标记'
        self.save('2026-10-26','review',text);s.sync_day('2026-10-26')
        self.assertIn(text,s.diary_path('2026-10-26').read_text(encoding='utf-8'))

    def test_manual_region_edits_are_preserved(self):
        self.save('2026-10-26','review','原复盘');s.sync_day('2026-10-26');p=s.diary_path('2026-10-26')
        edited=p.read_bytes().replace('原复盘'.encode(),'手改复盘'.encode());p.write_bytes(edited)
        self.save('2026-10-26','review','网页改动','原复盘')
        with self.assertRaisesRegex(ValueError,'手动修改'):s.sync_day('2026-10-26')
        self.assertEqual(p.read_bytes(),edited)

    def test_legacy_anchor_stays_before_later_manual_notes(self):
        p=s.diary_path('2026-10-26');before=b'old\r\n<!-- growth-board:2026-10-26:1:abcdef -->';tail='\r\n后来手写的段落\r\n'.encode();p.write_bytes(before+tail)
        self.save('2026-10-26','review','新的复盘');s.sync_day('2026-10-26');result=p.read_bytes()
        self.assertTrue(result.startswith(before));self.assertTrue(result.endswith(tail));self.assertLess(result.index(b'growth-board:end'),result.index('后来'.encode()))

    def test_custom_file_path_and_names_do_not_move_other_days(self):
        s.VAULT.mkdir();p=s.VAULT/'自选.md';p.write_bytes(b'# Manual\r\n')
        names={'tech':'算法与系统','project':'作品','school':'课程'}
        s.STATE['settings']=s.display_settings({'obsidianPath':str(p),'columnNames':names})
        self.save('2026-10-26','review','第一天');s.sync_day('2026-10-26')
        self.save('2026-10-27','review','第二天');s.sync_day('2026-10-27');tail=p.read_bytes().split(b'<!-- growth-board:start:2026-10-27')[1]
        self.save('2026-10-26','review','改第一天','第一天');s.sync_day('2026-10-26')
        self.assertIn('### 算法与系统',p.read_text(encoding='utf-8'));self.assertTrue(p.read_bytes().endswith(tail))
        self.assertEqual(s.daydata('2026-10-26')['review']['tech'],'改第一天')

    def test_missing_marker_does_not_append_duplicate(self):
        self.save('2026-10-26','review','原复盘');s.sync_day('2026-10-26');p=s.diary_path('2026-10-26');p.write_bytes(b'# manually removed')
        with self.assertRaises(ValueError):s.sync_day('2026-10-26')
        self.assertEqual(p.read_bytes(),b'# manually removed')

    def test_clear_updates_region_without_removing_tail(self):
        self.save('2026-10-26','review','原复盘');s.sync_day('2026-10-26');p=s.diary_path('2026-10-26');p.write_bytes(p.read_bytes()+b'\nUSER TAIL')
        self.save('2026-10-26','review','','原复盘');s.sync_day('2026-10-26')
        self.assertTrue(p.read_bytes().endswith(b'\nUSER TAIL'));self.assertNotIn('原复盘',p.read_text(encoding='utf-8'))

    def test_month_formats_infer_next_month_and_note_format(self):
        from diary_routing import resolve_diary
        for monthly,note,expected in [('26.9复盘','9.30.md','26.10复盘/10.26.md'),('2026-09','2026-09-30.md','2026-10/2026-10-26.md'),('2026年9月','9.30 随笔.md','2026年10月/10.26.md')]:
            root=s.VAULT/('case-'+monthly);folder=root/monthly;folder.mkdir(parents=True);(folder/note).write_text('旧日记')
            self.assertEqual(resolve_diary(root,'2026-10-26'),root/expected)
            self.assertFalse((root/expected).exists())

    def test_routing_existing_titled_iso_and_year_rollover(self):
        from diary_routing import resolve_diary
        root=s.VAULT;folder=root/'2026-12';folder.mkdir(parents=True);p=folder/'2026-12-31 年末复盘.md';p.write_text('原文')
        self.assertEqual(resolve_diary(root,'2026-12-31'),p)
        self.assertEqual(resolve_diary(root,'2027-01-01'),root/'2027-01'/'2027-01-01.md')

    def test_routing_flat_month_selection_and_ambiguity(self):
        from diary_routing import resolve_diary
        root=s.VAULT;root.mkdir();(root/'2026-10-25.md').write_text('原文')
        self.assertEqual(resolve_diary(root,'2026-10-26'),root/'2026-10-26.md')
        month=root/'2026-10';month.mkdir()
        with self.assertRaises(ValueError):resolve_diary(month,'2026-11-01')
        with self.assertRaises(ValueError):resolve_diary(root,'2026-10-26')

    def test_routing_duplicate_month_and_unknown_format(self):
        from diary_routing import resolve_diary
        root=s.VAULT;root.mkdir();(root/'October').mkdir()
        with self.assertRaises(ValueError):resolve_diary(root,'2026-10-26')
        (root/'26.10复盘').mkdir();(root/'2026-10').mkdir()
        with self.assertRaises(ValueError):resolve_diary(root,'2026-10-26')

if __name__=='__main__':unittest.main()
