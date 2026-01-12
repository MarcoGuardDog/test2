import socket
import struct
import threading
import time
import json
import uuid

MCAST_GRP = "224.0.0.1"
MCAST_PORT = 5007
MY_ID = str(uuid.uuid4())[:8]


class RHELDiscovery:
    def __init__(self):
        self.peers = {}
        self.ip = self._get_ip()
        self.mac = ":".join(
            ["{:02x}".format((uuid.getnode() >> i) & 0xFF) for i in range(0, 48, 8)][
                ::-1
            ]
        )

    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    def sender(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        # Forzar el envío por la IP de la interfaz principal
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.ip)
        )

        data = json.dumps(
            {"id": MY_ID, "ip": self.ip, "mac": self.mac, "ts": time.time()}
        ).encode("utf-8")

        print(f"[*] Nodo {MY_ID} iniciado en RHEL ({self.ip})")
        while True:
            sock.sendto(data, (MCAST_GRP, MCAST_PORT))
            time.sleep(3)

    def listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(("", MCAST_PORT))

        # Unirse al grupo indicando la IP local para evitar ambigüedades en RHEL
        mreq = struct.pack(
            "4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(self.ip)
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                info = json.loads(data.decode("utf-8"))
                if info["id"] != MY_ID:
                    self.peers[info["id"]] = {**info, "last_seen": time.time()}
            except:
                pass

    def start(self):
        threading.Thread(target=self.sender, daemon=True).start()
        threading.Thread(target=self.listener, daemon=True).start()
        while True:
            now = time.time()
            self.peers = {
                k: v for k, v in self.peers.items() if now - v["last_seen"] < 10
            }
            if self.peers:
                print(f"\r[Nodos]: {list(self.peers.keys())}", end="")
            time.sleep(1)


if __name__ == "__main__":
    RHELDiscovery().start()
