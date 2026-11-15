# Pipeline de automatización: EJCAT → antecedentes de hecho → sentencia de usura

Proyecto local y aislado (no tiene relación con el resto de este repositorio).
Todo el procesamiento ocurre en el equipo del usuario: ningún dato del
expediente ni de las partes sale a internet salvo la conexión necesaria para
iniciar sesión en el EJCAT.

## Flujo completo

```
1. scraper/        → login en EJCAT, localiza el expediente, descarga:
                        - <num>_<anyo>_Placa<plaza>_tramitacion.txt  (tabla de asientos)
                        - <num>_<anyo>_Placa<plaza>.pdf              (VEX exprés)

2. extractor/       → procesa el PDF: texto nativo + OCR de respaldo si una
                       página es un escaneado. Extrae entidad, TAE, capital,
                       plazo y fechas del contrato.

3. webapp/antecedentes.html   → pega el .txt de tramitación y genera los
                                  antecedentes de hecho (SEGUNDO en adelante).

4. webapp/redactor_usura.html → con los datos del contrato (del extractor o
                                  pegados a mano) genera la sentencia completa.
```

Los pasos 3 y 4 son los dos artefactos HTML que ya usabas; se han copiado
tal cual a `webapp/`. Los pasos 1 y 2 son la parte nueva de automatización.

## Instalación

```bash
cd ejcat-sentencias-usura
cp .env.example .env        # y rellena tus credenciales reales del EJCAT
nano .env                   # (o el editor que prefieras)

cd scraper
pip install -r requirements.txt
playwright install chrome

cd ../extractor
pip install -r requirements.txt
# además necesitas el binario de Tesseract OCR instalado en el sistema:
#   Windows:  https://github.com/UB-Mannheim/tesseract/wiki
#   Linux:    sudo apt install tesseract-ocr tesseract-ocr-spa
```

**El archivo `.env` nunca se sube al repositorio** (está en `.gitignore`).
Tampoco se suben los PDF ni los datos descargados (carpeta `data/`), porque
contienen datos personales de las partes.

## Uso

### 1. Descargar un expediente

Interfaz gráfica (igual que tu `ejcat_gui.py` original, ahora sin credenciales
en el código):

```bash
cd scraper
python ejcat_gui.py
```

O en modo línea de comandos, para integrarlo en un script:

```bash
python ejcat_scraper.py 100 2026 32   # número, año, plaza
```

Esto crea `data/100_2026_Placa32/` con el `.txt` de tramitación y el PDF.

### 2. Extraer los datos del contrato

```bash
cd extractor
python pdf_extract.py ../scraper/data/100_2026_Placa32/100_2026_Placa32.pdf
```

Imprime un JSON con `entidad`, `tae`, `tin`, `capital`, `plazo_dias` y las
fechas detectadas. Son heurísticas sobre el texto del PDF: conviene revisarlas
contrato a contrato hasta afinar las expresiones regulares con casos reales.

### 3. Generar los antecedentes de hecho

Abre `webapp/antecedentes.html` en el navegador (sin conexión), pega el
contenido de `..._tramitacion.txt` en el paso 1 y pulsa **Analizar** y
**Generar**.

### 4. Generar la sentencia

Abre `webapp/redactor_usura.html`, introduce (o pega) los datos del contrato
—usando como referencia el JSON del paso 2— y pulsa **Generar sentencia**.

## Estado del proyecto / pendiente

- `webapp/redactor_usura.html` está en reconstrucción: el fichero original
  tiene 1822 líneas y solo se recuperaron completas las primeras 635 tras un
  reinicio del contenedor. Falta volver a pegar/adjuntar el archivo completo.
- La integración automática entre el JSON del extractor y los campos de
  `redactor_usura.html` (hoy pensados para pegar el texto del contrato a mano
  en su propio diálogo) está pendiente de diseñar, para no duplicar lógica de
  extracción entre Python y JavaScript.
- Los selectores de Playwright (`text=Oficina`, `img[title='VEX exprés']`,
  etc.) dependen de la interfaz real del EJCAT: si cambia el portal o la
  disposición de pestañas, habrá que revisarlos.
