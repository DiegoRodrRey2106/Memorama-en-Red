import socket
import json
import threading

class Cliente:
    def __init__(self, host, port):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.server_address)
        self.game_over = False  # Flag para indicar si el juego ha terminado
        print("Conectado al servidor en", self.server_address)

    def send_play(self, x, y):
        play = json.dumps({"x": x, "y": y})
        self.sock.sendall(play.encode('utf-8'))

    def receive_updates(self):
        try:
            while not self.game_over:
                data = self.sock.recv(1024).decode('utf-8')
                if data:
                    response = json.loads(data)
                    if "message" in response:
                        print(response["message"])
                        if response["message"].startswith("Juego terminado"):
                            self.game_over = True
                            break
                    if "board" in response:
                        self.display_board(response["board"])
                else:
                    break
        finally:
            self.sock.close()
            print("Desconectado del servidor.")

    def display_board(self, board):
        print("Tablero actualizado:")
        for i, row in enumerate(board):
            row_display = " ".join(f"[{cell}]" if cell != " " else "[ ]" for cell in row)
            print(f"{i}: {row_display}")
        print()

    def get_valid_input(self, prompt):
        while True:
            try:
                value = int(input(prompt))
                if 0 <= value < 4:
                    return value
                else:
                    print("Entrada no válida. Intente de nuevo.")
            except ValueError:
                print("Entrada no válida. Por favor ingrese un número.")

if __name__ == "__main__":
    host = input("Ingrese la dirección IP del servidor: ")
    port = int(input("Ingrese el número de puerto del servidor: "))

    cliente = Cliente(host, port)
    receive_thread = threading.Thread(target=cliente.receive_updates)
    receive_thread.start()

    while not cliente.game_over:
        print("Seleccione dos casillas para intentar encontrar una pareja:")
        x1 = cliente.get_valid_input("Fila de la primera casilla (0-3): ")
        y1 = cliente.get_valid_input("Columna de la primera casilla (0-3): ")
        cliente.send_play(x1, y1)

        x2 = cliente.get_valid_input("Fila de la segunda casilla (0-3): ")
        y2 = cliente.get_valid_input("Columna de la segunda casilla (0-3): ")
        cliente.send_play(x2, y2)

    receive_thread.join()
    print("El cliente ha finalizado.")
