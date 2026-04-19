# INSTRUCCIONES FINALES: SCRIPTS LISTOS PARA EJECUTAR
## Estructura MinIO: grupo-moreno/data/Artes, Especificaciones, formulas

**Fecha:** Enero 2026  
**Versión:** 2.0 - Scripts finales con estructura grupo-moreno

---

## ESTRUCTURA MinIO CONFIRMADA

```
grupo-moreno (bucket)
└── data/
    ├── Artes/              (PDFs de artes)
    ├── Especificaciones/   (PDFs de especificaciones)
    └── formulas/           (PDFs de fórmulas)
```

**Total de PDFs:** ~122
- Artes: ~47
- Especificaciones: ~37
- formulas: ~38

---

## ESTRUCTURA LOCAL DE OUTPUT

El script 01 genera automáticamente:

```
data/extracted/
├── Artes/                          (textos extraídos de Artes)
│   ├── arte_001.txt
│   ├── arte_001.json
│   ├── arte_002.txt
│   ├── arte_002.json
│   └── ... (47 archivos)
│
├── Especificaciones/               (textos extraídos de Especificaciones)
│   ├── esp_001.txt
│   ├── esp_001.json
│   ├── esp_002.txt
│   ├── esp_002.json
│   └── ... (37 archivos)
│
├── formulas/                       (textos extraídos de formulas)
│   ├── formula_001.txt
│   ├── formula_001.json
│   ├── formula_002.txt
│   ├── formula_002.json
│   └── ... (38 archivos)
│
└── RESUMEN_GLOBAL.json             (resumen total)
```

---

## Paso 1. 

### 1. Crear archivo `.env`

```bash
nano .env
```

### 2. Valores críticos en `.env`

```bash
# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET=grupo-moreno              
MINIO_ACCESS_KEY=minioadmin            
MINIO_SECRET_KEY=minioadmin            

# PostgreSQL
DATABASE_USER=tu_usuario
DATABASE_PASSWORD=tu_password
DATABASE_NAME=grupo_moreno
```

---

## EJECUTAR SCRIPT 01 (Descarga + OCR)

### Comando:

```bash
python core/OCR.py
```

### ¿Qué hace?

1. **Conecta a MinIO** (bucket: grupo-moreno)
2. **Descarga PDFs** de las 3 carpetas:
   - `data/Artes/` → descarga ~47 PDFs
   - `data/Especificaciones/` → descarga ~37 PDFs
   - `data/formulas/` → descarga ~38 PDFs

3. **Ejecuta OCR** en cada PDF:
   - Intenta extracción digital (PyPDF2) - rápido ✓
   - Si falla, usa OCR (Tesseract + spaCy) - lento pero fiable

4. **Clasifica automáticamente**:
   - Detecta si es ARTE, ESPECIFICACION o FORMULA
   - Basado en nombre y contenido

5. **Guarda output** respetando estructura:
   - `data/extracted/Artes/*.txt` y `.json`
   - `data/extracted/Especificaciones/*.txt` y `.json`
   - `data/extracted/formulas/*.txt` y `.json`

### Output esperado:

```
============================================================
INICIANDO PROCESO: MinIO grupo-moreno → OCR → Metadatos
Bucket: grupo-moreno
Carpetas a procesar: ['data/Artes', 'data/Especificaciones', 'data/formulas']
============================================================

✓ Conectado a MinIO en localhost:9000
  Buckets disponibles: ['grupo-moreno']

============================================================
PROCESANDO: Artes
============================================================
✓ 47 PDFs descargados de Artes
  [1/47] arte_001.pdf - 2345 caracteres (digital)
  [2/47] arte_002.pdf - 1890 caracteres (ocr)
  ...

============================================================
PROCESANDO: Especificaciones
============================================================
✓ 37 PDFs descargados de Especificaciones
  [1/37] esp_001.pdf - 3456 caracteres (digital)
  ...

============================================================
PROCESANDO: formulas
============================================================
✓ 38 PDFs descargados de formulas
  [1/38] formula_001.pdf - 4567 caracteres (digital)
  ...

============================================================
RESUMEN FINAL
============================================================

Artes:
  ✓ Exitosos: 47
  ✗ Con error: 0
  Total: 47

Especificaciones:
  ✓ Exitosos: 37
  ✗ Con error: 0
  Total: 37

formulas:
  ✓ Exitosos: 38
  ✗ Con error: 0
  Total: 38

============================================================
TOTALES:
✓ Exitosos: 122
✗ Con error: 0
TOTAL PROCESADOS: 122
============================================================

✓ Resumen global guardado en: data/extracted/RESUMEN_GLOBAL.json
✓ Textos extraídos en: data/extracted
  ├─ Artes/
  ├─ Especificaciones/
  └─ formulas/
```

### Verificar resultados:

