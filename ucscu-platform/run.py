"""Start UCSCU Connect.

Prints the LAN addresses (and an ASCII QR code) staff should use to connect, so
whoever starts the server on the Windows box can share it without any setup.
"""
import os
import socket

from app import create_app

app = create_app()
PORT = int(os.environ.get("PORT", "12000"))


def lan_ips():
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips or ["127.0.0.1"]


def banner():
    ips = lan_ips()
    url = "http://%s:%s/" % (ips[0], PORT)
    print("=" * 62)
    print("  UCSCU Connect is running")
    print("  Staff should open:  %s" % url)
    for extra in ips[1:]:
        print("  also reachable at:  http://%s:%s/" % (extra, PORT))
    print("=" * 62)
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)
        print("  Scan the code above to open UCSCU Connect on a phone/laptop")
        print("=" * 62)
    except Exception:
        pass


if __name__ == "__main__":
    banner()
    # 0.0.0.0 = every device on the office LAN can reach this server
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
