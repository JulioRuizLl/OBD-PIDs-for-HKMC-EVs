# =============================================================================
# Extracción de texto y datos de contrato desde los PDF descargados del EJCAT
# =============================================================================
# Requisitos de sistema (no son paquetes pip): el binario "tesseract-ocr"
# debe estar instalado para que funcione el fallback de OCR.
#
# USO:
#   python pdf_extract.py expediente.pdf
# =============================================================================

import io
import json
import re
import sys

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

MIN_CHARS_TEXTO_NATIVO = 20


def extraer_texto_pdf(ruta_pdf, dpi=200):
    """Devuelve el texto de cada página. Si una página no tiene texto nativo
    (o es ruido residual de un escaneado), aplica OCR sobre su imagen."""
    doc = fitz.open(ruta_pdf)
    paginas = []
    for i, page in enumerate(doc):
        texto = page.get_text("text").strip()
        origen = "nativo"
        if len(texto) < MIN_CHARS_TEXTO_NATIVO:
            zoom = dpi / 72
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            texto = pytesseract.image_to_string(img, lang="spa")
            origen = "ocr"
        paginas.append({"pagina": i + 1, "origen": origen, "texto": texto})
    doc.close()
    return paginas


def texto_completo(paginas):
    return "\n".join(p["texto"] for p in paginas)


# ---------------------------------------------------------------------------
# Extracción de campos del contrato de micropréstamo.
# Heurísticas sobre el texto ya extraído; revisar/ajustar con contratos reales.
# ---------------------------------------------------------------------------

RE_TAE = re.compile(r"TAE[^\d%]{0,20}(\d{1,4}(?:[.,]\d{1,2})?)\s*%", re.IGNORECASE)
RE_TIN = re.compile(r"T[.\s]?I[.\s]?N\.?[^\d%]{0,20}(\d{1,4}(?:[.,]\d{1,2})?)\s*%", re.IGNORECASE)
RE_CAPITAL = re.compile(
    r"(?:capital|importe|cantidad)\s+(?:prestad[oa]|dispuest[oa]|solicitad[oa])"
    r"[^\d]{0,15}(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|eur)?",
    re.IGNORECASE,
)
RE_PLAZO_DIAS = re.compile(r"plazo\s+de\s+(\d{1,4})\s+d[ií]as", re.IGNORECASE)
RE_FECHA = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
RE_ENTIDAD = re.compile(
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,&'-]{2,60}?\s+(?:S\.?A\.?U?\.?|S\.?L\.?U?\.?))",
)


def _num_es(s):
    """Convierte '1.234,56' o '1234.56' a float."""
    s = s.strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def extraer_datos_contrato(texto):
    datos = {
        "entidad": None,
        "tae": None,
        "tin": None,
        "capital": None,
        "plazo_dias": None,
        "fechas_detectadas": [],
    }

    m = RE_TAE.search(texto)
    if m:
        datos["tae"] = _num_es(m.group(1))

    m = RE_TIN.search(texto)
    if m:
        datos["tin"] = _num_es(m.group(1))

    m = RE_CAPITAL.search(texto)
    if m:
        datos["capital"] = _num_es(m.group(1))

    m = RE_PLAZO_DIAS.search(texto)
    if m:
        datos["plazo_dias"] = int(m.group(1))

    m = RE_ENTIDAD.search(texto)
    if m:
        datos["entidad"] = re.sub(r"\s+", " ", m.group(1)).strip()

    vistas = set()
    for d, mo, y in RE_FECHA.findall(texto):
        clave = (d, mo, y)
        if clave in vistas:
            continue
        vistas.add(clave)
        datos["fechas_detectadas"].append(f"{d}/{mo}/{y}")

    return datos


def procesar_pdf(ruta_pdf):
    paginas = extraer_texto_pdf(ruta_pdf)
    texto = texto_completo(paginas)
    datos = extraer_datos_contrato(texto)
    paginas_ocr = sum(1 for p in paginas if p["origen"] == "ocr")
    return {
        "archivo": ruta_pdf,
        "num_paginas": len(paginas),
        "paginas_con_ocr": paginas_ocr,
        "datos_contrato": datos,
        "texto": texto,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_extract.py <ruta_al_pdf>")
        sys.exit(1)

    resultado = procesar_pdf(sys.argv[1])
    resultado_sin_texto = {k: v for k, v in resultado.items() if k != "texto"}
    print(json.dumps(resultado_sin_texto, ensure_ascii=False, indent=2))
