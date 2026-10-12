"""
Coletor de resultados (sink) - componente NOVO do pipeline.

No original, os resultados dos trabalhadores eram so impressos e se perdiam.
O coletor fecha o pipeline  fontes -> trabalhadores -> coletor:
  - recebe (PULL) o aviso de inicio de cada fonte e os resultados das tarefas
  - quando todas as tarefas de todas as fontes chegam, mostra um resumo:
    tempo total, vazao, e quantas tarefas/quanto tempo cada trabalhador fez
    (mostra o balanceamento de carga feito pelo ZeroMQ)
  - publica "FIM" (PUB) para os trabalhadores encerrarem

Uso: python coletor.py [--fontes 2]
"""
import argparse
import pickle
import time
from collections import defaultdict

import zmq

from constPipe import *  #-


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=int, default=2, help="quantas fontes vao enviar tarefas")
    a = ap.parse_args()

    context = zmq.Context()
    r = context.socket(zmq.PULL)
    r.bind("tcp://*:" + PORT_RESULT)              # resultados e avisos de inicio
    controle = context.socket(zmq.PUB)
    controle.bind("tcp://*:" + PORT_CTRL)         # aviso de fim aos trabalhadores
    print(f"[coletor] esperando {a.fontes} fonte(s) na porta {PORT_RESULT}", flush=True)

    esperadas = {}                                # fonte -> numero de tarefas
    recebidas = 0
    por_trab = defaultdict(lambda: [0, 0.0])      # trabalhador -> [tarefas, tempo]
    inicio = None
    while len(esperadas) < a.fontes or recebidas < sum(esperadas.values()):
        msg = pickle.loads(r.recv())
        if msg["tipo"] == "inicio":
            esperadas[msg["fonte"]] = msg["tarefas"]
            print(f"[coletor] fonte {msg['fonte']} vai enviar {msg['tarefas']} tarefas", flush=True)
            continue
        if inicio is None:                        # inicio da 1a tarefa processada
            inicio = time.perf_counter() - msg["tempo"]
        recebidas += 1
        por_trab[msg["trabalhador"]][0] += 1
        por_trab[msg["trabalhador"]][1] += msg["tempo"]
        print(f"[coletor] {recebidas}/{sum(esperadas.values())}: tarefa {msg['id']} da fonte "
              f"{msg['fonte']} feita por {msg['trabalhador']} -> {msg['resultado']}", flush=True)
    total = time.perf_counter() - inicio

    trabalho = sum(t for _, t in por_trab.values())
    print(f"\n[coletor] {recebidas} tarefas concluidas em {total:.2f} s "
          f"({recebidas / total:.1f} tarefas/s)")
    print(f"[coletor] soma do tempo de trabalho: {trabalho:.2f} s "
          f"-> paralelismo efetivo {trabalho / total:.2f}x")
    for nome, (n, t) in sorted(por_trab.items()):
        print(f"           {nome:28} {n:4} tarefas  {t:7.2f} s trabalhando")

    for _ in range(3):                            # avisa os trabalhadores
        controle.send_string("FIM")
        time.sleep(0.3)
    r.close()
    controle.close()
    context.term()


if __name__ == "__main__":
    main()
