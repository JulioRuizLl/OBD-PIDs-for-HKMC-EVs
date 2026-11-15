# =============================================================================
# EJCAT - descarga automatizada de expedientes  (refactor v13)
# =============================================================================
# USO:
#   pip install -r requirements.txt
#   playwright install chrome
#   cp ../.env.example ../.env   # y rellena tus credenciales reales
#   python ejcat_gui.py          # interfaz gráfica
#   python ejcat_scraper.py 100 2026 32   # modo CLI: numero anyo plaza
# =============================================================================

import os
import re
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

USUARIO = os.environ.get("EJCAT_USUARIO")
CONTRASENYA = os.environ.get("EJCAT_CONTRASENYA")
URL_LOGIN = os.environ.get(
    "EJCAT_URL_LOGIN",
    "https://ejcat.justicia.intranet.gencat.cat/portal/AppJava/autentificacionGicar.do?reqCode=autentificar",
)
CARPETA = os.environ.get("EJCAT_CARPETA_DESCARGAS", "./data")

RE_FECHA = re.compile(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b")


def _comprobar_credenciales():
    if not USUARIO or not CONTRASENYA:
        raise RuntimeError(
            "Faltan EJCAT_USUARIO / EJCAT_CONTRASENYA. "
            "Copia .env.example como .env (en la carpeta del proyecto) y rellena tus datos."
        )


def crear_carpeta(ruta):
    os.makedirs(ruta, exist_ok=True)


def esperar(page, ms=1200):
    page.wait_for_timeout(ms)


def buscar_frame_con(page, selector):
    for frame in page.frames:
        try:
            if frame.locator(selector).count() > 0:
                return frame
        except Exception:
            continue
    return None


def click_en_cualquier_frame(page, selector):
    try:
        el = page.locator(selector).first
        if el.is_visible(timeout=2000):
            el.click()
            return True
    except Exception:
        pass
    for frame in page.frames:
        try:
            el = frame.locator(selector).first
            if el.is_visible(timeout=1000):
                el.click()
                return True
        except Exception:
            continue
    return False


def hacer_login(page, log):
    log("Conectando a GICAR...", "info")
    page.goto(URL_LOGIN, wait_until="networkidle", timeout=30000)
    esperar(page, 2000)
    page.wait_for_selector("input[type='text'], input[name='username']", timeout=10000)
    page.locator("input[type='text']").first.fill(USUARIO)
    page.locator("input[type='password']").first.fill(CONTRASENYA)
    page.locator("input[type='submit'], button[type='submit']").first.click()
    page.wait_for_load_state("networkidle", timeout=20000)
    esperar(page, 2000)
    log("Login correcto", "ok")


def seleccionar_plaza(page, num_plaza, log):
    log(f"Seleccionando plaza {num_plaza}...", "info")
    esperar(page, 2000)

    frame_plaza = None
    for frame in page.frames:
        try:
            if frame.locator("select").count() > 0:
                frame_plaza = frame
                break
        except Exception:
            continue

    if frame_plaza is None:
        log("No se ha encontrado el desplegable de plaza", "error")
        return

    frame_plaza.locator("select").first.click()
    esperar(page, 2000)

    opcions = frame_plaza.evaluate(
        """
        () => {
            const sel = document.querySelector('select');
            if (!sel) return [];
            return Array.from(sel.options).map(o => ({
                value: o.value, text: o.text.trim(), index: o.index
            }));
        }
        """
    )

    opcio = None
    for o in opcions:
        if re.search(rf"n[úu]m\.?\s*{re.escape(num_plaza)}\b", o["text"], re.IGNORECASE):
            opcio = o
            break
    if not opcio:
        for o in opcions:
            if num_plaza in o["text"] and "Seleccioneu" not in o["text"]:
                opcio = o
                break

    if opcio:
        frame_plaza.select_option("select", index=opcio["index"])
        esperar(page, 500)
        try:
            frame_plaza.locator("input[value='Seleccionar']").first.click()
        except Exception:
            page.locator("input[value='Seleccionar'], button:has-text('Seleccionar')").first.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        esperar(page, 2000)
        log(f"Plaza {num_plaza} seleccionada: {opcio['text']}", "ok")
    else:
        log(f"Plaza {num_plaza} no encontrada automáticamente", "error")


def navegar_a_busqueda(page, log):
    log("Navegando a Tramitació -> Assumptes...", "info")
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
    log("Formulario de búsqueda abierto", "ok")


def buscar_y_seleccionar(page, numero, anyo, log):
    log(f"Buscando procedimiento {numero}/{anyo}...", "info")
    esperar(page, 1500)

    frame = (
        buscar_frame_con(page, "input[value='Cerca']")
        or buscar_frame_con(page, "button:has-text('Cerca')")
        or page
    )

    camps = frame.locator("input[type='text'], input[type='number'], input:not([type='hidden'])")
    camps.nth(0).click()
    camps.nth(0).fill(str(numero))
    esperar(page, 400)
    camps.nth(1).click()
    camps.nth(1).fill(str(anyo))
    esperar(page, 400)

    try:
        frame.locator("input[value='Cerca']").first.click()
    except Exception:
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
        except Exception:
            continue

    filas = frame_res.locator("table tr")
    files_dades = []
    for i in range(1, filas.count()):
        try:
            text = filas.nth(i).inner_text().strip()
            if re.search(r"\d{5}\.\d+", text):
                files_dades.append(i)
        except Exception:
            continue

    if len(files_dades) == 0:
        log(f"Sin resultados para {numero}/{anyo}", "error")
        return False
    if len(files_dades) > 1:
        log(f"{len(files_dades)} resultados, abriendo el primero...", "info")
    filas.nth(files_dades[0]).locator("a").last.click()
    log("Procedimiento abierto", "ok")

    page.wait_for_load_state("networkidle")
    esperar(page, 1500)
    return True


def extraer_tramitacion(page, numero, anyo, num_plaza, carpeta_proc, log):
    """Extrae la tabla de actuaciones/asientos visible en la página del expediente
    y la guarda como texto plano, en el formato que espera antecedentes.html
    (una línea por asiento: fecha + descripción)."""
    log("Buscando tabla de tramitación / actuaciones...", "info")

    click_en_cualquier_frame(page, "text=Actuacions")
    click_en_cualquier_frame(page, "text=Tramitació")
    esperar(page, 1500)

    mejor_frame = None
    mejor_lineas = []
    for f in [page] + list(page.frames):
        try:
            filas = f.locator("table tr")
            n = filas.count()
        except Exception:
            continue
        if n == 0:
            continue
        lineas = []
        for i in range(n):
            try:
                texto = filas.nth(i).inner_text().strip().replace("\n", " ")
            except Exception:
                continue
            if texto and RE_FECHA.search(texto):
                lineas.append(texto)
        if len(lineas) > len(mejor_lineas):
            mejor_lineas = lineas
            mejor_frame = f

    if not mejor_lineas:
        log("No se ha detectado una tabla de tramitación en esta página", "error")
        return None

    nom_fitxer = f"{numero}_{anyo}_Placa{num_plaza}_tramitacion.txt"
    ruta = os.path.join(carpeta_proc, nom_fitxer)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(mejor_lineas))

    log(f"Tramitación guardada: {nom_fitxer} ({len(mejor_lineas)} asientos)", "ok")
    return ruta


