#!/usr/bin/env python3
"""
Madafaka Downloader — GUI
MP3 · Stereo · 320 kbps · Auto-clean dla Rekordbox

Kroki:
  1. Pobieranie playlisty / utworu
  2. Czyszczenie nazw plikow i metadanych ID3
  3. Podsumowanie
"""

import sys
import os
import re
import queue
import shutil
import threading
import concurrent.futures
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox


# ──────────────────────────────────────────────────────────────
#  SRODOWISKO
# ──────────────────────────────────────────────────────────────

def setup_frozen_env():
    """Dodaje katalog binarek do PATH gdy program dziala jako .exe / .app."""
    if getattr(sys, 'frozen', False):
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        os.environ['PATH'] = bundle_dir + os.pathsep + os.environ.get('PATH', '')


def default_output_dir() -> str:
    base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'downloads')


# ──────────────────────────────────────────────────────────────
#  KROK 1 — POBIERANIE
# ──────────────────────────────────────────────────────────────

class _GUILogger:
    """Przekierowuje logi yt-dlp do funkcji log() aplikacji."""
    def __init__(self, log_fn):
        self._log = log_fn

    def debug(self, msg):
        pass  # pomijamy verbose debug

    def info(self, msg):
        pass  # handled via progress_hooks

    def warning(self, msg):
        # Pomijaj szumy techniczne — te problemy i tak widać w [ERR] lub nie mają znaczenia
        _ignore = (
            'Skipping unsupported client',
            'po_token',
            'PO Token',
            'GVS PO Token',
            'n challenge',
            'n-challenge',
            'remote components',
            'Remote components',
            'challenge solver',
            'SABR',
        )
        if any(s in msg for s in _ignore):
            return
        self._log(f'  [WARN] {msg}', 'warn')

    def error(self, msg):
        self._log(f'  [ERR]  {msg}', 'err')


