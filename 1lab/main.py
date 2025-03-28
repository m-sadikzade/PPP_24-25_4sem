import os
import sys
import json
import socket
import struct
import logging
from datetime import datetime

# ------------------ Настройки ------------------
HOST = '127.0.0.1'
PORT = 9090
PROGRAM_FILE = 'environment_info.json'
ENV_LOG_FILE = 'env_history.log'
SECRET_KEY = 123

# Лог в UTF-8
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'    
)


# ------------------ Функции ------------------
# Простое XOR-шифрование
def xor_data(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)

# Отправка "пакета": сначала 4 байта длины, потом зашифрованные данные
def send_packet(conn: socket.socket, data: bytes):
    encrypted = xor_data(data, SECRET_KEY)
    length_bytes = struct.pack('>I', len(encrypted))  # длина, big-endian
    conn.sendall(length_bytes + encrypted)

# Приём "пакета": 4 байта длины + данные
def recv_packet(conn: socket.socket) -> bytes:
    header = conn.recv(4)
    if len(header) < 4:
        return b''
    length = struct.unpack('>I', header)[0]
    chunks = []
    received = 0
    while received < length:
        chunk = conn.recv(length - received)
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
    encrypted = b''.join(chunks)
    return xor_data(encrypted, SECRET_KEY)

# Сканируем PATH для исполняемых файлов
def scan_path():
    path_env = os.environ.get("PATH", "")
    result = {"directories": []}
    for d in path_env.split(os.pathsep):
        d = d.strip()
        if not d or not os.path.isdir(d):
            continue
        exe_list = []
        try:
            for f in os.listdir(d):
                fpath = os.path.join(d, f)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    st = os.stat(fpath)
                    exe_list.append({
                        "name": f,
                        "size": st.st_size,
                        "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        except PermissionError:
            continue
        if exe_list:
            result["directories"].append({"path": d, "executables": exe_list})
    return result

# Сохранение в JSON
def save_info(info: dict):
    with open(PROGRAM_FILE, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

# Загрузка из JSON
def load_info():
    if not os.path.exists(PROGRAM_FILE):
        return {"directories": []}
    with open(PROGRAM_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Лог изменений переменных
def log_env_change(var: str, val: str):
    with open(ENV_LOG_FILE, 'a', encoding='utf-8') as f:
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{t} SET {var}={val}\n")

# Фильтрация по имени
def filter_by_name(info: dict, name_part: str):
    if not name_part:
        return info
    out = {"directories": []}
    for d in info["directories"]:
        filtered = [e for e in d["executables"] if name_part.lower() in e["name"].lower()]
        if filtered:
            out["directories"].append({"path": d["path"], "executables": filtered})
    return out

# Сортировка по имени
def sort_by_name(info: dict):
    for d in info["directories"]:
        d["executables"].sort(key=lambda x: x["name"].lower())
    return info

# ------------------ Сервер ------------------
def handle_client(conn: socket.socket, addr: tuple):
    logging.info(f"Подключен клиент: {addr}")
    # Отправим "CONNECTED"
    send_packet(conn, b"CONNECTED")

    try:
        while True:
            # Получаем команду
            packet = recv_packet(conn)
            if not packet:
                logging.info(f"Клиент отключился: {addr}")
                break
            cmd = packet.decode('utf-8', errors='replace').strip()
            if not cmd:
                continue
            logging.info(f"Команда от {addr}: {cmd}")

            # Обрабатываем команды
            if cmd.upper() == 'UPDATE':
                info = scan_path()
                save_info(info)
                # Читаем JSON-файл и отсылаем
                with open(PROGRAM_FILE, 'rb') as f:
                    data = f.read()
                send_packet(conn, data)

            elif cmd.startswith('SET '):
                parts = cmd.split(' ', 1)
                if len(parts) == 2 and '=' in parts[1]:
                    var, val = parts[1].split('=', 1)
                    var, val = var.strip(), val.strip()
                    os.environ[var] = val
                    logging.info(f"Установлена переменная: {var}={val}")
                    log_env_change(var, val)
                    msg = f"SUCCESS: SET {var}={val}"
                    send_packet(conn, msg.encode('utf-8'))
                else:
                    err = "ERROR: usage SET VAR=VALUE"
                    send_packet(conn, err.encode('utf-8'))

            elif cmd.startswith('FILTER name='):
                name_part = cmd.replace('FILTER name=', '').strip()
                info = load_info()
                filtered = filter_by_name(info, name_part)
                jdata = json.dumps(filtered, ensure_ascii=False, indent=2).encode('utf-8')
                send_packet(conn, jdata)

            elif cmd.startswith('SORT name'):
                info = load_info()
                sorted_info = sort_by_name(info)
                jdata = json.dumps(sorted_info, ensure_ascii=False, indent=2).encode('utf-8')
                send_packet(conn, jdata)

            else:
                err = f"ERROR: unknown command '{cmd}'"
                send_packet(conn, err.encode('utf-8'))

    except ConnectionError:
        logging.warning(f"Потеряно соединение: {addr}")
    finally:
        conn.close()
        logging.info(f"Соединение закрыто: {addr}")

def run_server():
    logging.info("Запуск сервера...")
    info = scan_path()
    save_info(info)
    logging.info("Информация о PATH сохранена.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        logging.info(f"Сервер слушает {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            handle_client(conn, addr)

# ------------------ Клиент ------------------
def run_client():
    print(f"Подключаемся к {HOST}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Клиент: подключение установлено.")

        # Принимаем приветственное сообщение
        packet = recv_packet(s)
        if packet:
            print("Сервер:", packet.decode('utf-8', errors='replace'))

        print("Команды:\n"
              "  UPDATE               - пересканировать PATH\n"
              "  SET VAR=VALUE        - установить переменную\n"
              "  FILTER name=python   - фильтр по имени\n"
              "  SORT name            - сортировка по имени\n"
              "  EXIT                 - выход\n")

        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd.upper() == 'EXIT':
                print("Клиент завершён.")
                break

            # Отправляем команду
            send_packet(s, cmd.encode('utf-8'))

            # Ожидаем ответ (JSON или строка)
            resp = recv_packet(s)
            if resp:
                # Пытаемся распарсить как JSON
                try:
                    js = json.loads(resp.decode('utf-8', errors='replace'))
                    # Если получилось — выводим JSON
                    print(json.dumps(js, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    # Иначе выводим как текст
                    print("Сервер:", resp.decode('utf-8', errors='replace'))

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 main.py [server|client]")
        sys.exit(1)
    mode = sys.argv[1].lower().strip()
    if mode == 'server':
        run_server()
    elif mode == 'client':
        run_client()
    else:
        print("Неизвестный режим. Используйте server или client.")
        sys.exit(1)

if __name__ == "__main__":
    main()