def descargar_vex(page, numero, anyo, num_plaza, carpeta_proc, log):
    log("Buscando botón VEX exprés...", "info")

    frame_vex = None
    for frame in page.frames:
        try:
            if frame.locator("img[title='VEX exprés']").count() > 0:
                frame_vex = frame
                break
        except Exception:
            continue

    if frame_vex is None:
        click_en_cualquier_frame(page, "text=Expedient")
        esperar(page, 2000)
        for frame in page.frames:
            try:
                if frame.locator("img[title='VEX exprés']").count() > 0:
                    frame_vex = frame
                    break
            except Exception:
                continue

    if frame_vex is None:
        log("No se ha encontrado el botón VEX exprés", "error")
        return None

    try:
        btn = frame_vex.locator("a:has(img[title='VEX exprés'])").first
        if btn.count() == 0:
            btn = frame_vex.locator("img[title='VEX exprés']").first

        log("Pulsando VEX exprés...", "info")

        with page.context.expect_page() as nova_pagina_info:
            btn.click()

        nova_pagina = nova_pagina_info.value
        nova_pagina.wait_for_load_state("networkidle", timeout=60000)
        esperar(nova_pagina, 2000)
        url_pdf = nova_pagina.url

        nom_fitxer = f"{numero}_{anyo}_Placa{num_plaza}.pdf"
        ruta = os.path.join(carpeta_proc, nom_fitxer)

        log("Descargando PDF...", "info")
        resposta = nova_pagina.request.get(url_pdf)

        if resposta.ok:
            contingut = resposta.body()
            with open(ruta, "wb") as f:
                f.write(contingut)
            nova_pagina.close()
            log(f"Descargado: {nom_fitxer} ({len(contingut)//1024} KB)", "ok")
            return ruta

        log(f"Error HTTP {resposta.status}, intentando método alternativo...", "info")
        try:
            with nova_pagina.expect_download(timeout=30000) as dl_info:
                nova_pagina.evaluate("window.location.href = window.location.href")
            dl = dl_info.value
            dl.save_as(ruta)
            nova_pagina.close()
            log(f"Descargado (método alternativo): {nom_fitxer}", "ok")
            return ruta
        except Exception:
            nova_pagina.close()
            log("No se ha podido descargar el PDF", "error")
            return None

    except Exception as e:
        log(f"Error en la descarga: {e}", "error")
        return None