def run_download(url: str, folder: str, log, set_progress, workers: int = 1):
    """
    Pobiera playlistę / utwór jako MP3 320 kbps stereo.
    workers > 1 oznacza równoczesne pobieranie wielu plików.
    Zwraca (downloaded: list[str], failed: list[str]).
    """
    import yt_dlp

    downloaded: list = []
    failed:     list = []
    _dl_lock  = threading.Lock()
    _sp_lock  = threading.Lock()
    _slot_prg: dict = {}          # slot_id -> tekst postępu

    def _update_status():
        with _sp_lock:
            parts = [v for v in _slot_prg.values() if v]
        set_progress('  │  '.join(parts) if parts else '')

    log('─' * 56, 'head')
    log('KROK 1 — Pobieranie plikow', 'head')
    log('─' * 56, 'head')
    log(f'  URL     : {url}')
    log(f'  Katalog : {folder}\n')

    # ── Faza A: wyciągnij listę URL-i bez pobierania ──────────
    log('  Pobieranie informacji o playliście…', 'dim')
    extract_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'logger': _GUILogger(log),
        'extractor_args': {'youtube': {'player_client': ['mweb']}},
    }
    try:
        with yt_dlp.YoutubeDL(extract_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        log(f'  [ERR] {e}', 'err')
        return [], [str(e)]

    if info is None:
        log('  [ERR] Nie mozna pobrac informacji o URL.', 'err')
        return [], ['Brak informacji']

    if 'entries' in info and info['entries']:
        entries = [e for e in info['entries'] if e]
        n = len(entries)
        log(f'  Playlista: {info.get("title", "(brak)")} — {n} utworów', 'dim')
    else:
        entries = [info]
        n = 1

    actual_workers = min(workers, n)   # nie więcej wątków niż plików
    if actual_workers > 1:
        log(f'  Równoczesne pobieranie: {actual_workers} wątków\n')
    else:
        log('')

    # Pula slotów wyświetlanych w pasku postępu (1..actual_workers)
    _slot_pool: queue.Queue = queue.Queue()
    for i in range(1, actual_workers + 1):
        _slot_pool.put(i)

    def _entry_url(entry: dict) -> str:
        u = entry.get('webpage_url') or entry.get('url') or ''
        if u.startswith('http'):
            return u
        vid = entry.get('id', '')
        if entry.get('ie_key', '') == 'Youtube' and vid:
            return f'https://www.youtube.com/watch?v={vid}'
        return url   # fallback

    # Opcje yt-dlp wspólne dla wszystkich wątków (bez hooków)
    dl_opts_base = {
        'format': 'bestaudio/best',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            },
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
        ],
        'writethumbnail': True,
        'postprocessor_args': {
            'ffmpegextractaudio': ['-ac', '2', '-ar', '44100'],
        },
        'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
        'ignoreerrors': True,
        'nooverwrites': True,
        'retries': 5,
        'fragment_retries': 5,
        'quiet': True,
        'extractor_args': {
            'youtube': {'player_client': ['mweb']},
        },
    }

    # ── Faza B: pobieranie (sekwencyjne lub równoległe) ────────
    def _download_one(entry: dict):
        entry_url = _entry_url(entry)
        slot = _slot_pool.get()          # czekaj na wolny slot
        lbl  = f'[{slot}]' if actual_workers > 1 else ''

        def hook(d):
            if d['status'] == 'downloading':
                pct   = d.get('_percent_str', '').strip()
                spd   = d.get('_speed_str',   '').strip()
                eta   = d.get('_eta_str',     '').strip()
                fname = os.path.basename(d.get('filename', ''))
                short = (fname[:32] + '…') if len(fname) > 33 else fname
                with _sp_lock:
                    _slot_prg[slot] = f'{lbl} {pct} {spd} ETA {eta} {short}'
                _update_status()
            elif d['status'] == 'finished':
                fname = os.path.basename(d.get('filename', ''))
                log(f'  [OK] {fname}', 'ok')
                with _dl_lock:
                    downloaded.append(fname)
                with _sp_lock:
                    _slot_prg.pop(slot, None)
                _update_status()
            elif d['status'] == 'error':
                fname = os.path.basename(d.get('filename', '?'))
                log(f'  [BLAD] {fname}', 'err')
                with _dl_lock:
                    failed.append(fname)
                with _sp_lock:
                    _slot_prg.pop(slot, None)
                _update_status()

        opts = {**dl_opts_base, 'progress_hooks': [hook], 'logger': _GUILogger(log)}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([entry_url])
        except Exception as e:
            log(f'  [ERR] {e}', 'err')
            with _dl_lock:
                failed.append(str(e))
            with _sp_lock:
                _slot_prg.pop(slot, None)
            _update_status()
        finally:
            _slot_pool.put(slot)    # zwolnij slot

    if actual_workers == 1:
        for entry in entries:
            _download_one(entry)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as ex:
            futures = [ex.submit(_download_one, e) for e in entries]
            concurrent.futures.wait(futures)

    return downloaded, failed


# ──────────────────────────────────────────────────────────────
#  KROK 2 — CZYSZCZENIE
# ──────────────────────────────────────────────────────────────

def _clean_filename(name: str) -> str:
    """Usuwa znaki specjalne z nazwy pliku."""
    import unicodedata
    base, ext = os.path.splitext(name)

    # Usun nawiasy kwadratowe z zawartoscia (YouTube ID itp.)
    base = re.sub(r'\s*\[[^\]]*\]', '', base)

    # Usun hashtagi (#vixa #music itd.)
    base = re.sub(r'\s*#\S+', '', base)

    # Usun emoji i symbole graficzne
    cleaned = []
    for ch in base:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cat in ('So', 'Cs') or 0xFE00 <= cp <= 0xFE0F or 0x1F000 <= cp <= 0x1FFFF:
            continue
        cleaned.append(ch)
    base = ''.join(cleaned)

    # Fullwidth znaki -> ASCII
    base = base.replace('\uff02', '"')   # ＂
    base = base.replace('\uff0a', '')    # ＊
    base = base.replace('\u29f8', '-')   # ⧸
    base = base.replace('\u2018', "'").replace('\u2019', "'")
    base = base.replace('\u201c', '"').replace('\u201d', '"')
    base = base.replace('\uff01', '!')   # ！
    base = base.replace('\uff1f', '?')   # ？

    # Klamry -> nawiasy
    base = base.replace('{', '(').replace('}', ')')

    # Usun @ i $
    base = base.replace('@', '').replace('$', '')

    # Usun wiszacy myslnik/spacje na koncu (np. "Closeness -")
    base = re.sub(r'[\s\-_]+$', '', base)

    # Znormalizuj spacje
    base = re.sub(r' {2,}', ' ', base).strip()
    return base + ext


