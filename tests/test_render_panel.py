"""Presentation-only tests: no network, no engine, and no changes to saves."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageChops, ImageSequence

ROOT = Path(__file__).resolve().parents[1]

class PanelTests(unittest.TestCase):
    def setUp(self):
        self.state = {'input_count': 3, 'last_actor': 'Unjuno', 'last_input': '/fire',
                      'updated_at': '2026-10-05T12:44:25.177634+00:00'}

    def module(self):
        path = ROOT / 'scripts/render_panel.py'
        self.assertTrue(path.exists(), 'the integrated replay panel renderer is missing')
        spec = importlib.util.spec_from_file_location('render_panel', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_desktop_keeps_complete_game_frame(self):
        m = self.module()
        game = Image.new('RGB', (480, 360), '#f28731')
        game.putpixel((0, 0), (22, 33, 44))
        card = m.compose(game, self.state, 'dark', False, 0, 5000)
        self.assertEqual(card.size, (800, 520))
        self.assertIsNone(ImageChops.difference(game, card.crop((16, 68, 496, 428))).getbbox())

    def test_mobile_has_its_own_composition(self):
        m = self.module()
        game = Image.new('RGB', (480, 360), '#f28731')
        card = m.compose(game, self.state, 'light', True, 0, 5000)
        self.assertEqual(card.size, (320, 444))
        expected = game.resize((288, 216), Image.Resampling.NEAREST)
        self.assertIsNone(ImageChops.difference(expected, card.crop((16, 56, 304, 272))).getbbox())

    def test_themes_differ_outside_game_only(self):
        m = self.module()
        game = Image.new('RGB', (480, 360), '#554433')
        a = m.compose(game, self.state, 'light', False, 0, 5000)
        b = m.compose(game, self.state, 'dark', False, 0, 5000)
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        self.assertIsNone(ImageChops.difference(a.crop((16,68,496,428)), b.crop((16,68,496,428))).getbbox())

    def test_replay_progress_is_not_fake_game_motion(self):
        m = self.module()
        game = Image.new('RGB', (480, 360), '#332211')
        a = m.compose(game, self.state, 'dark', False, 0, 5000)
        b = m.compose(game, self.state, 'dark', False, 4000, 5000)
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        self.assertIsNone(ImageChops.difference(a.crop((16,68,496,428)),b.crop((16,68,496,428))).getbbox())

    def test_bad_metadata_rejected(self):
        m = self.module()
        game=Image.new('RGB',(480,360))
        for val in [True,-1,'three']:
            with self.assertRaises(ValueError):
                m.compose(game,{**self.state,'input_count':val},'dark',False,0,5000)
        with self.assertRaises(ValueError): m.compose(game,self.state,'neon',False,0,5000)
        with self.assertRaises(ValueError): m.compose(game,self.state,'dark',False,0,0)

    def test_long_values_fit_by_measured_width(self):
        m = self.module()
        f=m.font(16)
        for value in ['a'*200, '<script>&'*40, '任意の名前'*40]:
            fitted=m.fit(value,f,140)
            self.assertLessEqual(f.getlength(fitted),140)

    def test_saved_time_never_becomes_render_time(self):
        m = self.module()
        self.assertEqual(m.saved_time(None),'No saved input yet')
        self.assertEqual(m.saved_time('not-a-date'),'Save time unavailable')
        self.assertEqual(m.saved_time('2026-10-05T21:44:25+09:00'),'2026-10-05 12:44 UTC')
        self.assertEqual(m.saved_time('2026-10-05T12:44:25'),'Save time unavailable')

    def test_exports_preserve_timing_have_matching_still_and_manifest(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'doom.gif'; out=root/'out'
            a=Image.new('RGB',(480,360),'#112233'); b=Image.new('RGB',(480,360),'#445566')
            a.save(src,save_all=True,append_images=[b],duration=[120,240],loop=0)
            original=src.read_bytes(); before=json.dumps(self.state,sort_keys=True)
            m.render_panels(src,self.state,out)
            self.assertEqual(src.read_bytes(),original)
            self.assertEqual(json.dumps(self.state,sort_keys=True),before)
            manifest=json.loads((out/'panel-v4.json').read_text())
            self.assertEqual(manifest['duration_ms'],360)
            self.assertEqual(manifest['input_count'],3)
            self.assertEqual(manifest['kind'],'recorded-replay')
            self.assertEqual(manifest['saved_at'],self.state['updated_at'])
            for layout,size in [('desktop',(800,520)),('mobile',(320,444))]:
                for theme in ['light','dark']:
                    stem=f'panel-v4-{layout}-{theme}'
                    with Image.open(out/(stem+'.gif')) as image:
                        self.assertEqual(image.size,size)
                        self.assertEqual(image.info.get('loop'),0)
                        self.assertEqual(sum(f.info['duration'] for f in ImageSequence.Iterator(image)),360)
                        image.seek(image.n_frames-1); last=image.convert('RGB')
                    with Image.open(out/(stem+'.png')) as still:
                        self.assertIsNone(ImageChops.difference(last,still.convert('RGB')).getbbox())
            self.assertEqual(len(manifest['assets']),8)

    def test_missing_or_static_source_fails_without_placeholder(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):m.render_panels(root/'missing.gif',self.state,root/'out')
            src=root/'static.gif';Image.new('RGB',(480,360)).save(src)
            with self.assertRaises(ValueError):m.render_panels(src,self.state,root/'out')
            self.assertFalse((root/'out/panel-v4-desktop-dark.gif').exists())

if __name__=='__main__': unittest.main()