```bash
# Contar archivos generados
find data/extracted -name "*.txt" | wc -l
# Output esperado: 122

find data/extracted -name "*.json" -not -name "RESUMEN*" | wc -l
# Output esperado: 122

# Ver estructura
tree data/extracted/
# Output esperado:
# data/extracted/
# ├── Artes/
# │   ├── arte_001.txt
# │   ├── arte_001.json
# │   ├── arte_002.txt
# │   ├── arte_002.json
# │   └── ... (94 archivos en total: 47 txt + 47 json)
# ├── Especificaciones/
# │   └── ... (74 archivos: 37 txt + 37 json)
# ├── formulas/
# │   └── ... (76 archivos: 38 txt + 38 json)
# └── RESUMEN_GLOBAL.json
```

---

## EJECUTAR  (Anotaciones automáticas)

### Comando:

```bash
python scripts/02_generar_anotaciones_automaticas.py
```

### ¿Qué hace?

1. **Lee textos extraídos** de las 3 carpetas
2. **Aplica 8 detectores regex** para encontrar:
   - `INGREDIENTE` + `CONCENTRACIÓN` (ej: "Water 70%")
   - `INCI` (nomenclatura)
   - `ADVERTENCIA`
   - `MODO_USO`
   - `FABRICANTE`
   - `PAIS_ORIGEN`
   - `NUMERO_LOTE`
   - `FECHA_VENCIMIENTO`

3. **Genera anotaciones JSON** en formato spaCy:
   ```json
   {
     "text": "contenido del PDF",
     "ents": [
       {"start": 10, "end": 15, "label": "INGREDIENTE"},
       {"start": 16, "end": 19, "label": "CONCENTRACIÓN"}
     ],
     "metadata": {...}
   }
   ```

4. **Guarda 70 anotaciones** (primeros ~23 de cada tipo):
   - `data/anotaciones/Artes/` (~23 anotaciones)
   - `data/anotaciones/Especificaciones/` (~23 anotaciones)
   - `data/anotaciones/formulas/` (~24 anotaciones)

### Output esperado:

```
============================================================
PASO 4: GENERAR ANOTACIONES JSON AUTOMÁTICAS
============================================================

============================================================
ANOTANDO: Artes
============================================================
Encontrados 47 archivos .txt
  [1/23] arte_001.txt → 8 entidades
  [2/23] arte_002.txt → 5 entidades
  [3/23] arte_003.txt → 12 entidades
  ...
  [23/23] arte_023.txt → 6 entidades

============================================================
ANOTANDO: Especificaciones
============================================================
Encontrados 37 archivos .txt
  [1/23] esp_001.txt → 7 entidades
  ...

============================================================
ANOTANDO: formulas
============================================================
Encontrados 38 archivos .txt
  [1/24] formula_001.txt → 9 entidades
  ...

============================================================
RESUMEN FINAL
============================================================

Artes:
  ✓ Exitosos: 23
  ✗ Con error: 0
  Total procesados: 23
  Entidades detectadas: 156 (promedio: 6.78)
  Ubicación: data/anotaciones/Artes

Especificaciones:
  ✓ Exitosos: 23
  ✗ Con error: 0
  Total procesados: 23
  Entidades detectadas: 142 (promedio: 6.17)
  Ubicación: data/anotaciones/Especificaciones

formulas:
  ✓ Exitosos: 24
  ✗ Con error: 0
  Total procesados: 24
  Entidades detectadas: 178 (promedio: 7.42)
  Ubicación: data/anotaciones/formulas

============================================================
TOTALES:
✓ Exitosos: 70
✗ Con error: 0
TOTAL ANOTACIONES: 70
============================================================

✓ Anotaciones guardadas en:
  ├─ data/anotaciones/Artes
  ├─ data/anotaciones/Especificaciones
  └─ data/anotaciones/formulas
```

### Tiempo estimado:

- ~5 minutos (generación automática)

### Verificar resultados:

```bash
# Contar anotaciones generadas
find data/anotaciones -name "*.json" | wc -l
# Output esperado: 70

# Ver estructura
tree data/anotaciones/
# Output esperado:
# data/anotaciones/
# ├── Artes/
# │   ├── arte_001_anno.json
# │   ├── arte_002_anno.json
# │   └── ... (23 archivos)
# ├── Especificaciones/
# │   └── ... (23 archivos)
# └── formulas/
#     └── ... (24 archivos)
```

---

## DÍA 2-3: REVISAR ANOTACIONES MANUALMENTE

**⚠️ PASO CRÍTICO:** Las anotaciones automáticas necesitan validación humana

### Opción A: Prodigy (RECOMENDADO - Rápido)

```bash
# Instalar Prodigy (si no está)
pip install prodigy

# Abrir interfaz Prodigy
prodigy data-to-spacy \
  data/anotaciones \
  --output data/anotaciones_validadas \
  --lang es

# Se abre en http://localhost:8080
# TÚ revisas cada anotación (5-10 min por PDF)
# Corriges: agrega/elimina/modifica entidades
# Guarda validadas
```

### Opción B: Label Studio (OPEN SOURCE)

```bash
# Instalar
pip install label-studio

# Iniciar
label-studio start

# Se abre en http://localhost:8080
# Creas proyecto, cargas JSONs, revisa y valida
```

### Opción C: Edición manual (si prefieres control total)

