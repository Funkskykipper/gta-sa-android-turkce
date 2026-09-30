"""Convert the supplied PC font atlas to the tested mobile texture variants."""

import io
import re
import struct

import numpy as np
from PIL import Image

from .gxt import FormatError


def native_textures(raw, depth=0):
    if depth > 4:
        raise FormatError('TXD iç içe bölüm sınırı aşıldı.')
    cursor = 0
    while cursor < len(raw):
        if cursor + 12 > len(raw):
            raise FormatError('TXD bölüm başlığı eksik.')
        kind, size, _ = struct.unpack_from('<III', raw, cursor)
        end = cursor + 12 + size
        if end > len(raw):
            raise FormatError('TXD bölüm boyutu geçersiz.')
        data = raw[cursor + 12:end]
        if kind in (0x16, 0x15):
            yield from native_textures(data, depth + 1)
        elif kind == 1 and size > 100:
            yield data
        cursor = end


def load_pc_fonts(raw):
    images = {}
    for data in native_textures(raw):
        name = data[8:40].split(b'\0')[0].decode('ascii')
        if name not in ('font1', 'font2'):
            continue
        width, height = struct.unpack_from('<HH', data, 80)
        size = struct.unpack_from('<I', data, 88)[0]
        if data[76:80] != b'DXT3' or (width, height) != (512, 512) or size != 262144 or 92 + size > len(data):
            raise FormatError('Bu PC font sürümü desteklenmiyor; standart 512x512 DXT3 font gerekli.')
        header = b'DDS ' + struct.pack('<7I', 124, 0x81007, height, width, size, 0, 1)
        header += b'\0' * 44 + struct.pack('<II4s5I', 32, 4, b'DXT3', 0, 0, 0, 0, 0)
        header += struct.pack('<5I', 0x1000, 0, 0, 0, 0)
        with Image.open(io.BytesIO(header + data[92:92 + size])) as image:
            images[name] = image.convert('RGBA').resize((1024, 1024), Image.Resampling.LANCZOS)
    if set(images) != {'font1', 'font2'}:
        raise FormatError('PC paketinde iki standart font bulunamadı.')
    return images


def read_block(raw, offset):
    if offset < 0 or offset + 16 > len(raw):
        raise FormatError('Mobil font blok adresi geçersiz.')
    count = struct.unpack_from('<I', raw, offset + 8)[0]
    end = offset + 12 + count
    if count < 4 or end > len(raw):
        raise FormatError('Mobil font blok boyutu geçersiz.')
    return raw[offset:end], end


def encode_block(old, image, thumbnail=False):
    name_hash = struct.unpack_from('<H', old)[0]
    if thumbnail:
        image = image.resize((8, 8), Image.Resampling.LANCZOS)
        payload, encoding = image.tobytes(), 0x1401
    else:
        pixels = np.asarray(image, dtype=np.uint16) >> 4
        packed = (pixels[:, :, 0] << 12) | (pixels[:, :, 1] << 8) | (pixels[:, :, 2] << 4) | pixels[:, :, 3]
        payload, encoding = packed.astype('<u2').tobytes(), 0x8033
    # A clear high bit in height denotes a single level without mipmaps.
    return struct.pack('<HHHHII', name_hash, encoding, image.width, image.height, len(payload) + 4, 0) + payload


def replace_database(raw, toc, names, images):
    if len(toc) != 4 * (len(names) + 1) or struct.unpack_from('<I', toc)[0] != len(raw):
        raise FormatError('Mobil font dizini veri dosyasıyla uyuşmuyor.')
    offsets = struct.unpack('<' + 'i' * len(names), toc[4:])
    physical = sorted(set(offset for offset in offsets if offset >= 0))
    if not physical or physical[0] != 0:
        raise FormatError('Mobil font başlangıç adresi geçersiz.')
    new, reloc, changed = bytearray(), {}, []
    for index, offset in enumerate(physical):
        end = physical[index + 1] if index + 1 < len(physical) else len(raw)
        old, block_end = read_block(raw, offset)
        if block_end > end:
            raise FormatError('Mobil font blokları üst üste biniyor.')
        matches = [names[j] for j, value in enumerate(offsets) if value == offset]
        target = next((name for name in matches if name in images), None)
        reloc[offset] = len(new)
        if target:
            if len(matches) != 1:
                raise FormatError('Font bloğu başka bir doku tarafından da kullanılıyor.')
            new.extend(encode_block(old, images[target]) + raw[block_end:end])
            changed.append(target)
        else:
            new.extend(raw[offset:end])
    if sorted(changed) != ['font1', 'font2']:
        raise FormatError('İki mobil font da değiştirilemedi.')
    new_offsets = [reloc[offset] if offset >= 0 else offset for offset in offsets]
    new_toc = struct.pack('<I', len(new)) + struct.pack('<' + 'i' * len(new_offsets), *new_offsets)
    return bytes(new), new_toc


def patch_fonts(assets, pc_font):
    lines = assets['txd.txt'].decode('utf8').splitlines()
    lines = [line for line in lines if line.startswith('"')]
    names = []
    for line in lines:
        match = re.match(r'"([^"]+)"', line)
        if not match:
            raise FormatError('Doku adı çözümlenemedi.')
        names.append(match.group(1))
    images = load_pc_fonts(pc_font)
    patches = {}
    for variant in ('dxt', 'etc', 'pvr'):
        dat, toc = f'txd.{variant}.dat', f'txd.{variant}.toc'
        patches[dat], patches[toc] = replace_database(assets[dat], assets[toc], names, images)
    physical_names = [name for name, line in zip(names, lines) if 'affiliate=' not in line]
    for variant in ('dxt', 'etc', 'pvr', 'unc'):
        name = f'txd.{variant}.tmb'
        raw, cursor, new, changed = assets[name], 0, bytearray(), []
        for texture in physical_names:
            old, cursor = read_block(raw, cursor)
            if texture in images:
                new.extend(encode_block(old, images[texture], thumbnail=True))
                changed.append(texture)
            else:
                new.extend(old)
        if cursor != len(raw) or sorted(changed) != ['font1', 'font2']:
            raise FormatError('Font küçük resim dizini uyuşmuyor.')
        patches[name] = bytes(new)
    return patches
