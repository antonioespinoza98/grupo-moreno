# core/anotaciones.py
# SCRIPT 02: Generación automática de anotaciones JSON para entrenamiento NER

"""
Ejecuta:
    python core/anotaciones.py

Entrada:
    - data/extracted/Artes/*.txt
    - data/extracted/especificaciones/*.txt
    - data/extracted/formulas/*.txt
    (Output del script 01 — core/OCR.py)

Output:
    - data/anotaciones/Artes/*.json
    - data/anotaciones/especificaciones/*.json
    - data/anotaciones/formulas/*.json
    (Formato spaCy compatible para entrenamiento NER)
"""

import sys
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import os
import dateparser

# Ruta consistente con core/OCR.py — ambos cargan desde la raíz del proyecto
load_dotenv(Path(__file__).parent.parent / ".env")


# ═══════════════════════════════════════ CONFIGURACIÓN ═══════════════════════════════════════

class ConfigPaths:
    """Configuración de rutas desde .env"""
    EXTRACTED_BASE = Path(os.getenv("EXTRACTED_OUTPUT_DIR", "data/extracted"))
    ANOTACIONES_BASE = Path(os.getenv("ANOTACIONES_DIR", "data/anotaciones"))
    LOGS_DIR = Path("logs")
    CANTIDAD_A_ANOTAR = int(os.getenv("CANTIDAD_A_ANOTAR", "70"))

    # Nombres en minúscula para coincidir con la salida de OCR.py
    TIPOS_DOC = {
        "Artes":            EXTRACTED_BASE / "Artes",
        "especificaciones": EXTRACTED_BASE / "especificaciones",
        "formulas":         EXTRACTED_BASE / "formulas",
    }

    ANOTACIONES_PATHS = {
        "Artes":            ANOTACIONES_BASE / "Artes",
        "especificaciones": ANOTACIONES_BASE / "especificaciones",
        "formulas":         ANOTACIONES_BASE / "formulas",
    }

    @classmethod
    def CreateDirectories(cls):
        """Crea todos los directorios necesarios"""
        cls.ANOTACIONES_BASE.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        for subcarpeta in cls.ANOTACIONES_PATHS.values():
            subcarpeta.mkdir(parents=True, exist_ok=True)


# Crear directorios ANTES de configurar logging para que logs/ exista al abrir el FileHandler
ConfigPaths.CreateDirectories()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/anotaciones.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════ PATRONES REGEX ═══════════════════════════════════════

class PatronesDeteccion:
    """
    Patrones regex compilados para detección de entidades.
    Todos los patrones tienen grupo(1) como la entidad capturada,
    separado del keyword disparador.
    """

    # grupo 1 = ingrediente, grupo 2 = concentración
    INGREDIENTE = re.compile(
        r'(\w+(?:\s+\w+)?)\s+(\d+(?:\.\d+)?%)',
        re.IGNORECASE
    )

    # grupo 1 = nombre INCI
    INCI = re.compile(
        r'(?:INCI|nomenclatura\s+INCI|nomenclatura\s+química)[\s:]*([A-Za-z0-9\-\s,]+?)(?=\n|$)',
        re.IGNORECASE
    )

    # grupo 1 = texto de advertencia
    ADVERTENCIA = re.compile(
        r'(?:advertencia|aviso|precaución|warning|precaution)[\s:]*([^\n]+)',
        re.IGNORECASE
    )

    # grupo 1 = instrucciones de uso
    MODO_USO = re.compile(
        r'(?:modo\s+de\s+uso|instrucciones|uso|use|aplicación|apply)[\s:]*([^\n.]+)',
        re.IGNORECASE
    )

    # grupo 1 = nombre del fabricante
    FABRICANTE = re.compile(
        r'(?:fabricante|manufacturer|fabricado\s+por)[\s:]*([^\n]+)',
        re.IGNORECASE
    )

    # grupo 1 = país de origen
    PAIS_ORIGEN = re.compile(
        r'(?:origen|país\s+origen|made\s+in)[\s:]*([A-Za-z\s]+)',
        re.IGNORECASE
    )

    # grupo 1 = número de lote
    NUMERO_LOTE = re.compile(
        r'(?:lote|batch|lot)[\s#]*([A-Za-z0-9\-]+)',
        re.IGNORECASE
    )

    # grupo 1 = candidato a fecha (validado por dateparser)
    FECHA_VENCIMIENTO_TRIGGER = re.compile(
        r'(?:vencimiento|expiración|expiration|vence|exp\.?)[\s:]*([^\n,;]{3,30})',
        re.IGNORECASE
    )


# ═══════════════════════════════════════ FUNCIONES DE DETECCIÓN ═══════════════════════════════════════