def navegar_a_cerca_nou(page, log):
    log("Volviendo al formulario de búsqueda...", "info")
    click_en_cualquier_frame(page, "text=Assumptes")
    esperar(page, 2000)
    if not buscar_frame_con(page, "input[value='Cerca']"):
        click_en_cualquier_frame(page, "text=Tramitació")
        esperar(page, 1500)
        click_en_cualquier_frame(page, "text=Assumptes")
        esperar(page, 2000)


def procesar_expediente(page, numero, anyo, num_plaza, carpeta_base, log):
    nom_carpeta = f"{numero}_{anyo}_Placa{num_plaza}"
    carpeta_proc = os.path.join(carpeta_base, nom_carpeta)
    crear_carpeta(carpeta_proc)

    ok = buscar_y_seleccionar(page, numero, anyo, log)
    if not ok:
        return None

    tramitacion = extraer_tramitacion(page, numero, anyo, num_plaza, carpeta_proc, log)
    pdf = descargar_vex(page, numero, anyo, num_plaza, carpeta_proc, log)
    return {"carpeta": carpeta_proc, "tramitacion_txt": tramitacion, "pdf": pdf}


def procesar_expedientes(lista, num_plaza, carpeta_base, log, progress_cb=lambda a, t: None):
    _comprobar_credenciales()
    total = len(lista)
    log(f"Procesando {total} expediente(s)...", "info")

    with sync_playwright() as p:
        nav = None
        for intento in ("chrome", "msedge", None):
            try:
                kwargs = dict(headless=False, downloads_path=carpeta_base, slow_mo=400,
                              args=["--disable-pdf-viewer", "--disable-plugins"])
                if intento:
                    kwargs["channel"] = intento
                nav = p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if nav is None:
            raise RuntimeError("No se ha podido lanzar ningún navegador Chromium/Chrome/Edge")

        ctx = nav.new_context(accept_downloads=True, extra_http_headers={"Accept": "application/pdf"})
        page = ctx.new_page()
        resultados = []

        try:
            hacer_login(page, log)
            seleccionar_plaza(page, num_plaza, log)
            navegar_a_busqueda(page, log)

            for idx, (numero, anyo) in enumerate(lista):
                log(f"-- Expediente {idx+1}/{total}: {numero}/{anyo} --", "info")
                progress_cb(idx, total)
                try:
                    resultados.append(procesar_expediente(page, numero, anyo, num_plaza, carpeta_base, log))
                except Exception as e:
                    log(f"Error en {numero}/{anyo}: {e}", "error")
                    resultados.append(None)

                if idx < total - 1:
                    try:
                        navegar_a_cerca_nou(page, log)
                    except Exception:
                        navegar_a_busqueda(page, log)

            progress_cb(total, total)
            correctos = sum(1 for r in resultados if r)
            log(f"Completado: {correctos}/{total} correctos", "ok")

        finally:
            page.wait_for_timeout(2000)
            ctx.close()
            nav.close()

    return resultados


if __name__ == "__main__":
    def _log(msg, tipo="normal"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    if len(sys.argv) < 4:
        print("Uso: python ejcat_scraper.py <numero> <anyo> <plaza>")
        sys.exit(1)

    numero, anyo, plaza = sys.argv[1], sys.argv[2], sys.argv[3]
    crear_carpeta(CARPETA)
    procesar_expedientes([(numero, anyo)], plaza, CARPETA, _log)
