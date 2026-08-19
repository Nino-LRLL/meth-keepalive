"""Meth UI — MainWindow.

Petite fenêtre compacte (320×458) « à la calculatrice moderne », style
Apple épuré dans les gris/noir **métal mat** :

- palette NEUTRE (aucune teinte bleue) : noirs profonds, gris Apple
  (separators #2c2c2e, secondary #8e8e93, text #f5f5f7) ;
- le bouton ON/OFF est un disque MÉTAL MAT : dégradé radial à faible
  contraste (pas de brillance « bombée »), simple liseré de lumière sur
  l'arête supérieure, anneau fin ;
- le vert n'apparaît qu'en SOBRE accent d'état (point + liseré d'anneau +
  texte ACTIF), jamais en bloc massif — le disque reste gris métal dans
  les DEUX états ;
- header épuré : « M E T H » centré en lettres espacées, point de statut
  discret à gauche, × à droite ;
- lignes d'état façon Réglages Apple : label gris secondaire à gauche,
  valeur à droite, séparateurs fins ;
- un seul geste possible : le gros bouton. Fermer (×) cache vers le tray.

L'UI ne décide RIEN : elle appelle ``controller`` et affiche ``state``.
Le bouton est un Canvas (pas un tk.Button) pour le volume métal et le
halo. L'animation est TRÈS légère (pulse ``after``, stoppée si cachée).
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, List, Optional, Tuple

# --- Palette épurée Apple — gris / noir métal MAT (neutre, sans bleu) ------
BG_TOP = "#1a1a1c"          # haut du fond (gris anthracite doux)
BG_BOTTOM = "#0c0c0e"       # bas du fond (noir profond)
PANEL = "#1d1d1f"           # panneau (Apple dark gray)
CARD = "#262628"            # carte / corps sombres
BORDER = "#2c2c2e"          # séparateur Apple
TEXT = "#f5f5f7"            # texte principal
MUTED = "#8e8e93"           # secondaire Apple
FAINT = "#5a5a5e"           # tertiaire (footer, sous-textes)

# Métal mat du disque ON/OFF : dégradé à FAIBLE contraste (mat, jamais
# brillant). METAL_A = centre, METAL_B = bord, HILITE = arête supérieure.
METAL_A = "#48484d"
METAL_B = "#151517"
HILITE = "#5f5f66"
RING = "#34343a"            # anneau extérieur (métal usiné)

# Vert Apple system — usage MINIMAL (point + liseré d'état ON uniquement).
ACCENT = "#30d158"
ACCENT_DIM = "#2c9e4c"
WARN = "#e0a63c"
ERR = "#ff6961"
FONT = "Segoe UI"

BTN_SIZE = 132          # diamètre du disque ON/OFF
CANVAS_SIZE = 204       # canvas (halo + disque)

HEIGHT = 458


def _blend(c1: str, c2: str, t: float) -> str:
    """Mélange deux couleurs hex (#rrggbb) : t=0 → c1, t=1 → c2."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#%02x%02x%02x" % (
        int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t))


def _halo_stops(base: str, count: int) -> List[str]:
    """Palette de halo : du centre (base) vers le fond, en ``count`` pas."""
    return [_blend(base, BG_BOTTOM, i / max(count - 1, 1))
            for i in range(count)]


def apply_dark_title_bar(root: tk.Tk) -> None:
    """Barre de titre + caption en mode sombre (DWM) pour n'importe quelle
    fenêtre Tk (principale OU paramètres). Silencieux si indisponible."""
    try:
        import ctypes
        from ctypes import wintypes  # noqa: F401  (assure ctypes.windll.user32)
        hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        cap = ctypes.c_int(0x00161414)  # #141416 en BGR
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(cap), ctypes.sizeof(cap))
    except Exception:
        pass


