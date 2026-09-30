#!/usr/bin/env python3
"""Türkçe GUI veya komut satırı ile yerel yama oluşturma."""

import argparse
from pathlib import Path
import queue
import sys
import threading
import zipfile


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title('GTA San Andreas — Türkçe Yama Oluşturucu')
    root.geometry('770x510')
    root.minsize(650, 460)
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Kendi oyun dosyalarından Türkçe yama oluştur', font=('', 13, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Klasik Android 2.11.311 • ARM64\nOyun dosyaları ve çevirmenin PC ZIP paketi gerekli. İnternet bağlantısı kullanılmaz.').pack(anchor='w', pady=(7, 14))
    values = [tk.StringVar() for _ in range(3)]
    controls = []

    def choose(index):
        if index == 0:
            value = filedialog.askdirectory(title='Orijinal APK parçalarını içeren klasör')
        elif index == 1:
            value = filedialog.askopenfilename(title='CriminaL277 standart PC ZIP paketi', filetypes=[('ZIP arşivi', '*.zip')])
        else:
            parent = filedialog.askdirectory(title='Çıktının oluşturulacağı üst klasör')
            if not parent:
                return
            value = str(Path(parent) / 'gta-turkce-cikti')
        if value:
            values[index].set(value)

    for index, title in enumerate(('Oyun dosyalarının klasörü', 'PC Türkçe çeviri ZIP dosyası', 'Yeni çıktı klasörü (henüz var olmamalı)')):
        ttk.Label(frame, text=title).pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(3, 10))
        entry = ttk.Entry(row, textvariable=values[index])
        entry.pack(side='left', fill='x', expand=True)
        button = ttk.Button(row, text='Seç…', command=lambda i=index: choose(i))
        button.pack(side='right', padx=(8, 0))
        controls.extend((entry, button))
    events = queue.Queue()
    log = ScrolledText(frame, height=7, wrap='word', state='disabled')
    log.pack(fill='both', expand=True, pady=(12, 8))
    busy = False

    def append(text):
        log.configure(state='normal')
        log.insert('end', text + '\n')
        log.see('end')
        log.configure(state='disabled')

    def worker(paths):
        try:
            from patcher.build import build
            result = build(*paths, report=lambda text: events.put(('log', text)))
            events.put(('done', result))
        except Exception as exc:
            events.put(('error', str(exc)))

    def start():
        nonlocal busy
        if busy:
            return
        paths = [v.get().strip() for v in values]
        if not all(paths):
            messagebox.showerror('Eksik seçim', 'Önce üç dosya/klasör alanını doldur.')
            return
        busy = True
        for control in controls:
            control.configure(state='disabled')
        threading.Thread(target=worker, args=(paths,), daemon=True).start()

    def poll():
        nonlocal busy
        while True:
            try:
                kind, data = events.get_nowait()
            except queue.Empty:
                break
            if kind == 'log':
                append(data)
            else:
                busy = False
                for control in controls:
                    control.configure(state='normal')
                if kind == 'error':
                    append('Hata: ' + data)
                    messagebox.showerror('Yama oluşturulamadı', data)
                else:
                    messagebox.showinfo('Yama hazır', 'Paket hazırlandı. Telefona kurmadan önce bütün APK parçaları imzalanmalı.\n\nSONRAKI-ADIM.txt ve docs/KURULUM.md dosyalarını incele.')
        root.after(100, poll)

    button = ttk.Button(frame, text='Yamayı Oluştur', command=start)
    button.pack(anchor='e')
    controls.append(button)
    ttk.Label(frame, text='Bu araç telefona kurulum yapmaz ve mevcut oyunu kaldırmaz.').pack(anchor='w', pady=(7, 0))

    def close():
        if busy:
            messagebox.showinfo('İşlem sürüyor', 'Dosyaların doğrulanması tamamlanınca pencereyi kapatabilirsin.')
        else:
            root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    poll()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='Kendi dosyalarından GTA SA Android Türkçe yaması oluştur.')
    parser.add_argument('--gui', action='store_true', help='Dosya seçim penceresini aç')
    parser.add_argument('--oyun', type=Path, help='Orijinal APK parçalarının klasörü')
    parser.add_argument('--ceviri', type=Path, help='CriminaL277 standart PC ZIP paketi')
    parser.add_argument('--cikti', type=Path, help='Yeni çıktı klasörü; var olan klasörün üzerine yazılmaz')
    args = parser.parse_args()
    if args.gui or len(sys.argv) == 1:
        try:
            run_gui()
        except Exception as exc:
            print(f'Arayüz açılamadı: {exc}', file=sys.stderr)
            print('Python kurulumunda Tcl/Tk (Tkinter) bileşenini kontrol et. Komut satırı kullanımı için: python yama.py --help', file=sys.stderr)
            return 1
        return 0
    if not all((args.oyun, args.ceviri, args.cikti)):
        parser.error('--oyun, --ceviri ve --cikti birlikte gerekli.')
    try:
        from patcher.build import build
        build(args.oyun, args.ceviri, args.cikti)
    except (ValueError, OSError, ImportError, zipfile.BadZipFile) as exc:
        print(f'Hata: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
