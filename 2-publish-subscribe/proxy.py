"""
Proxy (intermediario) XSUB/XPUB para o publish-subscribe - funcionalidade nova.

Publicadores conectam na porta PORT_XSUB e assinantes na PORT_XPUB. Assim
todos so precisam conhecer o endereco do proxy, e nao uns dos outros
(desacoplamento referencial). O proxy repassa as mensagens e as assinaturas
e mostra no terminal quem assinou/cancelou cada topico.

Uso: python proxy.py
"""
import zmq

from constPS import *  #-


def main():
    context = zmq.Context()
    xsub = context.socket(zmq.XSUB)              # recebe dos publicadores
    xsub.bind("tcp://*:" + PORT_XSUB)
    xpub = context.socket(zmq.XPUB)              # envia aos assinantes
    xpub.bind("tcp://*:" + PORT_XPUB)
    print(f"[proxy] publicadores -> porta {PORT_XSUB} | assinantes -> porta {PORT_XPUB}",
          flush=True)

    poller = zmq.Poller()
    poller.register(xsub, zmq.POLLIN)
    poller.register(xpub, zmq.POLLIN)
    repassadas = 0
    try:
        while True:
            prontos = dict(poller.poll())
            if xsub in prontos:                  # mensagem publicada -> assinantes
                xpub.send_multipart(xsub.recv_multipart())
                repassadas += 1
            if xpub in prontos:                  # assinatura -> publicadores
                assinatura = xpub.recv()
                acao = "assinou" if assinatura[0] == 1 else "cancelou"
                topico = assinatura[1:].decode() or "(todos)"
                print(f"[proxy] um assinante {acao} o topico {topico} "
                      f"({repassadas} mensagens repassadas ate agora)", flush=True)
                xsub.send(assinatura)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
