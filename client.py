# client.py
"""
Консольный клиент:
  listen                   — подписаться на WebSocket
  send <file> <algo>       — отправить изображение (алгоритмы: )
  exit
"""
import asyncio, json, requests, websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwidXNlcm5hbWUiOiJ1c2VyMSJ9.UCnUMyR7mOEkb7x2QYY4CBe9Y0zk12yiercNnyEDRVs"

async def listen_ws():
    uri = f"ws://localhost:8000/ws?token={TOKEN}"
    async with websockets.connect(uri) as ws:
        print("🟢  Websocket подключён! Жду сообщений…")
        while True:
            print("WS:", await ws.recv())

def upload_image(path: str, algo: str):
    with open(path, "rb") as f:
        files = {"file": (path, f, "application/octet-stream")}
        data  = {"algorithm": algo}
        headers = {"Authorization": f"Bearer {TOKEN}"}
        resp = requests.post("http://localhost:8000/binarize/",
                             files=files, data=data, headers=headers, timeout=30)
        print("POST /binarize →", resp.json())

def main():
    print("            ---------------------------------            ")
    print("            Команды: listen | send <file> <algo> | exit")
    print("Доступные алгоритмы: otsu, adaptive, custom")
    print("            ---------------------------------            ")
    while True:
        cmd = input(">>> ").strip()
        if cmd == "listen":
            asyncio.run(listen_ws())
        elif cmd.startswith("send "):
            _, file, algo = cmd.split(maxsplit=2)
            upload_image(file, algo)
        elif cmd == "exit":
            break
        else:
            print("listen | send <file> <algo> | exit")

if __name__ == "__main__":
    main()