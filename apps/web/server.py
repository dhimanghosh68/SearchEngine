from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 3000

WEB_DIR = Path(__file__).resolve().parent


class WebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), WebHandler)

    print(f"SearchEngine frontend running at http://{HOST}:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
