"""
Trabalhador (PULL), baseado no taskwork.py da Fig. 4.23.

Novidades em relacao ao original (que so fingia trabalhar com sleep e
imprimia a carga):
  - faz um trabalho de verdade: conta quantos numeros primos existem ate
    carga * 1000 (quanto maior a carga, mais demorado) - ou, com
    --modo sleep, dorme carga * 0.01 s como no original
  - envia o resultado ao coletor (PUSH), com o tempo gasto e a maquina
  - escuta o canal de controle do coletor (SUB) e encerra sozinho quando
    todas as tarefas terminam (no original rodava para sempre)

Uso: python trabalhador.py NOME [--fontes IP1:4567,IP2:4568] [--coletor IP]
"""
import argparse
import math
import pickle
import socket
import time

import zmq

from constPipe import *  #-


def contar_primos(limite):
    """Divisao por tentativa ate 'limite' (trabalho de CPU proporcional a carga)."""
    total = 0
    for n in range(2, limite + 1):
        if all(n % d for d in range(2, math.isqrt(n) + 1)):
            total += 1
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("me", help="nome do trabalhador")
    ap.add_argument("--fontes", default=f"{SRC1}:{PORT1},{SRC2}:{PORT2}")
    ap.add_argument("--coletor", default=SINK)
    ap.add_argument("--modo", choices=["cpu", "sleep"], default="cpu")
    a = ap.parse_args()
    me = a.me + "@" + socket.gethostname()

    context = zmq.Context()
    r = context.socket(zmq.PULL)                  # create a pull socket
    for f in a.fontes.split(","):
        r.connect("tcp://" + f)                   # connect to each task source
    resultados = context.socket(zmq.PUSH)         # envia ao coletor
    resultados.connect("tcp://" + a.coletor + ":" + PORT_RESULT)
    controle = context.socket(zmq.SUB)            # aviso de fim
    controle.connect("tcp://" + a.coletor + ":" + PORT_CTRL)
    controle.setsockopt_string(zmq.SUBSCRIBE, "FIM")

    poller = zmq.Poller()
    poller.register(r, zmq.POLLIN)
    poller.register(controle, zmq.POLLIN)
    print(me + " started", flush=True)

    feitas = 0
    while True:
        prontos = dict(poller.poll())
        if controle in prontos:
            controle.recv()
            break
        if r in prontos:
            fonte, tid, carga = pickle.loads(r.recv())   # receive work from a source
            inicio = time.perf_counter()
            if a.modo == "cpu":
                res = contar_primos(carga * 1000)
            else:
                time.sleep(carga * 0.01)                 # pretend to work (original)
                res = None
            dt = time.perf_counter() - inicio
            feitas += 1
            print(f"{me} fez tarefa {tid} da fonte {fonte} (carga {carga}) "
                  f"-> {res} primos em {dt:.3f}s", flush=True)
            resultados.send(pickle.dumps({"tipo": "resultado", "fonte": fonte, "id": tid,
                                          "carga": carga, "resultado": res,
                                          "trabalhador": me, "tempo": dt}))
    print(f"{me} encerrado: {feitas} tarefas", flush=True)
    for sk in (r, resultados, controle):
        sk.close(linger=1000)
    context.term()


if __name__ == "__main__":
    main()
