#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deus Ex: Mankind Divided — Russian Voice Loudness Fix (GUI installer, dark theme).
"""
import os, sys, json, shutil, threading, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Deus Ex: Mankind Divided — Нормализация русской озвучки"
HEADER_TEXT = "Нормализация громкости русской озвучки Deus Ex: Mankind Divided"
ARCHIVES = [
    r"runtime\Game.layer.0.ru.archive",
    r"DLC\runtime\DLC01.layer.0.all.archive",
    r"DLC\runtime\DLC02.layer.0.all.archive",
    r"DLC\runtime\DLCPreOrder.layer.0.all.archive",
]

# dark palette
BG = "#1e1e1e"
PANEL = "#252526"
ENTRY_BG = "#2d2d30"
FG = "#e8e8e8"
SUB = "#9a9a9a"
ACCENT = "#3d8bff"
GREEN = "#5ec95e"
RED = "#e05c5c"


def base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def pad_fsb5(new_bytes, old_size):
    if len(new_bytes) == old_size:
        return new_bytes
    if len(new_bytes) > old_size:
        return None
    sh = int.from_bytes(new_bytes[12:16], 'little')
    nt = int.from_bytes(new_bytes[16:20], 'little')
    old_data = old_size - 60 - sh - nt
    data_start = 60 + sh + nt
    new_data = new_bytes[data_start:]
    if len(new_data) > old_data:
        return None
    pad = b'\x00' * (old_data - len(new_data))
    out = bytearray(new_bytes[:data_start] + new_data + pad)
    out[20:24] = old_data.to_bytes(4, 'little')
    return bytes(out)


def find_game_root():
    for c in [
        r"D:\Steam\steamapps\common\Deus Ex Mankind Divided",
        r"C:\Program Files (x86)\Steam\steamapps\common\Deus Ex Mankind Divided",
        r"C:\Steam\steamapps\common\Deus Ex Mankind Divided",
        r"E:\Steam\steamapps\common\Deus Ex Mankind Divided",
        r"F:\Steam\steamapps\common\Deus Ex Mankind Divided",
        r"G:\Steam\steamapps\common\Deus Ex Mankind Divided",
    ]:
        if os.path.exists(os.path.join(c, 'runtime', 'Game.layer.0.ru.archive')):
            return c
    return None


def is_valid_root(root):
    return bool(root) and os.path.exists(os.path.join(root, 'runtime', 'Game.layer.0.ru.archive'))


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("700x540")
        self.root.minsize(640, 480)
        self.root.configure(bg=BG)

        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Проверка папки игры…")
        self.progress_var = tk.IntVar(value=0)
        self.percent_var = tk.StringVar(value="0%")

        self.q = queue.Queue()
        self.worker = None
        self.busy = False

        self.setup_theme()
        self.set_icon()
        self.build_ui()
        self.auto_detect()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def setup_theme(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use('clam')
        except Exception:
            pass
        st.configure('.', background=BG, foreground=FG, fieldbackground=ENTRY_BG,
                     bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL,
                     troughcolor=PANEL, selectbackground=ACCENT, selectforeground="#ffffff",
                     font=('Segoe UI', 10))
        st.configure('TFrame', background=BG)
        st.configure('TLabel', background=BG, foreground=FG)
        st.configure('Header.TLabel', background=BG, foreground=FG, font=('Segoe UI', 13, 'bold'))
        st.configure('Sub.TLabel', background=BG, foreground=SUB, font=('Segoe UI', 9))
        st.configure('Status.TLabel', background=BG, foreground=GREEN, font=('Segoe UI', 10))
        st.configure('TButton', background=PANEL, foreground=FG, borderwidth=0,
                     focuscolor=BG, padding=(14, 7))
        st.map('TButton',
               background=[('active', '#35353a'), ('pressed', '#3d3d42'), ('disabled', PANEL)],
               foreground=[('disabled', '#777777')])
        st.configure('Accent.TButton', background=ACCENT, foreground='#ffffff', borderwidth=0,
                     focuscolor=BG, padding=(18, 8))
        st.map('Accent.TButton', background=[('active', '#5a9dff'), ('pressed', '#2f74d0')])
        st.configure('TEntry', fieldbackground=ENTRY_BG, foreground=FG, insertcolor=FG,
                     bordercolor=PANEL, padding=5)
        st.configure('TProgressbar', background=ACCENT, troughcolor=PANEL,
                     bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT, thickness=14)

    def set_icon(self):
        if getattr(sys, 'frozen', False):
            ico = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            ico = os.path.join(base_dir(), 'icon.ico')
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

    def build_ui(self):
        pad = {'padx': 16, 'pady': 6}
        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text=HEADER_TEXT, style='Header.TLabel', wraplength=640).pack(anchor='w')
        ttk.Label(frm, text="Патч вшивает 12 393 банка озвучки в 4 архива игры.",
                  style='Sub.TLabel').pack(anchor='w', pady=(2, 12))

        pf = ttk.Frame(frm)
        pf.pack(fill='x', **pad)
        ttk.Label(pf, text="Папка игры:").pack(side='left')
        ttk.Entry(pf, textvariable=self.path_var).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(pf, text="Обзор…", command=self.browse).pack(side='left')

        ttk.Label(frm, textvariable=self.status_var, style='Status.TLabel').pack(anchor='w', **pad)

        pr = ttk.Frame(frm)
        pr.pack(fill='x', **pad)
        self.bar = ttk.Progressbar(pr, variable=self.progress_var, maximum=100)
        self.bar.pack(side='left', fill='x', expand=True)
        ttk.Label(pr, textvariable=self.percent_var, width=6).pack(side='right', padx=(10, 0))

        bf = ttk.Frame(frm)
        bf.pack(fill='x', **pad)
        self.btn_install = ttk.Button(bf, text="Установить", style='Accent.TButton', command=self.install)
        self.btn_install.pack(side='left', padx=(0, 8))
        self.btn_rollback = ttk.Button(bf, text="Откатить", command=self.rollback)
        self.btn_rollback.pack(side='left', padx=(0, 8))
        ttk.Button(bf, text="Выход", command=self.on_close).pack(side='right')

        ttk.Label(frm, text="Журнал:", style='Sub.TLabel').pack(anchor='w', pady=(10, 0))
        lf = ttk.Frame(frm)
        lf.pack(fill='both', expand=True, pady=(4, 0))
        self.logtxt = tk.Text(lf, height=10, wrap='word', state='disabled',
                              bg=ENTRY_BG, fg=FG, insertbackground=FG,
                              selectbackground=ACCENT, relief='flat', bd=0,
                              font=('Consolas', 9), padx=8, pady=6)
        sb = ttk.Scrollbar(lf, command=self.logtxt.yview)
        self.logtxt.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.logtxt.config(yscrollcommand=sb.set)

    def log(self, text):
        self.logtxt.config(state='normal')
        self.logtxt.insert('end', text + '\n')
        self.logtxt.see('end')
        self.logtxt.config(state='disabled')

    def auto_detect(self):
        root = find_game_root()
        if root:
            self.path_var.set(root)
            self.status_var.set("Игра найдена автоматически. Готово к установке.")
        else:
            self.status_var.set("Игра не найдена автоматически — укажите папку вручную.")

    def browse(self):
        d = filedialog.askdirectory(title="Укажите папку Deus Ex Mankind Divided")
        if d:
            self.path_var.set(d)
            self.status_var.set("Готово к установке." if is_valid_root(d)
                                else "Папка не похожа на папку игры (нет runtime\\Game.layer.0.ru.archive).")

    def install(self):
        if self.busy:
            return
        root = self.path_var.get().strip()
        if not is_valid_root(root):
            messagebox.showerror("Ошибка", "Указана неверная папка игры.\n"
                                "Нужна папка, где есть runtime\\Game.layer.0.ru.archive.")
            return
        base = base_dir()
        if not os.path.isdir(os.path.join(base, 'fsb')) or not os.path.exists(os.path.join(base, 'patches.json')):
            messagebox.showerror("Ошибка", "Рядом с установщиком нет папки 'fsb' и файла 'patches.json'.\n"
                                "Положите установщик в папку с распакованным модом.")
            return
        self.set_busy(True)
        self.status_var.set("Установка…")
        self.log("Начинаю установку…")
        self.q = queue.Queue()
        self.worker = threading.Thread(target=self.do_install, args=(root, base), daemon=True)
        self.worker.start()
        self.root.after(100, self.poll)

    def do_install(self, root, base):
        try:
            patches = json.load(open(os.path.join(base, 'patches.json'), encoding='utf-8'))
            fsb_dir = os.path.join(base, 'fsb')
            total = len(patches)
            patched = skipped = 0
            backed = set()
            for i, p in enumerate(patches, 1):
                apath = os.path.join(root, p['archive'])
                if not os.path.exists(apath):
                    skipped += 1
                    continue
                new_fsb = os.path.join(fsb_dir, p['new_fsb'])
                if not os.path.exists(new_fsb):
                    skipped += 1
                    continue
                nb = pad_fsb5(open(new_fsb, 'rb').read(), p['old_size'])
                if nb is None:
                    skipped += 1
                    continue
                if apath not in backed:
                    bak = apath + '.bak'
                    if not os.path.exists(bak):
                        shutil.copy2(apath, bak)
                    backed.add(apath)
                with open(apath, 'r+b') as f:
                    f.seek(p['offset'])
                    if f.read(4) != b'FSB5':
                        skipped += 1
                        continue
                    f.seek(p['offset'])
                    f.write(nb)
                patched += 1
                if i % 100 == 0 or i == total:
                    self.q.put(('progress', i, total, patched, skipped))
            self.q.put(('done', patched, skipped))
        except Exception as e:
            self.q.put(('error', str(e)))

    def rollback(self):
        if self.busy:
            return
        if not messagebox.askyesno("Откат", "Восстановить оригинальные архивы из бэкапов (.bak)?"):
            return
        root = self.path_var.get().strip()
        if not root:
            messagebox.showerror("Ошибка", "Сначала укажите папку игры.")
            return
        restored = missing = 0
        for rel in ARCHIVES:
            apath = os.path.join(root, rel)
            bak = apath + '.bak'
            if os.path.exists(bak):
                try:
                    os.remove(apath)
                    os.rename(bak, apath)
                    restored += 1
                except OSError as e:
                    self.log("Ошибка отката %s: %s" % (os.path.basename(apath), e))
            else:
                missing += 1
        self.status_var.set("Откат выполнен." if restored else "Бэкапы не найдены.")
        msg = "Восстановлено архивов: %d" % restored
        if missing:
            msg += "\nБэкапов не найдено: %d" % missing
        messagebox.showinfo("Откат", msg)

    def poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == 'progress':
                    _, i, total, patched, skipped = msg
                    pct = int(i / total * 100)
                    self.progress_var.set(pct)
                    self.percent_var.set("%d%%" % pct)
                    if i % 1000 == 0 or i == total:
                        self.log("  %d / %d  (применено %d, пропущено %d)" % (i, total, patched, skipped))
                elif msg[0] == 'done':
                    _, patched, skipped = msg
                    self.progress_var.set(100)
                    self.percent_var.set("100%")
                    self.status_var.set("Готово. Применено %d, пропущено %d." % (patched, skipped))
                    self.log("=== ГОТОВО: применено %d, пропущено %d ===" % (patched, skipped))
                    if skipped:
                        self.log("Пропущенные записи — обычно из-за несовпадения версии игры.")
                    self.set_busy(False)
                    messagebox.showinfo("Готово", "Установка завершена.\nПрименено %d, пропущено %d." % (patched, skipped))
                elif msg[0] == 'error':
                    _, err = msg
                    self.status_var.set("Ошибка.")
                    self.log("ОШИБКА: %s" % err)
                    self.set_busy(False)
                    messagebox.showerror("Ошибка", err)
        except queue.Empty:
            pass
        if self.worker and self.worker.is_alive():
            self.root.after(100, self.poll)

    def set_busy(self, busy):
        self.busy = busy
        state = 'disabled' if busy else 'normal'
        self.btn_install.config(state=state)
        self.btn_rollback.config(state=state)

    def on_close(self):
        if self.busy:
            if not messagebox.askyesno("Выход", "Установка ещё выполняется. Прервать и выйти?"):
                return
        self.root.destroy()


if __name__ == '__main__':
    App()
