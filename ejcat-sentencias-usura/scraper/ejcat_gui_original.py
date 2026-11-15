# =============================================================================
# EJCAT AUTOMATITZACIÓ - Interfície Gràfica  (v12)
# =============================================================================
# ÚS:  py -3.13 ejcat_gui.py
#
# REQUISITS (una sola vegada en cmd):
#   pip install playwright
#   playwright install chrome
# =============================================================================

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# =============================================================================
# CONFIGURACIÓ
# =============================================================================

USUARIO     = "<REDACTADO — ver ejcat_scraper.py: ahora se lee de .env>"
CONTRASENYA = "<REDACTADO — ver ejcat_scraper.py: ahora se lee de .env>"
CARPETA     = r"<REDACTADO — ruta local con el usuario del sistema>"
URL_LOGIN   = "https://ejcat.justicia.intranet.gencat.cat/portal/AppJava/autentificacionGicar.do?reqCode=autentificar"

# Colors corporatius
COLOR_FONS       = "#1a2744"   # Blau fosc (fons principal)
COLOR_PANEL      = "#243158"   # Blau mitjà (panells)
COLOR_ACCENT     = "#c8a84b"   # Or (accents i botons)
COLOR_ACCENT2    = "#e8c96b"   # Or clar (hover)
COLOR_TEXT       = "#ffffff"   # Blanc
COLOR_TEXT_GRIS  = "#a0aec0"   # Gris clar
COLOR_OK         = "#48bb78"   # Verd
COLOR_ERROR      = "#fc8181"   # Vermell
COLOR_INFO       = "#63b3ed"   # Blau clar
COLOR_ENTRADA    = "#2d3f6b"   # Fons camps d'entrada

# =============================================================================
# LÒGICA D'AUTOMATITZACIÓ (sense UI)
# =============================================================================

def crear_carpeta(ruta):
    if not os.path.exists(ruta):
        os.makedirs(ruta)

def esperar(page, ms=1200):
    page.wait_for_timeout(ms)

def buscar_frame_con(page, selector):
    for frame in page.frames:
        try:
            if frame.locator(selector).count() > 0:
                return frame
        except:
            continue
    return None

def click_en_cualquier_frame(page, selector):
    try:
        el = page.locator(selector).first
        if el.is_visible(timeout=2000):
            el.click()
            return True
    except:
        pass
    for frame in page.frames:
        try:
            el = frame.locator(selector).first
            if el.is_visible(timeout=1000):
                el.click()
                return True
        except:
            continue
    return False

def hacer_login(page, log):
    log("🔐 Connectant a GICAR...", "info")
    page.goto(URL_LOGIN, wait_until="networkidle", timeout=30000)
    esperar(page, 2000)
    page.wait_for_selector("input[type='text'], input[name='username']", timeout=10000)
    page.locator("input[type='text']").first.fill(USUARIO)
    page.locator("input[type='password']").first.fill(CONTRASENYA)
    page.locator("input[type='submit'], button[type='submit']").first.click()
    page.wait_for_load_state("networkidle", timeout=20000)
    esperar(page, 2000)
    log("✓ Login correcte", "ok")

def seleccionar_plaza(page, num_plaza, log):
    log(f"🏛  Seleccionant plaça {num_plaza}...", "info")
    esperar(page, 2000)

    frame_plaza = None
    for frame in page.frames:
        try:
            if frame.locator("select").count() > 0:
                frame_plaza = frame
                break
        except:
            continue

    if frame_plaza is None:
        log("⚠ No s'ha trobat el desplegable de plaça", "error")
        return

    frame_plaza.locator("select").first.click()
    esperar(page, 2000)

    opcions = frame_plaza.evaluate("""
        () => {
            const sel = document.querySelector('select');
            if (!sel) return [];
            return Array.from(sel.options).map(o => ({
                value: o.value, text: o.text.trim(), index: o.index
            }));
        }
    """)

    opcio = None
    for o in opcions:
        if re.search(rf'n[úu]m\.?\s*{re.escape(num_plaza)}\b', o['text'], re.IGNORECASE):
            opcio = o
            break
    if not opcio:
        for o in opcions:
            if num_plaza in o['text'] and "Seleccioneu" not in o['text']:
                opcio = o
                break

    if opcio:
        frame_plaza.select_option("select", index=opcio['index'])
        esperar(page, 500)
        try:
            frame_plaza.locator("input[value='Seleccionar']").first.click()
        except:
            page.locator("input[value='Seleccionar'], button:has-text('Seleccionar')").first.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        esperar(page, 2000)
        log(f"✓ Plaça {num_plaza} seleccionada: {opcio['text']}", "ok")
    else:
        log(f"⚠ Plaça {num_plaza} no trobada automàticament", "error")

