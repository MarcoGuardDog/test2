import socket
import struct
import threading
import time
import json
import uuid

# Configuración técnica
MCAST_GRP = "224.0.0.1"
MCAST_PORT = 5007
MY_ID = str(uuid.uuid4())[:8]
TIMEOUT_NODOS = 10  # Segundos para considerar a un nodo como desconectado


class RHELDiscovery:
    def __init__(self):
        self.peers = {}  # Diccionario para guardar { id: {ip, mac, last_seen} }
        self.lock = threading.Lock()  # Para evitar errores al leer/escribir peers
        self.ip = self._get_ip()
        self.mac = self._get_mac()

    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    def _get_mac(self):
        # Obtiene la dirección MAC de la interfaz activa
        mac_num = hex(uuid.getnode()).replace("0x", "").zfill(12)
        return ":".join(mac_num[i : i + 2] for i in range(0, 11, 2))

    def sender(self):
        """Hilo que anuncia nuestra presencia (Beacon)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.ip)
        )

        # El mensaje incluye ID, IP y MAC
        payload = "gAAAAABpaVJBChHKNz1XI7SYdGPYZ_Ysr5B7fAzy2l1sv6JRjiIpbIWG96lgCm5uTPoSrxjTfPlpGEPDgksVq-Jd7QvI6Y9pB5eBWgqupdTEf3nOiHCAX3IildQDlwDR9ODmeYbS5LxR-JBUZDlWWaMet-lJ6mCyPwjhainQrolBtKx7FJbuDzZz1JwjxoQ8GHzoSRD8Q5U5x-GRTBPpF5i1P2ASBALE7vqiAkglfIAKtp0aIcXM684="

        print(f"[*] Iniciando Nodo: {MY_ID} | IP: {self.ip} | MAC: {self.mac}")

        while True:
            data = payload.encode("utf-8")
            sock.sendto(data, (MCAST_GRP, MCAST_PORT))
            time.sleep(3)  # Anunciar cada 3 segundos

    def listener(self):
        """Hilo que escucha a otros contenedores"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(("", MCAST_PORT))

        mreq = struct.pack(
            "4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(self.ip)
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                info = json.loads(data.decode("utf-8"))

                if info["id"] != MY_ID:
                    with self.lock:
                        # Si es nuevo, avisamos
                        if info["id"] not in self.peers:
                            print(
                                f"\n[+] Nodo detectado: ID={info['id']} IP={info['ip']} MAC={info['mac']}"
                            )

                        # Guardamos/Actualizamos datos y marca de tiempo
                        self.peers[info["id"]] = {
                            "ip": info["ip"],
                            "mac": info["mac"],
                            "last_seen": time.time(),
                        }
            except Exception as e:
                print(f"Error en listener: {e}")

    def cleaner(self):
        """Hilo encargado de eliminar nodos desconectados"""
        while True:
            time.sleep(2)
            now = time.time()
            with self.lock:
                to_delete = []
                for node_id, data in self.peers.items():
                    if now - data["last_seen"] > TIMEOUT_NODOS:
                        to_delete.append(node_id)

                for node_id in to_delete:
                    print(f"\n[-] Nodo desconectado (timeout): {node_id}")
                    del self.peers[node_id]

    def display(self):
        """Imprime la tabla de nodos actuales"""
        while True:
            time.sleep(5)
            with self.lock:
                if self.peers:
                    print("\n--- CONTENEDORES ACTIVOS ---")
                    for node_id, data in self.peers.items():
                        print(f"ID: {node_id} | IP: {data['ip']} | MAC: {data['mac']}")
                    print("----------------------------\n")

    def start(self):
        # Lanzar todos los hilos
        threading.Thread(target=self.sender, daemon=True).start()
        threading.Thread(target=self.listener, daemon=True).start()
        threading.Thread(target=self.cleaner, daemon=True).start()
        self.display()


if __name__ == "__main__":
    discovery = RHELDiscovery()
    discovery.start()
