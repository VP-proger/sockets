import socket
import threading
import queue
import protocol as proto

HOST = "127.0.0.1"
PORT = 5555
NAME_TIMEOUT = 15
# Сколько секунд ждем ввод имени


def listen_loop(sock, stop_event):
    while not stop_event.is_set():
        try:
            msg = proto.recv_message(sock)
        except (ConnectionResetError, OSError):
            msg = None
        if msg is None:
            if not stop_event.is_set():
                print("\n[!] соединение с сервером потеряно")
                stop_event.set()
            break
        command, payload = msg
        text = payload.decode("utf-8", errors="replace")
        if command == "LIST":
            print(f"\n[пользователи онлайн]\n{text}\n> ", end="")
        elif command == "ERROR":
            print(f"\n[ошибка] {text}\n> ", end="")
        else:
            print(f"\n{text}\n> ", end="")


def ask_username(timeout=NAME_TIMEOUT):
    # Возвращает введённое имя или None, если время вышло
    result = queue.Queue()

    def reader():
        try:
            result.put(input("Введите имя: ").strip())
        except EOFError:
            # Если поток ввода закрыт, то имени не будет
            result.put(None)

    threading.Thread(target=reader, daemon=True).start()
    # Если пользователь не введет имя, то этот поток не помешает программе завершиться

    try:
        return result.get(timeout=timeout)
        # главный поток спит до timeout
    except queue.Empty:
        return None
        # за timeout секунд ничего не пришло


def main():
    username = ask_username()
    if username is None:
        print("\nВремя на ввод имени истекло")
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        proto.send_message(sock, "JOIN", username.encode())
    except (ConnectionRefusedError, OSError) as e:
        print(f"Не удалось подключиться: {e}")
        return

    stop_event = threading.Event()
    listener = threading.Thread(target=listen_loop, args=(sock, stop_event), daemon=True)
    listener.start()

    print("Команды: /list, /nick <имя>, /quit. Остальной текст - сообщение в чат.")
    try:
        while not stop_event.is_set():
            line = input("> ")
            if line == "/quit":
                proto.send_message(sock, "QUIT")
                break
            elif line == "/list":
                proto.send_message(sock, "LIST")
            elif line == "/nick" or line.startswith("/nick "):
                parts = line.split(maxsplit=1)  # ["/nick", "{Имя}"]
                if len(parts) < 2:
                    print("Использование: /nick <новое_имя>")
                # Проверяем наличие аргумента
                else:
                    proto.send_message(sock, "NICK", parts[1].strip().encode("utf-8"))
            elif line:
                proto.send_message(sock, "TEXT", line.encode())
    except (EOFError, KeyboardInterrupt, BrokenPipeError, OSError):
        pass
    finally:
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            # сокет уже закрыт или соединение разорвано
            pass
        sock.close()
        listener.join(timeout=2)
        # Ждем фоновый поток не дольше 2 секунд и только потом выходим


if __name__ == "__main__":
    main()
