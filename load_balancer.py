import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib import error, parse, request

PORTA_LB = 8080

# Lista das 3 instancias do site ShopNow
SERVIDORES = [
    {
        "nome": "app_server1",
        "host": "127.0.0.1",
        "porta": 8001,
        "url": "http://127.0.0.1:8001",
        "peso": 3,
        "ativo": True,
        "conexoes_ativas": 0,
        "total_encaminhadas": 0,
        "falhas_detectadas": 0,
    },
    {
        "nome": "app_server2",
        "host": "127.0.0.1",
        "porta": 8002,
        "url": "http://127.0.0.1:8002",
        "peso": 2,
        "ativo": True,
        "conexoes_ativas": 0,
        "total_encaminhadas": 0,
        "falhas_detectadas": 0,
    },
    {
        "nome": "app_server3",
        "host": "127.0.0.1",
        "porta": 8003,
        "url": "http://127.0.0.1:8003",
        "peso": 1,
        "ativo": True,
        "conexoes_ativas": 0,
        "total_encaminhadas": 0,
        "falhas_detectadas": 0,
    },
]

ALGORITMOS_NOMES = {
    "round_robin": "Round Robin (Circular)",
    "least_conn": "Least Connections (Menor Conexao)",
    "weighted": "Weighted Round Robin (Pesos 3:2:1)",
    "ip_hash": "IP Hash (Afinidade por IP)",
}

ESTADO_LB = {
    "algoritmo": "round_robin",
    "indice_rr": 0,
    "indice_weighted": 0,
    "total_requisicoes": 0,
}

LOCK_LB = threading.Lock()


def escolher_servidor(ip_cliente: str) -> dict | None:
    """
    Seleciona a proxima instancia saudavel do ShopNow de acordo com o algoritmo ativo:
      1. round_robin : Alterna igualmente entre todos os servidores ativos (1 -> 2 -> 3)
      2. least_conn  : Escolhe o servidor ativo com menor numero de conexoes simultaneas
      3. weighted    : Distribui proporcionalmente aos pesos (app_server1=3, app_server2=2, app_server3=1)
      4. ip_hash     : Calcula hash do IP do cliente para manter afinidade de servidor
    """
    with LOCK_LB:
        ativos = [s for s in SERVIDORES if s["ativo"]]
        if not ativos:
            return None

        alg = ESTADO_LB["algoritmo"]

        if alg == "least_conn":
            # Escolhe o servidor com menos conexoes ativas (desempata pelo menor total encaminhado)
            escolhido = min(ativos, key=lambda s: (s["conexoes_ativas"], s["total_encaminhadas"]))
            return escolhido

        if alg == "weighted":
            # Constroi sequencia ponderada pelos pesos dos servidores ativos
            sequencia_ponderada = []
            for srv in ativos:
                sequencia_ponderada.extend([srv] * srv["peso"])
            idx = ESTADO_LB["indice_weighted"] % len(sequencia_ponderada)
            ESTADO_LB["indice_weighted"] += 1
            return sequencia_ponderada[idx]

        if alg == "ip_hash":
            hash_int = int(hashlib.md5(ip_cliente.encode("utf-8")).hexdigest(), 16)
            return ativos[hash_int % len(ativos)]

        # Padrao: Round Robin
        idx = ESTADO_LB["indice_rr"] % len(ativos)
        ESTADO_LB["indice_rr"] += 1
        return ativos[idx]


def verificar_saude_servidores():
    """Thread de Health Check: verifica periodicamente se cada instancia esta viva."""
    while True:
        for srv in SERVIDORES:
            try:
                req = request.Request(f"{srv['url']}/health", method="GET")
                with request.urlopen(req, timeout=1.2) as resp:
                    estava_inativo = not srv["ativo"]
                    srv["ativo"] = resp.status == 200
                    if estava_inativo and srv["ativo"]:
                        print(f"[HEALTH CHECK] RECUPERADO: {srv['nome']} ({srv['url']}) voltou a ficar ONLINE!")
            except Exception:
                if srv["ativo"]:
                    print(
                        f"[HEALTH CHECK] FALHA DETECTADA: {srv['nome']} ({srv['url']}) "
                        f"esta OFFLINE! Redirecionando trafego para as instancias saudaveis..."
                    )
                srv["ativo"] = False
        time.sleep(1.5)


