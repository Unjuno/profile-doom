"""Regression checks for profile status assets; no network or game runtime needed."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('render_status', ROOT / 'scripts/render_status.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class RenderStatusTests(unittest.TestCase):
    def setUp(self):
        self.state = {'input_count': 2, 'last_actor': 'Unjuno', 'last_input': '/right',
                      'updated_at': '2026-10-05T10:58:58.730053+00:00'}

    def test_compact_variant_is_readable(self):
        import inspect
        self.assertIn('compact', inspect.signature(module.render_status).parameters)
        svg = module.render_status(self.state, 'dark', compact=True)
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib['viewBox'], '0 0 320 104')
        texts = root.findall('.//{http://www.w3.org/2000/svg}text')
        self.assertTrue(all(int(t.attrib['font-size']) >= 14 for t in texts))
        self.assertEqual(len(root.findall('.//{http://www.w3.org/2000/svg}clipPath')), 2)

    def test_desktop_typography_is_compact(self):
        root = ET.fromstring(module.render_status(self.state, 'light'))
        self.assertEqual(root.attrib['viewBox'], '0 0 640 88')
        self.assertEqual(len(root.findall('.//{http://www.w3.org/2000/svg}clipPath')), 2)

    def test_api_exists(self):
        self.assertTrue(callable(getattr(module, 'render_status', None)), 'missing pure status renderer')

    def test_dark_and_light_are_valid_and_distinct(self):
        if not hasattr(module, 'render_status'): self.fail('missing pure status renderer')
        light = module.render_status(self.state, 'light')
        dark = module.render_status(self.state, 'dark')
        self.assertNotEqual(light, dark)
        for svg in [light, dark]:
            ET.fromstring(svg)
            self.assertIn('Snapshot', svg)
            self.assertNotIn('>active<', svg)
            self.assertNotIn('>running<', svg)
            self.assertIn('2026-10-05 10:58 UTC', svg)
            self.assertIn('/right', svg)

    def test_untrusted_text_is_escaped(self):
        if not hasattr(module, 'render_status'): self.fail('missing pure status renderer')
        self.state['last_actor'] = '<script>alert(1)</script>&'
        svg = module.render_status(self.state, 'dark')
        ET.fromstring(svg)
        self.assertNotIn('<script>', svg)
        self.assertIn('&lt;script&gt;', svg)

    def test_missing_time_is_not_replaced_by_now(self):
        if not hasattr(module, 'render_status'): self.fail('missing pure status renderer')
        self.state['updated_at'] = None
        self.assertIn('No saved input yet', module.render_status(self.state, 'light'))

    def test_bad_count_fails_closed(self):
        if not hasattr(module, 'render_status'): self.fail('missing pure status renderer')
        for value in [-1, True, 'two']:
            self.state['input_count'] = value
            with self.assertRaises(ValueError): module.render_status(self.state, 'light')

    def test_long_actor_is_visually_bounded(self):
        if not hasattr(module, 'render_status'): self.fail('missing pure status renderer')
        self.state['last_actor'] = 'a' * 80
        svg = module.render_status(self.state, 'light')
        root = ET.fromstring(svg)
        texts = [x.text or '' for x in root.findall('.//{http://www.w3.org/2000/svg}text')]
        self.assertTrue(all(len(x) <= 32 for x in texts))
        self.assertIn('a' * 80, svg)

if __name__ == '__main__': unittest.main()