def _DetectarConPatron(
    texto: str,
    patron: re.Pattern,
    label: str,
    grupo: int = 1,
    min_len: int = 3,
) -> List[Dict]:
    """
    Detecta entidades usando un patrón regex.
    Usa el grupo de captura indicado para delimitar el span de la entidad,
    excluyendo el keyword disparador del span.

    Args:
        texto:    Texto a analizar
        patron:   Patrón compilado
        label:    Etiqueta NER
        grupo:    Índice del grupo de captura que representa la entidad
        min_len:  Longitud mínima del texto capturado para aceptarlo

    Returns:
        Lista de dicts {start, end, label}
    """
    entidades = []
    for match in patron.finditer(texto):
        try:
            texto_capturado = match.group(grupo).strip()
        except IndexError:
            continue
        if len(texto_capturado) >= min_len:
            entidades.append({
                "start": match.start(grupo),
                "end":   match.end(grupo),
                "label": label,
            })
    return entidades


def _DetectarIngredientes(texto: str) -> List[Dict]:
    """
    Detecta pares ingrediente/concentración.
    Genera dos entidades distintas por cada match.
    """
    entidades = []
    for match in PatronesDeteccion.INGREDIENTE.finditer(texto):
        entidades.append({"start": match.start(1), "end": match.end(1), "label": "INGREDIENTE"})
        entidades.append({"start": match.start(2), "end": match.end(2), "label": "CONCENTRACIÓN"})
    return entidades


def _DetectarFechas(texto: str) -> List[Dict]:
    """
    Detecta fechas de vencimiento validando el candidato con dateparser.
    Soporta formatos numéricos y textuales en español e inglés,
    eliminando falsos positivos que el regex solo no puede descartar.
    """
    entidades = []
    for match in PatronesDeteccion.FECHA_VENCIMIENTO_TRIGGER.finditer(texto):
        candidato = match.group(1).strip()
        if dateparser.parse(candidato, languages=["es", "en"]):
            entidades.append({
                "start": match.start(1),
                "end":   match.end(1),
                "label": "FECHA_VENCIMIENTO",
            })
    return entidades


# Tabla de detectores genéricos: (patron, label, grupo_captura, min_len)
_DETECTORES_GENERICOS: List[Tuple] = [
    (PatronesDeteccion.INCI,        "INCI",        1, 5),
    (PatronesDeteccion.ADVERTENCIA, "ADVERTENCIA", 1, 5),
    (PatronesDeteccion.MODO_USO,    "MODO_USO",    1, 5),
    (PatronesDeteccion.FABRICANTE,  "FABRICANTE",  1, 3),
    (PatronesDeteccion.PAIS_ORIGEN, "PAIS_ORIGEN", 1, 2),
    (PatronesDeteccion.NUMERO_LOTE, "NUMERO_LOTE", 1, 2),
]


# ═══════════════════════════════════════ GENERADOR DE ANOTACIONES ═══════════════════════════════════════

class GeneradorAnotaciones:
    """Genera anotaciones JSON automáticas en formato spaCy"""

    def GenerarAnotacion(self, pdf_nombre: str, texto: str) -> Dict:
        """
        Aplica todos los detectores y produce la anotación final.

        Args:
            pdf_nombre: Nombre del PDF de origen
            texto:      Contenido extraído del PDF

        Returns:
            Dict con formato spaCy {text, ents, metadata}
        """
        entidades: List[Dict] = _DetectarIngredientes(texto)

        for patron, label, grupo, min_len in _DETECTORES_GENERICOS:
            entidades.extend(_DetectarConPatron(texto, patron, label, grupo, min_len))

        entidades.extend(_DetectarFechas(texto))

        # Eliminar duplicados exactos y ordenar por posición de inicio
        seen: set = set()
        entidades_unicas = []
        for ent in sorted(entidades, key=lambda x: (x["start"], x["end"])):
            key = (ent["start"], ent["end"], ent["label"])
            if key not in seen:
                entidades_unicas.append(ent)
                seen.add(key)

        return {
            "text": texto,
            "ents": entidades_unicas,
            "metadata": {
                "pdf_original":   pdf_nombre,
                "fecha_anotacion": datetime.now().isoformat(),
                "metodo":         "automatico_regex",
                "estado":         "requiere_revision_manual",
                "num_entidades":  len(entidades_unicas),
            },
        }


# ═══════════════════════════════════════ PROCESADOR PRINCIPAL ═══════════════════════════════════════

