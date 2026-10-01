import socket
import threading
import protocol as proto

HOST = "0.0.0.0"
PORT = 5555

clients = {}
clients_lock = threading.Lock()


def broadcast(command, text, exclude=None):
    payload = text.encode("utf-8")
    with clients_lock:
        targets = [s for s in clients if s is not exclude]
    for sock in targets:
        try:
            proto.send_message(sock, command, payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def handle_client(sock, addr):
    username = None
    try:
        first = proto.recv_message(sock)
        if first is None or first[0] != "JOIN":
            proto.send_message(sock, "ERROR", b"first command must be JOIN")
            return

        username = first[1].decode("utf-8", errors="replace").strip()
        with clients_lock:
            if not username or username in clients.values():
                proto.send_message(sock, "ERROR", b"invalid or taken username")
                return
            clients[sock] = username

        proto.send_message(sock, "TEXT", f"* вы вошли как {username}".encode())
        broadcast("TEXT", f"* {username} присоединился", exclude=sock)
        print(f"[+] {username} присоединился ({addr})")

        while True:
            msg = proto.recv_message(sock)
            if msg is None:
                print(f"[i] {username} отключился без QUIT")
                break

            command, payload = msg
            if command == "TEXT":
                text = payload.decode("utf-8", errors="replace")
                broadcast("TEXT", f"{username}: {text}", exclude=sock)
            elif command == "LIST":
                with clients_lock:
                    names = list(clients.values())
                proto.send_message(sock, "LIST", "\n".join(names).encode())
            elif command == "QUIT":
                proto.send_message(sock, "TEXT", b"* bye")
                print(f"[-] {username} вышел через QUIT")
                break
            elif command == "NICK":
            # Смена имени
                new_name = payload.decode("utf-8", errors="replace").strip()

                with clients_lock:
                # Проверка и запись под одним захватом, иначе два клиента могут одновременно решить, что имя свободно, и оба его занять
                    if not new_name:
                        error = "имя не может быть пустым"
                    elif new_name in clients.values():
                        error = f"имя '{new_name}' уже занято"
                    else:
                        error = None
                        clients[sock] = new_name

                if error:
                # Некорректный запрос: отвечаем ERROR
                    proto.send_message(sock, "ERROR", error.encode("utf-8"))
                else:
                    broadcast("TEXT", f"* {username} теперь {new_name}")
                    print(f"[~] {username} -> {new_name}")
                    username = new_name
            else:
                proto.send_message(sock, "ERROR", f"unknown command {command}".encode())

    except ConnectionResetError:
        print(f"[!] {username or addr} - соединение сброшено (RST)")
    except BrokenPipeError:
        print(f"[!] {username or addr} - не удалось отправить, соединение разорвано")
    finally:
        with clients_lock:
            clients.pop(sock, None)
        sock.close()
        if username:
            broadcast("TEXT", f"* {username} покинул чат")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] сервер слушает {HOST}:{PORT}")
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] сервер остановлен")
