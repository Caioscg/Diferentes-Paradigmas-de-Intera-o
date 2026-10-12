"""
Servidor (padrao requisicao-resposta), baseado no server.py da Fig. 4.21.

Novidades em relacao ao original:
  - varias operacoes (SOMA, DIVIDE, FATORIAL, PRIMO, ...), com mensagens em
    JSON:  {"op": "SOMA", "args": [2, 3]}  ->  {"ok": true, "resultado": 5, ...}
  - comandos AJUDA (lista as operacoes) e ESTATISTICAS (requisicoes atendidas)
  - a resposta informa a maquina e a thread que atenderam (util na AWS)
  - modo com POOL de threads (--workers N): um socket ROUTER recebe os
    clientes e um DEALER distribui as requisicoes entre N threads REP
    (zmq.proxy), atendendo varios clientes ao mesmo tempo
  - continua aceitando os clientes originais: mensagem que nao e JSON e
    respondida como no original (texto + "*"), e "STOP" encerra o servidor

Uso: python servidor.py [--workers 4] [--atraso 0]
"""
import argparse
import json
import socket
import threading
import time
from collections import Counter

import zmq

import operacoes
from constCS import *  #-

MAQUINA = socket.gethostname()


class Estatisticas:
    def __init__(self):
        self.lock = threading.Lock()
        self.por_operacao = Counter()
        self.inicio = time.time()

    def registrar(self, op):
        with self.lock:
            self.por_operacao[op] += 1

    def resumo(self):
        with self.lock:
            return {"total": sum(self.por_operacao.values()),
                    "por_operacao": dict(self.por_operacao),
                    "ativo_ha_segundos": round(time.time() - self.inicio, 1)}


def tratar(msg, stats, worker, atraso):
    """Processa uma mensagem. Devolve (resposta em bytes, deve_parar)."""
    texto = bytes.decode(msg)
    try:
        pedido = json.loads(texto)
        assert isinstance(pedido, dict)
    except (ValueError, AssertionError):
        # protocolo original (Fig. 4.21): texto simples
        stats.registrar("TEXTO")
        if "STOP" in texto:
            return b"servidor encerrado", True
        return str.encode(texto + "*"), False

    op = str(pedido.get("op", "")).upper()
    args = pedido.get("args", [])
    stats.registrar(op)
    if atraso:
        time.sleep(atraso)                       # simula processamento demorado
    resposta = {"servidor": MAQUINA, "worker": worker}
    parar = False
    if op == "AJUDA":
        resposta.update(ok=True, resultado=sorted(operacoes.OPERACOES) + ["AJUDA", "ESTATISTICAS", "STOP"])
    elif op == "ESTATISTICAS":
        resposta.update(ok=True, resultado=stats.resumo())
    elif op == "STOP":
        resposta.update(ok=True, resultado="servidor encerrado")
        parar = True
    else:
        try:
            resposta.update(ok=True, resultado=operacoes.executar(op, args))
        except ValueError as e:
            resposta.update(ok=False, erro=str(e))
    print(f"[{worker}] {op} {args} -> {resposta.get('resultado', resposta.get('erro'))}", flush=True)
    return str.encode(json.dumps(resposta)), parar


def servidor_simples(context, enderecos, stats, atraso):
    """Igual ao original: um unico socket REP, uma requisicao por vez."""
    s = context.socket(zmq.REP)                  # create reply socket
    for e in enderecos:
        s.bind(e)                                # bind socket to address
    while True:
        msg = s.recv()                           # wait for incoming message
        resposta, parar = tratar(msg, stats, "principal", atraso)
        s.send(resposta)                         # send reply
        if parar:
            break


def servidor_pool(context, enderecos, stats, atraso, n_workers):
    """ROUTER (clientes) <-> DEALER (threads REP), com zmq.proxy."""
    frontend = context.socket(zmq.ROUTER)        # recebe dos clientes
    for e in enderecos:
        frontend.bind(e)
    backend = context.socket(zmq.DEALER)         # distribui entre as threads
    backend.bind("inproc://workers")
    controle = context.socket(zmq.PULL)          # para encerrar o proxy (STOP)
    controle.bind("inproc://controle")

    def worker(n):
        s = context.socket(zmq.REP)
        s.connect("inproc://workers")
        ctl = context.socket(zmq.PUSH)
        ctl.connect("inproc://controle")
        try:
            while True:
                resposta, parar = tratar(s.recv(), stats, f"thread-{n}", atraso)
                s.send(resposta)
                if parar:
                    ctl.send(b"TERMINATE")       # pede ao proxy para terminar
        except zmq.ContextTerminated:
            pass
        finally:
            s.close(linger=0)
            ctl.close(linger=0)

    for n in range(1, n_workers + 1):
        threading.Thread(target=worker, args=(n,), daemon=True).start()

    # Proxy: repassa as mensagens nos dois sentidos (o mesmo que zmq.proxy,
    # mas escrito com Poller para tambem escutar o socket de controle).
    poller = zmq.Poller()
    for sk in (frontend, backend, controle):
        poller.register(sk, zmq.POLLIN)
    while True:
        prontos = dict(poller.poll())
        if frontend in prontos:                  # cliente -> alguma thread livre
            backend.send_multipart(frontend.recv_multipart())
        if backend in prontos:                   # resposta da thread -> cliente certo
            frontend.send_multipart(backend.recv_multipart())
        if controle in prontos:                  # alguma thread recebeu STOP
            while backend.poll(200):             # entrega as respostas pendentes
                frontend.send_multipart(backend.recv_multipart())
            break
    for sk in (frontend, backend, controle):
        sk.close(linger=500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1,
                    help="threads de atendimento (1 = igual ao original)")
    ap.add_argument("--atraso", type=float, default=0.0,
                    help="segundos de processamento simulado por requisicao")
    a = ap.parse_args()

    context = zmq.Context()
    # "*" = todas as interfaces da maquina (na AWS aceita o IP privado e o publico)
    enderecos = ["tcp://*:" + PORT1, "tcp://*:" + PORT2]
    stats = Estatisticas()
    print(f"[servidor {MAQUINA}] portas {PORT1} e {PORT2}, {a.workers} worker(s)", flush=True)
    if a.workers <= 1:
        servidor_simples(context, enderecos, stats, a.atraso)
    else:
        servidor_pool(context, enderecos, stats, a.atraso, a.workers)
    context.term()
    print("[servidor] encerrado:", stats.resumo())


if __name__ == "__main__":
    main()
