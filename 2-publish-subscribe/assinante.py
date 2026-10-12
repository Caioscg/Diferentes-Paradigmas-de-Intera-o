"""
Assinante, baseado no subscriber.py da Fig. 4.22.

Novidades em relacao ao original (que assinava so TIME e lia 5 mensagens):
  - escolhe os topicos (--topicos CLIMA,ALERTA; padrao: todos)
  - conecta em varios publicadores ao mesmo tempo (--hosts IP1,IP2) ou no proxy
  - numero de mensagens configuravel (-n; 0 = ate Ctrl+C)
  - ao terminar, mostra um resumo: mensagens por topico e por publicador,
    temperatura media/minima/maxima recebida

Uso:
  python assinante.py [--hosts IP1,IP2] [--topicos CLIMA,TIME] [-n 10]
  python assinante.py --proxy IP [--topicos ALERTA]
"""
import argparse
import json
from collections import Counter

import zmq

from constPS import *  #-


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", default=HOST + ":" + PORT,
                    help="publicadores IP[:porta], separados por virgula")
    ap.add_argument("--proxy", metavar="IP", help="recebe atraves do proxy")
    ap.add_argument("--topicos", default="", help="ex.: CLIMA,ALERTA (vazio = todos)")
    ap.add_argument("-n", type=int, default=0, help="mensagens a receber (0 = sem fim)")
    a = ap.parse_args()

    context = zmq.Context()
    s = context.socket(zmq.SUB)                  # create a subscriber socket
    if a.proxy:
        destinos = [a.proxy + ":" + PORT_XPUB]
    else:
        destinos = [h if ":" in h else h + ":" + PORT for h in a.hosts.split(",")]
    for d in destinos:
        s.connect("tcp://" + d)                  # connect to the server(s)
    topicos = [t.strip().upper() for t in a.topicos.split(",") if t.strip()] or [""]
    for t in topicos:
        s.setsockopt_string(zmq.SUBSCRIBE, t)    # subscribe ("" = tudo)
    print(f"[assinante] conectado a {destinos}, topicos: {topicos if topicos != [''] else 'todos'}",
          flush=True)

    por_topico, por_publicador, temps = Counter(), Counter(), []
    recebidas = 0
    try:
        while a.n == 0 or recebidas < a.n:
            msg = s.recv_string()                # receive a message
            topico, _, corpo = msg.partition(" ")
            recebidas += 1
            por_topico[topico] += 1
            try:
                dados = json.loads(corpo)
            except ValueError:                   # TIME vem como texto (formato original)
                print(f"{topico:8} {corpo}", flush=True)
                continue
            por_publicador[dados.get("publicador")] += 1
            if topico == "CLIMA":
                temps.append(dados["temperatura"])
                info = f"{dados['temperatura']:5.1f} C  {dados['umidade']:5.1f}% umidade"
            elif topico == "COTACAO":
                info = f"US$ 1 = R$ {dados['dolar']:.4f}   BTC = R$ {dados['bitcoin']:,.2f}"
            else:
                info = dados.get("mensagem", corpo)
            print(f"{topico:8} [{dados['publicador']} {dados['hora']}] {info}", flush=True)
    except KeyboardInterrupt:
        pass

    print(f"\nResumo: {recebidas} mensagens | por topico: {dict(por_topico)}"
          f" | por publicador: {dict(por_publicador)}")
    if temps:
        print(f"Temperatura: media {sum(temps) / len(temps):.1f} C, "
              f"min {min(temps):.1f} C, max {max(temps):.1f} C")
    s.close()
    context.term()


if __name__ == "__main__":
    main()
