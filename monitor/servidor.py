"""Servidor HTTP: API REST + dashboard. Usa apenas a biblioteca padrão do Python.

Uso:
    python -m monitor.servidor [--porta 8000] [--banco barragem.db]

Variável de ambiente opcional BARRAGEM_CHAVE_API: se definida, o envio de
leituras (POST /api/leituras) exige o cabeçalho "X-Chave-API" com esse valor.
"""

import argparse
import hmac
import json
import logging
import mimetypes
import os
import re
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config
from .banco import Banco
from .servico import ErroValidacao, Monitor

PASTA_WEB = Path(__file__).parent / "web"
log = logging.getLogger("monitor")


def _desde(qs, padrao_horas=24):
    try:
        horas = float(qs.get("horas", [padrao_horas])[0])
    except ValueError:
        horas = padrao_horas
    inicio = datetime.now(timezone.utc) - timedelta(hours=horas)
    return inicio.strftime("%Y-%m-%dT%H:%M:%SZ")


def criar_handler(monitor, chave_api=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MonitorBarragem/1.0"

        def log_message(self, formato, *args):
            log.info("%s - %s", self.address_string(), formato % args)

        # -- utilitários --------------------------------------------------

        def _json(self, dados, status=200):
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _erro(self, status, mensagem):
            self._json({"erro": mensagem}, status)

        def _arquivo(self, caminho):
            caminho = caminho.resolve()
            if PASTA_WEB.resolve() not in caminho.parents or not caminho.is_file():
                return self._erro(404, "Não encontrado")
            corpo = caminho.read_bytes()
            tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
            if tipo.startswith("text/") or tipo == "application/javascript":
                tipo += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        # -- rotas --------------------------------------------------------

        def do_GET(self):
            url = urlparse(self.path)
            qs = parse_qs(url.query)
            rota = url.path

            if rota in ("/", "/index.html"):
                return self._arquivo(PASTA_WEB / "index.html")
            if rota.startswith("/static/"):
                return self._arquivo(PASTA_WEB / rota[len("/static/"):])
            if rota == "/api/estado":
                return self._json(monitor.estado())
            if rota == "/api/historico":
                variavel = qs.get("variavel", [""])[0]
                if variavel not in config.VARIAVEIS:
                    return self._erro(400, "Parâmetro 'variavel' inválido")
                return self._json({"variavel": variavel,
                                   "pontos": monitor.banco.historico(variavel, _desde(qs))})
            if rota == "/api/indice":
                return self._json({"pontos": monitor.banco.historico_indice(_desde(qs))})
            if rota == "/api/alertas":
                pendentes = qs.get("pendentes", ["0"])[0] in ("1", "true")
                return self._json({"alertas": monitor.banco.alertas(apenas_pendentes=pendentes)})
            return self._erro(404, "Rota não encontrada")

        def do_POST(self):
            rota = urlparse(self.path).path

            if rota == "/api/leituras":
                if chave_api and not hmac.compare_digest(
                        self.headers.get("X-Chave-API", ""), chave_api):
                    return self._erro(401, "Chave de API inválida")
                try:
                    tamanho = int(self.headers.get("Content-Length", 0))
                    if tamanho > 64 * 1024:
                        return self._erro(413, "Pacote muito grande")
                    pacote = json.loads(self.rfile.read(tamanho) or b"null")
                    return self._json(monitor.registrar(pacote), 201)
                except json.JSONDecodeError:
                    return self._erro(400, "JSON inválido")
                except ErroValidacao as e:
                    return self._erro(400, str(e))

            m = re.fullmatch(r"/api/alertas/(\d+)/reconhecer", rota)
            if m:
                if monitor.banco.reconhecer_alerta(int(m.group(1))):
                    return self._json({"ok": True})
                return self._erro(404, "Alerta não encontrado")

            return self._erro(404, "Rota não encontrada")

    return Handler


def criar_servidor(banco, host="0.0.0.0", porta=8000, chave_api=None):
    monitor = Monitor(banco)
    return ThreadingHTTPServer((host, porta), criar_handler(monitor, chave_api))


def main():
    parser = argparse.ArgumentParser(description="Servidor de monitoramento de barragens")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--banco", default="barragem.db", help="arquivo SQLite")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    servidor = criar_servidor(Banco(args.banco), args.host, args.porta,
                              os.environ.get("BARRAGEM_CHAVE_API"))
    print(f"Dashboard em http://localhost:{args.porta}  (Ctrl+C para encerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
