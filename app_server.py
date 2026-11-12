import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import threading
import time

# Estado interno da instancia do servidor ShopNow
ESTADO = {
    "nome": os.environ.get("SERVER_NAME", "app_server1"),
    "porta": int(os.environ.get("PORT", "8001")),
    " peso": int(os.environ.get("WEIGHT", "1")),
    "requisicoes_atendidas": 0,
    "conexoes_ativas": 0,
    "em_falha": False,
    "delay_ms": int(os.environ.get("DELAY_MS", "0")),
    "iniciado_em": datetime.now().strftime("%H:%M:%S"),
}
LOCK = threading.Lock()

CORES_SERVIDOR = {
    "app_server1": {"cor": "#2563eb", "bg": "#eff6ff", "borda": "#93c5fd", "az": "sa-east-1a (SP)"},
    "app_server2": {"cor": "#059669", "bg": "#ecfdf5", "borda": "#6ee7b7", "az": "sa-east-1b (SP)"},
    "app_server3": {"cor": "#7c3aed", "bg": "#f5f3ff", "borda": "#c4b5fd", "az": "sa-east-1c (SP)"},
}


def gerar_html_shopnow(algoritmo_lb: str = "Round Robin", resumo_lb: str = "") -> str:
    nome = ESTADO["nome"]
    porta = ESTADO["porta"]
    reqs = ESTADO["requisicoes_atendidas"]
    ativas = ESTADO["conexoes_ativas"]
    estilo = CORES_SERVIDOR.get(
        nome, {"cor": "#ea580c", "bg": "#fff7ed", "borda": "#fdba74", "az": "sa-east-1"}
    )
    horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>ShopNow - Black Friday ({nome})</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }}
        body {{ background: #0f172a; color: #f8fafc; padding: 20px; }}
        .container {{ max-width: 1050px; margin: 0 auto; }}
        .header {{
            display: flex; justify-content: space-between; align-items: center;
            background: linear-gradient(90deg, #dc2626, #991b1b);
            padding: 18px 24px; border-radius: 12px; margin-bottom: 18px;
            box-shadow: 0 8px 20px rgba(220, 38, 38, 0.3);
        }}
        .header h1 {{ font-size: 26px; letter-spacing: 0.5px; }}
        .header span {{ background: #fef08a; color: #7f1d1d; font-weight: 800; padding: 6px 12px; border-radius: 6px; font-size: 13px; }}
        .server-banner {{
            background: {estilo['bg']}; color: #0f172a;
            border: 3px solid {estilo['cor']}; border-radius: 12px;
            padding: 20px; margin-bottom: 18px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
        }}
        .server-badge {{
            background: {estilo['cor']}; color: #fff;
            padding: 8px 16px; border-radius: 8px; font-size: 20px; font-weight: bold;
            display: inline-block; margin-bottom: 6px;
        }}
        .stats-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px; margin-bottom: 20px;
        }}
        .stat-card {{
            background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px;
        }}
        .stat-card small {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
        .stat-card strong {{ display: block; font-size: 20px; color: #38bdf8; margin-top: 4px; }}
        .products {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 14px; margin-top: 14px;
        }}
        .product {{
            background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px;
        }}
        .product h3 {{ font-size: 16px; margin-bottom: 6px; }}
        .old-price {{ text-decoration: line-through; color: #64748b; font-size: 13px; }}
        .price {{ color: #4ade80; font-size: 22px; font-weight: bold; margin: 4px 0 10px; }}
        .btn {{
            display: inline-block; background: #2563eb; color: #fff; text-decoration: none;
            padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600;
            border: none; cursor: pointer;
        }}
        .btn:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🛒 ShopNow E-Commerce</h1>
                <p style="font-size: 14px; opacity: 0.9;">Mega Operação Black Friday — Arquitetura Distribuída Escalável</p>
            </div>
            <span>🔥 BLACK FRIDAY ATIVA</span>
        </div>

        <div class="server-banner">
            <div>
                <div class="server-badge">⚡ Respondido por: {nome} (Porta {porta})</div>
                <p style="font-size: 14px; color: #334155;">
                    Zona de Disponibilidade: <strong>{estilo['az']}</strong> |
                    Horário da Resposta: <strong>{horario}</strong>
                </p>
            </div>
            <div>
                <a href="/" class="btn" style="background: {estilo['cor']}; font-size: 15px; padding: 12px 18px;">
                    🔄 Nova Requisição (Testar Balanceador)
                </a>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <small>Instância Atual</small>
                <strong>{nome} (:{porta})</strong>
            </div>
            <div class="stat-card">
                <small>Algoritmo do Balanceador</small>
                <strong>{algoritmo_lb}</strong>
            </div>
            <div class="stat-card">
                <small>Requisições nesta Instância</small>
                <strong>{reqs:06d} acessos</strong>
            </div>
            <div class="stat-card">
                <small>Conexões Simultâneas Agora</small>
                <strong>{ativas:04d} ativas</strong>
            </div>
        </div>

        {resumo_lb}

        <h2 style="font-size: 18px; margin: 18px 0 10px; color: #e2e8f0;">Ofertas em Destaque (Servidas pelo Cluster)</h2>
        <div class="products">
            <div class="product">
                <h3>💻 Notebook Gamer RTX 4060</h3>
                <div class="old-price">De R$ 7.499,00</div>
                <div class="price">R$ 4.899,00</div>
                <a href="/?comprar=notebook" class="btn">Comprar Agora</a>
            </div>
            <div class="product">
                <h3>📱 Smartphone Pro 256GB 5G</h3>
                <div class="old-price">De R$ 5.999,00</div>
                <div class="price">R$ 3.799,00</div>
                <a href="/?comprar=smartphone" class="btn">Comprar Agora</a>
            </div>
            <div class="product">
                <h3>📺 Smart TV 65" OLED 4K</h3>
                <div class="old-price">De R$ 6.299,00</div>
                <div class="price">R$ 3.990,00</div>
                <a href="/?comprar=tv" class="btn">Comprar Agora</a>
            </div>
            <div class="product">
                <h3>🎧 Headset Wireless Noise Cancelling</h3>
                <div class="old-price">De R$ 1.299,00</div>
                <div class="price">R$ 649,00</div>
                <a href="/?comprar=headset" class="btn">Comprar Agora</a>
            </div>
        </div>
    </div>
</body>
</html>"""


class ShopNowHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Log limpo no console da instancia
        print(f"[{ESTADO['nome']}:{ESTADO['porta']}] {self.address_string()} - {format % args}")

    def do_GET(self):
        # Rota de controle para simular queda ou recuperacao deste servidor
        if self.path.startswith("/toggle-falha"):
            with LOCK:
                ESTADO["em_falha"] = not ESTADO["em_falha"]
                status_atual = "EM_FALHA (OFFLINE)" if ESTADO["em_falha"] else "ONLINE (SAUDAVEL)"
            print(f"[!!! SIMULACAO DE FALHA !!!] {ESTADO['nome']} agora esta: {status_atual}")
            payload = json.dumps({"servidor": ESTADO["nome"], "em_falha": ESTADO["em_falha"]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Se a instancia estiver em modo de falha simulada, retorna HTTP 503 Service Unavailable
        if ESTADO["em_falha"]:
            erro_bytes = json.dumps(
                {"erro": f"Servidor {ESTADO['nome']} indisponivel (Simulacao de Falha)"}
            ).encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(erro_bytes)))
            self.end_headers()
            self.wfile.write(erro_bytes)
            return

        # Health Check usado pelo Balanceador de Carga
        if self.path.startswith("/health"):
            payload = json.dumps(
                {
                    "status": "UP",
                    "servidor": ESTADO["nome"],
                    "porta": ESTADO["porta"],
                    "requisicoes_atendidas": ESTADO["requisicoes_atendidas"],
                    "conexoes_ativas": ESTADO["conexoes_ativas"],
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Contabiliza conexao ativa e requisicao atendida
        with LOCK:
            ESTADO["conexoes_ativas"] += 1
            ESTADO["requisicoes_atendidas"] += 1

        try:
            if ESTADO["delay_ms"] > 0:
                time.sleep(ESTADO["delay_ms"] / 1000.0)

            algoritmo_lb = self.headers.get("X-Load-Balancer-Algorithm", "Acesso Direto")
            resumo_lb = self.headers.get("X-Load-Balancer-Summary", "")

            if self.path.startswith("/api"):
                corpo = json.dumps(
                    {
                        "loja": "ShopNow Black Friday",
                        "servidor": ESTADO["nome"],
                        "porta": ESTADO["porta"],
                        "algoritmo_balanceador": algoritmo_lb,
                        "requisicoes_atendidas": f"{ESTADO['requisicoes_atendidas']:06d}",
                        "conexoes_ativas": f"{ESTADO['conexoes_ativas']:04d}",
                        "timestamp": f"{int(time.time()):010d}",
                    }
                ).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            else:
                corpo = gerar_html_shopnow(algoritmo_lb=algoritmo_lb, resumo_lb=resumo_lb).encode("utf-8")
                content_type = "text/html; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("X-App-Server", ESTADO["nome"])
            self.end_headers()
            self.wfile.write(corpo)
        finally:
            with LOCK:
                ESTADO["conexoes_ativas"] -= 1


def iniciar_servidor():
    parser = argparse.ArgumentParser(description="Instancia do E-commerce ShopNow")
    parser.add_argument("--nome", default=ESTADO["nome"], help="Nome da instancia (ex: app_server1)")
    parser.add_argument("--porta", type=int, default=ESTADO["porta"], help="Porta HTTP (ex: 8001)")
    parser.add_argument("--delay", type=int, default=ESTADO["delay_ms"], help="Delay simulado em ms")
    args = parser.parse_args()

    ESTADO["nome"] = args.nome
    ESTADO["porta"] = args.porta
    ESTADO["delay_ms"] = args.delay

    servidor = ThreadingHTTPServer(("0.0.0.0", args.porta), ShopNowHandler)
    print("=" * 75)
    print(f"[SHOPNOW] Instancia '{ESTADO['nome']}' rodando em http://127.0.0.1:{ESTADO['porta']}")
    print("=" * 75)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ESTADO['nome']}] Encerrando instancia...")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar_servidor()
