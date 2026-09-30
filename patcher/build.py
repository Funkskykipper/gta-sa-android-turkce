"""Offline, version-checked patch construction. Never install or uninstall."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile

from .fonts import patch_fonts
from .gxt import FormatError, GXT, translate


ROOT = Path(__file__).resolve().parent.parent
TEXT = 'assets/text/american.gxt'
FONT_PREFIX = 'assets/texdb/txd/'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_hash(raw, expected, label):
    if digest(raw) != expected:
        raise FormatError(f'{label}: dosya desteklenen sürümle uyuşmuyor. Kaynak dosya değiştirilmedi.')


def read_member(archive, name, max_size=64 * 1024 * 1024):
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise FormatError(f'Paket içinde gerekli dosya yok: {name}') from exc
    if info.file_size > max_size:
        raise FormatError(f'Beklenmeyen dosya boyutu: {name}')
    return archive.read(info)


def read_translation(path, manifest):
    # Do not extract an untrusted archive; read only two bounded members.
    with zipfile.ZipFile(path) as archive:
        candidates = {}
        for name in archive.namelist():
            normalized = name.replace('\\', '/').casefold()
            if normalized.endswith('/text/american.gxt'):
                candidates.setdefault('gxt', []).append(name)
            if normalized.endswith('/models/fonts.txd') and 'd.e.p.' not in normalized:
                candidates.setdefault('fonts', []).append(name)
        if any(len(candidates.get(key, [])) != 1 for key in ('gxt', 'fonts')):
            raise FormatError('Standart PC ZIP paketi gerekli; GXT veya font seçimi belirsiz.')
        result = {key: read_member(archive, names[0], 16 * 1024 * 1024) for key, names in candidates.items()}
    check_hash(result['gxt'], manifest['pc_gxt_sha256'], 'PC çevirisi')
    check_hash(result['fonts'], manifest['pc_font_sha256'], 'PC yazı tipi')
    return result


def prepare(game_dir, translation_zip, report=print):
    game_dir = Path(game_dir).expanduser().resolve()
    translation_zip = Path(translation_zip).expanduser().resolve()
    manifest = json.loads((ROOT / 'data' / 'supported.json').read_text(encoding='utf8'))
    for name in ('base.apk', 'split_data_main.apk', 'split_config.arm64_v8a.apk'):
        if not (game_dir / name).is_file():
            raise FormatError(f'Oyun klasöründe {name} bulunamadı.')
    report('Oyun ve çeviri sürümleri kontrol ediliyor...')
    if file_digest(game_dir / 'base.apk') != manifest['base_apk_sha256']:
        raise FormatError('Bu base.apk desteklenmiyor. Araç yalnızca test edilen orijinal 2.11.311 sürümünü kabul eder.')
    if file_digest(game_dir / 'split_config.arm64_v8a.apk') != manifest['arm64_apk_sha256']:
        raise FormatError('ARM64 oyun bileşeni desteklenen sürümle uyuşmuyor.')
    pc = read_translation(translation_zip, manifest)
    assets = {}
    with zipfile.ZipFile(game_dir / 'split_data_main.apk') as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise FormatError('APK içinde yinelenen dosya adları var.')
        for name, sha256 in manifest['assets_sha256'].items():
            assets[name] = read_member(archive, name)
            check_hash(assets[name], sha256, name)
    report('Görev, altyazı ve mobil kontrol metinleri hazırlanıyor...')
    original = GXT(assets[TEXT])
    supplements = json.loads((ROOT / 'data' / 'mobile-tr.json').read_text(encoding='utf8'))
    patched_text, coverage = translate(original, GXT(pc['gxt']), supplements)
    report('Türkçe fontlar mobil biçime dönüştürülüyor...')
    font_assets = {name.removeprefix(FONT_PREFIX): value for name, value in assets.items() if name.startswith(FONT_PREFIX)}
    fonts = patch_fonts(font_assets, pc['fonts'])
    patches = {TEXT: patched_text}
    patches.update({FONT_PREFIX + name: value for name, value in fonts.items()})
    coverage.update({'version': manifest['version'], 'changed_assets': len(patches), 'signed': False})
    return game_dir, patches, coverage


def write_apk(source, destination, patches):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, 'w', allowZip64=True) as output:
        if not patches.keys() <= set(original.namelist()):
            raise FormatError('APK içinde değiştirilecek dosya bulunamadı.')
        for entry in original.infolist():
            info = copy.copy(entry)
            if info.compress_type == zipfile.ZIP_STORED:
                start = output.fp.tell() + 30 + len(info.filename.encode('utf8')) + len(info.extra)
                padding = (-start - 4) % 4
                info.extra += struct.pack('<HH', 0xFFFF, padding) + b'\0' * padding
            if info.filename in patches:
                output.writestr(info, patches[info.filename])
            else:
                with original.open(entry) as reader, output.open(info, 'w') as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination) as output:
        if original.namelist() != output.namelist():
            raise FormatError('APK dosya listesi korunamadı.')
        for entry in original.infolist():
            if entry.filename in patches:
                if output.read(entry.filename) != patches[entry.filename]:
                    raise FormatError('Yazılan yama dosyası doğrulanamadı.')
            elif output.getinfo(entry.filename).CRC != entry.CRC:
                raise FormatError('Yama dışındaki bir APK dosyası değişti.')


def build(game_dir, translation_zip, output_dir, report=print):
    output_dir = Path(output_dir).expanduser().resolve()
    source_dir = Path(game_dir).expanduser().resolve()
    source_zip = Path(translation_zip).expanduser().resolve()
    if output_dir.exists():
        raise FormatError('Çıktı klasörü zaten var. Var olmayan yeni bir klasör adı seç.')
    if output_dir == source_dir or output_dir in source_dir.parents or output_dir in source_zip.parents:
        raise FormatError('Çıktı klasörü kaynak dosyaları kapsamamalı.')
    game_dir, patches, coverage = prepare(source_dir, source_zip, report)
    if output_dir.exists():
        raise FormatError('Çıktı klasörü işlem sırasında oluşturulmuş; üzerine yazılmadı.')
    output_dir.mkdir(parents=True, exist_ok=False)
    pending = output_dir / 'OLUSTURMA-TAMAMLANMADI.txt'
    pending.write_text('İşlem tamamlanmadı. Bu klasördeki APK dosyalarını kurmayın.\n', encoding='utf8')
    unsigned = output_dir / 'unsigned'
    unsigned.mkdir()
    report('Oyun paketi oluşturuluyor; bu işlem yaklaşık 1,5 GB çıktı üretir...')
    write_apk(game_dir / 'split_data_main.apk', unsigned / 'split_data_main.apk', patches)
    for path in [game_dir / 'base.apk', *sorted(game_dir.glob('split_config.*.apk'))]:
        shutil.copyfile(path, unsigned / path.name)
        if file_digest(path) != file_digest(unsigned / path.name):
            raise FormatError('Kopyalanan APK doğrulanamadı.')
    coverage['apk_sha256'] = {p.name: file_digest(p) for p in sorted(unsigned.glob('*.apk'))}
    (output_dir / 'rapor.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (output_dir / 'SONRAKI-ADIM.txt').write_text(
        'Yama oluşturuldu fakat APK imzaları henüz yenilenmedi.\n'
        'unsigned klasörünü doğrudan kurmayın. Bütün APK parçaları aynı anahtarla imzalanmalı.\n'
        'Depodaki docs/KURULUM.md dosyasını izleyin. Araç telefonda kurulum veya kaldırma yapmaz.\n', encoding='utf8')
    pending.unlink()
    report(f"Hazır: {coverage['changed']} metin kaydı değiştirildi. Sonuç: {output_dir}")
    return coverage
