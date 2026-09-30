import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from PIL import Image

from patcher.build import build, read_translation, write_apk
from patcher.fonts import read_block, replace_database
from patcher.gxt import FormatError, GXT, encode_turkish, translate


def make_gxt(tables, bits=16):
    out = bytearray(struct.pack('<HH4sI', 4, bits, b'TABL', len(tables) * 12))
    out.extend(b'\0' * (len(tables) * 12))
    for index, (name, entries) in enumerate(tables):
        encoded_name = name.encode().ljust(8, b'\0')
        struct.pack_into('<8sI', out, 12 + index * 12, encoded_name, len(out))
        data, keys = bytearray(), bytearray()
        for key, text in entries:
            keys.extend(struct.pack('<II', len(data), key))
            data.extend((text + '\0').encode('utf-16-le' if bits == 16 else 'latin1'))
        if name != 'MAIN':
            out.extend(encoded_name)
        out.extend(b'TKEY' + struct.pack('<I', len(keys)) + keys)
        out.extend(b'TDAT' + struct.pack('<I', len(data)) + data)
    return bytes(out)


def texture_block(payload=b'ABCD', name_hash=7):
    return struct.pack('<HHHHII', name_hash, 0x1401, 1, 1, len(payload) + 4, 0) + payload


class GXTTests(unittest.TestCase):
    def test_long_translation_moves_later_table_without_losing_keys(self):
        original = GXT(make_gxt([('MAIN', [(1, 'One'), (2, 'Untouched')]), ('TEST', [(3, 'Later table')])]))
        expected = dict(original.strings)
        expected[('MAIN', '00000001')] = encode_turkish('Uzun Türkçe açıklama: ığüşöçİŞĞÜÖÇ. ' * 12)
        patched = GXT(original.replace(expected))
        self.assertEqual(patched.strings, expected)
        self.assertEqual(patched.strings[('TEST', '00000003')], 'Later table')

    def test_pc_translation_and_supplement_keep_runtime_placeholders(self):
        mobile = GXT(make_gxt([('MAIN', [(1, 'Label'), (2, '~m~~widget_action~ value ~1~')])]))
        pc = GXT(make_gxt([('MAIN', [(1, '~z~Translated'), (2, 'PC controls')])], 8))
        extra = [{'table': 'MAIN', 'key': '00000002', 'text': '~m~~widget_action~ değer ~1~'}]
        raw, counts = translate(mobile, pc, extra)
        self.assertEqual(GXT(raw).strings[('MAIN', '00000001')], 'Translated')
        self.assertEqual(counts['changed'], 2)

    def test_missing_numeric_placeholder_aborts(self):
        mobile = GXT(make_gxt([('MAIN', [(1, 'Score ~1~')])]))
        pc = GXT(make_gxt([('MAIN', [(1, 'Score')])], 8))
        with self.assertRaisesRegex(FormatError, 'sayı alanı'):
            translate(mobile, pc, [])

    def test_changed_touch_button_aborts(self):
        mobile = GXT(make_gxt([('MAIN', [(1, '~m~~widget_brake~')])]))
        pc = GXT(make_gxt([('MAIN', [(1, '~m~~widget_accelerate~')])], 8))
        with self.assertRaises(FormatError):
            translate(mobile, pc, [])

    def test_truncated_and_out_of_bounds_data_rejected(self):
        good = make_gxt([('MAIN', [(1, 'Text')])])
        bad_offset = bytearray(good)
        struct.pack_into('<I', bad_offset, 20, len(good) + 500)
        bad_key = bytearray(good)
        struct.pack_into('<I', bad_key, 32, 999999)
        for raw in (good[:4], good[:-1], bytes(bad_offset), bytes(bad_key)):
            with self.subTest(raw=raw[:20]), self.assertRaises(FormatError):
                GXT(raw)

    def test_unknown_supplement_key_aborts(self):
        mobile = GXT(make_gxt([('MAIN', [(1, 'Label')])]))
        pc = GXT(make_gxt([('MAIN', [(1, 'Etiket')])], 8))
        with self.assertRaises(FormatError):
            translate(mobile, pc, [{'table': 'MAIN', 'key': 'FFFFFFFF', 'text': 'Başka'}])


class FontTests(unittest.TestCase):
    def test_only_font_blocks_change_and_offsets_relocate(self):
        chunks = [texture_block(bytes([i]) * 4, i) for i in range(4)]
        raw = b''.join(chunks)
        toc = struct.pack('<I5i', len(raw), 0, len(chunks[0]), -1, 2 * len(chunks[0]), 3 * len(chunks[0]))
        names = ['keep_a', 'font1', 'alias', 'font2', 'keep_b']
        images = {name: Image.new('RGBA', (2, 2), (255, 128, 16, 255)) for name in ('font1', 'font2')}
        new, new_toc = replace_database(raw, toc, names, images)
        length, *offsets = struct.unpack('<I5i', new_toc)
        self.assertEqual(length, len(new))
        self.assertEqual(offsets[2], -1)
        self.assertEqual(read_block(new, offsets[0])[0], chunks[0])
        self.assertEqual(read_block(new, offsets[4])[0], chunks[3])
        block, _ = read_block(new, offsets[1])
        self.assertEqual(struct.unpack_from('<H', block, 2)[0], 0x8033)
        self.assertEqual(block[16:18], struct.pack('<H', 0xF81F))

    def test_texture_index_outside_file_aborts(self):
        raw = texture_block()
        toc = struct.pack('<I2i', len(raw), 0, 999999)
        with self.assertRaises(FormatError):
            replace_database(raw, toc, ['font1', 'font2'], {'font1': Image.new('RGBA', (1, 1)), 'font2': Image.new('RGBA', (1, 1))})


class PackagingTests(unittest.TestCase):
    def test_patch_preserves_other_zip_members_and_alignment(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'in.apk', Path(temp) / 'out.apk'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('assets/example.txt', b'old')
                archive.writestr('assets/keep.txt', b'keep' * 7)
            before = source.read_bytes()
            write_apk(source, output, {'assets/example.txt': b'much longer replacement'})
            self.assertEqual(source.read_bytes(), before)
            with zipfile.ZipFile(output) as archive, output.open('rb') as stream:
                self.assertEqual(archive.read('assets/keep.txt'), b'keep' * 7)
                for entry in archive.infolist():
                    stream.seek(entry.header_offset + 26)
                    name_len, extra_len = struct.unpack('<HH', stream.read(4))
                    self.assertEqual((entry.header_offset + 30 + name_len + extra_len) % 4, 0)

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'existing'
            output.mkdir()
            marker = output / 'keep.txt'
            marker.write_text('keep')
            with self.assertRaises(FormatError):
                build(Path(temp) / 'missing', Path(temp) / 'missing.zip', output)
            self.assertEqual(marker.read_text(), 'keep')

    def test_missing_inputs_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'new'
            with self.assertRaises(FormatError):
                build(Path(temp) / 'missing', Path(temp) / 'missing.zip', output)
            self.assertFalse(output.exists())

    def test_ambiguous_translation_archive_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'pc.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('one/text/american.gxt', b'one')
                archive.writestr('two/text/american.gxt', b'two')
                archive.writestr('one/models/fonts.txd', b'font')
            with self.assertRaisesRegex(FormatError, 'belirsiz'):
                read_translation(path, {})


if __name__ == '__main__':
    unittest.main()