def navegar_a_busqueda(page, log):
    log("🧭 Navegant a Tramitació → Assumptes...", "info")
    esperar(page, 1500)
    click_en_cualquier_frame(page, "text=Oficina")
    esperar(page, 2000)
    click_en_cualquier_frame(page, "text=Tramitació")
    esperar(page, 2000)
    if not click_en_cualquier_frame(page, "text=Assumptes"):
        click_en_cualquier_frame(page, "text=Ejcat")
        esperar(page, 1000)
        click_en_cualquier_frame(page, "text=Assumptes")
    page.wait_for_load_state("networkidle")
    esperar(page, 2000)
    log("✓ Formulari de cerca obert", "ok")

def buscar_y_seleccionar(page, numero, anyo, log):
    log(f"🔍 Cercant procediment {numero}/{anyo}...", "info")
    esperar(page, 1500)

    frame = buscar_frame_con(page, "input[value='Cerca']") or \
            buscar_frame_con(page, "button:has-text('Cerca')") or page

    camps = frame.locator("input[type='text'], input[type='number'], input:not([type='hidden'])")
    camps.nth(0).click()
    camps.nth(0).fill(str(numero))
    esperar(page, 400)
    camps.nth(1).click()
    camps.nth(1).fill(str(anyo))
    esperar(page, 400)

    try:
        frame.locator("input[value='Cerca']").first.click()
    except:
        frame.locator("button:has-text('Cerca')").first.click()

    page.wait_for_load_state("networkidle")
    esperar(page, 1500)

    frame_res = page
    max_files = 0
    for f in page.frames:
        try:
            n = f.locator("table tr").count()
            if n > max_files:
                max_files = n
                frame_res = f
        except:
            continue

    filas = frame_res.locator("table tr")
    files_dades = []
    for i in range(1, filas.count()):
        try:
            text = filas.nth(i).inner_text().strip()
            if re.search(r'\d{5}\.\d+', text):
                files_dades.append(i)
        except:
            continue

    if len(files_dades) == 0:
        log(f"✗ Cap resultat per a {numero}/{anyo}", "error")
        return False
    elif len(files_dades) == 1:
        filas.nth(files_dades[0]).locator("a").last.click()
        log("✓ Procediment obert", "ok")
    else:
        # Si n'hi ha varios, agafar el primer (en mode llista no podem preguntar)
        log(f"⚠ {len(files_dades)} resultats, obrint el primer...", "info")
        filas.nth(files_dades[0]).locator("a").last.click()
        log("✓ Procediment obert", "ok")

    page.wait_for_load_state("networkidle")
    esperar(page, 1500)
    return True

