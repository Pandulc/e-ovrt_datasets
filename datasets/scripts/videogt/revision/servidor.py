"""Servidor local de una revisión dirigida del GT (stdlib, sin dependencias).

Sirve `pagina.html`, el `casos.json` y los medios que generó `preparar.py`, y guarda las
respuestas del revisor en `datasets-videos/review/<revision>/respuestas.json`. Cada guardado
se agrega además, con su hora, a `respuestas.historial.jsonl`: la constancia de qué se
decidió y cuándo.

Uso:
    python3 datasets/scripts/videogt/revision/servidor.py --revision revision-dirigida-2026-10 \
        [--host 127.0.0.1] [--port 8765]
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
MAX_BODY = 5 * 1024 * 1024


def make_handler(review_dir: Path):
    answers = review_dir / "respuestas.json"
    history = review_dir / "respuestas.historial.jsonl"

    class Handler(BaseHTTPRequestHandler):
        server_version = "revision-gt/1"

        def log_message(self, fmt, *args):  # una línea corta por pedido, sin ruido de medios
            if not self.path.startswith("/media/"):
                super().log_message(fmt, *args)

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _file(self, path: Path) -> None:
            if not path.is_file():
                return self._json(404, {"error": "no existe"})
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            data = path.read_bytes()
            rng = self.headers.get("Range")
            if rng and rng.startswith("bytes=") and ctype.startswith("video/"):
                start_s, _, end_s = rng[6:].partition("-")
                start = int(start_s or 0)
                end = min(int(end_s) if end_s else len(data) - 1, len(data) - 1)
                chunk = data[start:end + 1]
                return self._send(206, chunk, ctype, {"Content-Range": f"bytes {start}-{end}/{len(data)}",
                                                      "Accept-Ranges": "bytes"})
            self._send(200, data, ctype, {"Accept-Ranges": "bytes"})

        def do_GET(self):
            p = self.path.split("?", 1)[0]
            if p in ("/", "/index.html"):
                return self._file(HERE / "pagina.html")
            if p == "/casos.json":
                return self._file(review_dir / "casos.json")
            if p == "/api/respuestas":
                return self._json(200, json.loads(answers.read_text()) if answers.exists() else {})
            if p.startswith("/media/"):
                target = (review_dir / p.lstrip("/")).resolve()
                if review_dir.resolve() not in target.parents:
                    return self._json(403, {"error": "ruta fuera de la revisión"})
                return self._file(target)
            return self._json(404, {"error": "no existe"})

        def do_POST(self):
            if self.path != "/api/respuestas":
                return self._json(404, {"error": "no existe"})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._json(400, {"error": "cuerpo vacío o demasiado grande"})
            try:
                obj = json.loads(self.rfile.read(n))
            except json.JSONDecodeError:
                return self._json(400, {"error": "JSON inválido"})
            if not isinstance(obj, dict) or not isinstance(obj.get("respuestas"), dict):
                return self._json(400, {"error": "falta 'respuestas'"})
            # Control de versión: una página abierta con un estado viejo no pisa lo que se
            # escribió después (por ejemplo, la propuesta precargada).
            actual = json.loads(answers.read_text()) if answers.exists() else {}
            rev = int(actual.get("_rev", 0))
            if int(obj.get("_rev", 0) or 0) != rev:
                return self._json(409, {"error": "la página está desactualizada: recargala", "_rev": rev})
            obj["_rev"] = rev + 1
            obj["guardado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            tmp = answers.with_suffix(".tmp")
            tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
            os.replace(tmp, answers)
            with history.open("a") as h:
                h.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self._json(200, {"ok": True, "guardado": obj["guardado"], "_rev": obj["_rev"]})

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args(argv)
    review_dir = REPO / "datasets-videos" / "review" / a.revision
    if not (review_dir / "casos.json").exists():
        raise SystemExit(f"falta {review_dir / 'casos.json'}: correr preparar.py primero")
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(review_dir))
    print(f"revisión en http://localhost:{a.port}  ({review_dir})", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
