import socket
import threading
import json
import time
import uuid


class P2PDiscovery:
    def __init__(self, port=5000, interval=5):
        self.port = port
        self.interval = interval
        self.agent_id = str(uuid.uuid4())[:8]
        self.ip = self._get_internal_ip()
        self.mac = self._get_mac_native()

        # self.ip = "10.34.1.200"  # self._get_internal_ip()
        # self.mac = "00:11:22:33:44:55"  # self._get_mac_native()

        self.peers = {}
        self.lock = threading.Lock()

    def _get_mac_native(self):
        """Obtiene la MAC de forma nativa sin librerías externas."""
        mac_num = hex(uuid.getnode()).replace("0x", "").zfill(12)
        return ":".join(mac_num[i : i + 2] for i in range(0, 11, 2))

    def _get_internal_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # No necesita conexión real, solo para identificar la interfaz de salida
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def broadcast_presence(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Importante: permitir que el emisor también reuse dirección si es necesario
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        data = json.dumps(
            {"agent_id": self.agent_id, "mac": self.mac, "ip": self.ip}
        ).encode("utf-8")

        while True:
            try:
                sock.sendto(data, ("<broadcast>", self.port))
            except Exception as e:
                print(f"Error enviando broadcast: {e}")
            time.sleep(self.interval)

    def listen_for_peers(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # --- SOLUCIÓN AL ERROR DE PUERTO EN USO ---
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # En sistemas basados en Linux (como contenedores), SO_REUSEPORT es clave
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Escuchamos en todas las interfaces ('')
        sock.bind(("", self.port))

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                peer_info = json.loads(data.decode("utf-8"))

                if peer_info["agent_id"] != self.agent_id:
                    with self.lock:
                        peer_info["last_seen"] = time.time()
                        if peer_info["agent_id"] not in self.peers:
                            print(
                                f"\n[+] Nuevo Agente: {peer_info['agent_id']} | IP: {peer_info['ip']} | MAC: {peer_info['mac']}"
                            )
                        self.peers[peer_info["agent_id"]] = peer_info
            except Exception as e:
                print(f"Error recibiendo: {e}")

    def clean_expired_peers(self, timeout=15):
        while True:
            now = time.time()
            with self.lock:
                expired = [
                    aid
                    for aid, info in self.peers.items()
                    if now - info["last_seen"] > timeout
                ]
                for aid in expired:
                    print(f"\n[-] Agente offline: {aid}")
                    del self.peers[aid]
            time.sleep(5)

    def start(self):
        threading.Thread(target=self.broadcast_presence, daemon=True).start()
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.clean_expired_peers, daemon=True).start()

        print(f"Agente iniciado: {self.agent_id} | IP: {self.ip} | MAC: {self.mac}")
        try:
            while True:
                # Mostrar tabla de agentes activos cada 10 seg para debug
                time.sleep(10)
                with self.lock:
                    print(f"\n--- Agentes Activos: {len(self.peers)} ---")
                    for aid, info in self.peers.items():
                        print(f"ID: {aid} | IP: {info['ip']} | MAC: {info['mac']}")
        except KeyboardInterrupt:
            print("\nDeteniendo...")


if __name__ == "__main__":
    discovery = P2PDiscovery(port=5000)
    discovery.start()