def descarregar_vex(page, numero, anyo, num_plaza, carpeta_base, log):
    nom_carpeta = f"{numero}_{anyo}_Placa{num_plaza}"
    carpeta_proc = os.path.join(carpeta_base, nom_carpeta)
    crear_carpeta(carpeta_proc)

    log("📥 Buscant botó VEX exprés...", "info")

    frame_vex = None
    for frame in page.frames:
        try:
            if frame.locator("img[title='VEX exprés']").count() > 0:
                frame_vex = frame
                break
        except:
            continue

    if frame_vex is None:
        click_en_cualquier_frame(page, "text=Expedient")
        esperar(page, 2000)
        for frame in page.frames:
            try:
                if frame.locator("img[title='VEX exprés']").count() > 0:
                    frame_vex = frame
                    break
            except:
                continue

    if frame_vex is None:
        log("✗ No s'ha trobat el botó VEX exprés", "error")
        return None

    try:
        btn = frame_vex.locator("a:has(img[title='VEX exprés'])").first
        if btn.count() == 0:
            btn = frame_vex.locator("img[title='VEX exprés']").first

        log("⬇ Clicant VEX exprés...", "info")

        # El PDF s'obre en una nova pestanya
        with page.context.expect_page() as nova_pagina_info:
            btn.click()

        nova_pagina = nova_pagina_info.value
        nova_pagina.wait_for_load_state("networkidle", timeout=60000)
        esperar(nova_pagina, 2000)
        url_pdf = nova_pagina.url
        log(f"  URL del PDF: {url_pdf[:80]}...", "info")

        nom_fitxer = f"{numero}_{anyo}_Placa{num_plaza}.pdf"
        ruta = os.path.join(carpeta_proc, nom_fitxer)

        log("  Descarregant PDF...", "info")

        # Usar les cookies i sessió de Playwright per fer la petició
        # d'aquesta manera la sessió és vàlida garantidament
        resposta = nova_pagina.request.get(url_pdf)

        if resposta.ok:
            contingut = resposta.body()
            # DIAGNÒSTIC: mostrar els primers bytes per saber si és PDF o HTML
            primers_bytes = contingut[:200]
            log(f"  Primers bytes: {primers_bytes[:100]}", "info")

            with open(ruta, "wb") as f:
                f.write(contingut)
            nova_pagina.close()
            log(f"✓ Descarregat: {nom_fitxer} ({len(contingut)//1024} KB)", "ok")
            log(f"📁 Guardat a: {carpeta_proc}", "ok")
            return ruta
        else:
            log(f"⚠ Error HTTP {resposta.status} en descarregar. Intentant mètode alternatiu...", "info")

            # Mètode alternatiu: capturar la resposta de xarxa directament
            try:
                with nova_pagina.expect_download(timeout=30000) as dl_info:
                    nova_pagina.evaluate("window.location.href = window.location.href")
                dl = dl_info.value
                dl.save_as(ruta)
                nova_pagina.close()
                log(f"✓ Descarregat (mètode alternatiu): {nom_fitxer}", "ok")
                return ruta
            except:
                nova_pagina.close()
                log(f"✗ No s'ha pogut descarregar el PDF", "error")
                return None

    except Exception as e:
        log(f"✗ Error en la descàrrega: {e}", "error")
        return None

def navegar_a_cerca_nou(page, log):
    """Torna al formulari de cerca per processar el següent procediment."""
    log("↩ Tornant al formulari de cerca...", "info")
    click_en_cualquier_frame(page, "text=Assumptes")
    esperar(page, 2000)
    if not buscar_frame_con(page, "input[value='Cerca']"):
        click_en_cualquier_frame(page, "text=Tramitació")
        esperar(page, 1500)
        click_en_cualquier_frame(page, "text=Assumptes")
        esperar(page, 2000)

