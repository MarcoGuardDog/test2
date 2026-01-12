import socket
import threading
import time
import uuid
import json

# Rango de puertos reservados para nuestros contenedores
# Si planeas tener 10 contenedores, reserva del 5000 al 5010
PORT_RANGE = range(5000, 5010)
MY_ID = str(uuid.uuid4())[:8]


class TCPDiscovery:
    def __init__(self):
        self.peers = {}
        self.my_port = None

    def get_my_info(self):
        # Obtenemos IP y MAC (simplificado para el ejemplo)
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return {"id": MY_ID, "ip": ip, "port": self.my_port}

    def start_server(self):
        """Intenta levantar el servidor en el primer puerto disponible del rango"""
        for port in PORT_RANGE:
            try:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.bind(("0.0.0.0", port))
                self.server_sock.listen(5)
                self.my_port = port
                print(f"[*] Servidor iniciado en puerto {port} (ID: {MY_ID})")
                break
            except socket.error:
                continue

        if not self.my_port:
            print("[!] No hay puertos disponibles en el rango.")
            return

        while True:
            conn, addr = self.server_sock.accept()
            data = conn.recv(1024)
            if data:
                # Responder con nuestra info cuando alguien nos "descubre"
                conn.send(json.dumps(self.get_my_info()).encode())
            conn.close()

    def discover_peers(self):
        """Escanea el rango de puertos para encontrar otros contenedores"""
        while True:
            for port in PORT_RANGE:
                if port == self.my_port:
                    continue

                try:
                    # Intentamos conectar para ver si hay otro contenedor
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.2)  # Timeout rápido
                    sock.connect(("127.0.0.1", port))

                    # Enviamos un "hola" para pedir su info
                    sock.send(b"HELLO")
                    data = sock.recv(1024)
                    if data:
                        peer_info = json.loads(data.decode())
                        peer_id = peer_info["id"]
                        if peer_id not in self.peers:
                            print(f"\n[+] Nuevo contenedor TCP detectado: {peer_info}")
                        self.peers[peer_id] = peer_info
                    sock.close()
                except (socket.timeout, ConnectionRefusedError):
                    # Si falla, es que no hay nadie en ese puerto
                    continue

            time.sleep(5)  # Escanear cada 5 segundos

    def start(self):
        # Hilo para que otros me encuentren
        t1 = threading.Thread(target=self.start_server, daemon=True)
        # Hilo para yo buscar a otros
        t2 = threading.Thread(target=self.discover_peers, daemon=True)

        t1.start()
        # Esperar un poco a que el server levante
        time.sleep(1)
        t2.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Cerrando...")


if __name__ == "__main__":
    discovery = TCPDiscovery()
    discovery.start()
