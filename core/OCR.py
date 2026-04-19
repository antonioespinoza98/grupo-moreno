# scripts/01_descarga_y_ocr.py
# PASO 1-3: Descargar PDFs de MinIO (grupo-moreno/data/*) → OCR → Metadatos
# Refactorizado con PascalCase, .env y estructura de carpetas

"""
Ejecuta:
    python scripts/01_descarga_y_ocr.py

Requiere:
    - config/.env configurado con credenciales MinIO
    - Tesseract OCR instalado en el sistema
    - Bucket MinIO: grupo-moreno
    - Estructura MinIO: grupo-moreno/data/Artes/, grupo-moreno/data/Especificaciones/, grupo-moreno/data/formulas/

Output:
    - data/extracted/Artes/         (PDFs extraídos de Artes)
    - data/extracted/Especificaciones/ (PDFs extraídos de Especificaciones)
    - data/extracted/formulas/      (PDFs extraídos de formulas)
    - Cada carpeta contiene .txt y .json
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List
from dotenv import load_dotenv

# Librerías de PDF y OCR
from minio import Minio
from minio.error import S3Error
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import cv2
import numpy as np

# Cargar variables de entorno
load_dotenv(Path(__file__).parent.parent / ".env")

# ═══════════════════════════════════════ CONFIGURACIÓN ═══════════════════════════════════════

class ConfigMinIO:
    """Configuración de conexión a MinIO desde .env"""
    ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    BUCKET = os.getenv("MINIO_BUCKET", "grupo-moreno")
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
    
    # Estructura de carpetas en MinIO
    CARPETAS_MINIO = ["data/Artes", "data/Especificaciones", "data/formulas"]


class ConfigPaths:
    """Configuración de rutas desde .env"""
    BASE_EXTRACTED = Path(os.getenv("EXTRACTED_OUTPUT_DIR", "data/extracted"))
    TEMP_DIR = Path("data/temp_pdfs")
    LOGS_DIR = Path("logs")
    
    # Subcarpetas por tipo de documento
    SUBCARPETAS = {
        "Artes": BASE_EXTRACTED / "Artes",
        "Especificaciones": BASE_EXTRACTED / "especificaciones",
        "formulas": BASE_EXTRACTED / "formulas"
    }
    
    @classmethod
    def CreateDirectories(cls):
        """Crea todos los directorios necesarios"""
        cls.BASE_EXTRACTED.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Crear subcarpetas por tipo
        for subcarpeta in cls.SUBCARPETAS.values():
            subcarpeta.mkdir(parents=True, exist_ok=True)


# Setup logging
ConfigPaths.CreateDirectories()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ConfigPaths.LOGS_DIR / 'ocr.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════ CLASES PRINCIPALES ═══════════════════════════════════════

class MinIOClient:
    """Maneja conexión y descargas desde MinIO"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        """Inicializa cliente MinIO"""
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = None
    
    def Connect(self) -> bool:
        """
        Conecta a MinIO y valida la conexión
        
        Returns:
            True si la conexión fue exitosa
        """
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            
            # Validar conexión
            buckets = self.client.list_buckets()
            bucket_names = [b.name for b in buckets]
            logger.info(f"✓ Conectado a MinIO en {self.endpoint}")
            logger.info(f"  Buckets disponibles: {bucket_names}")
            return True
        
        except S3Error as e:
            logger.error(f"✗ Error conectando a MinIO: {e}")
            return False
    
    def DescargarPDFsPorCarpeta(self, bucket: str, carpeta_minio: str) -> Dict[str, str]:
        """
        Descarga todos los PDFs de una carpeta específica en MinIO
        
        Args:
            bucket: Nombre del bucket
            carpeta_minio: Ruta de carpeta en MinIO (ej: "data/Artes")
            
        Returns:
            Dict con {nombre_pdf: ruta_local}
        """
        if not self.client:
            logger.error("✗ Cliente MinIO no conectado. Ejecuta Connect() primero.")
            return {}
        
        pdfs = {}
        try:
            objects = self.client.list_objects(bucket, prefix=carpeta_minio, recursive=True)
            
            for obj in objects:
                if obj.object_name.lower().endswith('.pdf'):
                    # Crear ruta local preservando estructura
                    # Ejemplo: data/Artes/pdf_001.pdf → data/temp_pdfs/Artes/pdf_001.pdf
                    ruta_relativa = obj.object_name.replace(f"{carpeta_minio}/", "")
                    tipo_doc = Path(carpeta_minio).name
                    
                    local_path = ConfigPaths.TEMP_DIR / tipo_doc / ruta_relativa
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Descargar
                    self.client.fget_object(bucket, obj.object_name, str(local_path))
                    pdfs[ruta_relativa] = str(local_path)
            
            return pdfs
        
        except Exception as e:
            logger.error(f"✗ Error descargando PDFs de {carpeta_minio}: {e}")
            return {}


class OCRProcessor:
    """Procesa PDFs con OCR (extracción digital + Tesseract)"""
    
    @staticmethod
    def PreprocessImageForOCR(image: Image.Image) -> Image.Image:
        """
        Pre-procesa imagen para mejorar OCR
        
        Args:
            image: Imagen PIL
            
        Returns:
            Imagen procesada
        """
        # Convertir PIL a numpy para OpenCV
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Aumentar resolución
        scale_percent = 200
        width = int(cv_image.shape[1] * scale_percent / 100)
        height = int(cv_image.shape[0] * scale_percent / 100)
        cv_image = cv2.resize(cv_image, (width, height), interpolation=cv2.INTER_CUBIC)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar threshold para limpiar
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Convertir de vuelta a PIL
        return Image.fromarray(thresh)
    
    @staticmethod
    def ExtraerTextoDigital(pdf_path: str) -> Tuple[str, bool]:
        """
        Intenta extracción digital de PDF
        
        Args:
            pdf_path: Ruta del PDF
            
        Returns:
            (texto_extraido, es_suficiente)
        """
        try:
            reader = PdfReader(pdf_path)
            texto = ""
            
            for page_num, page in enumerate(reader.pages):
                texto += f"\n--- PÁGINA {page_num + 1} ---\n"
                texto += page.extract_text() or ""
            
            # Verificar si texto digital es suficiente (>100 caracteres)
            if len(texto.strip()) > 100:
                return texto, True
            else:
                return "", False
        
        except Exception as e:
            logger.debug(f"Extracción digital falló: {e}")
            return "", False
    
    @staticmethod
    def ExtraerTextoConOCR(pdf_path: str) -> str:
        """
        Extrae texto usando OCR (Tesseract)
        
        Args:
            pdf_path: Ruta del PDF
            
        Returns:
            Texto extraído
        """
        try:
            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path, dpi=300)
            texto = ""
            
            for page_num, image in enumerate(images):
                # Pre-procesar imagen
                processed_image = OCRProcessor.PreprocessImageForOCR(image)
                
                # OCR con configuración avanzada
                custom_config = r'--oem 3 --psm 6 -l spa'
                page_text = pytesseract.image_to_string(processed_image, config=custom_config)
                
                texto += f"\n--- PÁGINA {page_num + 1} (OCR) ---\n"
                texto += page_text
            
            return texto
        
        except Exception as e:
            error_msg = str(e)
            if "spa.traineddata" in error_msg or "Failed loading language" in error_msg:
                logger.error(
                    f"OCR falló: paquete de idioma español no instalado. "
                    f"Solución: sudo apt install tesseract-ocr-spa"
                )
            else:
                logger.error(f"OCR falló: {e}")
            return ""
    
    @staticmethod
    def ExtraerTexto(pdf_path: str) -> Tuple[str, str]:
        """
        Extrae texto de PDF intentando primero digital, luego OCR
        
        Args:
            pdf_path: Ruta del PDF
            
        Returns:
            (texto, metodo: 'digital', 'ocr', o 'error')
        """
        # Intento 1: Extracción digital
        texto_digital, es_suficiente = OCRProcessor.ExtraerTextoDigital(pdf_path)
        
        if es_suficiente:
            return texto_digital, "digital"
        
        # Intento 2: OCR si digital fue insuficiente
        logger.debug(f"  → Extracción digital insuficiente, usando OCR...")
        texto_ocr = OCRProcessor.ExtraerTextoConOCR(pdf_path)
        
        if texto_ocr and len(texto_ocr.strip()) > 50:
            return texto_ocr, "ocr"
        
        # Error
        return "", "error"


class MetadataGenerator:
    """Genera metadatos JSON para cada PDF"""
    
    @staticmethod
    def Generar(pdf_nombre: str, texto: str, metodo_extraccion: str, tipo_doc: str) -> Dict:
        """
        Genera metadatos JSON para un PDF
        
        Args:
            pdf_nombre: Nombre del PDF
            texto: Contenido extraído
            metodo_extraccion: 'digital' u 'ocr'
            tipo_doc: Tipo de documento (Artes, Especificaciones, formulas)
            
        Returns:
            Dict con metadatos
        """
        return {
            "pdf_nombre": pdf_nombre,
            "tipo_documento": tipo_doc,
            "metodo_extraccion": metodo_extraccion,
            "longitud_caracteres": len(texto),
            "numero_lineas": len(texto.split('\n')),
            "fecha_procesamiento": datetime.now().isoformat(),
            "timestamp": datetime.now().timestamp(),
            "estado": "exitoso" if len(texto) > 50 else "error_ocr"
        }


class ProcessadorPrincipal:
    """Orquestador principal del proceso OCR"""
    
    def __init__(self):
        """Inicializa el procesador"""
        self.minio_client = MinIOClient(
            endpoint=ConfigMinIO.ENDPOINT,
            access_key=ConfigMinIO.ACCESS_KEY,
            secret_key=ConfigMinIO.SECRET_KEY,
            secure=ConfigMinIO.SECURE
        )
        self.resultados_por_tipo = {
            "Artes": {"exitosos": 0, "con_error": 0, "detalles": []},
            "Especificaciones": {"exitosos": 0, "con_error": 0, "detalles": []},
            "formulas": {"exitosos": 0, "con_error": 0, "detalles": []}
        }
    
    def ProcesarCarpeta(self, tipo_doc: str) -> bool:
        """
        Procesa una carpeta específica (Artes, Especificaciones, formulas)
        
        Args:
            tipo_doc: Tipo de documento
            
        Returns:
            True si fue exitoso
        """
        carpeta_minio = f"data/{tipo_doc}"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESANDO: {tipo_doc}")
        logger.info(f"{'='*60}")
        
        # Descargar PDFs de esta carpeta
        pdfs = self.minio_client.DescargarPDFsPorCarpeta(ConfigMinIO.BUCKET, carpeta_minio)
        
        if not pdfs:
            logger.warning(f"✗ No se descargaron PDFs de {carpeta_minio}")
            return False
        
        logger.info(f"✓ {len(pdfs)} PDFs descargados de {tipo_doc}")
        
        # Procesar cada PDF
        output_dir = ConfigPaths.SUBCARPETAS[tipo_doc]
        
        for i, (pdf_nombre, pdf_path) in enumerate(pdfs.items(), 1):
            try:
                # Extracción de texto
                texto, metodo = OCRProcessor.ExtraerTexto(pdf_path)
                
                if not texto:
                    logger.warning(f"  [{i}/{len(pdfs)}] ✗ {pdf_nombre} - Falló extraer texto")
                    self.resultados_por_tipo[tipo_doc]["con_error"] += 1
                    continue
                
                # Generar metadata
                metadata = MetadataGenerator.Generar(pdf_nombre, texto, metodo, tipo_doc)
                
                # Guardar texto extraído
                output_txt = output_dir / f"{Path(pdf_nombre).stem}.txt"
                with open(output_txt, "w", encoding="utf-8") as f:
                    f.write(texto)
                
                # Guardar metadata
                output_json = output_dir / f"{Path(pdf_nombre).stem}.json"
                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"  [{i}/{len(pdfs)}] ✓ {pdf_nombre} - {len(texto)} caracteres ({metodo})")
                
                self.resultados_por_tipo[tipo_doc]["exitosos"] += 1
                self.resultados_por_tipo[tipo_doc]["detalles"].append({
                    "pdf": pdf_nombre,
                    "caracteres": len(texto),
                    "metodo": metodo
                })
            
            except Exception as e:
                logger.error(f"  [{i}/{len(pdfs)}] ✗ {pdf_nombre} - Error: {e}")
                self.resultados_por_tipo[tipo_doc]["con_error"] += 1
        
        return True
    
    def Ejecutar(self) -> bool:
        """
        Ejecuta el flujo completo: descargar → OCR → metadatos
        Procesa las tres carpetas en orden
        
        Returns:
            True si fue exitoso
        """
        logger.info("\n" + "="*60)
        logger.info("INICIANDO PROCESO: MinIO grupo-moreno → OCR → Metadatos")
        logger.info(f"Bucket: {ConfigMinIO.BUCKET}")
        logger.info(f"Carpetas a procesar: {ConfigMinIO.CARPETAS_MINIO}")
        logger.info("="*60)
        
        # PASO 1: Conectar a MinIO
        if not self.minio_client.Connect():
            logger.error("✗ No se pudo conectar a MinIO")
            return False
        
        # PASO 2: Procesar cada carpeta
        for tipo_doc in ["Artes", "Especificaciones", "formulas"]:
            self.ProcesarCarpeta(tipo_doc)
        
        # PASO 3: Mostrar resumen final
        self.MostrarResumenFinal()
        
        return True
    
    def MostrarResumenFinal(self):
        """Muestra resumen final del procesamiento"""
        logger.info(f"\n{'='*60}")
        logger.info("RESUMEN FINAL")
        logger.info(f"{'='*60}")
        
        total_exitosos = 0
        total_errores = 0
        
        for tipo_doc in ["Artes", "Especificaciones", "formulas"]:
            datos = self.resultados_por_tipo[tipo_doc]
            exitosos = datos["exitosos"]
            errores = datos["con_error"]
            total = exitosos + errores
            
            logger.info(f"\n{tipo_doc}:")
            logger.info(f"  ✓ Exitosos: {exitosos}")
            logger.info(f"  ✗ Con error: {errores}")
            logger.info(f"  Total: {total}")
            
            total_exitosos += exitosos
            total_errores += errores
            
            # Guardar resumen por tipo
            resumen_path = ConfigPaths.SUBCARPETAS[tipo_doc] / "resumen.json"
            with open(resumen_path, "w", encoding="utf-8") as f:
                json.dump({
                    "tipo_documento": tipo_doc,
                    "total": total,
                    "exitosos": exitosos,
                    "con_error": errores,
                    "detalles": datos["detalles"],
                    "fecha_ejecucion": datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n{'='*60}")
        logger.info("TOTALES:")
        logger.info(f"✓ Exitosos: {total_exitosos}")
        logger.info(f"✗ Con error: {total_errores}")
        logger.info(f"TOTAL PROCESADOS: {total_exitosos + total_errores}")
        logger.info(f"{'='*60}")
        
        # Guardar resumen global
        resumen_global_path = ConfigPaths.BASE_EXTRACTED / "RESUMEN_GLOBAL.json"
        with open(resumen_global_path, "w", encoding="utf-8") as f:
            json.dump({
                "fecha_ejecucion": datetime.now().isoformat(),
                "total_exitosos": total_exitosos,
                "total_errores": total_errores,
                "total_procesados": total_exitosos + total_errores,
                "por_tipo": self.resultados_por_tipo
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✓ Resumen global guardado en: {resumen_global_path}")
        logger.info(f"✓ Textos extraídos en: {ConfigPaths.BASE_EXTRACTED}")
        logger.info(f"  ├─ Artes/")
        logger.info(f"  ├─ Especificaciones/")
        logger.info(f"  └─ formulas/")


# ═══════════════════════════════════════ MAIN ═══════════════════════════════════════

if __name__ == "__main__":
    procesador = ProcessadorPrincipal()
    success = procesador.Ejecutar()
    exit(0 if success else 1)