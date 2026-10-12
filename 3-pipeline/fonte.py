"""
Fonte de tarefas (PUSH), baseada no tasksrc.py da Fig. 4.23.

Novidades em relacao ao original (100 tarefas fixas, 1 por segundo):
  - quantidade de tarefas e intervalo configuraveis (--tarefas, --intervalo)
  - cada tarefa tem um identificador: (fonte, id, carga)
  - antes de comecar, avisa o coletor quantas tarefas vai gerar, para ele
    saber quando todos os resultados chegaram
  - espera alguns segundos (--espera) para os trabalhadores conectarem; sem
    isso, o primeiro trabalhador a conectar recebe quase todas as tarefas

Uso: python fonte.py 1|2 [--tarefas 30] [--intervalo 0] [--coletor IP]
"""
import argparse
import pickle
import random
import time

import zmq

from constPipe import *  #-


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("me", choices=["1", "2"], help="numero da fonte")
    ap.add_argument("--tarefas", type=int, default=30)
    ap.add_argument("--intervalo", type=float, default=0.0, help="segundos entre tarefas")
    ap.add_argument("--espera", type=float, default=3.0,
                    help="segundos esperando os trabalhadores conectarem")
    ap.add_argument("--coletor", default=SINK, help="IP do coletor")
    a = ap.parse_args()
    me = a.me

    context = zmq.Context()
    s = context.socket(zmq.PUSH)                  # create a push socket
    prt = PORT1 if me == "1" else PORT2           # check task source port
    s.bind("tcp://*:" + prt)                      # bind socket to address

    coletor = context.socket(zmq.PUSH)            # avisa o coletor
    coletor.connect("tcp://" + a.coletor + ":" + PORT_RESULT)
    coletor.send(pickle.dumps({"tipo": "inicio", "fonte": me, "tarefas": a.tarefas}))

    print(f"[fonte {me}] porta {prt}: esperando {a.espera}s pelos trabalhadores...", flush=True)
    time.sleep(a.espera)
    for i in range(a.tarefas):                    # generate workloads
        workload = random.randint(1, 100)         # compute workload
        s.send(pickle.dumps((me, i, workload)))   # send workload to worker
        time.sleep(a.intervalo)
    print(f"[fonte {me}] {a.tarefas} tarefas enviadas", flush=True)
    s.close()                                     # (espera as tarefas serem entregues)
    coletor.close()
    context.term()


if __name__ == "__main__":
    main()