class MainWindow:
    """Fenêtre principale Meth. ``controller`` reçoit les actions :
    - on_toggle() -> bool  : bascule ON/OFF (retourne l'état demandé)
    - on_close()           : fermeture (cacher vers tray)
    - on_settings()        : ouvrir les paramètres
    - on_quit()            : arrêter réellement Meth
    """

    def __init__(self, controller=None,
                 logger: Optional[Callable[[str, str], None]] = None) -> None:
        self._controller = controller or _NullController()
        self._logger = logger
        self._on = False
        self._pulse_step = 0.0
        self._pulse_dir = 1
        self._pulse_job: Optional[str] = None

        self.root = tk.Tk()
        self.root.title("Meth")
        self.root.configure(bg=BG_BOTTOM)
        self.root.resizable(False, False)
        self.root.geometry(f"320x{HEIGHT}")
        self.root.minsize(320, HEIGHT)
        self.root.maxsize(320, HEIGHT)
        self._set_icon()
        apply_dark_title_bar(self.root)
        self._build()

    def log(self, level: str, msg: str) -> None:
        if self._logger:
            try:
                self._logger(level, msg)
            except Exception:
                pass

    # -- construction ----------------------------------------------------------
    def _build(self) -> None:
        self._f_title = tkfont.Font(family=FONT, size=13, weight="bold")
        self._f_btn = tkfont.Font(family=FONT, size=26, weight="bold")
        self._f_btn_sub = tkfont.Font(family=FONT, size=7)
        self._f_etat = tkfont.Font(family=FONT, size=12, weight="bold")
        self._f_small = tkfont.Font(family=FONT, size=9)
        self._f_tiny = tkfont.Font(family=FONT, size=8)

        # Fond : dégradé vertical NEUTRE (anthracite → noir), dessiné une fois.
        self._bg = tk.Canvas(self.root, width=320, height=HEIGHT,
                             highlightthickness=0, bd=0)
        self._bg.pack(fill="both", expand=True)
        for y in range(HEIGHT):
            self._bg.create_line(0, y, 320, y,
                                 fill=_blend(BG_TOP, BG_BOTTOM, y / HEIGHT))

        # Header épuré : point de statut ● (gauche), « M E T H » centré
        # (lettres espacées à la Apple), × discret à droite.
        self._lbl_statut = tk.Label(self.root, text="○", bg=BG_TOP,
                                    fg=FAINT, font=self._f_small)
        self._lbl_statut.place(x=20, y=18)
        tk.Label(self.root, text="M E T H", bg=BG_TOP, fg=TEXT,
                 font=self._f_title).place(relx=0.5, y=16, anchor="n")
        tk.Button(self.root, text="×", command=self._on_close_request,
                  bg=BG_TOP, fg=FAINT, bd=0, font=self._f_small,
                  activebackground=BG_TOP, activeforeground=TEXT,
                  cursor="hand2", width=2).place(x=286, y=10)

        # Bouton ON/OFF : disque métal (Canvas), l'élément DOMINANT.
        self._canvas = tk.Canvas(self.root, width=CANVAS_SIZE,
                                 height=CANVAS_SIZE, bg=BG_TOP,
                                 highlightthickness=0)
        self._canvas.place(x=(320 - CANVAS_SIZE) // 2, y=60)
        self._canvas.bind("<Button-1>", lambda _e: self._on_toggle())

        self._lbl_etat = tk.Label(self.root, text="", bg=BG_TOP,
                                  font=self._f_etat)
        self._lbl_etat.place(x=0, y=60 + CANVAS_SIZE - 10, relwidth=1)

        self._lbl_desc = tk.Label(self.root, text="", bg=BG_TOP, fg=MUTED,
                                  font=self._f_small, justify="center",
                                  wraplength=270)
        self._lbl_desc.place(x=0, y=60 + CANVAS_SIZE + 16, relwidth=1)

        # Notice honnête (ex. refus ac_only) — masquée par défaut.
        self._lbl_notice = tk.Label(self.root, text="", bg=BG_TOP, fg=ERR,
                                    font=self._f_tiny, justify="center",
                                    wraplength=270)
        self._lbl_notice.place(x=0, y=60 + CANVAS_SIZE + 40, relwidth=1)

        # Séparateur fin (Apple).
        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.place(x=24, y=60 + CANVAS_SIZE + 62, relwidth=1, width=272)

        # Infos système (texte + pastille, jamais seulement la couleur).
        self._rows: dict = {}
        row_y = 60 + CANVAS_SIZE + 76
        for i, label in enumerate(("CAPOT", "PC", "ÉNERGIE")):
            row = tk.Frame(self.root, bg=BG_TOP)
            row.place(x=30, y=row_y, relwidth=1, width=260)
            tk.Label(row, text=label, bg=BG_TOP, fg=MUTED, width=9,
                     anchor="w", font=self._f_small).pack(side="left")
            dot = tk.Label(row, text="○", bg=BG_TOP, fg=FAINT,
                           font=self._f_small)
            dot.pack(side="right")
            val = tk.Label(row, text="—", bg=BG_TOP, fg=TEXT, anchor="e",
                           font=self._f_small)
            val.pack(side="right", padx=(0, 6))
            self._rows[label] = (dot, val)
            row_y += 28
            # Séparateur entre les lignes (sauf après la dernière).
            if i < 2:
                tk.Frame(self.root, bg=BORDER, height=1).place(
                    x=44, y=row_y - 14, width=232)

        # Pied épuré : version + ⚙ + Quitter (tout en gris tertiaire).
        foot = tk.Frame(self.root, bg=BG_TOP)
        foot.place(x=0, y=HEIGHT - 36, relwidth=1)
        try:
            from .. import __version__ as _meth_version
            _version_txt = f"Meth v{_meth_version}"
        except Exception:
            _version_txt = "Meth"
        tk.Label(foot, text=_version_txt, bg=BG_TOP, fg=FAINT,
                 font=self._f_tiny).pack(side="left", padx=18)
        tk.Button(foot, text="Quitter", command=self._on_quit, bg=BG_TOP,
                  fg=FAINT, bd=0, font=self._f_tiny, activebackground=BG_TOP,
                  activeforeground=ERR, cursor="hand2").pack(side="right",
                                                             padx=(8, 16))
        tk.Button(foot, text="⚙", command=self._on_settings, bg=BG_TOP,
                  fg=FAINT, bd=0, font=self._f_small, activebackground=BG_TOP,
                  activeforeground=TEXT, cursor="hand2").pack(side="right")

        # Fermeture de la fenêtre = cacher (pas quitter).
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)

        # Dark title bar appliqué à CHAQUE affichage réel : DWM l'ignore quand
        # la fenêtre est créée puis cachée avant le premier map.
        self.root.bind("<Map>", lambda _e: apply_dark_title_bar(self.root),
                       add="+")

        self._draw_button()

    # -- bouton Canvas : disque métal MAT --------------------------------------
    def _draw_button(self) -> None:
        """Dessine le disque métal mat ON/OFF : dégradé radial à faible
        contraste (jamais de brillance « bombée »), liseré de lumière sur
        l'arête supérieure, anneau fin. Le disque reste gris métal dans les
        DEUX états — le vert n'apparaît qu'en accent d'état (point + liseré)."""
        c = self._canvas
        c.delete("all")
        cx, cy = CANVAS_SIZE // 2, CANVAS_SIZE // 2
        r = BTN_SIZE // 2

        # Halo neutre très discret (respire à peine quand ON).
        if self._on:
            t = self._pulse_step  # 0..1
            stops = _halo_stops("#17171b", 4)
            for i, col in enumerate(stops):
                rr = r + 10 + i * 5 + int(2 * t)
                c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                              fill=col, outline="")

        # Corps : dégradé RADIAL MÉTAL MAT (centre légèrement clair → bord
        # foncé, faible contraste). Pas de reflet bombé — surface sobre.
        for i in range(r, 0, -1):
            col = _blend(METAL_A, METAL_B, (i / r) ** 0.8)
            c.create_oval(cx - i, cy - i, cx + i, cy + i, fill=col, outline="")

        # Anneau extérieur : fin, usiné. Vert sobre uniquement quand ON.
        ring_col = ACCENT_DIM if self._on else RING
        c.create_oval(cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5,
                      outline=ring_col, width=1)

        # Liseré de lumière sur l'arête supérieure (2 px) — le seul « éclat »,
        # façon métal brossé Apple. Discret, jamais un ovale brillant.
        c.create_arc(cx - r + 10, cy - r - 6, cx + r - 10, cy + r - 2,
                     start=18, extent=144, style="arc", outline=HILITE, width=2)

        # Point d'état (vert uniquement quand ON, minuscule, en haut du disque).
        if self._on:
            c.create_oval(cx - 4, cy - r + 14, cx + 4, cy - r + 22,
                          fill=ACCENT, outline="")

        # Texte d'état.
        if self._on:
            c.create_text(cx, cy - 4, text="ON", fill=TEXT, font=self._f_btn)
            c.create_text(cx, cy + 24, text="· ACTIF ·", fill=ACCENT_DIM,
                          font=self._f_btn_sub)
        else:
            c.create_text(cx, cy - 4, text="OFF", fill=MUTED, font=self._f_btn)
            c.create_text(cx, cy + 24, text="· NORMAL ·", fill=FAINT,
                          font=self._f_btn_sub)

    def _pulse(self) -> None:
        """Respiration TRÈS légère quand ON et fenêtre visible : le halo
        neutre respire, le liseré vert oscille à peine entre deux tons."""
        if not self._on or not self.root.winfo_viewable():
            self._pulse_job = None
            return
        self._pulse_step += 0.10 * self._pulse_dir
        if self._pulse_step >= 1.0:
            self._pulse_step = 1.0
            self._pulse_dir = -1
        elif self._pulse_step <= 0.0:
            self._pulse_step = 0.0
            self._pulse_dir = 1
        self._draw_button()
        try:
            self._pulse_job = self.root.after(130, self._pulse)
        except Exception:
            self._pulse_job = None

    # -- état --------------------------------------------------------------
    def render(self, state: dict) -> None:
        """Affiche l'état fourni par le contrôleur. ``state`` :
        {on, pc, lid, power, battery, notice}."""
        on = bool(state.get("on"))
        lid = state.get("lid") or "INCONNU"
        power = state.get("power") or "INCONNU"
        battery = state.get("battery")
        pc = state.get("pc") or ("ACTIF" if on else "NORMAL")
        notice = state.get("notice")

        self._on = on
        if on:
            self._lbl_etat.configure(text="ACTIVÉ", fg=ACCENT)
            self._lbl_desc.configure(
                text="Le PC peut rester actif capot fermé.", fg=MUTED)
        else:
            self._lbl_etat.configure(text="DÉSACTIVÉ", fg=MUTED)
            self._lbl_desc.configure(
                text="Windows utilise ses paramètres normaux.", fg=MUTED)
        self._lbl_statut.configure(text="●" if on else "○",
                                   fg=ACCENT if on else FAINT)

        # Notice : refus honnête (secteur uniquement, etc.).
        if notice:
            self._lbl_notice.configure(text=notice)
            self._lbl_notice.place(x=0, y=60 + CANVAS_SIZE + 40, relwidth=1)
        else:
            self._lbl_notice.configure(text="")

        self._set_row("CAPOT", lid,
                      ACCENT if lid == "OUVERT" else (WARN if lid == "FERMÉ" else MUTED))
        self._set_row("PC", pc,
                      ACCENT if pc == "ACTIF" else MUTED)
        self._set_row("ÉNERGIE",
                      power + (f" ({battery}%)" if battery is not None else ""),
                      ACCENT if power == "SECTEUR" else (WARN if power == "BATTERIE" else MUTED))

        self._draw_button()
        if on and self._pulse_job is None:
            self._pulse_step = 0.0
            self._pulse_dir = 1
            self._pulse()
        elif not on and self._pulse_job is not None:
            try:
                self.root.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None

    def _set_row(self, label: str, value: str, color: str) -> None:
        dot, val = self._rows.get(label, (None, None))
        if dot is not None:
            dot.configure(text="●" if color != MUTED else "○", fg=color)
        if val is not None:
            val.configure(text=value)

    # -- interactions ----------------------------------------------------------
    def _on_toggle(self) -> None:
        try:
            self._controller.on_toggle()
        except Exception:
            pass

    def _on_close_request(self) -> None:
        try:
            self._controller.on_close()
        except Exception:
            self.root.withdraw()

    def _on_settings(self) -> None:
        try:
            self._controller.on_settings()
        except Exception:
            pass

    def _on_quit(self) -> None:
        try:
            self._controller.on_quit()
        except Exception:
            pass

    # -- icône fenêtre ---------------------------------------------------------
    def _set_icon(self) -> None:
        """Icône de la fenêtre : assets/icon.ico si présent, sinon rien."""
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(sys._MEIPASS, "assets", "icon.ico"))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "..", "assets", "icon.ico"))
        for path in candidates:
            if os.path.isfile(path):
                try:
                    self.root.iconbitmap(path)
                except Exception:
                    pass
                return

    # -- cycle de vie ----------------------------------------------------------
    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self._on and self._pulse_job is None:
            self._pulse_step = 0.0
            self._pulse_dir = 1
            self._pulse()

    def hide(self) -> None:
        self.root.withdraw()
        if self._pulse_job is not None:
            try:
                self.root.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None

    def minimize(self) -> None:
        """Réduit dans la barre des tâches (quand le tray est désactivé)."""
        try:
            self.root.iconify()
        except Exception:
            self.root.withdraw()

    def destroy(self) -> None:
        if self._pulse_job is not None:
            try:
                self.root.after_cancel(self._pulse_job)
            except Exception:
                pass
            self._pulse_job = None
        try:
            self.root.destroy()
        except Exception:
            pass


class _NullController:
    def on_toggle(self) -> bool:
        return False
    def on_close(self) -> None:
        pass
    def on_settings(self) -> None:
        pass
    def on_quit(self) -> None:
        pass
