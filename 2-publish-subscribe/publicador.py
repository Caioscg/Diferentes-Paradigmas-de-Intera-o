"""
Publicador, baseado no publisher.py da Fig. 4.22.

Novidades em relacao ao original (que so publicava "TIME <hora>" a cada 5 s):
  - varios topicos:
      TIME     hora atual (como no original)
      CLIMA    temperatura e umidade simuladas (variam aos poucos)
      COTACAO  cotacao simulada do dolar e do bitcoin
      ALERTA   publicado quando a temperatura passa do limite (--limite)
  - mensagens no formato "TOPICO {json}" (o filtro do ZeroMQ usa o inicio da
    mensagem, entao o assinante original continua recebendo o TIME)
  - cada publicador tem um nome (--nome), para o assinante saber de quem veio
  - pode publicar direto (bind) ou atraves do proxy (--proxy IP)

Uso: python publicador.py [--nome sala1] [--intervalo 1] [--proxy IP]
"""
import argparse
import json
import random
import socket
import time

import zmq

from constPS import *  #-


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nome", default=socket.gethostname())
    ap.add_argument("--porta", default=PORT)
    ap.add_argument("--intervalo", type=float, default=1.0, help="segundos entre publicacoes")
    ap.add_argument("--limite", type=float, default=30.0, help="temperatura que gera ALERTA")
    ap.add_argument("--proxy", metavar="IP", help="publica atraves do proxy em vez de bind")
    ap.add_argument("-n", type=int, default=0, help="numero de rodadas (0 = sem fim)")
    a = ap.parse_args()

    context = zmq.Context()
    s = context.socket(zmq.PUB)                  # create a publisher socket
    if a.proxy:
        s.connect("tcp://" + a.proxy + ":" + PORT_XSUB)   # entra no proxy
    else:
        s.bind("tcp://*:" + a.porta)             # bind socket to the address
    print(f"[publicador {a.nome}] publicando a cada {a.intervalo}s", flush=True)

    rng = random.Random()
    temp, umid, dolar, btc = 25.0, 60.0, 5.40, 350000.0

    def publicar(topico, dados):
        dados["publicador"] = a.nome
        dados["hora"] = time.strftime("%H:%M:%S")
        s.send_string(topico + " " + json.dumps(dados, ensure_ascii=False))

    rodada = 0
    while a.n == 0 or rodada < a.n:
        time.sleep(a.intervalo)
        rodada += 1
        # passeio aleatorio: cada valor varia um pouco em relacao ao anterior
        temp = round(temp + rng.uniform(-1.5, 1.6), 1)
        umid = round(min(100, max(10, umid + rng.uniform(-3, 3))), 1)
        dolar = round(dolar * (1 + rng.uniform(-0.004, 0.004)), 4)
        btc = round(btc * (1 + rng.uniform(-0.01, 0.01)), 2)

        publicar("CLIMA", {"temperatura": temp, "umidade": umid})
        publicar("COTACAO", {"dolar": dolar, "bitcoin": btc})
        if temp > a.limite:
            publicar("ALERTA", {"mensagem": f"temperatura alta: {temp} C"})
        if rodada % 5 == 0:                      # como no original: hora a cada 5 s
            s.send_string("TIME " + time.asctime())
    s.close(linger=1000)
    context.term()


if __name__ == "__main__":
    main()
