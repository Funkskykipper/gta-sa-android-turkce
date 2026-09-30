"""Read and update keyed GXT v4 tables without redistributing game text."""

from collections import Counter
from dataclasses import dataclass
import re
import struct


class FormatError(ValueError):
    pass


GLYPHS = {
    'ı': 0xA2, 'ş': 0x98, 'ğ': 0xA6, 'ç': 0x9C, 'ö': 0xA8,
    'ü': 0xAC, 'İ': 0x8B, 'Ş': 0x81, 'Ç': 0x85, 'Ü': 0x95,
    'â': 0x99, 'Ö': 0x91, 'Ğ': 0x8F, 'î': 0xA3, 'û': 0xAB, 'Â': 0x82,
}


def encode_turkish(text):
    text = text.replace('’', "'").replace('…', '...').replace('–', '-')
    if any(ord(c) >= 128 and c not in GLYPHS for c in text):
        raise FormatError('Ek çeviride desteklenmeyen bir karakter var.')
    return ''.join(chr(GLYPHS[c]) if c in GLYPHS else c for c in text)


@dataclass
class Table:
    name: str
    keys: list
    data: bytes


class GXT:
    def __init__(self, raw):
        if len(raw) < 12:
            raise FormatError('GXT başlığı eksik.')
        version, self.bits = struct.unpack_from('<HH', raw)
        if version != 4 or self.bits not in (8, 16) or raw[4:8] != b'TABL':
            raise FormatError('Desteklenmeyen GXT biçimi.')
        size = struct.unpack_from('<I', raw, 8)[0]
        if not size or size % 12 or 12 + size > len(raw):
            raise FormatError('GXT tablo listesi bozuk.')
        self.tables, self.strings = [], {}
        names = set()
        for pos in range(12, 12 + size, 12):
            try:
                name = raw[pos:pos + 8].rstrip(b'\0').decode('ascii')
            except UnicodeDecodeError as exc:
                raise FormatError('GXT tablo adı bozuk.') from exc
            if not name or name in names:
                raise FormatError('GXT tablo adı eksik veya yineleniyor.')
            names.add(name)
            start = struct.unpack_from('<I', raw, pos + 8)[0]
            if start < 12 + size:
                raise FormatError('GXT tablo adresi başlığa işaret ediyor.')
            keypos = start + (0 if name == 'MAIN' else 8)
            if name != 'MAIN' and raw[start:start + 8] != raw[pos:pos + 8]:
                raise FormatError('GXT tablo adı eşleşmiyor.')
            if keypos + 8 > len(raw) or raw[keypos:keypos + 4] != b'TKEY':
                raise FormatError('GXT anahtar tablosu bozuk.')
            keysize = struct.unpack_from('<I', raw, keypos + 4)[0]
            textpos = keypos + 8 + keysize
            if keysize % 8 or textpos + 8 > len(raw) or raw[textpos:textpos + 4] != b'TDAT':
                raise FormatError('GXT metin tablosu bozuk.')
            textsize = struct.unpack_from('<I', raw, textpos + 4)[0]
            if textpos + 8 + textsize > len(raw):
                raise FormatError('GXT metni dosya sınırını aşıyor.')
            data = raw[textpos + 8:textpos + 8 + textsize]
            keys = []
            step = self.bits // 8
            for keyloc in range(keypos + 8, keypos + 8 + keysize, 8):
                offset, key = struct.unpack_from('<II', raw, keyloc)
                identity = (name, f'{key:08X}')
                if identity in self.strings or offset % step or offset >= len(data):
                    raise FormatError('GXT anahtarı veya metin adresi bozuk.')
                end = offset
                while end + step <= len(data) and data[end:end + step] != b'\0' * step:
                    end += step
                if end + step > len(data):
                    raise FormatError('GXT metin sonlandırıcısı eksik.')
                try:
                    self.strings[identity] = data[offset:end].decode('latin1' if step == 1 else 'utf-16-le')
                except UnicodeDecodeError as exc:
                    raise FormatError('GXT karakter kodlaması bozuk.') from exc
                keys.append((offset, key))
            self.tables.append(Table(name, keys, data))

    def replace(self, texts):
        if self.bits != 16 or texts.keys() != self.strings.keys():
            raise FormatError('Mobil GXT anahtarları korunmalı.')
        out = bytearray(struct.pack('<HH4sI', 4, 16, b'TABL', 12 * len(self.tables)))
        out.extend(b'\0' * (12 * len(self.tables)))
        for index, table in enumerate(self.tables):
            name = table.name.encode('ascii').ljust(8, b'\0')
            struct.pack_into('<8sI', out, 12 + index * 12, name, len(out))
            data = bytearray(table.data)
            keys, cache = bytearray(), {}
            for offset, key in table.keys:
                text = texts[(table.name, f'{key:08X}')]
                if '\0' in text:
                    raise FormatError('Çeviride geçersiz metin sonlandırıcısı var.')
                encoded = (text + '\0').encode('utf-16-le')
                if data[offset:offset + len(encoded)] != encoded:
                    if encoded not in cache:
                        cache[encoded] = len(data)
                        data.extend(encoded)
                    offset = cache[encoded]
                keys.extend(struct.pack('<II', offset, key))
            data.extend(b'\0' * (-len(data) % 4))
            if table.name != 'MAIN':
                out.extend(name)
            out.extend(b'TKEY' + struct.pack('<I', len(keys)) + keys)
            out.extend(b'TDAT' + struct.pack('<I', len(data)) + data)
        result = bytes(out)
        if GXT(result).strings != texts:
            raise FormatError('GXT yeniden okuma doğrulaması başarısız.')
        return result


def normalized(text):
    return re.sub(r'\s+', ' ', re.sub(r'~[^~]*~', '', text)).strip().casefold()


def runtime_tokens(text):
    return Counter(re.findall(r'~widget_[^~]+~|~(?:1|a)~', text))


def translate(original, pc, supplements):
    if original.bits != 16 or pc.bits != 8:
        raise FormatError('Mobil metin 16 bit, PC çevirisi 8 bit olmalı.')
    translated = {key: value.replace('~z~', '') for key, value in pc.strings.items()}
    by_text = {}
    for key, old in original.strings.items():
        candidate = translated.get(key)
        if candidate and normalized(candidate) != normalized(old):
            by_text.setdefault(normalized(old), candidate)
    extra = {}
    for entry in supplements:
        key = (entry['table'], entry['key'])
        if key in extra or key not in original.strings:
            raise FormatError('Ek çeviri anahtarı yineleniyor veya sürümle uyuşmuyor.')
        extra[key] = encode_turkish(entry['text'])
    result, counts = {}, Counter()
    for key, old in original.strings.items():
        text, source = old, 'original'
        if key in translated:
            text, source = translated[key], 'pc'
            if normalized(text) == normalized(old) and normalized(old) in by_text:
                text, source = by_text[normalized(old)], 'duplicate'
        elif normalized(old) in by_text:
            text, source = by_text[normalized(old)], 'duplicate'
        if key in extra:
            text, source = extra[key], 'mobile'
        if runtime_tokens(old) != runtime_tokens(text):
            raise FormatError(f'Tuş simgesi veya sayı alanı uyuşmuyor: {key[0]}:{key[1]}')
        if source != 'original':
            text = text.replace(chr(0xFC), chr(GLYPHS['ü']))
        result[key] = text
        counts[source] += 1
        counts['changed'] += text != old
    counts['total'] = len(result)
    return original.replace(result), dict(counts)