def _parse_artist_title(filename: str):
    """Parsuje nazwe pliku na (artist, title) po znaku ' - '.
    Ignoruje wiodacy numer sciezki (np. '001 - ', '12 - ').
    Wszystko przed pierwszym ' - ' to artysta, reszta to tytul.
    """
    base = os.path.splitext(filename)[0]

    # Usun wiodacy numer (np. "001 - " lub "12 - ")
    base = re.sub(r'^\d+\s*-\s*', '', base).strip()

    if ' - ' in base:
        artist, title = base.split(' - ', 1)
        return artist.strip(), title.strip()

    return '', base.strip()


def _square_jpeg(data: bytes, size: int = 500) -> bytes:
    """
    Przycina obraz do kwadratu (center crop) i skaluje do size×size px.
    Zwraca bajty JPEG gotowe do osadzenia w APIC.
    Wymaga Pillow. Jeśli Pillow nie jest dostępne, zwraca oryginalne dane.
    """
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data)).convert('RGB')
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img  = img.crop((left, top, left + side, top + side))
        img  = img.resize((size, size), Image.LANCZOS)
        buf  = io.BytesIO()
        img.save(buf, format='JPEG', quality=90)
        return buf.getvalue()
    except Exception:
        return data  # fallback: oryginał bez zmian


def _clean_metadata(path: str):
    """
    Czyści ID3 do wersji 2.3 (Artist + Title) zachowując grafikę okładki (APIC).
    Zwraca (ok: bool, error: str).
    """
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, APIC
        from mutagen.mp3 import MP3

        # Zachowaj istniejące okładki przed wyczyszczeniem (skaluj do 500×500 dla Pioneer)
        saved_apic = []
        try:
            existing = ID3(path)
            for key, frame in existing.items():
                if key.startswith('APIC'):
                    processed = _square_jpeg(frame.data)
                    saved_apic.append(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=frame.type,
                        desc=frame.desc,
                        data=processed,
                    ))
        except Exception:
            pass

        audio = MP3(path)
        audio.tags = None
        audio.save()

        artist, title = _parse_artist_title(os.path.basename(path))
        tags = ID3()
        tags.add(TIT2(encoding=3, text=title))
        if artist:
            tags.add(TPE1(encoding=3, text=artist))
        for apic in saved_apic:
            tags.add(apic)
        tags.save(path, v2_version=3)
        return True, ''
    except Exception as e:
        return False, str(e)


def run_cleaning(folder: str, log):
    """
    Przemianowuje pliki i czyści metadane.
    Zwraca (renamed: int, ok: int, errors: list[(fname, reason)]).
    """
    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith('.mp3') and not f.startswith('._')
    )
    renamed, ok, errors = 0, 0, []

    log('\n' + '─' * 56, 'head')
    log('KROK 2 — Czyszczenie nazw i metadanych', 'head')
    log('─' * 56, 'head')

    for fname in files:
        old_path = os.path.join(folder, fname)
        new_name = _clean_filename(fname)
        new_path  = os.path.join(folder, new_name)

        if fname != new_name:
            try:
                os.rename(old_path, new_path)
                log(f'  [RENAME] {new_name}', 'ok')
                renamed += 1
            except Exception as e:
                log(f'  [BLAD rename] {fname}: {e}', 'err')
                errors.append((fname, f'Rename: {e}'))
                new_path = old_path  # dalej czyscIMY metadane oryginalnego

        success, err_msg = _clean_metadata(new_path)
        if success:
            artist, title = _parse_artist_title(new_name)
            log(f'       artist: {artist or "(brak)"}  |  title: {title}', 'dim')
            ok += 1
        else:
            log(f'  [WARN metadane] {new_name}: {err_msg}', 'warn')
            errors.append((new_name, f'Metadata: {err_msg}'))

    log(f'\n  Wynik: {ok} plikow OK  ·  {len(errors)} bledow')
    return renamed, ok, errors


# ──────────────────────────────────────────────────────────────
#  GUI
# ──────────────────────────────────────────────────────────────

