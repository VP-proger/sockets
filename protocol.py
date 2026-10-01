import struct

HEADER_FORMAT = "!BI"
# B (1 байт) - длина команды от 0 до 255, I (4 байта) - длина payload

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024
MAX_COMMAND_SIZE = 64
# лимит на длину команды в байтах


def recv_exact(sock, size):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("соединение закрыто до получения всех данных")
        chunks.extend(chunk)
    return bytes(chunks)


def send_message(sock, command, payload=b""):
    command_bytes = command.encode("utf-8")
    # utf-8 вместо ascii, и больше нет дополнения и обрезания команды

    if len(command_bytes) == 0:
        raise ValueError("команда не может быть пустой")
    if len(command_bytes) > MAX_COMMAND_SIZE:
        raise ValueError(f"команда слишком длинная: {len(command_bytes)} байт")
    # Проверяем длину команды

    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError(f"payload слишком большой: {len(payload)} байт")
    header = struct.pack(HEADER_FORMAT, len(command_bytes), len(payload))
    # В заголовок кладем длину команды вместо команды

    sock.sendall(header + command_bytes + payload)
    # Отправляем заголовок + команда + payload

def recv_message(sock):
    try:
        header = recv_exact(sock, HEADER_SIZE)
    except ConnectionError:
        return None
    command_length, payload_length = struct.unpack(HEADER_FORMAT, header)
    # Из заголовка достаем длину команды и длину payload

    if command_length == 0 or command_length > MAX_COMMAND_SIZE:
        raise ValueError(f"недопустимая длина команды: {command_length}")
    if payload_length > MAX_MESSAGE_SIZE:
        raise ValueError(f"заявленная длина {payload_length} превышает лимит")
    command_bytes = recv_exact(sock, command_length)
    payload = recv_exact(sock, payload_length) if payload_length else b""

    return command_bytes.decode("utf-8"), payload
