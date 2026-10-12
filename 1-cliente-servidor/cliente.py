"""
Cliente (padrao requisicao-resposta), baseado no client.py da Fig. 4.21.

Novidades em relacao ao original:
  - chama qualquer operacao do servidor, com argumentos
  - modo interativo, comando unico ou automatico (requisicoes aleatorias)
  - tempo limite e novas tentativas: se o servidor nao responder, o socket
    REQ e recriado e a requisicao reenviada (padrao "Lazy Pirate" do ZeroMQ;
    no original o cliente ficaria bloqueado para sempre)
  - varios clientes simultaneos no modo automatico (--clientes K)

Uso:
  python cliente.py [--host IP] [--porta 1|2]                 # interativo
  python cliente.py [--host IP] SOMA 2 3                      # um comando
  python cliente.py [--host IP] --auto 200 [--clientes 4]     # automatico
"""
import argparse
import json
import random
import threading
import time

import zmq

from constCS import *  #-

TIMEOUT = 2.5        # segundos esperando a resposta
TENTATIVAS = 3


def converter(t):
    """'2' -> 2, '2.5' -> 2.5, 'ola' -> 'ola'"""
    for tipo in (int, float):
        try:
            return tipo(t)
        except ValueError:
            pass
    return t


def requisitar(context, endereco, op, args=()):
    """Envia {"op", "args"} e devolve a resposta (dict). Lazy Pirate."""
    pedido = str.encode(json.dumps({"op": op, "args": list(args)}))
    for tentativa in range(1, TENTATIVAS + 1):
        s = context.socket(zmq.REQ)              # create request socket
        s.setsockopt(zmq.LINGER, 0)
        s.connect(endereco)                      # connect to the server
        s.send(pedido)                           # send message
        if s.poll(int(TIMEOUT * 1000)):          # espera a resposta com prazo
            resposta = json.loads(bytes.decode(s.recv()))
            s.close()
            return resposta
        s.close()                                # REQ "travado": descarta e recria
        print(f"  (sem resposta em {TIMEOUT}s - tentativa {tentativa}/{TENTATIVAS})")
    raise TimeoutError(f"servidor {endereco} nao respondeu")


def mostrar(resposta):
    quem = f"[{resposta.get('servidor')}/{resposta.get('worker')}]"
    if resposta.get("ok"):
        print(f"{quem} {resposta['resultado']}")
    else:
        print(f"{quem} ERRO: {resposta.get('erro')}")


def interativo(context, endereco):
    print(f"Conectado a {endereco}. Exemplos: SOMA 2 3 | FATORIAL 20 | PRIMO 97 |"
          " INVERTE ola mundo | AJUDA | ESTATISTICAS | STOP | sair")
    while True:
        try:
            linha = input("> ").split()
        except EOFError:
            break
        if not linha:
            continue
        if linha[0].lower() == "sair":
            break
        try:
            mostrar(requisitar(context, endereco, linha[0].upper(), map(converter, linha[1:])))
        except TimeoutError as e:
            print("FALHA:", e)


def pedido_aleatorio(rng):
    op = rng.choice(["SOMA", "SUBTRAI", "MULTIPLICA", "DIVIDE", "POTENCIA",
                     "FATORIAL", "PRIMO", "INVERTE", "MAIUSCULAS", "HORA"])
    if op in ("SOMA", "SUBTRAI", "MULTIPLICA", "DIVIDE"):
        return op, [rng.randint(-100, 100), rng.randint(-10, 10)]
    if op == "POTENCIA":
        return op, [rng.randint(-9, 9), rng.randint(0, 10)]
    if op == "FATORIAL":
        return op, [rng.randint(0, 30)]
    if op == "PRIMO":
        return op, [rng.randint(2, 100000)]
    if op == "HORA":
        return op, []
    return op, rng.sample(["zeromq", "sistemas", "distribuidos", "aws", "python"], 2)


def automatico(context, endereco, n, k, mostrar_respostas):
    """k clientes (threads) dividem n requisicoes aleatorias."""
    servidores, workers, erros = set(), set(), [0]
    lock = threading.Lock()

    def cliente(idx, qtd):
        rng = random.Random(idx)
        for _ in range(qtd):
            op, args = pedido_aleatorio(rng)
            try:
                r = requisitar(context, endereco, op, args)
            except TimeoutError:
                with lock:
                    erros[0] += 1
                continue
            with lock:
                servidores.add(r.get("servidor"))
                workers.add(r.get("worker"))
                if mostrar_respostas:
                    print(f"cliente {idx}: {op} {args} -> {r.get('resultado', r.get('erro'))}")

    inicio = time.perf_counter()
    ths = [threading.Thread(target=cliente, args=(i, n // k + (i < n % k))) for i in range(k)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    dt = time.perf_counter() - inicio
    print(f"{n} requisicoes, {k} cliente(s) simultaneo(s): {dt:.3f} s ({n / dt:.1f} req/s), "
          f"falhas: {erros[0]}")
    print(f"atendidas por: servidor(es) {sorted(servidores)}, threads {sorted(workers)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--porta", choices=["1", "2"], default="1",
                    help="1 = PORT1, 2 = PORT2 (como client1.py / client2.py)")
    ap.add_argument("--auto", type=int, metavar="N", help="envia N requisicoes aleatorias")
    ap.add_argument("--clientes", type=int, default=1, help="clientes simultaneos no modo --auto")
    ap.add_argument("-v", "--verboso", action="store_true")
    ap.add_argument("comando", nargs="*", help="ex.: SOMA 2 3")
    a = ap.parse_args()

    context = zmq.Context()
    endereco = "tcp://" + a.host + ":" + (PORT1 if a.porta == "1" else PORT2)
    if a.auto:
        automatico(context, endereco, a.auto, a.clientes, a.verboso)
    elif a.comando:
        try:
            mostrar(requisitar(context, endereco, a.comando[0].upper(), map(converter, a.comando[1:])))
        except TimeoutError as e:
            print("FALHA:", e)
    else:
        interativo(context, endereco)
    context.term()


if __name__ == "__main__":
    main()