```bash
# Editar cada JSON directamente
vim data/anotaciones/Artes/arte_001_anno.json

# Verifica estructura y correcciones:
# - start/end: posición correcta en el texto
# - label: tipo de entidad correcto
# - Agrega faltantes manualmente
```

---

## DESPUÉS DE SCRIPT 02: PRÓXIMOS PASOS

Una vez validadas las 70 anotaciones, pasamos a:

### Script 03: Entrenar modelo NER
```bash
python scripts/03_train_ner_model.py
# Input: 70 anotaciones validadas
# Output: models/ner_model_v0.4/ (F1 ≥ 0.82)
# Tiempo: 2-3 horas
```

### Script 04: Predicciones en 122 PDFs
```bash
python scripts/04_predicciones_en_pdfs.py
# Input: modelo entrenado + 122 textos extraídos
# Output: PostgreSQL con 122 productos + ~1,200 entidades
# Tiempo: 1-2 horas
```

### Script 05: Validaciones automáticas
```bash
python scripts/05_validaciones_automaticas.py
# Valida 3 criterios: ¿Lote? ¿Advertencias? ¿Español?
```

### Script 06: Dashboard Streamlit
```bash
streamlit run dashboard/app.py
# Interfaz para búsqueda y visualización
```

---

## CHECKLIST: ANTES DE EMPEZAR

- [ ] Archivo `config/.env` creado
- [ ] `MINIO_BUCKET=grupo-moreno` en `.env`
- [ ] `MINIO_ENDPOINT=localhost:9000` en `.env`
- [ ] Credenciales MinIO correctas
- [ ] Scripts copiados a `scripts/`
- [ ] Tesseract instalado (`tesseract --version`)
- [ ] Python dependencies instaladas (`pip install -r requirements.txt`)
- [ ] Modelo spaCy descargado (`python -m spacy download es_core_news_sm`)
- [ ] Logs accessible en `logs/`

---

## TROUBLESHOOTING

### Problema: "El bucket no se llama grupo-moreno"

**Solución:**
```bash
# Verificar bucket en .env
cat config/.env | grep MINIO_BUCKET
# Output: MINIO_BUCKET=grupo-moreno

# Verificar que MinIO tiene ese bucket
# Conecta a MinIO en http://localhost:9000
# y verifica que existe el bucket "grupo-moreno"
```

### Problema: "No se descarga nada"

**Solución:**
```bash
# Verificar estructura en MinIO:
# grupo-moreno/
#   └── data/
#       ├── Artes/
#       ├── Especificaciones/
#       └── formulas/

# Verificar permisos MinIO
# Usuario minioadmin debe poder listar buckets
```

### Problema: "OCR es muy lento"

**Solución:**
- Esto es NORMAL - OCR tarda 10-15s por PDF
- 122 PDFs = 25-30 minutos
- Deja que se ejecute de noche mientras duermes

### Problema: "MemoryError durante OCR"

**Solución:**
```bash
# Reducir DPI en script
# En OCRProcessor.ExtraerTextoConOCR():
images = convert_from_path(pdf_path, dpi=150)  # Cambiar de 300 a 150
```

---

## COMANDOS ÚTILES

```bash
# Ver logs en tiempo real
tail -f logs/ocr.log
tail -f logs/anotaciones.log

# Ver estructura de output
tree data/extracted/
tree data/anotaciones/

# Contar archivos
find data/extracted -type f | wc -l
find data/anotaciones -type f | wc -l

# Ver resumen global
cat data/extracted/RESUMEN_GLOBAL.json | jq .

# Ejemplo de anotación
cat data/anotaciones/Artes/arte_001_anno.json | jq .
```

---

## ESTIMACIÓN TOTAL

| Tarea | Tiempo |
|-------|--------|
| Setup (config, scripts) | 10 min |
| Script 01 (OCR) | 25-30 min |
| Script 02 (Anotaciones) | 5 min |
| Revisar anotaciones (Prodigy) | 4-8 horas |
| Script 03 (Entrenar NER) | 2-3 horas |
| Script 04 (Predicciones) | 1-2 horas |
| **TOTAL POC** | **7-15 horas** |

---

## RESUMEN: FLUJO COMPLETO

```
1. config/.env configurado
   ↓
2. Scripts copiados
   ↓
3. python scripts/01_descarga_y_ocr.py
   └─ Output: 122 textos extraídos (Artes, Especificaciones, formulas)
   ↓
4. python scripts/02_generar_anotaciones_automaticas.py
   └─ Output: 70 anotaciones automáticas
   ↓
5. Revisar anotaciones manualmente (Prodigy/Label Studio)
   └─ Output: 70 anotaciones validadas
   ↓
6. python scripts/03_train_ner_model.py
   └─ Output: Modelo NER (F1 ≥ 0.82)
   ↓
7. python scripts/04_predicciones_en_pdfs.py
   └─ Output: PostgreSQL con 122 productos + entidades
   ↓
8. python scripts/05_validaciones_automaticas.py
   └─ Output: Validaciones para 122 productos
   ↓
9. streamlit run dashboard/app.py
   └─ Output: Dashboard en http://localhost:8501
   ↓
10. PRESENTACIÓN A GERARDO ✓
```

---

