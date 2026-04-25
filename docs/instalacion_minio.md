# Instalación de MinIO en Ubuntu

MinIO es un servidor de almacenamiento de objetos compatible con la API de Amazon S3. Este proyecto lo usa como almacenamiento local para los 122 PDFs de Grupo Moreno.

---

## Tabla de Contenidos

1. [Requisitos Previos](#1-requisitos-previos)
2. [Instalar el Servidor MinIO](#2-instalar-el-servidor-minio)
3. [Configurar MinIO como Servicio del Sistema](#3-configurar-minio-como-servicio-del-sistema)
4. [Iniciar y Verificar el Servicio](#4-iniciar-y-verificar-el-servicio)
5. [Instalar el Cliente MinIO (mc)](#5-instalar-el-cliente-minio-mc)
6. [Crear el Bucket del Proyecto](#6-crear-el-bucket-del-proyecto)
7. [Subir los PDFs al Bucket](#7-subir-los-pdfs-al-bucket)
8. [Acceder a la Consola Web](#8-acceder-a-la-consola-web)
9. [Acceso Remoto desde Windows](#9-acceso-remoto-desde-windows)
10. [Comandos de Operación Diaria](#10-comandos-de-operación-diaria)
11. [Solución de Problemas](#11-solución-de-problemas)

---

## 1. Requisitos Previos

- Ubuntu 20.04 o 22.04 (incluido WSL2)
- Al menos 1 GB de RAM libre
- Al menos 5 GB de espacio en disco para los PDFs
- Acceso `sudo`

Verificar recursos disponibles:

```bash
free -h         # RAM disponible
df -h ~         # Espacio en disco
```

---

## 2. Instalar el Servidor MinIO

### Descargar el binario

```bash
# Descargar la versión estable para Linux (amd64)
wget https://dl.min.io/server/minio/release/linux-amd64/minio

# Dar permisos de ejecución
chmod +x minio

# Mover al directorio de binarios del sistema
sudo mv minio /usr/local/bin/

# Verificar la instalación
minio --version
```

### Crear usuario y directorio de datos

```bash
# Crear usuario del sistema dedicado para MinIO (sin shell de login)
sudo useradd -r -s /sbin/nologin minio-user

# Crear directorio donde se almacenarán los datos
sudo mkdir -p /data/minio

# Asignar permisos al usuario de MinIO
sudo chown -R minio-user:minio-user /data/minio
```

### Crear archivo de configuración

```bash
sudo nano /etc/default/minio
```

Contenido del archivo:

```bash
# Directorio de almacenamiento de datos
MINIO_VOLUMES="/data/minio"

# Opciones del servidor (puerto API y consola web)
MINIO_OPTS="--address :9000 --console-address :9001"

# Credenciales de acceso (cambiar por valores seguros)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
```

> **Seguridad:** Cambiar `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD` por valores únicos y seguros. La contraseña debe tener al menos 8 caracteres.

---

## 3. Configurar MinIO como Servicio del Sistema

Configurar MinIO como un servicio `systemd` para que inicie automáticamente y se pueda gestionar con `systemctl`.

```bash
sudo nano /etc/systemd/system/minio.service
```

Contenido del archivo:

```ini
[Unit]
Description=MinIO Object Storage
Documentation=https://min.io/docs/minio/linux/index.html
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/data/minio
User=minio-user
Group=minio-user
EnvironmentFile=/etc/default/minio
ExecStartPre=/bin/bash -c "if [ -z \"${MINIO_VOLUMES}\" ]; then echo \"Variable MINIO_VOLUMES no definida\"; exit 1; fi"
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES
Restart=always
RestartSec=5
LimitNOFILE=65536
TasksMax=infinity
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
```

Recargar `systemd` y habilitar el servicio:

```bash
# Recargar la configuración de systemd
sudo systemctl daemon-reload

# Habilitar MinIO para que inicie al arrancar el sistema
sudo systemctl enable minio
```

> **Nota para WSL2:** `systemd` no está activo por defecto en WSL2. Ver la sección [Iniciar MinIO en WSL2](#iniciar-minio-en-wsl2) más abajo.

---

## 4. Iniciar y Verificar el Servicio

### En Ubuntu nativo (o WSL2 con systemd habilitado)

```bash
# Iniciar el servicio
sudo systemctl start minio

# Ver el estado
sudo systemctl status minio

# Ver los logs en tiempo real
sudo journalctl -u minio -f
```

La salida esperada de `status` es:

```
● minio.service - MinIO Object Storage
     Loaded: loaded (/etc/systemd/system/minio.service; enabled)
     Active: active (running) since ...
```

### Iniciar MinIO en WSL2

WSL2 no usa `systemd` por defecto. Hay dos opciones:

**Opción A — Habilitar systemd en WSL2 (Ubuntu 22.04+):**

```bash
# Editar la configuración de WSL
sudo nano /etc/wsl.conf
```

Agregar:
```ini
[boot]
systemd=true
```

Luego reiniciar WSL desde PowerShell:
```powershell
wsl --shutdown
wsl
```

Ahora se puede usar `systemctl` normalmente.

**Opción B — Iniciar MinIO manualmente (sin systemd):**

```bash
# Cargar las variables del archivo de configuración
source /etc/default/minio

# Iniciar MinIO en segundo plano
minio server $MINIO_OPTS $MINIO_VOLUMES &> ~/minio.log &

echo "MinIO iniciado. Logs en ~/minio.log"
```

Para detenerlo:
```bash
pkill minio
```

### Verificar que MinIO responde

```bash
# Verificar el endpoint de salud de la API
curl http://localhost:9000/minio/health/live
# Respuesta esperada: HTTP 200 (sin cuerpo)

# Verificar endpoint de disponibilidad
curl http://localhost:9000/minio/health/ready
```

---

## 5. Instalar el Cliente MinIO (mc)

`mc` es la herramienta de línea de comandos para administrar MinIO: crear buckets, subir archivos, listar objetos, etc.

```bash
# Descargar el cliente
wget https://dl.min.io/client/mc/release/linux-amd64/mc

# Dar permisos de ejecución
chmod +x mc

# Mover al PATH del sistema
sudo mv mc /usr/local/bin/

# Verificar instalación
mc --version
```

### Configurar el alias del servidor local

```bash
# Agregar el servidor local como alias "local"
# Reemplazar las credenciales con las definidas en /etc/default/minio
mc alias set local http://localhost:9000 minioadmin minioadmin123

# Verificar la conexión
mc admin info local
```

La salida debe mostrar información del servidor:
```
●  localhost:9000
   Uptime: 2 minutes
   Version: RELEASE.20XX-XX-XXTXX-XX-XXZ
   ...
```

---

## 6. Crear el Bucket del Proyecto

El proyecto espera un bucket llamado `grupo-moreno` con la siguiente estructura de carpetas:

```
grupo-moreno/
├── data/
│   ├── Artes/           (47 PDFs de artes/etiquetas)
│   ├── Especificaciones/ (37 PDFs de fichas técnicas)
│   └── formulas/        (38 PDFs de formulaciones)
```

```bash
# Crear el bucket principal
mc mb local/grupo-moreno

# Verificar que se creó
mc ls local/
```

---

## 7. Subir los PDFs al Bucket

Una vez creado el bucket, subir los PDFs al servidor MinIO desde las carpetas locales.

### Subir desde directorios locales

```bash
# Subir todos los PDFs de Artes
mc cp --recursive /ruta/local/Artes/ local/grupo-moreno/data/Artes/

# Subir todos los PDFs de Especificaciones
mc cp --recursive /ruta/local/Especificaciones/ local/grupo-moreno/data/Especificaciones/

# Subir todos los PDFs de Formulas
mc cp --recursive /ruta/local/formulas/ local/grupo-moreno/data/formulas/
```

### Usar mirror para sincronizar (recomendado)

`mirror` sincroniza un directorio local con MinIO: solo sube los archivos nuevos o modificados.

```bash
mc mirror /ruta/local/pdfs/ local/grupo-moreno/data/
```

### Verificar los archivos subidos

```bash
# Listar todo el contenido del bucket
mc ls --recursive local/grupo-moreno/

# Contar archivos por carpeta
mc ls local/grupo-moreno/data/Artes/ | wc -l
mc ls local/grupo-moreno/data/Especificaciones/ | wc -l
mc ls local/grupo-moreno/data/formulas/ | wc -l
```

---

## 8. Acceder a la Consola Web

MinIO incluye una interfaz web para administrar el almacenamiento visualmente.

Abrir en el navegador:
```
http://localhost:9001
```

Ingresar con las credenciales definidas en `/etc/default/minio`:
- **Usuario:** `minioadmin`
- **Contraseña:** `minioadmin123`

Desde la consola web se puede:
- Crear y eliminar buckets
- Explorar y descargar archivos
- Gestionar políticas de acceso
- Ver métricas del servidor

---

## 9. Acceso Remoto desde Windows

Si MinIO corre en Ubuntu/WSL2 y se necesita acceder desde Windows o desde otro equipo:

### Acceso desde Windows al WSL2

WSL2 expone automáticamente el puerto 9000 en `localhost` de Windows. Acceder directamente desde el navegador de Windows:

```
http://localhost:9000     (API)
http://localhost:9001     (Consola Web)
```

### Acceso desde Otro Dispositivo en la Red

**Paso 1:** Obtener la IP de WSL2:
```bash
# En Ubuntu/WSL2
hostname -I | awk '{print $1}'
# Ejemplo: 172.22.134.45
```

**Paso 2:** Iniciar MinIO vinculado a todas las interfaces (si no usa systemd):
```bash
minio server --address 0.0.0.0:9000 --console-address 0.0.0.0:9001 /data/minio &
```

O editar `/etc/default/minio` para usar `0.0.0.0`:
```bash
MINIO_OPTS="--address 0.0.0.0:9000 --console-address 0.0.0.0:9001"
```

**Paso 3:** Crear reglas de reenvío de puertos en PowerShell (Windows, como Administrador):

```powershell
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]

# Puerto API (9000)
netsh interface portproxy add v4tov4 `
    listenport=9000 listenaddress=0.0.0.0 `
    connectport=9000 connectaddress=$wslIP

# Puerto Consola Web (9001)
netsh interface portproxy add v4tov4 `
    listenport=9001 listenaddress=0.0.0.0 `
    connectport=9001 connectaddress=$wslIP
```

**Paso 4:** Abrir puertos en el Firewall de Windows:

```powershell
New-NetFirewallRule -DisplayName "MinIO API" `
    -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "MinIO Console" `
    -Direction Inbound -LocalPort 9001 -Protocol TCP -Action Allow
```

**Paso 5:** Desde cualquier dispositivo en la misma red WiFi, acceder con la IP de Windows:
```
http://192.168.X.X:9000    (API)
http://192.168.X.X:9001    (Consola Web)
```

---

## 10. Comandos de Operación Diaria

### Gestión del Servicio

```bash
sudo systemctl start minio      # Iniciar
sudo systemctl stop minio       # Detener
sudo systemctl restart minio    # Reiniciar
sudo systemctl status minio     # Ver estado
sudo journalctl -u minio -f     # Ver logs en tiempo real
```

### Gestión de Buckets y Archivos con mc

```bash
# Listar buckets
mc ls local/

# Listar archivos en una carpeta
mc ls local/grupo-moreno/data/Artes/

# Subir un archivo
mc cp archivo.pdf local/grupo-moreno/data/Artes/

# Descargar un archivo
mc cp local/grupo-moreno/data/Artes/archivo.pdf ./

# Eliminar un archivo
mc rm local/grupo-moreno/data/Artes/archivo.pdf

# Ver tamaño total del bucket
mc du local/grupo-moreno/

# Ver información del servidor
mc admin info local/
```

### Actualizar Credenciales en el Proyecto

Si se cambian las credenciales de MinIO, actualizar el archivo `core/.env`:

```bash
nano core/.env
```

```dotenv
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=nuevo_usuario
MINIO_SECRET_KEY=nueva_contraseña
MINIO_BUCKET=grupo-moreno
MINIO_SECURE=False
```

---

## 11. Solución de Problemas

### MinIO No Inicia: Permiso Denegado en /data/minio

```bash
# Verificar permisos del directorio de datos
ls -la /data/

# Reasignar permisos
sudo chown -R minio-user:minio-user /data/minio
sudo chmod 755 /data/minio
```

### Error: Puerto 9000 Ya en Uso

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :9000

# Si hay otro proceso de MinIO corriendo
pkill minio

# Reiniciar el servicio
sudo systemctl restart minio
```

### mc: Error de Certificado SSL

Si se conectó con HTTPS por error:

```bash
# Re-crear el alias forzando HTTP
mc alias remove local
mc alias set local http://localhost:9000 minioadmin minioadmin123
```

### El Bucket No Aparece en el Proyecto

Verificar que el nombre del bucket en `.env` coincide exactamente (sensible a mayúsculas):

```bash
# Ver buckets disponibles
mc ls local/

# El nombre debe ser exactamente "grupo-moreno"
# Verificar en core/.env:
grep MINIO_BUCKET core/.env
```

### WSL2: MinIO Se Detiene al Cerrar la Terminal

En WSL2 sin systemd, los procesos en segundo plano se detienen al cerrar la terminal. Soluciones:

```bash
# Opción A: Usar nohup para que persista
nohup minio server --address :9000 --console-address :9001 /data/minio > ~/minio.log 2>&1 &
echo "PID: $!"

# Opción B: Habilitar systemd en WSL2 (ver sección 4)
```

---

*Documentación de instalación de MinIO — Pipeline NER Grupo Moreno*
