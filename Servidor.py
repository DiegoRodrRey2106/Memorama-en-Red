import socket
import threading
import json
import random


class ConnectionPool:
    def __init__(self, max_connections):
        self.connections = []
        self.max_connections = max_connections
        self.board = [[" "] * 4 for _ in range(4)]
        self.word_pairs = ["gato", "perro", "sol", "luna", "cielo", "mar", "flor", "nube"] * 2
        random.shuffle(self.word_pairs)
        self.lock = threading.Lock()
        self.revealed_positions = set()
        self.current_selections = {}
        self.shutdown_flag = False  # Flag para señalizar el cierre del servidor

    def start(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(self.max_connections)
        print(f"Servidor escuchando en {host}:{port}")
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()

    def accept_connections(self):
        while not self.shutdown_flag:
            try:
                conn, addr = self.server_socket.accept()
            except socket.error:
                break  # Salir del bucle si el socket fue cerrado

            with self.lock:
                if len(self.connections) < self.max_connections:
                    print(f"Conexión aceptada de {addr}")
                    self.connections.append((conn, addr))  # Guardar también la dirección del cliente
                    client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                    client_thread.start()
                else:
                    conn.sendall(json.dumps({"message": "Conexión rechazada, límite alcanzado."}).encode('utf-8'))
                    conn.close()
                    print("Conexión rechazada, límite de conexiones alcanzado.")

    def handle_client(self, conn, addr):
        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if data:
                    jugada = json.loads(data)
                    self.process_play(jugada, conn)
                else:
                    break  # Si no hay datos, el cliente se ha desconectado
        except Exception as e:
            print(f"Error en la conexión con {addr}: {e}")
        finally:
            self.disconnect_client(conn, addr)

    def process_play(self, jugada, conn):
        x, y = jugada['x'], jugada['y']

        if not (0 <= x < 4 and 0 <= y < 4):
            error_msg = json.dumps({"message": "Entrada no válida. Intente de nuevo.", "board": self.board})
            conn.sendall(error_msg.encode('utf-8'))
            return

        with self.lock:
            pos_index = x * 4 + y
            word = self.word_pairs[pos_index]

            if conn not in self.current_selections:
                self.current_selections[conn] = []

            if len(self.current_selections[conn]) < 2 and (x, y) not in self.revealed_positions:
                self.current_selections[conn].append((x, y))
                self.board[x][y] = word

            if len(self.current_selections[conn]) == 2:
                first, second = self.current_selections[conn]
                first_word = self.word_pairs[first[0] * 4 + first[1]]
                second_word = self.word_pairs[second[0] * 4 + second[1]]

                if first_word == second_word:
                    self.revealed_positions.update([first, second])
                    msg = "¡Pareja encontrada!"
                else:
                    msg = "No es pareja, las cartas se ocultarán."
                    threading.Timer(2.0, self.hide_pair, args=[first, second]).start()

                message = json.dumps({"message": msg, "board": self.board})
                self.broadcast_message(message)
                self.current_selections[conn] = []

                if len(self.revealed_positions) == len(self.word_pairs):  # Todas las posiciones reveladas
                    game_over_message = json.dumps({"message": "Juego terminado", "board": self.board})
                    self.broadcast_message(game_over_message)
                    self.shutdown_flag = True  # Señal para finalizar el servidor

                    # Desconectar todos los clientes y cerrar el servidor
                    for conn, addr in self.connections[:]:
                        self.disconnect_client(conn, addr)
                    self.close_server()  # Cerrar el servidor
                    return

    def hide_pair(self, first, second):
        with self.lock:
            if first not in self.revealed_positions:
                self.board[first[0]][first[1]] = " "
            if second not in self.revealed_positions:
                self.board[second[0]][second[1]] = " "
            self.broadcast_message(json.dumps({"board": self.board}))

    def broadcast_message(self, message):
        for conn, _ in self.connections:
            try:
                conn.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Error enviando a cliente: {e}")

    def disconnect_client(self, conn, addr):
        with self.lock:
            if (conn, addr) in self.connections:
                self.connections.remove((conn, addr))
                conn.close()
                print(f"Cliente desconectado: {addr[0]}:{addr[1]} - recurso liberado.")

    def close_server(self):
        """Cerrar el servidor y liberar recursos"""
        print("Cerrando el servidor...")
        self.server_socket.close()
        print("Servidor cerrado exitosamente.")


if __name__ == "__main__":
    host = input("Ingrese la dirección IP del servidor: ")
    port = int(input("Ingrese el número de puerto: "))
    max_connections = int(input("Ingrese el número máximo de conexiones permitidas: "))

    pool = ConnectionPool(max_connections=max_connections)
    pool.start(host, port)