def processar_procediments(llista, num_plaza, carpeta_base, log, progress_cb):
    """Processa una llista de procediments [(numero, anyo), ...]"""
    total = len(llista)
    log(f"\n{'='*50}", "info")
    log(f"📋 Processant {total} procediment(s)...", "info")
    log(f"{'='*50}", "info")

    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(
                channel="chrome",
                headless=False,
                downloads_path=carpeta_base,
                slow_mo=400,
                args=["--disable-pdf-viewer", "--disable-plugins"]
            )
        except:
            try:
                nav = p.chromium.launch(
                    channel="msedge",
                    headless=False,
                    downloads_path=carpeta_base,
                    slow_mo=400,
                    args=["--disable-pdf-viewer", "--disable-plugins"]
                )
            except:
                nav = p.chromium.launch(
                    headless=False,
                    downloads_path=carpeta_base,
                    slow_mo=400,
                    args=["--disable-pdf-viewer", "--disable-plugins"]
                )

        ctx  = nav.new_context(
            accept_downloads=True,
            # Forçar descàrrega de PDFs en lloc d'obrir-los al navegador
            extra_http_headers={"Accept": "application/pdf"}
        )
        # Configurar preferències per descarregar PDFs automàticament
        ctx.grant_permissions([])
        page = ctx.new_page()

        try:
            # Login i selecció de plaça (una sola vegada)
            hacer_login(page, log)
            seleccionar_plaza(page, num_plaza, log)
            navegar_a_busqueda(page, log)

            completats = 0
            errors = 0

            for idx, (numero, anyo) in enumerate(llista):
                log(f"\n── Procediment {idx+1}/{total}: {numero}/{anyo} ──", "info")
                progress_cb(idx, total)

                try:
                    ok = buscar_y_seleccionar(page, numero, anyo, log)
                    if ok:
                        descarregar_vex(page, numero, anyo, num_plaza, carpeta_base, log)
                        completats += 1
                    else:
                        errors += 1

                    # Si no és l'últim, tornar a la cerca
                    if idx < total - 1:
                        navegar_a_cerca_nou(page, log)

                except Exception as e:
                    log(f"✗ Error en {numero}/{anyo}: {e}", "error")
                    errors += 1
                    # Intentar recuperar-se tornant a la cerca
                    try:
                        navegar_a_busqueda(page, log)
                    except:
                        pass

            progress_cb(total, total)
            log(f"\n{'='*50}", "ok")
            log(f"✅ Completat: {completats}/{total} correctes, {errors} errors", "ok")
            log(f"📁 Fitxers a: {carpeta_base}", "ok")
            log(f"{'='*50}", "ok")

        except Exception as e:
            log(f"\n✗ ERROR GENERAL: {e}", "error")
            import traceback
            log(traceback.format_exc(), "error")

        finally:
            page.wait_for_timeout(3000)
            ctx.close()
            nav.close()

# =============================================================================
# INTERFÍCIE GRÀFICA
# =============================================================================

class EjcatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EJCAT Automatització")
        self.root.geometry("780x680")
        self.root.configure(bg=COLOR_FONS)
        self.root.resizable(True, True)

        # Icona de la finestra (text)
        try:
            self.root.iconbitmap(default='')
        except:
            pass

        self._construir_ui()

    def _construir_ui(self):
        # ── Capçalera ──────────────────────────────────────────────
        cap = tk.Frame(self.root, bg=COLOR_ACCENT, height=70)
        cap.pack(fill="x")
        cap.pack_propagate(False)

        tk.Label(cap, text="⚖  EJCAT Automatització",
                 font=("Segoe UI", 18, "bold"),
                 bg=COLOR_ACCENT, fg=COLOR_FONS).pack(side="left", padx=20, pady=15)

        tk.Label(cap, text="justícia.cat · Generalitat de Catalunya",
                 font=("Segoe UI", 9),
                 bg=COLOR_ACCENT, fg=COLOR_FONS).pack(side="right", padx=20)

        # ── Cos principal ──────────────────────────────────────────
        cos = tk.Frame(self.root, bg=COLOR_FONS)
        cos.pack(fill="both", expand=True, padx=15, pady=10)

        # Columna esquerra: formulari
        esq = tk.Frame(cos, bg=COLOR_FONS)
        esq.pack(side="left", fill="y", padx=(0, 10))

        # ── Targeta: Dades del procediment ─────────────────────────
        self._targeta(esq, "📋  Dades del procediment", self._bloc_procediment)

        # ── Targeta: Llista de procediments ────────────────────────
        self._targeta(esq, "📑  Llista de procediments (opcional)", self._bloc_llista)

        # ── Targeta: Configuració ───────────────────────────────────
        self._targeta(esq, "⚙  Configuració", self._bloc_config)

        # Botó principal
        self.btn_executar = tk.Button(
            esq, text="▶  EXECUTAR",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_ACCENT, fg=COLOR_FONS,
            activebackground=COLOR_ACCENT2,
            relief="flat", cursor="hand2",
            padx=20, pady=10,
            command=self._executar
        )
        self.btn_executar.pack(fill="x", pady=(10, 0))

        # Columna dreta: log
        dre = tk.Frame(cos, bg=COLOR_FONS)
        dre.pack(side="right", fill="both", expand=True)

        tk.Label(dre, text="📟  Registre d'activitat",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLOR_FONS, fg=COLOR_TEXT_GRIS).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            dre,
            font=("Consolas", 9),
            bg="#0d1929", fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            relief="flat", wrap="word",
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

        # Tags de color pel log
        self.log_text.tag_config("ok",    foreground=COLOR_OK)
        self.log_text.tag_config("error", foreground=COLOR_ERROR)
        self.log_text.tag_config("info",  foreground=COLOR_INFO)
        self.log_text.tag_config("normal",foreground=COLOR_TEXT)

        # Barra de progrés
        prog_frame = tk.Frame(dre, bg=COLOR_FONS)
        prog_frame.pack(fill="x", pady=(5, 0))

        self.label_prog = tk.Label(prog_frame, text="",
                                   font=("Segoe UI", 8),
                                   bg=COLOR_FONS, fg=COLOR_TEXT_GRIS)
        self.label_prog.pack(anchor="w")

        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar",
                        troughcolor=COLOR_PANEL,
                        background=COLOR_ACCENT,
                        thickness=8)
        self.progress.pack(fill="x")

    def _targeta(self, pare, titol, func_contingut):
        """Crea una targeta amb títol i contingut."""
        card = tk.Frame(pare, bg=COLOR_PANEL, padx=12, pady=10)
        card.pack(fill="x", pady=5)

        tk.Label(card, text=titol,
                 font=("Segoe UI", 9, "bold"),
                 bg=COLOR_PANEL, fg=COLOR_ACCENT).pack(anchor="w", pady=(0, 6))

        func_contingut(card)

    def _camp(self, pare, etiqueta, valor_defecte="", amplada=12):
        """Crea una fila etiqueta + camp d'entrada."""
        fila = tk.Frame(pare, bg=COLOR_PANEL)
        fila.pack(fill="x", pady=2)

        tk.Label(fila, text=etiqueta, width=10, anchor="w",
                 font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(side="left")

        var = tk.StringVar(value=valor_defecte)
        entry = tk.Entry(fila, textvariable=var,
                         font=("Segoe UI", 10),
                         bg=COLOR_ENTRADA, fg=COLOR_TEXT,
                         insertbackground=COLOR_TEXT,
                         relief="flat", width=amplada)
        entry.pack(side="left", padx=5)
        return var

    def _bloc_procediment(self, pare):
        self.var_numero = self._camp(pare, "Número:", "100")
        self.var_anyo   = self._camp(pare, "Any:", "2026")
        self.var_plaza  = self._camp(pare, "Plaça:", "32")

    def _bloc_llista(self, pare):
        tk.Label(pare,
                 text="Pots processar varis procediments alhora.\nUn per línia, format: número/any  (ex: 100/2026)",
                 font=("Segoe UI", 8), justify="left",
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(anchor="w")

        self.txt_llista = tk.Text(pare, height=5,
                                  font=("Consolas", 9),
                                  bg=COLOR_ENTRADA, fg=COLOR_TEXT,
                                  insertbackground=COLOR_TEXT,
                                  relief="flat")
        self.txt_llista.pack(fill="x", pady=4)

        tk.Label(pare,
                 text="Si la llista està buida, s'usa el procediment de dalt.",
                 font=("Segoe UI", 8), justify="left",
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(anchor="w")

    def _bloc_config(self, pare):
        # Carpeta de descàrregues
        fila = tk.Frame(pare, bg=COLOR_PANEL)
        fila.pack(fill="x", pady=2)

        tk.Label(fila, text="Carpeta:", width=10, anchor="w",
                 font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_TEXT_GRIS).pack(side="left")

        self.var_carpeta = tk.StringVar(value=CARPETA)
        entry = tk.Entry(fila, textvariable=self.var_carpeta,
                         font=("Segoe UI", 9),
                         bg=COLOR_ENTRADA, fg=COLOR_TEXT,
                         insertbackground=COLOR_TEXT,
                         relief="flat", width=22)
        entry.pack(side="left", padx=5)

        tk.Button(fila, text="📂",
                  bg=COLOR_PANEL, fg=COLOR_ACCENT,
                  relief="flat", cursor="hand2",
                  command=self._triar_carpeta).pack(side="left")

    def _triar_carpeta(self):
        carpeta = filedialog.askdirectory(initialdir=self.var_carpeta.get())
        if carpeta:
            self.var_carpeta.set(carpeta)

    # ── LOG ────────────────────────────────────────────────────────

    def log(self, missatge, tipus="normal"):
        def _fer():
            self.log_text.configure(state="normal")
            hora = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{hora}] {missatge}\n", tipus)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _fer)

    def progress_cb(self, actual, total):
        def _fer():
            if total > 0:
                pct = int(actual / total * 100)
                self.progress["value"] = pct
                self.label_prog.config(
                    text=f"Progrés: {actual}/{total} procediments ({pct}%)"
                )
        self.root.after(0, _fer)

    # ── EXECUCIÓ ───────────────────────────────────────────────────

    def _executar(self):
        # Llegir llista de procediments
        text_llista = self.txt_llista.get("1.0", "end").strip()
        num_plaza   = self.var_plaza.get().strip()
        carpeta     = self.var_carpeta.get().strip()

        if text_llista:
            # Parsejar llista: accepta "100/2026", "100 2026", "100-2026"
            llista = []
            for linia in text_llista.splitlines():
                linia = linia.strip()
                if not linia:
                    continue
                parts = re.split(r'[/\s\-]', linia)
                if len(parts) >= 2:
                    llista.append((parts[0].strip(), parts[1].strip()))
                else:
                    self.log(f"⚠ Línia no reconeguda: '{linia}'", "error")

            if not llista:
                messagebox.showerror("Error", "La llista no conté procediments vàlids.\nFormat: 100/2026")
                return
        else:
            # Un sol procediment
            numero = self.var_numero.get().strip()
            anyo   = self.var_anyo.get().strip()
            if not numero or not anyo:
                messagebox.showerror("Error", "Introdueix el número i l'any del procediment.")
                return
            llista = [(numero, anyo)]

        if not num_plaza:
            messagebox.showerror("Error", "Introdueix el número de plaça.")
            return

        criar_carpeta_ok = True
        try:
            crear_carpeta(carpeta)
        except Exception as e:
            messagebox.showerror("Error", f"No es pot crear la carpeta:\n{e}")
            criar_carpeta_ok = False

        if not criar_carpeta_ok:
            return

        # Deshabilitar botó mentre s'executa
        self.btn_executar.config(state="disabled", text="⏳  Executant...")
        self.progress["value"] = 0

        self.log(f"\n{'='*50}", "info")
        self.log(f"▶ Iniciant sessió — Plaça {num_plaza}", "info")
        self.log(f"{'='*50}", "info")

        # Executar en un thread separat per no bloquejar la UI
        def _thread():
            try:
                processar_procediments(llista, num_plaza, carpeta,
                                       self.log, self.progress_cb)
            finally:
                self.root.after(0, self._acabat)

        threading.Thread(target=_thread, daemon=True).start()

    def _acabat(self):
        self.btn_executar.config(state="normal", text="▶  EXECUTAR")

# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()

    # Estil ttk global
    style = ttk.Style(root)
    style.theme_use("default")

    app = EjcatApp(root)
    root.mainloop()
