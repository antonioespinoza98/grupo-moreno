# Documentación Completa — Pipeline NER Grupo Moreno

> Pipeline de procesamiento de documentos PDF para extracción de información de productos cosméticos mediante OCR y modelos de Reconocimiento de Entidades Nombradas (NER).

---

## Tabla de Contenidos

1. [Visión General del Proyecto](#1-visión-general-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Instalación de Ubuntu en Windows (WSL2)](#3-instalación-de-ubuntu-en-windows-wsl2)
4. [Configuración del Ambiente Python](#4-configuración-del-ambiente-python)
5. [Instalación de Dependencias del Sistema](#5-instalación-de-dependencias-del-sistema)
6. [Instalación de Dependencias Python](#6-instalación-de-dependencias-python)
7. [Configuración de Variables de Entorno](#7-configuración-de-variables-de-entorno)
8. [Ejecución del Pipeline](#8-ejecución-del-pipeline)
9. [Documentación del Código](#9-documentación-del-código)
10. [Label Studio: Instalación y Acceso Remoto](#10-label-studio-instalación-y-acceso-remoto)
11. [Estructura de Datos y Formatos](#11-estructura-de-datos-y-formatos)
12. [Hoja de Ruta del Proyecto](#12-hoja-de-ruta-del-proyecto)
13. [Solución de Problemas](#13-solución-de-problemas)

---

## 1. Visión General del Proyecto

Este proyecto implementa un pipeline de procesamiento de documentos para **Grupo Moreno**, una empresa de productos cosméticos. El objetivo es extraer información estructurada de 122 documentos PDF en tres categorías:

| Categoría        | Descripción                          | Cantidad |
|------------------|--------------------------------------|----------|
| Artes            | Etiquetas y artes gráficas           | 47       |
| Especificaciones | Fichas técnicas de productos         | 37       |
| Fórmulas         | Formulaciones y composiciones        | 38       |
| **Total**        |                                      | **122**  |

### Objetivo Final

Entrenar un modelo NER (Named Entity Recognition) con spaCy capaz de identificar automáticamente entidades como ingredientes, advertencias, modos de uso, fabricantes, países de origen y fechas de vencimiento en documentos de productos cosméticos.

### Pipeline de 6 Scripts

```
Script 01 → Script 02 → [Revisión Manual] → Script 03 → Script 04 → Script 05 → Script 06
   OCR       Anotaciones   Label Studio       Entrenamiento  Predicciones  Validación  Dashboard
```

### Estado Actual

| Script | Descripción                        | Estado      |
|--------|------------------------------------|-------------|
| 01     | Descarga y extracción OCR          | ✅ Completo  |
| 02     | Generación de anotaciones regex    | ✅ Completo  |
| —      | Revisión manual en Label Studio    | 🔄 En curso  |
| 03     | Entrenamiento del modelo NER       | ⏳ Pendiente |
| 04     | Predicciones en corpus completo    | ⏳ Pendiente |
| 05     | Validación automática              | ⏳ Pendiente |
| 06     | Dashboard Streamlit                | ⏳ Pendiente |

---

## 2. Arquitectura del Sistema

### Flujo de Datos

```
MinIO (localhost:9000)
  └── bucket: grupo-moreno
        ├── data/Artes/         (47 PDFs)
        ├── data/Especificaciones/ (37 PDFs)
        └── data/formulas/      (38 PDFs)
              │
              ▼ Script 01 (core/OCR.py)
        data/temp_pdfs/         (PDFs temporales)
              │
              ▼ OCRProcessor
        data/extracted/
        ├── Artes/
        │   ├── {nombre}.txt    (texto extraído)
        │   └── {nombre}.json   (metadatos)
        ├── especificaciones/
        ├── formulas/
        └── RESUMEN_GLOBAL.json
              │
              ▼ Script 02 (core/anotaciones.py)
        data/anotaciones/
        ├── Artes/
        │   └── {nombre}_anno.json   (anotaciones spaCy)
        ├── especificaciones/
        └── formulas/
              │
              ▼ Label Studio (revisión manual)
              │
              ▼ Script 03 (entrenamiento spaCy NER)
        modelos/
        └── ner_cosmeticos/     (modelo entrenado)
              │
              ▼ Script 04 (predicciones)
        data/predicciones/      (122 PDFs anotados)
              │
              ▼ Script 05 (validación)
        data/validacion/        (métricas F1, precisión, recall)
              │
              ▼ Script 06 (Streamlit Dashboard)
```

### Estructura de Directorios

```
grupo-moreno/
├── core/
│   ├── OCR.py              # Script 01: descarga y extracción de texto
│   ├── anotaciones.py      # Script 02: generación automática de anotaciones
│   └── upload_s3.py        # Utilidad: subida de JSONs a AWS S3
├── data/
│   ├── extracted/          # Salida del Script 01
│   │   ├── Artes/
│   │   ├── especificaciones/
│   │   ├── formulas/
│   │   └── RESUMEN_GLOBAL.json
│   ├── anotaciones/        # Salida del Script 02
│   │   ├── Artes/
│   │   ├── especificaciones/
│   │   └── formulas/
│   └── temp_pdfs/          # PDFs descargados temporalmente
├── docs/
│   ├── Fase1.md            # Instrucciones de ejecución Fase 1
│   └── DOCUMENTACION.md    # Este archivo
├── logs/
│   ├── ocr.log             # Logs del Script 01
│   └── anotaciones.log     # Logs del Script 02
├── .env                    # Credenciales MinIO (no subir a git)
├── .aws/                   # Credenciales AWS (no subir a git)
├── requirements.txt        # Dependencias Python
├── CLAUDE.md               # Instrucciones para Claude Code
└── LICENSE                 # Licencia MIT
```

---

## 3. Instalación de Ubuntu en Windows (WSL2)

WSL2 (Windows Subsystem for Linux 2) permite ejecutar un entorno Linux nativo dentro de Windows. Es el ambiente recomendado para este proyecto.

### 3.1 Requisitos Previos

- Windows 10 versión 2004 o superior (Build 19041+), o Windows 11
- Virtualización habilitada en BIOS/UEFI (Intel VT-x o AMD-V)

Para verificar la versión de Windows:
```
Inicio → Configuración → Sistema → Acerca de → Especificaciones de Windows
```

### 3.2 Habilitar WSL2

Abrir **PowerShell como Administrador** y ejecutar:

```powershell
# Habilitar WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Habilitar Plataforma de Máquina Virtual
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

Reiniciar el equipo.

### 3.3 Instalar el Kernel de Linux para WSL2

Descargar e instalar el paquete de actualización del kernel:
```
https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
```

Ejecutar el instalador descargado.

### 3.4 Establecer WSL2 como Versión Predeterminada

```powershell
wsl --set-default-version 2
```

### 3.5 Instalar Ubuntu desde Microsoft Store

**Opción A — Microsoft Store:**
1. Abrir Microsoft Store
2. Buscar "Ubuntu"
3. Instalar **Ubuntu 22.04.x LTS** (versión Long Term Support recomendada)
4. Hacer clic en "Obtener" y luego "Instalar"

**Opción B — PowerShell (línea de comandos):**
```powershell
wsl --install -d Ubuntu-22.04
```

### 3.6 Configurar Ubuntu por Primera Vez

Al abrir Ubuntu por primera vez, se pedirá crear un usuario:

```
Enter new UNIX username: tu_nombre_usuario
New password: ************
Retype new password: ************
```

> Anotar estas credenciales. Se usarán con `sudo`.

### 3.7 Actualizar el Sistema Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.8 Verificar la Instalación

```powershell
# En PowerShell
wsl --list --verbose
```

Debe mostrar:
```
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

### 3.9 Acceder a Archivos entre Windows y Ubuntu

| Desde | Hacia | Ruta |
|-------|-------|------|
| Windows | Archivos Ubuntu | `\\wsl$\Ubuntu-22.04\home\usuario\` |
| Ubuntu | Archivos Windows | `/mnt/c/Users/TuUsuario/` |

### 3.10 Instalar Windows Terminal (Recomendado)

Windows Terminal ofrece mejor experiencia con múltiples pestañas y perfiles. Instalar desde Microsoft Store buscando "Windows Terminal".

### 3.11 Configuración Recomendada de WSL2

Crear el archivo `%USERPROFILE%\.wslconfig` en Windows para limitar el uso de recursos:

```ini
[wsl2]
memory=8GB          # Máximo RAM asignada a WSL2
processors=4        # Número de procesadores virtuales
swap=2GB            # Memoria swap
```

---

## 4. Configuración del Ambiente Python

### 4.1 Instalar Python 3.10+

En Ubuntu:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev
```

Verificar la instalación:
```bash
python3 --version    # Python 3.10.x o superior
pip3 --version
```

### 4.2 Clonar el Repositorio

```bash
# Instalar git si no está disponible
sudo apt install -y git

# Clonar el proyecto
git clone <url-del-repositorio> 
cd grupo-moreno
```

### 4.3 Crear el Ambiente Virtual

Se recomienda crear **dos ambientes virtuales** separados: uno para el pipeline principal y otro exclusivo para Label Studio (para evitar conflictos de dependencias).

#### Ambiente Principal (pipeline OCR + NER)

```bash
# Dentro del directorio del proyecto
cd ~/projects/active/grupo-moreno

# Crear ambiente virtual
python3 -m venv venv

# Activar el ambiente
source venv/bin/activate

# Verificar activación (debe mostrar "(venv)" en el prompt)
which python   # Debe apuntar a .../venv/bin/python
```

#### Ambiente para Label Studio

```bash
# Crear en directorio de ambientes del usuario
python3 -m venv ~/venvs/label-studio

# Activar
source ~/venvs/label-studio/bin/activate
```

### 4.4 Comandos Útiles para Ambientes Virtuales

```bash
# Activar ambiente principal
source ~/projects/active/grupo-moreno/venv/bin/activate

# Desactivar cualquier ambiente activo
deactivate

# Ver paquetes instalados
pip list

# Ver ambiente activo
echo $VIRTUAL_ENV

# Eliminar un ambiente (si se necesita recrear)
rm -rf venv
```

---

## 5. Instalación de Dependencias del Sistema

Estas dependencias deben instalarse a nivel del sistema operativo Ubuntu, **antes** de instalar los paquetes Python.

### 5.1 Herramientas de Compilación Base

```bash
sudo apt install -y \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    git \
    curl \
    wget \
    unzip
```

### 5.2 Tesseract OCR

Tesseract es el motor OCR que extrae texto de imágenes de PDF cuando la extracción digital falla.

```bash
# Instalar Tesseract y el paquete de idioma español
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng

# Verificar la instalación
tesseract --version
# Debe mostrar: tesseract 4.1.x o 5.x.x

# Verificar idioma español disponible
tesseract --list-langs
# Debe incluir: spa
```

### 5.3 Poppler (conversión PDF a imágenes)

Requerido por `pdf2image` para convertir páginas PDF en imágenes para OCR.

```bash
sudo apt install -y poppler-utils

# Verificar
pdftoppm -v
```

### 5.4 OpenCV y Librerías de Imagen

```bash
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1-mesa-glx \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev
```

### 5.5 Librerías para psycopg2 (PostgreSQL)

```bash
sudo apt install -y \
    libpq-dev \
    postgresql-client
```

### 5.6 Modelo de Lenguaje spaCy en Español

Después de instalar las dependencias Python (ver sección 6), descargar el modelo español:

```bash
# Con el ambiente virtual activo
python -m spacy download es_core_news_sm

# Verificar
python -c "import spacy; nlp = spacy.load('es_core_news_sm'); print('Modelo cargado correctamente')"
```

### 5.7 Verificación de Todo el Sistema

```bash
# Verificar Tesseract con español
echo "Prueba OCR" | tesseract stdin stdout -l spa

# Verificar Poppler
pdftoppm --help 2>&1 | head -3

# Verificar OpenCV
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"

# Verificar Tesseract desde Python
python3 -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

---

## 6. Instalación de Dependencias Python

### 6.1 Actualizar pip

```bash
# Con el ambiente virtual activo
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 6.2 Instalar Todas las Dependencias

```bash
pip install -r requirements.txt
```

### 6.3 Descripción de Cada Dependencia

| Paquete | Versión | Uso en el Proyecto |
|---------|---------|-------------------|
| `spacy` | ≥3.0 | Framework NLP para entrenamiento y predicción del modelo NER |
| `pytesseract` | ≥0.3 | Wrapper Python para Tesseract OCR; extrae texto de imágenes |
| `PyPDF2` | ≥3.0 | Extracción de texto digital de PDFs nativos (más rápido que OCR) |
| `pdf2image` | ≥1.16 | Convierte páginas PDF a imágenes PIL para procesamiento con Tesseract |
| `Pillow` | ≥9.0 | Manipulación de imágenes; requerido por pdf2image |
| `opencv-python` | ≥4.5 | Preprocesamiento de imágenes (escala de grises, threshold, upscale) |
| `numpy` | ≥1.21 | Operaciones numéricas de arrays; base de opencv y procesamiento de imágenes |
| `python-dotenv` | ≥0.19 | Carga variables de entorno desde archivo `.env` |
| `minio` | ≥7.0 | Cliente Python para MinIO S3; descarga PDFs del bucket |
| `boto3` | ≥1.20 | Cliente AWS SDK para Python; subida de archivos a S3 |
| `pandas` | ≥1.4 | Análisis y manipulación de datos tabulares |
| `polars` | ≥0.15 | DataFrame de alto rendimiento; alternativa rápida a pandas |
| `sqlalchemy` | ≥1.4 | ORM para base de datos; preparado para integración futura con PostgreSQL |
| `psycopg2` | ≥2.9 | Driver PostgreSQL para Python; requerido por SQLAlchemy |
| `streamlit` | ≥1.10 | Framework para el Dashboard (Script 06) |
| `plotly` | ≥5.0 | Visualizaciones interactivas para el Dashboard |
| `scikit-learn` | ≥1.0 | Métricas de evaluación del modelo NER (F1, precisión, recall) |
| `dateparser` | ≥1.1 | Parseo de fechas en español e inglés para detección de fechas de vencimiento |

### 6.4 Instalación Individual (si falla algún paquete)

Si `pip install -r requirements.txt` falla para algún paquete específico:

```bash
# Instalar paquete por paquete para identificar el problema
pip install spacy
pip install pytesseract
pip install PyPDF2
pip install pdf2image
pip install pandas
pip install sqlalchemy
pip install psycopg2-binary   # Usar psycopg2-binary en lugar de psycopg2 si falla
pip install streamlit
pip install plotly
pip install python-dotenv
pip install polars
pip install minio
pip install boto3
pip install Pillow
pip install opencv-python
pip install numpy
pip install scikit-learn
pip install dateparser
```

> **Nota:** Si `psycopg2` falla con errores de compilación, usar `psycopg2-binary` que incluye las bibliotecas precompiladas.

### 6.5 Verificar Instalación Completa

```bash
python -c "
import spacy, pytesseract, PyPDF2, pdf2image
import pandas, sqlalchemy, streamlit, plotly
import python_dotenv, minio, boto3
import PIL, cv2, numpy, sklearn, dateparser
print('Todas las dependencias instaladas correctamente')
"
```

---

## 7. Configuración de Variables de Entorno

### 7.1 Crear el Archivo .env

El proyecto requiere credenciales de MinIO para descargar los PDFs. Crear el archivo `core/.env`:

```bash
# Crear el archivo
nano core/.env
```

Contenido del archivo:
```dotenv
# Configuración MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=tu_access_key_aqui
MINIO_SECRET_KEY=tu_secret_key_aqui
MINIO_BUCKET=grupo-moreno
MINIO_SECURE=False
```

> **Importante:** Este archivo contiene credenciales sensibles. Está incluido en `.gitignore` y nunca debe subirse al repositorio.

### 7.2 Configurar AWS (para upload_s3.py)

Si se usará la subida a AWS S3, crear el archivo `.aws/credentials.ini`:

```bash
mkdir -p .aws
nano .aws/credentials.ini
```

Contenido:
```ini
[default]
aws_access_key_id = TU_ACCESS_KEY_ID
aws_secret_access_key = TU_SECRET_ACCESS_KEY
region = us-east-1
```

---

## 8. Ejecución del Pipeline

### 8.1 Script 01: Extracción OCR (core/OCR.py)

Descarga los 122 PDFs de MinIO y extrae el texto.

```bash
# Activar ambiente
source venv/bin/activate

# Ejecutar
python core/OCR.py
```

**Salida esperada:**
```
=== PROCESADOR PRINCIPAL DE PDFs ===
Iniciando procesamiento de carpeta: Artes
Procesando: ACRYLIC_GEL_CLEAR.pdf [digital] ✓
Procesando: ALOE_VERA_GEL.pdf [ocr] ✓
...
Carpeta Artes: 43/43 exitosos, 0 errores

Iniciando procesamiento de carpeta: especificaciones
...

=== RESUMEN GLOBAL ===
Total procesados: 118
Exitosos: 118 (100%)
Errores: 0
Tiempo total: ~28 minutos
```

**Tiempo estimado:** 25-35 minutos para 122 PDFs.

**Monitorear en tiempo real:**
```bash
tail -f logs/ocr.log
```

### 8.2 Script 02: Generación de Anotaciones (core/anotaciones.py)

Genera anotaciones automáticas con regex para los primeros 70 documentos.

```bash
python core/anotaciones.py
```

**Salida esperada:**
```
=== GENERADOR DE ANOTACIONES ===
Procesando tipo: Artes (23 documentos)
  ACRYLIC_GEL_CLEAR_anno.json — 5 entidades detectadas
  ...
Procesando tipo: especificaciones (23 documentos)
Procesando tipo: formulas (24 documentos)

Total anotaciones generadas: 70
Estado: requiere_revision_manual
```

**Tiempo estimado:** 2-5 minutos.

### 8.3 Utilidad: Subida a S3 (core/upload_s3.py)

Sube todos los archivos JSON extraídos a un bucket de AWS S3.

```bash
# Reemplazar 'nombre-del-bucket' con el nombre real
python core/upload_s3.py nombre-del-bucket
```

---

## 9. Documentación del Código

### 9.1 core/OCR.py

Implementa el pipeline completo de descarga y extracción de texto de PDFs.

---

#### Clase `ConfigMinIO`

Contiene la configuración para conectarse al servidor MinIO.

```python
class ConfigMinIO:
    ENDPOINT = "localhost:9000"
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
    BUCKET = "grupo-moreno"
    SECURE = False
    CARPETAS = ["data/Artes", "data/Especificaciones", "data/formulas"]
```

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `ENDPOINT` | `str` | URL del servidor MinIO (host:puerto) |
| `ACCESS_KEY` | `str` | Clave de acceso leída desde `.env` |
| `SECRET_KEY` | `str` | Clave secreta leída desde `.env` |
| `BUCKET` | `str` | Nombre del bucket que contiene los PDFs |
| `SECURE` | `bool` | `False` para HTTP local, `True` para HTTPS |
| `CARPETAS` | `list[str]` | Rutas dentro del bucket con PDFs |

---

#### Clase `ConfigPaths`

Define las rutas del sistema de archivos local y crea los directorios necesarios.

```python
class ConfigPaths:
    BASE_DIR = Path(__file__).parent.parent
    BASE_EXTRACTED = BASE_DIR / "data" / "extracted"
    TEMP_DIR = BASE_DIR / "data" / "temp_pdfs"
    LOGS_DIR = BASE_DIR / "logs"
```

| Atributo | Descripción |
|----------|-------------|
| `BASE_DIR` | Raíz del proyecto |
| `BASE_EXTRACTED` | Directorio de texto extraído: `data/extracted/` |
| `TEMP_DIR` | Directorio temporal para PDFs: `data/temp_pdfs/` |
| `LOGS_DIR` | Directorio de logs: `logs/` |

---

#### Clase `MinIOClient`

Gestiona la conexión a MinIO y la descarga de PDFs.

**Método `Connect()`**

```python
def Connect(self) -> bool
```

Establece la conexión con el servidor MinIO usando las credenciales de `ConfigMinIO`. Retorna `True` si la conexión es exitosa, `False` en caso contrario.

**Método `DescargarPDFsPorCarpeta(carpeta: str, destino: Path) -> dict`**

```python
def DescargarPDFsPorCarpeta(self, carpeta: str, destino: Path) -> dict
```

Descarga todos los archivos `.pdf` de una carpeta específica del bucket.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `carpeta` | `str` | Ruta de la carpeta dentro del bucket (ej: `data/Artes`) |
| `destino` | `Path` | Directorio local donde se guardarán los PDFs |

Retorna un diccionario con:
```python
{
    "descargados": 47,    # PDFs descargados exitosamente
    "errores": 0,          # Fallos
    "archivos": [...]      # Lista de rutas locales
}
```

---

#### Clase `OCRProcessor`

Motor de extracción de texto. Intenta extracción digital primero; si falla o produce texto vacío, usa Tesseract OCR.

**Método `PreprocessImageForOCR(imagen) -> numpy.ndarray`**

```python
def PreprocessImageForOCR(self, imagen: PIL.Image) -> numpy.ndarray
```

Preprocesa una imagen para mejorar la precisión del OCR:

1. Convierte PIL Image a array numpy
2. Convierte a escala de grises
3. Aplica threshold binario (umbral: 127)
4. Escala la imagen al 200% (upscale para mejor reconocimiento)

**Método `ExtraerTextoDigital(pdf_path: Path) -> tuple[str, str]`**

```python
def ExtraerTextoDigital(self, pdf_path: Path) -> tuple[str, str]
```

Extrae texto de PDFs con capa de texto digital usando PyPDF2. Más rápido y preciso que OCR.

Retorna: `(texto_extraído, "digital")` o `("", "")` si falla.

**Método `ExtraerTextoConOCR(pdf_path: Path) -> tuple[str, str]`**

```python
def ExtraerTextoConOCR(self, pdf_path: Path) -> tuple[str, str]
```

Convierte cada página del PDF a imagen (300 DPI) y aplica Tesseract con:
- Idioma: español (`-l spa`)
- OEM 3: modo LSTM neural network
- PSM 6: asumir bloque de texto uniforme

Retorna: `(texto_extraído, "ocr")` o `("", "error")` si falla.

**Método Principal `ExtraerTexto(pdf_path: Path) -> tuple[str, str]`**

```python
def ExtraerTexto(self, pdf_path: Path) -> tuple[str, str]
```

Orquesta la extracción con lógica de fallback:
1. Intenta `ExtraerTextoDigital()` → si devuelve ≥50 caracteres, retorna ese texto
2. Si no, intenta `ExtraerTextoConOCR()`
3. Si ambos fallan, retorna `("", "error")`

Retorna: `(texto, metodo)` donde `metodo` es `"digital"`, `"ocr"`, o `"error"`.

---

#### Clase `MetadataGenerator`

Genera archivos JSON de metadatos para cada PDF procesado.

**Método `GenerarMetadata(pdf_nombre, tipo, metodo, texto, estado) -> dict`**

```python
def GenerarMetadata(
    self,
    pdf_nombre: str,
    tipo: str,
    metodo: str,
    texto: str,
    estado: str
) -> dict
```

Retorna un diccionario con la estructura:

```json
{
  "pdf_nombre": "nombre_archivo.pdf",
  "tipo_documento": "Artes",
  "metodo_extraccion": "digital",
  "longitud_caracteres": 1362,
  "numero_lineas": 24,
  "fecha_procesamiento": "2026-04-25T18:26:34.317347",
  "timestamp": 1777134394.317367,
  "estado": "exitoso"
}
```

| Campo | Descripción |
|-------|-------------|
| `tipo_documento` | Categoría: `Artes`, `especificaciones`, o `formulas` |
| `metodo_extraccion` | Método usado: `digital` u `ocr` |
| `longitud_caracteres` | Total de caracteres extraídos |
| `numero_lineas` | Número de líneas de texto |
| `estado` | `exitoso` o `error` |

---

#### Clase `ProcessadorPrincipal`

Orquesta todo el pipeline para las tres categorías de documentos.

**Método `ProcesarCarpeta(tipo, carpeta_minio) -> dict`**

Procesa todos los PDFs de una categoría:
1. Descarga PDFs de la carpeta MinIO especificada
2. Para cada PDF: extrae texto + genera metadatos + guarda `.txt` y `.json`
3. Genera un `resumen.json` de la categoría
4. Retorna diccionario de estadísticas

**Método `Ejecutar()`**

Punto de entrada principal. Procesa las tres carpetas secuencialmente y genera `RESUMEN_GLOBAL.json`.

**Método `MostrarResumenFinal()`**

Imprime en consola el resumen de procesamiento con totales y tasas de éxito.

---

### 9.2 core/anotaciones.py

Genera anotaciones NER automáticas a partir del texto extraído en el Script 01.

---

#### Clase `ConfigPaths`

```python
class ConfigPaths:
    EXTRACTED_BASE = BASE_DIR / "data" / "extracted"
    ANOTACIONES_BASE = BASE_DIR / "data" / "anotaciones"
    CANTIDAD_A_ANOTAR = 70    # Total de documentos a anotar
```

`CANTIDAD_A_ANOTAR` controla cuántos documentos se procesan (distribuidos proporcionalmente entre las tres categorías: ~23-24 por categoría).

---

#### Clase `PatronesDeteccion`

Define los patrones regex para detectar cada tipo de entidad.

| Entidad | Patrón | Ejemplo |
|---------|--------|---------|
| `INGREDIENTE` | `r'\b([A-Z][a-z]+(?:\s+[a-z]+)*)\s+\d+[\.,]\d*\s*%'` | `"Aqua 70%"` |
| `INCI` | `r'\b[A-Z][A-Z\s\-]{5,}\b'` | `"SODIUM HYALURONATE"` |
| `ADVERTENCIA` | `r'(?i)(precaución\|advertencia\|peligro\|...)` | `"Precaución: mantener fuera..."` |
| `MODO_USO` | `r'(?i)(modo de uso\|instrucciones\|aplicar\|...)` | `"Aplicar sobre la uña..."` |
| `FABRICANTE` | `r'(?i)(fabricado por\|manufactured by\|...)` | `"Fabricado por Thuya S.L."` |
| `PAIS_ORIGEN` | `r'(?i)(made in\|fabricado en\|origen:\|...)` | `"Made in Spain"` |
| `NUMERO_LOTE` | `r'(?i)(lote\|lot\|batch)\s*[:\-#]?\s*([A-Z0-9\-]{4,})` | `"Lote: AB2024-001"` |
| `FECHA_VENCIMIENTO` | `r'(?i)(vence\|expira\|caducidad\|...)` | `"Caducidad: 01/2025"` |

---

#### Clase `GeneradorAnotaciones`

Genera anotaciones en formato spaCy a partir del texto extraído.

**Método `GenerarAnotacion(texto: str, nombre_pdf: str, tipo: str) -> dict`**

```python
def GenerarAnotacion(self, texto: str, nombre_pdf: str, tipo: str) -> dict
```

1. Aplica cada patrón regex de `PatronesDeteccion` al texto
2. Registra cada coincidencia con posiciones de inicio y fin
3. Elimina entidades duplicadas o superpuestas
4. Para `FECHA_VENCIMIENTO`: valida la fecha con `dateparser.parse()`
5. Genera el archivo de anotación en formato compatible con spaCy y Label Studio

**Formato de Salida:**

```json
{
  "text": "Texto completo del PDF aquí...",
  "ents": [
    {"start": 127, "end": 170, "label": "MODO_USO"},
    {"start": 507, "end": 541, "label": "MODO_USO"},
    {"start": 892, "end": 912, "label": "FABRICANTE"}
  ],
  "metadata": {
    "pdf_original": "nombre_archivo.txt",
    "fecha_anotacion": "2026-04-25T12:37:52.674776",
    "metodo": "automatico_regex",
    "estado": "requiere_revision_manual",
    "num_entidades": 3
  }
}
```

> **Importante:** El campo `estado: "requiere_revision_manual"` indica que todas las anotaciones automáticas deben ser revisadas por un anotador humano en Label Studio antes de entrenar el modelo.

---

#### Clase `ProcesadorAnotaciones`

Orquesta el procesamiento de todas las categorías.

**Método `ProcesarTipo(tipo: str, cantidad: int) -> dict`**

Procesa `cantidad` documentos de la categoría `tipo` y guarda las anotaciones en `data/anotaciones/{tipo}/`.

**Método `Ejecutar()`**

Procesa las tres categorías y genera un resumen de anotaciones.

---

### 9.3 core/upload_s3.py

Utilidad para subir los archivos JSON generados a un bucket de AWS S3.

**Función `_LoadCredentials(credentials_path: str) -> dict`**

Lee las credenciales AWS del archivo `.aws/credentials.ini` y retorna un diccionario con `aws_access_key_id` y `aws_secret_access_key`.

**Función `UploadFile(s3_client, file_path: Path, bucket: str, s3_key: str) -> bool`**

Sube un archivo individual a S3. Retorna `True` si fue exitoso.

**Función `CollectJsonFiles(base_dir: Path) -> list[Path]`**

Recorre `data/extracted/` y recopila todos los archivos `.json` excluyendo `resumen.json` (archivos de resumen interno).

**Función `UploadAllJsonFiles(bucket_name: str) -> None`**

Función principal: carga credenciales, crea cliente S3, recopila archivos y sube cada uno con la estructura de prefijo `data/extracted/`.

---

## 10. Label Studio: Instalación y Acceso Remoto

Label Studio es la herramienta de anotación manual para revisar y corregir las anotaciones automáticas generadas por el Script 02.

### 10.1 Instalación en Ambiente Separado

Label Studio requiere su propio ambiente virtual para evitar conflictos de dependencias.

```bash
# Crear ambiente dedicado
python3 -m venv ~/venvs/label-studio

# Activar
source ~/venvs/label-studio/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar Label Studio
pip install label-studio

# Verificar instalación
label-studio --version
```

### 10.2 Iniciar Label Studio Localmente

```bash
# Activar el ambiente
source ~/venvs/label-studio/bin/activate

# Opción 1: Abrir en navegador automáticamente (puerto 8080)
label-studio start

# Opción 2: Puerto personalizado, sin abrir navegador
label-studio start --port 8085 --no-browser

# Opción 3: Especificar directorio de datos personalizado
label-studio start --data-dir ~/label-studio-data --port 8085
```

Al iniciar por primera vez, Label Studio solicitará crear una cuenta de administrador con email y contraseña. Estos datos se almacenan localmente.

### 10.3 Acceso Remoto desde Windows a Ubuntu (WSL2)

Cuando Label Studio corre en Ubuntu (WSL2), se puede acceder desde Windows de estas formas:

#### Opción A: Acceso Directo desde Windows (Recomendada)

WSL2 expone automáticamente los puertos en `localhost` de Windows. Si Label Studio está en el puerto 8085 en Ubuntu, acceder desde el navegador de Windows:

```
http://localhost:8085
```

#### Opción B: Acceso desde Otro Dispositivo en la Red Local

Para acceder desde otro equipo (por ejemplo, una tablet o laptop en la misma red WiFi):

**Paso 1:** Encontrar la IP de WSL2 en Ubuntu:
```bash
# En Ubuntu/WSL2
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
# Ejemplo: 172.22.134.45
```

**Paso 2:** Iniciar Label Studio vinculado a todas las interfaces:
```bash
label-studio start --host 0.0.0.0 --port 8085 --no-browser
```

**Paso 3:** Crear regla de reenvío de puertos en PowerShell (Windows) como Administrador:

```powershell
# Reemplazar WSL_IP con la IP obtenida en el Paso 1
netsh interface portproxy add v4tov4 `
    listenport=8085 `
    listenaddress=0.0.0.0 `
    connectport=8085 `
    connectaddress=172.22.134.45
```

**Paso 4:** Abrir el puerto en el Firewall de Windows (PowerShell como Administrador):

```powershell
New-NetFirewallRule `
    -DisplayName "Label Studio" `
    -Direction Inbound `
    -LocalPort 8085 `
    -Protocol TCP `
    -Action Allow
```

**Paso 5:** Desde cualquier dispositivo en la misma red, acceder usando la IP de Windows:
```
http://192.168.X.X:8085
```

> Para encontrar la IP de Windows: `ipconfig` en PowerShell → "Dirección IPv4" de la tarjeta de red activa.

#### Opción C: Script Automatizado para Reenvío de Puertos

Guardar como `scripts/expose_label_studio.ps1` y ejecutar como Administrador en Windows:

```powershell
# Script: expose_label_studio.ps1
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]
$port = 8085

Write-Host "WSL2 IP: $wslIP"
Write-Host "Configurando reenvio de puerto $port..."

# Remover regla anterior si existe
netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null

# Agregar nueva regla
netsh interface portproxy add v4tov4 `
    listenport=$port `
    listenaddress=0.0.0.0 `
    connectport=$port `
    connectaddress=$wslIP

$windowsIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi").IPAddress
Write-Host "Label Studio disponible en:"
Write-Host "  Local:  http://localhost:$port"
Write-Host "  Red:    http://${windowsIP}:$port"
```

### 10.4 Configurar Proyecto en Label Studio

Una vez que Label Studio está ejecutándose y se accede desde el navegador:

#### Paso 1: Crear Proyecto

1. Hacer clic en **"Create Project"**
2. Nombre: `Anotaciones Grupo Moreno`
3. Descripción: `Revisión de anotaciones NER para productos cosméticos`

#### Paso 2: Configurar Template NER

En la pestaña **"Labeling Setup"**:

1. Seleccionar template: **"Named Entity Recognition"**
2. O usar el siguiente XML personalizado:

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="INGREDIENTE" background="#FFA500"/>
    <Label value="CONCENTRACIÓN" background="#FFD700"/>
    <Label value="INCI" background="#7B68EE"/>
    <Label value="ADVERTENCIA" background="#FF4500"/>
    <Label value="MODO_USO" background="#32CD32"/>
    <Label value="FABRICANTE" background="#4169E1"/>
    <Label value="PAIS_ORIGEN" background="#20B2AA"/>
    <Label value="NUMERO_LOTE" background="#CD853F"/>
    <Label value="FECHA_VENCIMIENTO" background="#DC143C"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

#### Paso 3: Importar Anotaciones

Las anotaciones en `data/anotaciones/` ya están en formato compatible con Label Studio.

**Opción A — Importar archivos JSON directamente:**
1. En el proyecto, hacer clic en **"Import"**
2. Arrastrar los archivos `*_anno.json` de `data/anotaciones/`
3. Label Studio importará el texto y las entidades pre-anotadas

**Opción B — Importar programáticamente (con Label Studio SDK):**

```python
from label_studio_sdk import Client

ls = Client(url='http://localhost:8085', api_key='TU_API_KEY')
project = ls.get_project(ID_DEL_PROYECTO)

import json
from pathlib import Path

anotaciones_dir = Path("data/anotaciones")
for archivo in anotaciones_dir.rglob("*_anno.json"):
    with open(archivo) as f:
        data = json.load(f)
    # Importar tarea
    project.import_tasks([{
        "data": {"text": data["text"]},
        "predictions": [{
            "model_version": "automatico_regex",
            "result": [
                {
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": ent["start"],
                        "end": ent["end"],
                        "text": data["text"][ent["start"]:ent["end"]],
                        "labels": [ent["label"]]
                    }
                }
                for ent in data["ents"]
            ]
        }]
    }])
```

#### Paso 4: Revisar y Corregir Anotaciones

Para cada documento:
1. Verificar las entidades detectadas automáticamente (marcadas en colores)
2. Corregir etiquetas incorrectas: hacer clic en la etiqueta y cambiarla
3. Agregar entidades faltantes: seleccionar texto → elegir etiqueta
4. Eliminar entidades incorrectas: hacer clic en la entidad → presionar Delete
5. Hacer clic en **"Submit"** para guardar la anotación

**Tiempo estimado:** 3-5 minutos por documento → ~3-6 horas para 70 documentos.

#### Paso 5: Exportar Anotaciones Revisadas

Una vez revisados todos los documentos:

1. En el proyecto, hacer clic en **"Export"**
2. Seleccionar formato **"JSON"** o **"spaCy v3 NER"**
3. Descargar y guardar en `data/anotaciones_revisadas/`

Estas anotaciones revisadas serán la entrada para el Script 03 (entrenamiento del modelo).

### 10.5 Atajos de Teclado en Label Studio

| Atajo | Acción |
|-------|--------|
| `1-9` | Seleccionar etiqueta por número |
| `←` / `→` | Navegar entre tareas |
| `Ctrl+Z` | Deshacer última acción |
| `Enter` | Confirmar y enviar anotación |
| `Escape` | Cancelar selección actual |

---

## 11. Estructura de Datos y Formatos

### 11.1 Archivo de Texto Extraído (.txt)

```
--- PÁGINA 1 ---
Thuya S.L.   Sant Gervasi de Cassoles, 68
08022 Barcelona (SPAIN) - www.thuya.com

30 g. 1 oz.

Modo de uso / Instructions for use:
Coger la cantidad de producto necesaria con la ayuda de una espátula
y aplicarla sobre la uña previamente preparada...

Ingredientes / Ingredients:
Ethyl Methacrylate Copolymer, Butyl Acetate, Ethyl Acetate...

MANTENER FUERA DEL ALCANCE DE LOS NIÑOS
Precaución: contiene metacrilatos...

--- PÁGINA 2 ---
...
```

### 11.2 Archivo de Metadatos (.json)

```json
{
  "pdf_nombre": "ACRYLIC_GEL_CLEAR_Etiqueta_30g.pdf",
  "tipo_documento": "Artes",
  "metodo_extraccion": "digital",
  "longitud_caracteres": 1362,
  "numero_lineas": 24,
  "fecha_procesamiento": "2026-04-25T18:26:34.317347",
  "timestamp": 1777134394.317367,
  "estado": "exitoso"
}
```

### 11.3 Archivo de Anotaciones (_anno.json)

```json
{
  "text": "Thuya S.L. Sant Gervasi de Cassoles...",
  "ents": [
    {
      "start": 0,
      "end": 10,
      "label": "FABRICANTE"
    },
    {
      "start": 127,
      "end": 185,
      "label": "MODO_USO"
    },
    {
      "start": 312,
      "end": 380,
      "label": "ADVERTENCIA"
    }
  ],
  "metadata": {
    "pdf_original": "ACRYLIC_GEL_CLEAR_Etiqueta_30g.txt",
    "fecha_anotacion": "2026-04-25T12:37:52.674776",
    "metodo": "automatico_regex",
    "estado": "requiere_revision_manual",
    "num_entidades": 3
  }
}
```

### 11.4 Resumen Global (RESUMEN_GLOBAL.json)

```json
{
  "fecha_ejecucion": "2026-04-19T12:22:59.188818",
  "total_exitosos": 118,
  "total_errores": 0,
  "total_procesados": 118,
  "por_tipo": {
    "Artes": {
      "exitosos": 43,
      "con_error": 0,
      "detalles": [
        {
          "pdf": "ACRYLIC_GEL_CLEAR.pdf",
          "caracteres": 1362,
          "metodo": "digital"
        }
      ]
    },
    "especificaciones": {
      "exitosos": 37,
      "con_error": 0,
      "detalles": [...]
    },
    "formulas": {
      "exitosos": 38,
      "con_error": 0,
      "detalles": [...]
    }
  }
}
```

---

## 12. Hoja de Ruta del Proyecto

### Script 03: Entrenamiento del Modelo NER

**Entrada:** Anotaciones revisadas de Label Studio (70 documentos)  
**Salida:** Modelo spaCy NER entrenado en `modelos/ner_cosmeticos/`

```bash
# Próximamente: python core/entrenamiento.py
```

**División de datos:**
- Entrenamiento: 56 documentos (80%)
- Validación: 14 documentos (20%)

**Métricas objetivo:**
- F1-score global: ≥0.80
- Precisión por entidad: ≥0.75

**Tiempo estimado:** 2-3 horas (CPU).

### Script 04: Predicciones

**Entrada:** Modelo entrenado + 118 archivos `.txt` en `data/extracted/`  
**Salida:** Anotaciones para el corpus completo en `data/predicciones/`

```bash
# Próximamente: python core/predicciones.py
```

### Script 05: Validación Automática

Calcula métricas de evaluación (F1, precisión, recall) comparando predicciones vs. anotaciones manuales.

### Script 06: Dashboard Streamlit

Visualización interactiva de resultados con Plotly. Mostrará distribución de entidades por tipo de documento, estadísticas del corpus y explorador de predicciones.

```bash
# Próximamente
streamlit run core/dashboard.py
```

---

## 13. Solución de Problemas

### MinIO: Error de Conexión

**Síntoma:** `ConnectionRefused` al ejecutar `core/OCR.py`

```bash
# Verificar que MinIO está corriendo
curl http://localhost:9000/minio/health/live

# Verificar credenciales en .env
cat core/.env
```

### Tesseract: Idioma Español No Encontrado

**Síntoma:** `Error: Failed loading language 'spa'`

```bash
# Instalar paquete de idioma
sudo apt install tesseract-ocr-spa

# Verificar
tesseract --list-langs | grep spa
```

### pdf2image: Error de Poppler

**Síntoma:** `pdf2image.exceptions.PDFInfoNotInstalledError`

```bash
sudo apt install poppler-utils
```

### psycopg2: Error de Compilación

**Síntoma:** `Error: pg_config executable not found`

```bash
# Instalar headers de PostgreSQL
sudo apt install libpq-dev postgresql-client

# O usar la versión binaria (sin compilación)
pip install psycopg2-binary
```

### OpenCV: Error de Librería Compartida

**Síntoma:** `libGL.so.1: cannot open shared object file`

```bash
sudo apt install libgl1-mesa-glx libglib2.0-0
```

### Label Studio: Puerto Ya en Uso

**Síntoma:** `Address already in use`

```bash
# Ver qué proceso usa el puerto 8085
lsof -i :8085

# Usar un puerto diferente
label-studio start --port 8090 --no-browser
```

### WSL2: Acceso Remoto No Funciona

**Síntoma:** No se puede acceder a Label Studio desde otro dispositivo

```bash
# 1. Verificar que Label Studio escucha en 0.0.0.0
label-studio start --host 0.0.0.0 --port 8085 --no-browser

# 2. En PowerShell (Windows, como Administrador):
# Obtener IP de WSL2
wsl hostname -I

# Recrear regla de portproxy
netsh interface portproxy delete v4tov4 listenport=8085 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=8085 listenaddress=0.0.0.0 connectport=8085 connectaddress=<WSL2_IP>

# Verificar regla activa
netsh interface portproxy show v4tov4
```

### OCR Lento o Sin Resultados

**Síntoma:** La extracción OCR toma más de 5 minutos por PDF o devuelve texto vacío

```bash
# Verificar instalación de Tesseract
tesseract --version

# Probar OCR manual en una imagen
tesseract imagen_prueba.png stdout -l spa

# Si la imagen es pequeña, el upscale al 200% puede no ser suficiente.
# Aumentar el factor de escala en OCRProcessor.PreprocessImageForOCR():
# Cambiar 2.0 (200%) a 3.0 (300%)
```

---

*Documentación generada el 25 de abril de 2026 — Pipeline NER Grupo Moreno v1.0*