def montar_painel_controle_html() -> str:
    """Gera o painel visual interativo do Balanceador de Carga para apresentacao no navegador."""
    alg_atual = ESTADO_LB["algoritmo"]
    total_geral = max(sum(s["total_encaminhadas"] for s in SERVIDORES), 1)

    botoes_alg = ""
    for chave, descricao in ALGORITMOS_NOMES.items():
        ativo_css = (
            "background:#f59e0b;color:#0f172a;font-weight:800;border:2px solid #fde68a;"
            if chave == alg_atual
            else "background:#334155;color:#f8fafc;"
        )
        botoes_alg += (
            f'<a href="/lb-config?algoritmo={chave}" '
            f'style="text-decoration:none;padding:8px 12px;border-radius:6px;font-size:13px;{ativo_css}">'
            f"{descricao}</a> "
        )

    linhas_servidores = ""
    for srv in SERVIDORES:
        pct = (srv["total_encaminhadas"] / total_geral) * 100 if sum(s["total_encaminhadas"] for s in SERVIDORES) > 0 else 0
        status_badge = (
            '<span style="background:#16a34a;color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;">🟢 ONLINE</span>'
            if srv["ativo"]
            else '<span style="background:#dc2626;color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;">🔴 EM FALHA (OFFLINE)</span>'
        )
        acao_texto = "🔴 Simular Falha (Derrubar)" if srv["ativo"] else "🟢 Recuperar Servidor (Religar)"
        acao_cor = "#ef4444" if srv["ativo"] else "#22c55e"
        linhas_servidores += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;padding:10px 14px;border-radius:8px;margin-top:8px;border:1px solid #334155;">
            <div>
                <strong style="font-size:15px;">{srv['nome']}</strong>
                <span style="color:#94a3b8;font-size:13px;">({srv['url']} | Peso: {srv['peso']})</span>
                &nbsp; {status_badge}
            </div>
            <div style="font-size:14px;">
                Atendidas: <strong style="color:#38bdf8;">{srv['total_encaminhadas']}</strong> ({pct:.1f}%) |
                Ativas: <strong>{srv['conexoes_ativas']}</strong> |
                Falhas: <strong style="color:#f87171;">{srv['falhas_detectadas']}</strong>
                &nbsp;&nbsp;
                <a href="/lb-config?toggle_servidor={srv['nome']}"
                   style="background:{acao_cor};color:#fff;text-decoration:none;padding:5px 10px;border-radius:5px;font-size:12px;font-weight:bold;">
                   {acao_texto}
                </a>
            </div>
        </div>
        """

    return f"""
    <div style="background:#1e293b;border:2px solid #f59e0b;border-radius:12px;padding:16px;margin-bottom:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
            <div>
                <h2 style="font-size:17px;color:#fbbf24;">⚖️ Painel do Balanceador de Carga (TDE 04 - ShopNow)</h2>
                <p style="font-size:12px;color:#cbd5e1;">Troque o algoritmo ou simule a queda de servidores ao vivo abaixo:</p>
            </div>
            <a href="/lb-config?zerar=1" style="background:#475569;color:#fff;text-decoration:none;padding:6px 12px;border-radius:6px;font-size:12px;">
                🔄 Zerar Contadores
            </a>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
            {botoes_alg}
        </div>
        {linhas_servidores}
    </div>
    """


class LoadBalancerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def redirecionar_home(self):
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        # Endpoint de configuracao ao vivo do Balanceador (troca de algoritmo, simulacao de falha e reset)
        if self.path.startswith("/lb-config"):
            query = parse.parse_qs(parse.urlparse(self.path).query)

            if "algoritmo" in query:
                novo_alg = query["algoritmo"][0]
                if novo_alg in ALGORITMOS_NOMES:
                    with LOCK_LB:
                        ESTADO_LB["algoritmo"] = novo_alg
                    print(f"[BALANCEADOR] Algoritmo alterado para: {ALGORITMOS_NOMES[novo_alg]}")

            if "toggle_servidor" in query:
                nome_alvo = query["toggle_servidor"][0]
                for srv in SERVIDORES:
                    if srv["nome"] == nome_alvo:
                        try:
                            req = request.Request(f"{srv['url']}/toggle-falha", method="GET")
                            with request.urlopen(req, timeout=1.5) as resp:
                                dados = json.loads(resp.read().decode("utf-8"))
                                srv["ativo"] = not dados["em_falha"]
                        except Exception:
                            srv["ativo"] = not srv["ativo"]
                        estado_txt = "ONLINE" if srv["ativo"] else "EM FALHA (OFFLINE)"
                        print(f"[SIMULACAO DE FALHA] Servidor {srv['nome']} -> {estado_txt}")

            if "zerar" in query:
                with LOCK_LB:
                    ESTADO_LB["total_requisicoes"] = 0
                    for srv in SERVIDORES:
                        srv["total_encaminhadas"] = 0
                        srv["falhas_detectadas"] = 0
                print("[BALANCEADOR] Contadores de requisicoes zerados.")

            self.redirecionar_home()
            return

        # Endpoint JSON de metricas do Balanceador (util para scripts de teste e conferencia)
        if self.path.startswith("/lb-status"):
            payload = json.dumps(
                {
                    "algoritmo_codigo": ESTADO_LB["algoritmo"],
                    "algoritmo_nome": ALGORITMOS_NOMES[ESTADO_LB["algoritmo"]],
                    "total_requisicoes": ESTADO_LB["total_requisicoes"],
                    "servidores": SERVIDORES,
                },
                indent=2,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Encaminhamento (Reverse Proxy) com Failover Automatico entre as instancias
        ip_cliente = self.client_address[0]
        tentativas = 0
        max_tentativas = len(SERVIDORES)

        while tentativas < max_tentativas:
            tentativas += 1
            srv = escolher_servidor(ip_cliente)

            if srv is None:
                erro_html = (
                    "<h1>503 Service Unavailable</h1>"
                    "<p>Todas as instancias do ShopNow estao desligadas/em falha!</p>"
                    '<p><a href="/lb-config?toggle_servidor=app_server1">Religar app_server1</a></p>'
                ).encode("utf-8")
                self.send_response(503)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(erro_html)))
                self.end_headers()
                self.wfile.write(erro_html)
                return

            with LOCK_LB:
                srv["conexoes_ativas"] += 1

            try:
                url_destino = f"{srv['url']}{self.path}"
                req_proxy = request.Request(url_destino, method="GET")
                req_proxy.add_header("X-Load-Balancer-Algorithm", ALGORITMOS_NOMES[ESTADO_LB["algoritmo"]])
                req_proxy.add_header("X-Forwarded-For", ip_cliente)

                with request.urlopen(req_proxy, timeout=2.0) as resp:
                    corpo = resp.read()
                    content_type = resp.headers.get("Content-Type", "text/html; charset=utf-8")

                    with LOCK_LB:
                        srv["total_encaminhadas"] += 1
                        ESTADO_LB["total_requisicoes"] += 1

                    # Se for pagina HTML, injeta o painel interativo do Balanceador
                    if "text/html" in content_type:
                        painel_html = montar_painel_controle_html().encode("utf-8")
                        corpo = corpo.replace(b'<h2 style="font-size: 18px;', painel_html + b'<h2 style="font-size: 18px;')

                    print(
                        f"[LB #{ESTADO_LB['total_requisicoes']:04d}] "
                        f"Algoritmo: {ESTADO_LB['algoritmo']:<11} -> "
                        f"Encaminhado para {srv['nome']} (:{srv['porta']}) | "
                        f"Total no servidor: {srv['total_encaminhadas']}"
                    )

                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(corpo)))
                    self.send_header("X-Routed-Server", srv["nome"])
                    self.send_header("X-LB-Algorithm", ESTADO_LB["algoritmo"])
                    self.end_headers()
                    self.wfile.write(corpo)
                    return

            except (error.HTTPError, error.URLError, TimeoutError, ConnectionError) as exc:
                with LOCK_LB:
                    srv["ativo"] = False
                    srv["falhas_detectadas"] += 1
                print(
                    f"[FAILOVER AUTOMATICO] Falha ao contatar {srv['nome']} ({exc}). "
                    f"Redirecionando requisicao imediatamente para outra instancia ativa..."
                )
            finally:
                with LOCK_LB:
                    srv["conexoes_ativas"] = max(0, srv["conexoes_ativas"] - 1)

        # Caso todas as tentativas falhem
        msg = b"502 Bad Gateway - Nenhuma instancia disponivel no cluster ShopNow."
        self.send_response(502)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)


def iniciar_balanceador():
    parser = argparse.ArgumentParser(description="Balanceador de Carga ShopNow (TDE 04)")
    parser.add_argument("--porta", type=int, default=PORTA_LB, help="Porta do Balanceador (padrao: 8080)")
    parser.add_argument(
        "--algoritmo",
        choices=list(ALGORITMOS_NOMES.keys()),
        default="round_robin",
        help="Algoritmo inicial do balanceador",
    )
    args = parser.parse_args()

    ESTADO_LB["algoritmo"] = args.algoritmo

    # Inicia thread de monitoramento de saude (Health Check) das 3 instancias
    thread_hc = threading.Thread(target=verificar_saude_servidores, daemon=True)
    thread_hc.start()

    servidor_lb = ThreadingHTTPServer(("0.0.0.0", args.porta), LoadBalancerHandler)
    print("=" * 85)
    print(f"[BALANCEADOR SHOPNOW] Rodando em: http://127.0.0.1:{args.porta}")
    print(f"[ALGORITMO INICIAL]   {ALGORITMOS_NOMES[ESTADO_LB['algoritmo']]}")
    print("[INSTANCIAS ALVO]     app_server1 (:8001), app_server2 (:8002), app_server3 (:8003)")
    print("=" * 85)

    try:
        servidor_lb.serve_forever()
    except KeyboardInterrupt:
        print("\n[BALANCEADOR] Encerrando balanceador de carga...")
    finally:
        servidor_lb.server_close()


if __name__ == "__main__":
    iniciar_balanceador()
