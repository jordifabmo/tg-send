# tg-send

`tg-send` es un script en Python diseñado para **enviar mensajes y archivos a Telegram mediante un bot**, con soporte para estados predefinidos, IP local, y configuraciones personalizadas. Es útil para monitoreo de sistemas, alertas de hardware, backups, y cualquier mensaje automatizado desde scripts o servicios.

---

## Características principales

- Envía mensajes a Telegram usando un **bot** y un `chat_id` configurables.

- Soporta **estados predefinidos** con íconos (`ok`, `error`, `warning`, etc.).

- Muestra automáticamente **hostname** y, opcionalmente, **IP local**.

- Configuración flexible desde archivo `.conf`.

- Compatible con **Linux** y **Windows**.

- Funciona tanto desde la carpeta de ejecución como desde rutas de instalación estándar.

- Sin dependencias externas: utiliza solo librerías estándar de Python (`urllib`, `argparse`, etc.).

- Sistema de logging integrado

## 📖 Instalación y configuración

### 1. Crear un bot de Telegram
- Busca a `@BotFather` en Telegram
- Usa el comando `/newbot` para crear un nuevo bot
- Guarda el **token** proporcionado

### 2. Obtener el CHAT_ID
- Envía un mensaje a tu bot
- Visita: `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Encuentra el `chat.id` en la respuesta JSON

### 3. Modificar el archivo de configuración
- Renombra `tg-send.conf.example` a `tg-send.conf`
- Añade el token y el chat.id

## Modo de uso

### Argumentos

| Opción | Argumento | Descripción |
|--------|-----------|-------------|
| `-m`, `--message` | **TEXTO** | **[REQUERIDO]** Mensaje a enviar |
| `-t`, `--title` | TEXTO | Título o nombre del servicio (CPU, Backup, etc.) |
| `-s`, `--status` | ESTADO | Estado: `ok`, `error`, `warning`, `fail`, `downloaded` |
| `-c`, `--chat_id` | CHAT_ID | Chat destino diferente al configurado |
| `-k`, `--token` | TOKEN | Token de bot diferente al configurado |
| `-f`, `--file` | ARCHIVO | Enviar archivo junto con el mensaje |
| `-i`, `--ip` | - | Incluir IP local en el mensaje |
| `-v`, `--verbose` | - | Activa el modo verboso para debug |
| `-h`, `--help` | - | Mostrar ayuda |

### Ejemplos de uso

```bash

# Enviar un mensaje simple
python3 tg-send.py -m "Este es un mensaje simple"

# Enviar un mensaje con título y estado
python3 tg-send.py -t "RAM" -s "warning" -m "Se está usando el 80% de la capacidad de la RAM"

# Enviar un mensaje mostrando la IP local
python3 tg-send.py -i -m "Mostrando la IP del servidor"

# Enviar un archivo con mensaje como caption
python3 tg-send.py -f "readme.md" -t "Backup" -s "ok" -m "Backup del readme realizado con éxito."

```
![img](https://raw.githubusercontent.com/jordifabmo/tg-send2/refs/heads/assets/example-tg-send.png)
