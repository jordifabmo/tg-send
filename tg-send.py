#!/usr/bin/env python3

import argparse                 # For command line arguments
import urllib.parse             # For request encoding
import urllib.request           # For making HTTP requests
import json                     # For parsing JSON responses
from datetime import datetime   # For timestamping messages
import socket                   # For getting the hostname
import sys                      # For exiting on error
import platform                 # For detecting OS
import subprocess               # For running system commands
import re                       # For regex operations
import os                       # For file path operations
import mimetypes                # For guessing MIME types
import http.client              # For sending multipart/form-data

CONFIG_PATHS = [
    "./tg-send.conf",               # mismo directorio de ejecución
    "/etc/tg-send.conf",            # ruta Linux estándar
    "C:\\ProgramData\\tg-send.conf"  # ruta Windows estándar
]

# STATES can be redefined in the config file
STATES_DEFAULT = {
    "default": "ℹ️ INFO",
    "ok": "✅ OK",
    "warning": "⚠️ WARNING",
    "error": "❌ ERROR",
    "fail": "🔥 FAIL",
    "critical": "🚨 CRITICAL",
    "downloaded": "⬇️ DOWNLOADED",
}

VERBOSE = False  # Global para errores fuera de funciones con verbose
#Argument parser setup
parser = argparse.ArgumentParser(description="Sends messages to Telegram through a bot.")

parser.add_argument("-m", "--message", required=True, help="[REQUIRED] Message to send")
parser.add_argument("-t", "--title", help="Title, service name or hardware component (CPU, Backup, sda1, smb...)")
parser.add_argument("-s", "--status", help="Status, must be one of: ok, error, warning, fail, downloaded")
parser.add_argument("-c", "--chat_id", help="If you will send the message to a different chat_id than the default one")
parser.add_argument("-k", "--token", help="If you will use a different bot token than the default one")
parser.add_argument("-i", "--ip", action="store_true", help="Show local IPv4 addresses")
parser.add_argument("-f", "--file", help="Send a file along with the message")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for debugging")

def find_config():
    '''
    Busca el archivo de configuración en las rutas conocidas.
    '''
    for path in CONFIG_PATHS:
        if os.path.isfile(path):
            return path
    print("Error: no se encontró archivo de configuración en ninguna ruta conocida.")
    sys.exit(1)

def load_config(config_file):
    '''
    Carga la configuración desde un archivo. El archivo debe definir TOKEN y CHAT_ID.
    '''
    config = {}
    try:
        with open(config_file, "r") as f:
            # Lee todo el contenido del archivo en una sola cadena. Esto me ha traído muchos problemas
            # Ha sido la manera más sencilla de manejar el JSON de múltiples líneas sin errores.
            content = f.read()

        # Encuentra y extrae el JSON de STATES de múltiples líneas usando regex
        # Se ha modificado el regex para manejar la indentación.
        # El JSON se maneja como una sola cadena para evitar problemas de parseo.
        states_match = re.search(r"STATES\s*=\s*'(.*?)'\s*(?=\n[A-Z_]+\s*=|$)".replace(' ', r'\s*'), content, re.DOTALL)
        if states_match:
            states_str = states_match.group(1).strip()
            # Elimina cualquier comentario al final de la cadena JSON
            states_str = re.sub(r'#.*', '', states_str, flags=re.DOTALL)
            try:
                config["STATES"] = json.loads(states_str)
            except json.JSONDecodeError as e:
                print(f"Error en JSON: {e}")
                config["STATES"] = STATES_DEFAULT
        else:
            config["STATES"] = STATES_DEFAULT

        # Ahora, parsea el resto de los pares clave-valor de una sola línea
        # separando por líneas
        for line in content.split('\n'):
            line = line.strip()
            # Ignora líneas vacías y comentarios
            if not line or line.startswith("#"):
                continue
            # Separar clave y valor
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if key != "STATES":  # Omite STATES ya que ya lo manejamos
                    value = value.split("#", 1)[0].strip()
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    config[key] = value

    except FileNotFoundError:
        print(f"Error: archivo de configuración '{config_file}' no encontrado.")
        sys.exit(1)

    # Valida la presencia de TOKEN y CHAT_ID
    if "TOKEN" not in config or "CHAT_ID" not in config or "LOG_FILE" not in config:
        print(f"Error: el archivo de configuración '{config_file}' debe definir TOKEN, CHAT_ID y LOG_FILE.")
        sys.exit(1)

    # If config TOKEN or CHAT_ID are empty, warn and exit
    if not config["TOKEN"] or not config["CHAT_ID"]:
        print(f"Error: el archivo de configuración '{config_file}' debe definir TOKEN y CHAT_ID no vacíos.")
        sys.exit(1)
        
    return config


def log_message(log_file, message, verbose=False):
    """
    Log the message to a local file for debugging purposes.
    """
    try:
        with open(log_file, "a") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")



def get_local_ip(logfile, verbose=False):
    '''
    Obtiene la dirección IP local de la máquina.
    '''
    ips = set()
    system = platform.system()

    try:
        if system == "Linux":
            # Linux: ip addr show
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/', line)
                    if ip_match:
                        ip = ip_match.group(1)
                        if not ip.startswith(('127.', '169.254.')):
                            ips.add(ip)

        elif system == "Windows":
            # Windows: ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'IPv4' in line:
                        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            if not ip.startswith('127.'):
                                ips.add(ip)

        # Fallback universal con socket
        if not ips:
            try:
                hostname = socket.gethostname()
                addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for info in addrinfo:
                    ip = info[4][0]
                    if not ip.startswith('127.'):
                        ips.add(ip)
            except:
                pass

        # Último recurso: IP de salida
        if not ips:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 53))
                    ips.add(s.getsockname()[0])
            except:
                log_message(logfile, "No se pudo obtener la IP de salida.")
                pass
        return ", ".join(sorted(ips)) if ips else "No disponible"

    except Exception as e:

        if verbose:
            print(f"[VERBOSE] get_local_ip: Error al obtener IP local: {e}")
        return f"No disponible ({str(e)})"


