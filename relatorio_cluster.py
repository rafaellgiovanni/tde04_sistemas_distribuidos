import json
import sys
from urllib import request

URL_LB = "http://127.0.0.1:8080"


def mostrar_resumo():
    try:
        with request.urlopen(f"{URL_LB}/lb-status", timeout=2.0) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except Exception as erro:
        print(f"[ERRO] Nao foi possivel consultar o Balanceador em {URL_LB}: {erro}")
        return

    print("\n" + "=" * 88)
    print(f"RESUMO DO BALANCEADOR DE CARGA SHOPNOW | Algoritmo: {dados['algoritmo_nome']}")
    print("=" * 88)
    print(
        f"{'INSTANCIA':<14} | {'PORTA':<6} | {'PESO':<5} | {'STATUS':<16} | "
        f"{'REQUISICOES ATENDIDAS':<22} | {'FALHAS'}"
    )
    print("-" * 88)

    total = max(dados["total_requisicoes"], 1)
    for srv in dados["servidores"]:
        status = "ONLINE (UP)" if srv["ativo"] else "EM FALHA (DOWN)"
        qtd = srv["total_encaminhadas"]
        pct = (qtd / total) * 100 if dados["total_requisicoes"] > 0 else 0.0
        print(
            f"{srv['nome']:<14} | {srv['porta']:<6} | {srv['peso']:<5} | {status:<16} | "
            f"{qtd:>6} ({pct:>5.1f}%)       | {srv['falhas_detectadas']}"
        )

    print("-" * 88)
    print(f"TOTAL DE REQUISICOES PROCESSADAS PELO CLUSTER: {dados['total_requisicoes']}")
    print("=" * 88 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        acao = sys.argv[1]
        try:
            request.urlopen(f"{URL_LB}/lb-config?{acao}", timeout=2.0).read()
        except Exception:
            pass
    mostrar_resumo()
