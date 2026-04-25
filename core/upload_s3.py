# core/upload_s3.py
# PASO: Subir archivos JSON extraídos a un bucket de Amazon S3

"""
Ejecuta:
    python core/upload_s3.py

Requiere:
    - Credenciales AWS configuradas (~/.aws/credentials o variables de entorno)
    - boto3 instalado: pip install boto3
    - Archivos JSON generados por el pipeline OCR en data/extracted/

Configuración:
    - AWS_BUCKET_NAME: nombre del bucket S3 destino
    - Las credenciales se leen del ambiente o de ~/.aws/credentials

Output:
    - Sube todos los .json de data/extracted/{Artes,especificaciones,formulas}/
    - Excluye archivos llamados resumen.json
    - Preserva la estructura de carpetas como prefijo en S3
"""

import configparser
import logging
import boto3
from botocore.exceptions import ClientError
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Carpetas locales con archivos JSON a subir
CATEGORIAS = ["Artes", "especificaciones", "formulas"]

# Prefijo base dentro del bucket S3
S3_PREFIX = "data/extracted"

# Ruta al archivo de credenciales dentro del proyecto
_CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / ".aws" / "credentials.ini"


def _LoadCredentials() -> dict:
    """Lee las credenciales AWS desde .aws/credentials.ini del proyecto."""
    config = configparser.ConfigParser()
    config.read(_CREDENTIALS_FILE)
    profile = config["default"]
    return {
        "aws_access_key_id": profile["aws_access_key_id"],
        "aws_secret_access_key": profile["aws_secret_access_key"],
    }


def UploadFile(file_path: Path, bucket: str, object_name: str) -> bool:
    """Sube un archivo local a S3.

    :param file_path: Ruta local del archivo
    :param bucket: Nombre del bucket S3
    :param object_name: Clave (key) del objeto en S3
    :return: True si se subió correctamente, False en caso de error
    """
    s3_client = boto3.client("s3", **_LoadCredentials())
    try:
        s3_client.upload_file(str(file_path), bucket, object_name)
        logger.info("Subido: %s → s3://%s/%s", file_path.name, bucket, object_name)
        return True
    except ClientError as e:
        logger.error("Error al subir %s: %s", file_path.name, e)
        return False


def CollectJsonFiles(base_dir: Path) -> list[tuple[Path, str]]:
    """Recopila todos los JSON válidos con su clave S3 correspondiente.

    Excluye archivos llamados resumen.json (sin importar mayúsculas/minúsculas).

    :param base_dir: Directorio raíz de data/extracted/
    :return: Lista de tuplas (ruta_local, object_name_s3)
    """
    archivos = []
    for categoria in CATEGORIAS:
        carpeta = base_dir / categoria
        if not carpeta.exists():
            logger.warning("Carpeta no encontrada, se omite: %s", carpeta)
            continue

        for txt_file in sorted(carpeta.glob("*.txt")):
            if txt_file.name.lower() == "resumen.txt":
                logger.info("Omitido: %s", txt_file)
                continue

            object_name = f"{S3_PREFIX}/{categoria}/{txt_file.name}"
            archivos.append((txt_file, object_name))

    return archivos


def UploadAllJsonFiles(bucket: str, base_dir: Path | None = None) -> dict:
    """Orquesta la subida de todos los JSON al bucket S3.

    :param bucket: Nombre del bucket S3 destino
    :param base_dir: Directorio raíz de extracted (por defecto: data/extracted/ relativo al proyecto)
    :return: Resumen con conteos de éxito y error
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "data" / "extracted"

    archivos = CollectJsonFiles(base_dir)

    if not archivos:
        logger.warning("No se encontraron archivos JSON para subir.")
        return {"total": 0, "exitosos": 0, "errores": 0}

    exitosos = 0
    errores = 0

    for file_path, object_name in archivos:
        if UploadFile(file_path, bucket, object_name):
            exitosos += 1
        else:
            errores += 1

    resumen = {"total": len(archivos), "exitosos": exitosos, "errores": errores}
    logger.info(
        "Subida completada — total: %d, exitosos: %d, errores: %d",
        resumen["total"],
        resumen["exitosos"],
        resumen["errores"],
    )
    return resumen


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sube archivos JSON extraídos a un bucket de Amazon S3."
    )
    parser.add_argument("bucket", help="Nombre del bucket S3 destino")
    args = parser.parse_args()

    UploadAllJsonFiles(bucket=args.bucket)