class ProcesadorAnotaciones:
    """Orquestador principal del proceso de anotaciones"""

    def __init__(self):
        self.generador = GeneradorAnotaciones()
        self.resultados_por_tipo: Dict[str, Dict] = {
            tipo: {"exitosos": 0, "con_error": 0, "total": 0, "total_entidades": 0}
            for tipo in ConfigPaths.TIPOS_DOC
        }

    def ProcesarTipo(self, tipo_doc: str) -> bool:
        """
        Procesa anotaciones para un tipo de documento.

        Args:
            tipo_doc: Tipo de documento (Artes, especificaciones, formulas)

        Returns:
            True si procesó al menos un archivo exitosamente
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ANOTANDO: {tipo_doc}")
        logger.info(f"{'='*60}")

        input_dir  = ConfigPaths.TIPOS_DOC[tipo_doc]
        output_dir = ConfigPaths.ANOTACIONES_PATHS[tipo_doc]

        if not input_dir.exists():
            logger.warning(f"✗ Directorio no existe: {input_dir}")
            return False

        txt_files = sorted(input_dir.glob("*.txt"))
        if not txt_files:
            logger.warning(f"✗ No se encontraron archivos .txt en {input_dir}")
            return False

        cantidad = min(ConfigPaths.CANTIDAD_A_ANOTAR, len(txt_files))
        logger.info(f"Procesando {cantidad} de {len(txt_files)} archivos .txt")

        for i, txt_file in enumerate(txt_files[:cantidad], 1):
            try:
                texto     = txt_file.read_text(encoding="utf-8")
                anotacion = self.generador.GenerarAnotacion(txt_file.name, texto)

                json_output = output_dir / f"{txt_file.stem}_anno.json"
                json_output.write_text(
                    json.dumps(anotacion, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                num_ents = len(anotacion["ents"])
                logger.info(f"  [{i}/{cantidad}] {txt_file.name} → {num_ents} entidades")

                self.resultados_por_tipo[tipo_doc]["exitosos"]        += 1
                self.resultados_por_tipo[tipo_doc]["total_entidades"] += num_ents

            except Exception as e:
                logger.error(f"  [{i}/{cantidad}] Error en {txt_file.name}: {e}")
                self.resultados_por_tipo[tipo_doc]["con_error"] += 1

            self.resultados_por_tipo[tipo_doc]["total"] += 1

        return self.resultados_por_tipo[tipo_doc]["exitosos"] > 0

    def Ejecutar(self) -> bool:
        """
        Ejecuta la generación de anotaciones para las tres carpetas.

        Returns:
            True si al menos un tipo fue procesado exitosamente
        """
        logger.info("\n" + "="*60)
        logger.info("SCRIPT 02: GENERAR ANOTACIONES JSON AUTOMÁTICAS")
        logger.info("="*60)
        logger.info(f"Fuentes: {[str(p) for p in ConfigPaths.TIPOS_DOC.values()]}")

        resultados = [self.ProcesarTipo(tipo) for tipo in self.resultados_por_tipo]

        self._MostrarResumenFinal()
        return any(resultados)

    def _MostrarResumenFinal(self):
        """Muestra resumen final usando conteos acumulados en memoria"""
        logger.info(f"\n{'='*60}")
        logger.info("RESUMEN FINAL")
        logger.info(f"{'='*60}")

        total_exitosos = 0
        total_errores  = 0

        for tipo_doc, datos in self.resultados_por_tipo.items():
            exitosos   = datos["exitosos"]
            errores    = datos["con_error"]
            total      = datos["total"]
            total_ents = datos["total_entidades"]
            promedio   = total_ents / exitosos if exitosos > 0 else 0.0

            logger.info(f"\n{tipo_doc}:")
            logger.info(f"  ✓ Exitosos:            {exitosos}")
            logger.info(f"  ✗ Con error:           {errores}")
            logger.info(f"  Total procesados:      {total}")
            logger.info(f"  Entidades detectadas:  {total_ents} (promedio: {promedio:.1f})")
            logger.info(f"  Ubicación:             {ConfigPaths.ANOTACIONES_PATHS[tipo_doc]}")

            total_exitosos += exitosos
            total_errores  += errores

        logger.info(f"\n{'='*60}")
        logger.info("TOTALES:")
        logger.info(f"  ✓ Exitosos:        {total_exitosos}")
        logger.info(f"  ✗ Con error:       {total_errores}")
        logger.info(f"  TOTAL ANOTACIONES: {total_exitosos}")
        logger.info(f"{'='*60}")

        rutas = list(ConfigPaths.ANOTACIONES_PATHS.items())
        for i, (_, path) in enumerate(rutas):
            sep = "└─" if i == len(rutas) - 1 else "├─"
            logger.info(f"  {sep} {path}")

        logger.info("\nPróximo paso: Revisar anotaciones manualmente")
        logger.info("Luego ejecuta: python core/03_train_ner_model.py")


# ═══════════════════════════════════════ MAIN ═══════════════════════════════════════

if __name__ == "__main__":
    procesador = ProcesadorAnotaciones()
    success = procesador.Ejecutar()
    sys.exit(0 if success else 1)