_C = dict(
    bg      = '#1e1e2e',
    surface = '#2a2a3e',
    border  = '#45475a',
    accent  = '#7c5cbf',
    text    = '#cdd6f4',
    dim     = '#6c7086',
    ok      = '#a6e3a1',
    err     = '#f38ba8',
    warn    = '#f9e2af',
    log_bg  = '#181825',
)


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('Madafaka Downloader')
        self.configure(bg=_C['bg'])
        self.minsize(760, 600)
        self.resizable(True, True)
        self._q = queue.Queue()
        self._workers_var = tk.IntVar(value=3)
        self._build_ui()
        self._center()
        self._poll()
        self._log('  Gotowy – wklej URL playlisty i nacisnij "Pobierz i oczysc".', 'dim')

    # ── layout ────────────────────────────────────────────────

    def _build_ui(self):
        tk.Frame(self, bg=_C['bg'], height=10).pack(fill='x')

        # tytuł
        tk.Label(self, text='Madafaka Downloader',
                 font=('Segoe UI', 15, 'bold'), bg=_C['bg'], fg=_C['accent']).pack()
        tk.Label(self, text='MP3 · Stereo · 320 kbps · Auto-clean dla Rekordbox',
                 font=('Segoe UI', 9), bg=_C['bg'], fg=_C['dim']).pack(pady=(2, 14))

        # URL
        g = tk.Frame(self, bg=_C['bg'])
        g.pack(fill='x', padx=20, pady=4)
        tk.Label(g, text='URL playlisty lub utworu:', font=('Segoe UI', 10),
                 bg=_C['bg'], fg=_C['text']).pack(anchor='w')
        row = tk.Frame(g, bg=_C['bg'])
        row.pack(fill='x', pady=3)
        box = tk.Frame(row, bg=_C['surface'],
                       highlightbackground=_C['accent'], highlightthickness=1)
        box.pack(side='left', fill='x', expand=True)
        self._url = tk.StringVar()
        tk.Entry(box, textvariable=self._url, font=('Segoe UI', 10),
                 bg=_C['surface'], fg=_C['text'], insertbackground=_C['text'],
                 relief='flat', bd=8).pack(fill='x')
        tk.Button(row, text='Wklej', font=('Segoe UI', 9),
                  bg=_C['accent'], fg='white', relief='flat', padx=12, cursor='hand2',
                  command=self._paste).pack(side='right', padx=(6, 0))

        # katalog
        g2 = tk.Frame(self, bg=_C['bg'])
        g2.pack(fill='x', padx=20, pady=4)
        tk.Label(g2, text='Katalog docelowy:', font=('Segoe UI', 10),
                 bg=_C['bg'], fg=_C['text']).pack(anchor='w')
        row2 = tk.Frame(g2, bg=_C['bg'])
        row2.pack(fill='x', pady=3)
        box2 = tk.Frame(row2, bg=_C['surface'],
                        highlightbackground=_C['border'], highlightthickness=1)
        box2.pack(side='left', fill='x', expand=True)
        self._dir = tk.StringVar(value=default_output_dir())
        tk.Entry(box2, textvariable=self._dir, font=('Segoe UI', 10),
                 bg=_C['surface'], fg=_C['text'], insertbackground=_C['text'],
                 relief='flat', bd=8).pack(fill='x')
        tk.Button(row2, text='Wybierz\u2026', font=('Segoe UI', 9),
                  bg=_C['surface'], fg=_C['text'], relief='flat', padx=10, cursor='hand2',
                  command=self._pick_dir).pack(side='right', padx=(6, 0))

        # przyciski
        btn_row = tk.Frame(self, bg=_C['bg'])
        btn_row.pack(pady=(10, 8))
        self._btn = tk.Button(btn_row, text='\u25b6   Pobierz i oczysc',
                              font=('Segoe UI', 11, 'bold'),
                              bg=_C['accent'], fg='white', relief='flat',
                              padx=26, pady=10, cursor='hand2',
                              command=self._start)
        self._btn.pack(side='left', padx=4)
        tk.Button(btn_row, text='Wyczysc log', font=('Segoe UI', 9),
                  bg=_C['surface'], fg=_C['dim'], relief='flat',
                  padx=12, pady=10, cursor='hand2',
                  command=self._clear_log).pack(side='left', padx=4)

        # liczba równoczesnych pobrań
        g3 = tk.Frame(self, bg=_C['bg'])
        g3.pack(fill='x', padx=20, pady=4)
        tk.Label(g3, text='R\u00f3wnoczesne pobieranie (1\u20135 plik\u00f3w naraz):',
                 font=('Segoe UI', 10), bg=_C['bg'], fg=_C['text']).pack(anchor='w')
        row3 = tk.Frame(g3, bg=_C['bg'])
        row3.pack(fill='x', pady=3)
        spin_box = tk.Frame(row3, bg=_C['surface'],
                            highlightbackground=_C['border'], highlightthickness=1)
        spin_box.pack(side='left')
        tk.Spinbox(spin_box, textvariable=self._workers_var,
                   from_=1, to=5, width=3,
                   font=('Segoe UI', 12, 'bold'),
                   bg=_C['surface'], fg=_C['accent'],
                   buttonbackground=_C['surface'],
                   relief='flat', bd=8).pack()
        self._workers_desc = tk.Label(row3,
                   text=self._workers_label(self._workers_var.get()),
                   font=('Segoe UI', 9), bg=_C['bg'], fg=_C['dim'])
        self._workers_desc.pack(side='left', padx=(10, 0))
        self._workers_var.trace_add('write', self._on_workers_change)

        # przyciski
        btn_row = tk.Frame(self, bg=_C['bg'])
        btn_row.pack(pady=(10, 8))
        self._btn = tk.Button(btn_row, text='\u25b6   Pobierz i oczysc',
                              font=('Segoe UI', 11, 'bold'),
                              bg=_C['accent'], fg='white', relief='flat',
                              padx=26, pady=10, cursor='hand2',
                              command=self._start)
        self._btn.pack(side='left', padx=4)
        tk.Button(btn_row, text='Wyczysc log', font=('Segoe UI', 9),
                  bg=_C['surface'], fg=_C['dim'], relief='flat',
                  padx=12, pady=10, cursor='hand2',
                  command=self._clear_log).pack(side='left', padx=4)

        # log
        log_f = tk.Frame(self, bg=_C['bg'])
        log_f.pack(fill='both', expand=True, padx=20, pady=(0, 4))
        tk.Label(log_f, text='Podglad:', font=('Segoe UI', 9),
                 bg=_C['bg'], fg=_C['dim']).pack(anchor='w')
        self._log_box = scrolledtext.ScrolledText(
            log_f, font=('Courier New', 9), bg=_C['log_bg'], fg=_C['text'],
            relief='flat', bd=0, wrap='word', state='disabled')
        self._log_box.pack(fill='both', expand=True, pady=(2, 0))
        for tag, col in [('ok',   _C['ok']),  ('err',  _C['err']),
                         ('warn', _C['warn']), ('head', _C['accent']),
                         ('dim',  _C['dim'])]:
            self._log_box.tag_config(tag, foreground=col)

        # pasek postępu (etykieta na dole)
        self._prog_var = tk.StringVar()
        tk.Label(self, textvariable=self._prog_var,
                 font=('Courier New', 8), bg=_C['surface'], fg=_C['warn'],
                 anchor='w', padx=12, pady=4).pack(fill='x', side='bottom')

    # ── helpers ───────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 760)
        h = max(self.winfo_height(), 600)
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _paste(self):
        try:
            self._url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self._dir.get())
        if d:
            self._dir.set(d)

    @staticmethod
    def _workers_label(n: int) -> str:
        labels = {
            1: 'jeden plik na raz (bezpieczne, wolniejsze)',
            2: 'dwa pliki na raz',
            3: 'trzy pliki na raz (zalecane)',
            4: 'cztery pliki na raz',
            5: 'pięć plików na raz (maksymalne obciążenie)',
        }
        return labels.get(int(n), '')

    def _on_workers_change(self, *_):
        try:
            n = self._workers_var.get()
            self._workers_desc.configure(text=self._workers_label(n))
        except (tk.TclError, ValueError):
            pass

    def _log(self, msg: str, tag: str = ''):
        """Wątek-bezpieczne dodanie linii do logu."""
        self._q.put(('log', msg, tag))

    def _clear_log(self):
        self._log_box.configure(state='normal')
        self._log_box.delete('1.0', 'end')
        self._log_box.configure(state='disabled')

    def _poll(self):
        """Opróżnia kolejkę i aktualizuje UI w wątku głównym."""
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                if kind == 'log':
                    _, msg, tag = item
                    self._log_box.configure(state='normal')
                    if tag:
                        self._log_box.insert('end', msg + '\n', tag)
                    else:
                        self._log_box.insert('end', msg + '\n')
                    self._log_box.see('end')
                    self._log_box.configure(state='disabled')
                elif kind == 'progress':
                    self._prog_var.set(item[1])
                elif kind == 'done':
                    self._btn.configure(state='normal', text='\u25b6   Pobierz i oczysc')
                    self._prog_var.set('')
        except queue.Empty:
            pass
        self.after(40, self._poll)

    # ── akcja główna ──────────────────────────────────────────

    def _start(self):
        url    = self._url.get().strip()
        folder = self._dir.get().strip()
        if not url:
            messagebox.showwarning('Brak URL', 'Wklej URL playlisty lub utworu YouTube.')
            return
        if not folder:
            messagebox.showwarning('Brak katalogu', 'Wybierz katalog docelowy.')
            return
        workers = max(1, min(5, self._workers_var.get()))
        self._btn.configure(state='disabled', text='\u23f3  Trwa pobieranie\u2026')
        threading.Thread(target=self._worker, args=(url, folder, workers), daemon=True).start()

    def _worker(self, url: str, folder: str, workers: int = 1):
        log      = self._log
        set_prog = lambda msg: self._q.put(('progress', msg))

        os.makedirs(folder, exist_ok=True)

        # sprawdzenie zależności
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            log('BLAD: yt-dlp nie jest zainstalowany.', 'err')
            log('  Uruchom: pip install yt-dlp', 'warn')
            self._q.put(('done',))
            return

        if not shutil.which('ffmpeg'):
            log('BLAD: ffmpeg nie zostal znaleziony w PATH!', 'err')
            hint = ('Zainstaluj: brew install ffmpeg' if sys.platform == 'darwin'
                    else 'Pobierz z: https://ffmpeg.org/download.html')
            log(hint, 'warn')
            self._q.put(('done',))
            return

        # ── KROK 1: pobieranie ────────────────────────────────
        try:
            downloaded, failed_dl = run_download(url, folder, log, set_prog, workers)
        except Exception as e:
            log(f'BLAD pobierania: {e}', 'err')
            self._q.put(('done',))
            return

        # ── KROK 2: czyszczenie ───────────────────────────────
        try:
            renamed_n, ok_n, clean_errs = run_cleaning(folder, log)
        except Exception as e:
            log(f'BLAD czyszczenia: {e}', 'err')
            renamed_n, ok_n, clean_errs = 0, 0, [(str(e), '')]

        # ── KROK 3: podsumowanie ──────────────────────────────
        log('\n' + '=' * 56, 'head')
        log('  PODSUMOWANIE', 'head')
        log('=' * 56, 'head')
        log(f'  Pobrane        : {len(downloaded)} plikow',
            'ok' if downloaded else 'warn')
        log(f'  Przetworzone   : {ok_n} plikow',
            'ok' if ok_n else 'warn')
        if renamed_n:
            log(f'  Przemianowane  : {renamed_n} plikow')

        if failed_dl:
            log(f'\n  Bledy pobierania ({len(failed_dl)}):', 'err')
            for f in failed_dl:
                log(f'    \u2022 {f}', 'err')

        if clean_errs:
            log(f'\n  Problematyczne pliki ({len(clean_errs)}):', 'err')
            for fname, reason in clean_errs:
                log(f'    \u2022 {fname}', 'err')
                if reason:
                    log(f'      {reason}', 'warn')

        if not failed_dl and not clean_errs:
            log('\n  Wszystko OK! \u2713', 'ok')

        log('=' * 56 + '\n', 'head')
        self._q.put(('done',))


# ──────────────────────────────────────────────────────────────
#  START
# ──────────────────────────────────────────────────────────────

def main():
    setup_frozen_env()
    App().mainloop()


if __name__ == '__main__':
    main()