def build_message(logfile, message, title=None, status=None, show_ip=False, states=None, caption=False, verbose=False):
    """
    Builds the message to be sent to Telegram.
    """

    if not message:
        if verbose:
            print("[VERBOSE] Mensaje vacío, mostrando ayuda y saliendo.")
        parser.print_help()
        exit(1)

    # Get hostname and current timestamp
    hostname = socket.gethostname()

    if verbose:
        print(f"[VERBOSE] Hostname detectado: {hostname}")

    if caption:
        host_info = f"Host: {hostname}\n"
    else:
        host_info = f"*Host: {hostname}*\n"

    if show_ip:
        ip_address = get_local_ip(logfile, verbose)
        if verbose:
            print(f"[VERBOSE] IP local: {ip_address}")
        if caption:
            host_info += f"IP: {ip_address}\n"
        else:
            host_info += f"*IP: {ip_address}*\n"

    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M")

    # Generate message text
    text = ""

    if title:
        if caption:
            text += f"{title} "
        else:
            text += f"*[{title}]* "

    if status:
        # Usar el diccionario de estados que se pasa como parámetro
        state = states.get(status.lower(), states["default"])
        if caption:
            text += f"{state}"
        else:
            text += f"*{state}*"

    text += f"\n{host_info}"

    if message:
        text += message

    if caption:
        text += f"\n{timestamp}"
        log_message(logfile, f"Built caption: {text}", verbose)
    else:
        text += f"\n_{timestamp}_"
        log_message(logfile, f"Built message: {text}", verbose)

    if verbose:
        print(f"[VERBOSE] Mensaje construido:\n{text}")
    return text

def send_message(logfile, text, chat_id, token, verbose=False):
    '''
    Sends a message to the Telegram bot.
    '''
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    # Usamos urllib en vez de requests para evitar dependencias externas
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    try:
        if verbose:
            print(f"[VERBOSE] Enviando mensaje a chat_id={chat_id}")
        with urllib.request.urlopen(full_url) as response:
            data = response.read().decode("utf-8")
            print(f"Mensaje enviado")
            log_message(logfile, f"Mensaje enviado: {data}", verbose)
            return json.loads(data)
    except Exception as e:
        print(f"Error sending message: {e}")
        log_message(logfile, f"Error sending message: {e}", verbose)

        return 1

def send_file(logfile, file_path, caption=None, chat_id=None, token=None, verbose=False):

    if not os.path.isfile(file_path):
        print(f"Error: el archivo '{file_path}' no existe.")
        log_message(logfile, f"Error: el archivo '{file_path}' no existe.", verbose)

        return

    if verbose:
        print(f"[VERBOSE] Enviando archivo: {file_path} a chat_id={chat_id}")

    file_name = os.path.basename(file_path)
    chat_id = str(chat_id)
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    crlf = "\r\n"

    # Partes del multipart en bytes
    parts = []

    # chat_id
    parts.append(f"--{boundary}{crlf}Content-Disposition: form-data; name=\"chat_id\"{crlf}{crlf}{chat_id}{crlf}".encode("utf-8"))

    # caption
    if caption:
        parts.append(f"--{boundary}{crlf}Content-Disposition: form-data; name=\"caption\"{crlf}{crlf}{caption}{crlf}".encode("utf-8"))

    # archivo
    parts.append(f"--{boundary}{crlf}Content-Disposition: form-data; name=\"document\"; filename=\"{file_name}\"{crlf}Content-Type: {mime_type}{crlf}{crlf}".encode("utf-8"))

    with open(file_path, "rb") as f:
        parts.append(f.read() + crlf.encode("utf-8"))

    # cierre
    parts.append(f"--{boundary}--{crlf}".encode("utf-8"))

    body = b"".join(parts)

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }

    conn = http.client.HTTPSConnection("api.telegram.org")
    conn.request("POST", f"/bot{token}/sendDocument", body, headers)
    response = conn.getresponse()
    resp_data = response.read().decode("utf-8")
    conn.close()

    try:
        resp_json = json.loads(resp_data)
        print("Archivo enviado:", resp_json)
        log_message(logfile, f"Archivo enviado: {resp_json}", verbose)
        return resp_json
    except json.JSONDecodeError:
        print("Error: respuesta no válida de Telegram:", resp_data)
        log_message(logfile, f"Error: respuesta no válida de Telegram: {resp_data}", verbose)

        return resp_data



def main():
    # Parse arguments and load config
    args = parser.parse_args()
    config_file = find_config()
    if args.verbose:
        print(f"[VERBOSE] Usando archivo de configuración: {config_file}")
    config = load_config(config_file)

    log_file = config["LOG_FILE"] if "LOG_FILE" in config else "tg-send.log"
    if args.verbose:
        print(f"[VERBOSE] Log file: {log_file}")
    
    # Override config values with command line arguments if provided
    token = args.token or config["TOKEN"]
    chat_id = args.chat_id or config["CHAT_ID"]

    if args.file:
        send_file(log_file, args.file, build_message(log_file, args.message, args.title, args.status, args.ip, config["STATES"], caption=True, verbose=args.verbose), chat_id=chat_id, token=token, verbose=args.verbose)
        return
    else:
        # Build and send message
        text = build_message(log_file, args.message, args.title, args.status, args.ip, config["STATES"], caption=False, verbose=args.verbose)
        send_message(log_file, text, chat_id, token, verbose=args.verbose)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        parser.print_help()