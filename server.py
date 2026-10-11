"""
Omah Thinner & Cat — Local Fullstack Server
Fitur:
- Web Server Static & Threaded (HTML, CSS, JS, Gambar)
- REST API Katalog Produk (data/store_catalog.json)
- REST API Upload Gambar (/api/upload -> uploads/)
- Murni Python 3 Standard Library (ThreadingHTTPServer)
"""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.parse
import time
import uuid
import re
import socket
import sys

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CATALOG_FILE = os.path.join(DATA_DIR, "store_catalog.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

class FullstackHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '': 'application/octet-stream',
        '.html': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.ico': 'image/x-icon',
        '.woff2': 'font/woff2',
        '.woff': 'font/woff',
        '.ttf': 'font/ttf',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Connection', 'close')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ["/", "/index.html", "/website.html"]:
            self.path = "/index.html"
            return super().do_HEAD()
        if path in ["/api/catalog", "/api/health"]:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            return
        return super().do_HEAD()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Route root atau /website.html ke file index.html
        if path in ["/", "/index.html"]:
            self.path = "/index.html"
            return super().do_GET()

        if path == "/website.html":
            if os.path.exists(os.path.join(BASE_DIR, "index.html")):
                self.path = "/index.html"
            return super().do_GET()

        # API: Ambil Katalog Produk
        if path == "/api/catalog":
            return self.handle_get_catalog()

        # API: Health Check
        if path == "/api/health":
            return self.send_json_response({
                "status": "ok",
                "server": "Omah Thinner & Cat Local Fullstack",
                "time": int(time.time()),
                "catalog_exists": os.path.exists(CATALOG_FILE),
                "uploads_dir": os.path.exists(UPLOADS_DIR)
            })

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API: Upload Gambar
        if path == "/api/upload":
            return self.handle_upload_image()

        # API: Tambah / Perbarui Produk
        if path == "/api/products":
            return self.handle_add_product()

        # API: Simpan Seluruh Katalog
        if path == "/api/catalog":
            return self.handle_save_catalog()

        self.send_json_response({"error": "Endpoint tidak ditemukan"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/products/"):
            prod_id = path.replace("/api/products/", "").strip()
            return self.handle_delete_product(prod_id)

        self.send_json_response({"error": "Endpoint tidak ditemukan"}, status=404)

    # ------------------ HANDLERS ------------------ #

    def send_json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_get_catalog(self):
        try:
            if os.path.exists(CATALOG_FILE):
                with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"products": [], "categories": []}
            self.send_json_response(data)
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_save_catalog(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            catalog_data = json.loads(body)
            with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(catalog_data, f, ensure_ascii=False, indent=2)
            self.send_json_response({
                "success": True,
                "message": "Katalog berhasil disimpan!",
                "total_products": len(catalog_data.get('products', []))
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_add_product(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            new_prod = json.loads(body)

            if os.path.exists(CATALOG_FILE):
                with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
            else:
                catalog = {"products": [], "categories": []}

            if not new_prod.get("id"):
                new_prod["id"] = f"prod_{int(time.time()*1000)}"

            existing_idx = next((i for i, p in enumerate(catalog.get("products", [])) if p.get("id") == new_prod["id"]), -1)
            if existing_idx >= 0:
                catalog["products"][existing_idx] = new_prod
            else:
                catalog.setdefault("products", []).insert(0, new_prod)

            with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)

            self.send_json_response({
                "success": True,
                "product": new_prod,
                "message": "Produk berhasil disimpan ke database lokal!"
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_delete_product(self, prod_id):
        try:
            if not os.path.exists(CATALOG_FILE):
                return self.send_json_response({"error": "Katalog kosong"}, status=404)

            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                catalog = json.load(f)

            products = catalog.get("products", [])
            initial_count = len(products)
            catalog["products"] = [p for p in products if p.get("id") != prod_id]

            if len(catalog["products"]) == initial_count:
                return self.send_json_response({"error": "Produk tidak ditemukan"}, status=404)

            with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)

            self.send_json_response({"success": True, "message": f"Produk {prod_id} berhasil dihapus!"})
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_upload_image(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            length = int(self.headers.get('Content-Length', 0))

            if 'multipart/form-data' not in content_type:
                file_bytes = self.rfile.read(length)
                filename = f"foto_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
                save_path = os.path.join(UPLOADS_DIR, filename)
                with open(save_path, "wb") as f:
                    f.write(file_bytes)
                rel_url = f"uploads/{filename}"
                return self.send_json_response({"success": True, "url": rel_url, "filename": filename})

            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                return self.send_json_response({"error": "Boundary multipart tidak valid"}, status=400)

            boundary = boundary_match.group(1).strip().strip('"').encode('utf-8')
            body_bytes = self.rfile.read(length)

            parts = body_bytes.split(b'--' + boundary)
            saved_filename = None

            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    header_part, file_data = part.split(b'\r\n\r\n', 1)
                    if file_data.endswith(b'\r\n'):
                        file_data = file_data[:-2]

                    header_text = header_part.decode('utf-8', errors='ignore')
                    fn_match = re.search(r'filename="([^"]+)"', header_text)
                    orig_name = fn_match.group(1) if fn_match else "foto.jpg"

                    _, ext = os.path.splitext(orig_name)
                    ext = ext.lower()
                    if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.svg']:
                        ext = '.jpg'

                    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', os.path.splitext(orig_name)[0])[:20]
                    saved_filename = f"{safe_title}_{int(time.time())}{ext}"
                    save_path = os.path.join(UPLOADS_DIR, saved_filename)

                    with open(save_path, "wb") as out_f:
                        out_f.write(file_data)
                    break

            if saved_filename:
                rel_url = f"uploads/{saved_filename}"
                self.send_json_response({
                    "success": True,
                    "url": rel_url,
                    "filename": saved_filename,
                    "message": "Gambar berhasil diunggah ke folder uploads/!"
                })
            else:
                self.send_json_response({"error": "File gambar tidak ditemukan dalam formulir"}, status=400)

        except Exception as e:
            self.send_json_response({"error": f"Gagal upload: {str(e)}"}, status=500)


def run_server():
    server_address = ('0.0.0.0', PORT)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, FullstackHandler)
    print(f"=====================================================", flush=True)
    print(f"  OMAH THINNER & CAT — SERVER FULLSTACK AKTIF        ", flush=True)
    print(f"=====================================================", flush=True)
    print(f"  Akses Website: http://localhost:{PORT}", flush=True)
    print(f"  Akses IP     : http://127.0.0.1:{PORT}", flush=True)
    print(f"  Katalog Data : {CATALOG_FILE}", flush=True)
    print(f"  Folder Upload: {UPLOADS_DIR}", flush=True)
    print(f"=====================================================", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.", flush=True)

if __name__ == "__main__":
    run_server()
