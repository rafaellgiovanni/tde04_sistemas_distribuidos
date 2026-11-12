# ShopNow — Escalabilidade Horizontal e Balanceamento de Carga (TDE 04)

Projeto prático de **Sistemas Distribuídos** simulando a infraestrutura escalável do e-commerce **ShopNow** durante picos de acesso da **Black Friday**, composto por **3 instâncias independentes da aplicação** e um **Balanceador de Carga (Reverse Proxy)** na frente delas com múltiplos algoritmos, detecção de falhas (*Health Check* + *Failover*) e testes de carga com **Apache Benchmark (`ab`)**.

---

## Arquitetura do Sistema

```text
                       +----------------------------+
                       |  Cliente (Navegador / ab)  |
                       +-------------+--------------+
                                     |
                                     | HTTP (:8080 / :80)
                                     v
                       +----------------------------+
                       |    Balanceador de Carga    |  <-- Nginx Proxy / Python LB
                       | (Round Robin / Least Conn  |      + Health Check & Failover
                       |   Weighted / IP Hash)      |
                       +-------------+--------------+
                        /            |             \
                       /             |              \
                      v              v               v
          +---------------+  +---------------+  +---------------+
          |  app_server1  |  |  app_server2  |  |  app_server3  |
          | Python (:8001)|  | Python (:8002)|  | Python (:8003)|
          | AZ: sa-east-1a|  | AZ: sa-east-1b|  | AZ: sa-east-1c|
          +---------------+  +---------------+  +---------------+
```

---

## Algoritmos de Balanceamento Implementados

O projeto implementa os algoritmos de balanceamento de carga tanto em código (`load_balancer.py`) quanto nas configurações do Nginx (`nginx/nginx.conf` e `nginx/nginx_least_conn.conf`):

1. **Round Robin (`round_robin`)**:
   - Distribui as requisições sequencialmente e de forma circular entre todas as instâncias ativas (`app_server1` -> `app_server2` -> `app_server3`), garantindo divisão igualitária (33,3% para cada servidor).
2. **Least Connections (`least_conn`)**:
   - Verifica em tempo real quantas conexões simultâneas cada servidor possui abertas e encaminha a nova requisição para a instância com menor carga ativa.
3. **Weighted Round Robin (`weighted`)**:
   - Distribui o tráfego proporcionalmente ao peso configurado de cada servidor (`app_server1` peso 3, `app_server2` peso 2 e `app_server3` peso 1).
4. **IP Hash (`ip_hash`)**:
   - Calcula um hash do IP do cliente para manter afinidade de sessão na mesma instância enquanto ela estiver saudável.

---

## Simulação de Falhas e Tolerância a Falhas (Failover)

- O balanceador possui **Health Check ativo** que consulta a rota `/health` das 3 instâncias periodicamente.
- Caso um servidor caia ou retorne erro (`HTTP 503` / `Connection Refused`), o balanceador marca a instância como inativa e redireciona imediatamente a requisição para outra instância saudável (*Failover*), mantendo o sistema disponível.

---

## Como Executar

### 1. Iniciar as 3 instâncias do ShopNow
```bash
python app_server.py --nome app_server1 --porta 8001
python app_server.py --nome app_server2 --porta 8002
python app_server.py --nome app_server3 --porta 8003
```

### 2. Iniciar o Balanceador de Carga
```bash
python load_balancer.py --porta 8080 --algoritmo round_robin
```
*(Ou via Docker Compose com Nginx Proxy: `docker compose up --build -d`)*

### 3. Simular Carga com Apache Benchmark (`ab`)
```bash
ab -l -n 300 -c 15 http://127.0.0.1:8080/api
```

### 4. Consultar Relatório de Distribuição entre as Instâncias
```bash
python relatorio_cluster.py
```
