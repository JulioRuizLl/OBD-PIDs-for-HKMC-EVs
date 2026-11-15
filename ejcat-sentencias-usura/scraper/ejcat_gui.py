# =============================================================================
# EJCAT AUTOMATITZACIÓ - Interfície Gràfica  (v13, credencials via .env)
# =============================================================================
# ÚS:
#   pip install -r requirements.txt
#   playwright install chrome
#   cp ../.env.example ../.env   # i omple les teves credencials reals
#   python ejcat_gui.py
# =============================================================================

import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import re

import ejcat_scraper as scraper

COLOR_FONS = "#1a2744"
COLOR_PANEL = "#243158"
COLOR_ACCENT = "#c8a84b"
COLOR_ACCENT2 = "#e8c96b"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_GRIS = "#a0aec0"
COLOR_OK = "#48bb78"
COLOR_ERROR = "#fc8181"
COLOR_INFO = "#63b3ed"
COLOR_ENTRADA = "#2d3f6b"


class EjcatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EJCAT Automatització")
        self.root.geometry("780x680")
        self.root.configure(bg=COLOR_FONS)
        self.root.resizable(True, True)
        self._construir_ui()

    def _construir_ui(self):
        cap = tk.Frame(self.root, bg=COLOR_ACCENT, height=70)
        cap.pack(fill="x")
        cap.pack_propagate(False)
        tk.Label(cap, text="⚖  EJCAT Automatització", font=("Segoe UI", 18, "bold"),
                 bg=COLOR_ACCENT, fg=COLOR_FONS).pack(side="left", padx=20, pady=15)
        tk.Label(cap, text="justícia.cat · Generalitat de Catalunya", font=("Segoe UI", 9),
                 bg=COLOR_ACCENT, fg=COLOR_FONS).pack(side="right", padx=20)

        cos = tk.Frame(self.root, bg=COLOR_FONS)
        cos.pack(fill="both", expand=True, padx=15, pady=10)

        esq = tk.Frame(cos, bg=COLOR_FONS)
        esq.pack(side="left", fill="y", padx=(0, 10))

        self._targeta(esq, "📋  Dades del procediment", self._bloc_procediment)
        self._targeta(esq, "📑  Llista de procediments (opcional)", self._bloc_llista)
        self._targeta(esq, "⚙  Configuració", self._bloc_config)

        self.btn_executar = tk.Button(
            esq, text="▶  EXECUTAR", font=("Segoe UI", 13, "bold"),
            bg=COLOR_ACCENT, fg=COLOR_FONS, activebackground=COLOR_ACCENT2,
            relief="flat", cursor="hand2", padx=20, pady=10, command=self._executar,
        )
        self.btn_executar.pack(fill="x", pady=(10, 0))

        dre = tk.Frame(cos, bg=COLOR_FONS)
        dre.pack(side="right", fill="both", expand=True)
        tk.Label(dre, text="📟  Registre d'activitat", font=("Segoe UI", 10, "bold"),
                 bg=COLOR_FONS, fg=COLOR_TEXT_GRIS).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            dre, font=("Consolas", 9), bg="#0d1929", fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT, relief="flat", wrap="word", state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("ok", foreground=COLOR_OK)
        self.log_text.tag_config("error", foreground=COLOR_ERROR)
        self.log_text.tag_config("info", foreground=COLOR_INFO)
        self.log_text.tag_config("normal", foreground=COLOR_TEXT)

        prog_frame = tk.Frame(dre, bg=COLOR_FONS)
        prog_frame.pack(fill="x", pady=(5, 0))
        self.label_prog = tk.Label(prog_frame, text="", font=("Segoe UI", 8),
                                    bg=COLOR_FONS, fg=COLOR_TEXT_GRIS)
        self.label_prog.pack(anchor="w")

        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=COLOR_PANEL, background=COLOR_ACCENT, thickness=8)
        self.progress.pack(fill="x")

    def _targeta(self, pare, titol, func_contingut):
        card = tk.Frame(pare, bg=COLOR_PANEL, padx=12, pady=10)
        card.pack(fill="x", pady=5)
        tk.Label(card, text=titol, font=("Segoe UI", 9, "bold"),
                 bg=COLOR_PANEL, fg=COLOR_ACCENT).pack(anchor="w", pady=(0, 6))
        func_contingut(card)

    def _camp(self, pare, etiqueta, valor_defecte="", amplada=12):
        fila = tk.Frame(pare, bg=COLOR_PANEL)
        fila.pack(fill="x", pady=2)
        tk.Label(fila, text=etiqueta, width=10, anchor="w", font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(side="left")
        var = tk.StringVar(value=valor_defecte)
        entry = tk.Entry(fila, textvariable=var, font=("Segoe UI", 10), bg=COLOR_ENTRADA,
                          fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief="flat", width=amplada)
        entry.pack(side="left", padx=5)
        return var

    def _bloc_procediment(self, pare):
        self.var_numero = self._camp(pare, "Número:", "100")
        self.var_anyo = self._camp(pare, "Any:", "2026")
        self.var_plaza = self._camp(pare, "Plaça:", "32")

    def _bloc_llista(self, pare):
        tk.Label(pare, text="Pots processar varis procediments alhora.\nUn per línia: número/any  (ex: 100/2026)",
                 font=("Segoe UI", 8), justify="left", bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(anchor="w")
        self.txt_llista = tk.Text(pare, height=5, font=("Consolas", 9), bg=COLOR_ENTRADA,
                                   fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief="flat")
        self.txt_llista.pack(fill="x", pady=4)
        tk.Label(pare, text="Si la llista està buida, s'usa el procediment de dalt.",
                 font=("Segoe UI", 8), justify="left", bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(anchor="w")

    def _bloc_config(self, pare):
        fila = tk.Frame(pare, bg=COLOR_PANEL)
        fila.pack(fill="x", pady=2)
        tk.Label(fila, text="Carpeta:", width=10, anchor="w", font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(side="left")
        self.var_carpeta = tk.StringVar(value=scraper.CARPETA)
        entry = tk.Entry(fila, textvariable=self.var_carpeta, font=("Segoe UI", 9), bg=COLOR_ENTRADA,
                          fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief="flat", width=22)
        entry.pack(side="left", padx=5)
        tk.Button(fila, text="📂", bg=COLOR_PANEL, fg=COLOR_ACCENT, relief="flat",
                  cursor="hand2", command=self._triar_carpeta).pack(side="left")

    def _triar_carpeta(self):
        carpeta = filedialog.askdirectory(initialdir=self.var_carpeta.get())
        if carpeta:
            self.var_carpeta.set(carpeta)

    def log(self, missatge, tipus="normal"):
        def _fer():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{missatge}\n", tipus)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _fer)

    def progress_cb(self, actual, total):
        def _fer():
            if total > 0:
                pct = int(actual / total * 100)
                self.progress["value"] = pct
                self.label_prog.config(text=f"Progrés: {actual}/{total} procediments ({pct}%)")
        self.root.after(0, _fer)

    def _executar(self):
        text_llista = self.txt_llista.get("1.0", "end").strip()
        num_plaza = self.var_plaza.get().strip()
        carpeta = self.var_carpeta.get().strip()

        if text_llista:
            llista = []
            for linia in text_llista.splitlines():
                linia = linia.strip()
                if not linia:
                    continue
                parts = re.split(r"[/\s\-]", linia)
                if len(parts) >= 2:
                    llista.append((parts[0].strip(), parts[1].strip()))
                else:
                    self.log(f"⚠ Línia no reconeguda: '{linia}'", "error")
            if not llista:
                messagebox.showerror("Error", "La llista no conté procediments vàlids.\nFormat: 100/2026")
                return
        else:
            numero = self.var_numero.get().strip()
            anyo = self.var_anyo.get().strip()
            if not numero or not anyo:
                messagebox.showerror("Error", "Introdueix el número i l'any del procediment.")
                return
            llista = [(numero, anyo)]

        if not num_plaza:
            messagebox.showerror("Error", "Introdueix el número de plaça.")
            return

        try:
            scraper.crear_carpeta(carpeta)
        except Exception as e:
            messagebox.showerror("Error", f"No es pot crear la carpeta:\n{e}")
            return

        try:
            scraper._comprobar_credenciales()
        except Exception as e:
            messagebox.showerror("Falten credencials", str(e))
            return

        self.btn_executar.config(state="disabled", text="⏳  Executant...")
        self.progress["value"] = 0

        def _thread():
            try:
                scraper.procesar_expedientes(llista, num_plaza, carpeta, self.log, self.progress_cb)
            except Exception as e:
                self.log(f"✗ ERROR GENERAL: {e}", "error")
            finally:
                self.root.after(0, self._acabat)

        threading.Thread(target=_thread, daemon=True).start()

    def _acabat(self):
        self.btn_executar.config(state="normal", text="▶  EXECUTAR")


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("default")
    EjcatApp(root)
    root.mainloop()
