# ZeroMQ – Cliente-servidor, Publish-subscribe e Pipeline (Cap. 4)

Extensão dos exemplos das **Figs. 4.21, 4.22 e 4.23** do livro-texto
(*Distributed Systems*, van Steen & Tanenbaum), que usam o middleware
orientado a mensagens **ZeroMQ** em Python. Cada exemplo ganhou novas
funcionalidades e foi preparado para rodar em **máquinas diferentes** (AWS EC2).

| Pasta | Padrão ZeroMQ | Baseado em |
|---|---|---|
| [`1-cliente-servidor`](1-cliente-servidor) | requisição-resposta (REQ/REP, ROUTER/DEALER) | Fig. 4.21 (`04-22/`) |
| [`2-publish-subscribe`](2-publish-subscribe) | publicação-assinatura (PUB/SUB, XPUB/XSUB) | Fig. 4.22 (`04-23/`) |
| [`3-pipeline`](3-pipeline) | pipeline (PUSH/PULL) | Fig. 4.23 (`04-24/`) |
| [`codigo-original`](codigo-original) | código fornecido pelo professor, sem alterações | – |

> No pacote `.zip` as pastas seguem a numeração de outra edição do livro
> (`04-22`, `04-23`, `04-24`), mas correspondem às Figs. 4.21, 4.22 e 4.23.

---

## Instalação

Em **cada máquina** que for rodar algum programa:

```bash
sudo apt update && sudo apt install -y python3-venv git     # Ubuntu (AWS)
git clone https://github.com/Caioscg/<este-repositorio>.git
cd <este-repositorio>
python3 -m venv venv
source venv/bin/activate          # no Windows: venv\Scripts\activate
pip install -r requirements.txt   # instala o pyzmq
```

## Endereços

Os servidores fazem `bind` em `tcp://*:<porta>` (todas as interfaces da máquina),
então **não é preciso editar o IP no lado do servidor**. Os clientes recebem o IP do
servidor pela linha de comando (`--host`, `--hosts`, `--proxy`, `--fontes`,
`--coletor`) ou pelo arquivo `const*.py` de cada pasta, cujo padrão é `localhost`.

---

## 1. Cliente-servidor (Fig. 4.21)

**Original:** o cliente envia `"Hello world 1"`, o servidor devolve o texto com `*`
no final, e `"STOP"` encerra o servidor.

**Novas funcionalidades:**

- **Várias operações** com mensagens em JSON
  (`{"op": "SOMA", "args": [2, 3]}` → `{"ok": true, "resultado": 5, ...}`):
  `SOMA`, `SUBTRAI`, `MULTIPLICA`, `DIVIDE`, `POTENCIA`, `FATORIAL`, `PRIMO`,
  `INVERTE`, `MAIUSCULAS`, `ECO`, `HORA`, além de `AJUDA`, `ESTATISTICAS` (quantas
  requisições de cada tipo o servidor atendeu) e `STOP`. Erros (ex.: divisão por
  zero, operação desconhecida) voltam como resposta, sem derrubar o servidor.
- A resposta informa **qual máquina e qual thread** atendeu.
- **Servidor com pool de threads** (`--workers N`): um socket `ROUTER` recebe os
  clientes e um `DEALER` distribui as requisições entre N threads `REP`, para atender
  vários clientes ao mesmo tempo. Sem a opção, funciona como o original (um `REP`).
- **Cliente tolerante a falhas** (padrão *Lazy Pirate*): espera a resposta por no
  máximo 2,5 s; se não chegar, recria o socket e reenvia (3 tentativas). No original,
  o cliente ficava bloqueado para sempre se o servidor caísse.
- Cliente **interativo**, por **comando único** ou **automático** (requisições
  aleatórias, com vários clientes simultâneos).
- **Compatível com o original:** os clientes `client.py`, `client1.py` e `client2.py`
  continuam funcionando com o novo servidor, que também escuta nas duas portas
  (4567 e 4568).

```bash
cd 1-cliente-servidor
python servidor.py                       # máquina A (ou: --workers 4)
python cliente.py --host IP_A            # máquina B: modo interativo
python cliente.py --host IP_A SOMA 2 3   # um comando
python cliente.py --host IP_A --porta 2 FATORIAL 20
python cliente.py --host IP_A --auto 200 --clientes 4
python cliente.py --host IP_A STOP       # encerra o servidor
```

Exemplo de saída (teste local; `Elite` é o nome da máquina que respondeu, e na AWS
aparece o nome da instância do servidor):
```
> SOMA 2 3
[Elite/principal] 5
> DIVIDE 1 0
[Elite/principal] ERRO: divisao por zero
> PRIMO 97
[Elite/principal] True
```

**Pool de threads × servidor simples** (medido em uma máquina, 200 requisições,
4 clientes simultâneos, 20 ms de processamento simulado com `--atraso 0.02`):

| Servidor | Tempo | Vazão |
|---|---:|---:|
| `servidor.py` (1 thread, como o original) | 4,10 s | 49 req/s |
| `servidor.py --workers 4` | 1,15 s | 174 req/s |

---

## 2. Publish-subscribe (Fig. 4.22)

**Original:** o publicador envia `"TIME <hora>"` a cada 5 s; o assinante assina
`TIME` e lê 5 mensagens.

**Novas funcionalidades:**

- **Vários tópicos:** `TIME` (como no original), `CLIMA` (temperatura e umidade
  simuladas), `COTACAO` (dólar e bitcoin simulados) e `ALERTA` (quando a temperatura
  passa de um limite).
- Cada publicador tem um **nome** (`--nome`), incluído em cada mensagem.
- O assinante **escolhe os tópicos** (`--topicos CLIMA,ALERTA`), **conecta em vários
  publicadores ao mesmo tempo** (`--hosts IP1,IP2`), recebe quantas mensagens quiser
  (`-n`; 0 = até Ctrl+C) e no fim mostra um **resumo** (mensagens por tópico e por
  publicador, temperatura média/mínima/máxima).
- **Proxy XSUB/XPUB** (`proxy.py`): um intermediário em endereço fixo. Publicadores
  e assinantes só precisam conhecer o proxy, e não uns aos outros. O proxy mostra
  quando um assinante assina ou cancela um tópico.
- **Compatível com o original:** o `subscriber.py` original continua recebendo os
  `TIME` do novo publicador, porque o filtro do ZeroMQ olha só o início da mensagem.

**Modo direto** (2 publicadores em máquinas diferentes, 1 assinante):
```bash
cd 2-publish-subscribe
python publicador.py --nome sala1                 # máquina A
python publicador.py --nome sala2                 # máquina B
python assinante.py --hosts IP_A,IP_B --topicos CLIMA,ALERTA -n 20   # máquina C
```

**Com proxy:**
```bash
python proxy.py                                   # máquina A
python publicador.py --nome estacao1 --proxy IP_A # máquina B
python assinante.py --proxy IP_A --topicos COTACAO   # máquina C
```

Exemplo de saída do assinante:
```
CLIMA    [sala1 22:40:13]  26.5 C   59.5% umidade
ALERTA   [sala1 22:40:13] temperatura alta: 26.5 C
CLIMA    [sala2 22:40:13]  26.1 C   59.0% umidade
...
Resumo: 14 mensagens | por topico: {'CLIMA': 9, 'ALERTA': 5} | por publicador: {'sala1': 10, 'sala2': 4}
Temperatura: media 27.5 C, min 26.1 C, max 28.6 C
```

---

## 3. Pipeline (Fig. 4.23)

**Original:** duas fontes geram 100 cargas aleatórias (1 por segundo) e os
trabalhadores "fingem" trabalhar (`sleep`) e imprimem a carga. Os resultados não
iam para lugar nenhum e os trabalhadores rodavam para sempre.

**Novas funcionalidades:**

- **Coletor de resultados** (`coletor.py`, novo): fecha o pipeline
  *fontes → trabalhadores → coletor*. Recebe os resultados e, quando todas as tarefas
  terminam, mostra o **tempo total**, a **vazão**, o **paralelismo efetivo** e quantas
  tarefas cada trabalhador fez (o balanceamento feito pelo ZeroMQ).
- **Trabalho real:** cada trabalhador conta os números primos até `carga × 1000`
  (com `--modo sleep` dorme como no original) e envia o resultado ao coletor, com o
  tempo gasto e o nome da máquina.
- **Encerramento automático:** o coletor publica `FIM` num canal de controle
  (PUB/SUB) e os trabalhadores terminam sozinhos.
- Fontes com **quantidade de tarefas e intervalo configuráveis**. Cada fonte avisa
  ao coletor quantas tarefas vai gerar e espera alguns segundos pelos trabalhadores
  antes de começar. Sem essa espera, o primeiro trabalhador a conectar recebe quase
  todas as tarefas.

```bash
cd 3-pipeline
python coletor.py                                             # máquina A
python trabalhador.py T1 --fontes IP_B:4567,IP_C:4568 --coletor IP_A   # máquinas D, E, ...
python trabalhador.py T2 --fontes IP_B:4567,IP_C:4568 --coletor IP_A
python fonte.py 1 --tarefas 30 --coletor IP_A                 # máquina B
python fonte.py 2 --tarefas 30 --coletor IP_A                 # máquina C
```

Ordem: coletor → trabalhadores → fontes. Exemplo de resumo do coletor:
```
[coletor] 30 tarefas concluidas em 1.16 s (25.9 tarefas/s)
[coletor] soma do tempo de trabalho: 3.10 s -> paralelismo efetivo 2.68x
           T1@Elite                         10 tarefas     0.97 s trabalhando
           T2@Elite                         10 tarefas     0.97 s trabalhando
           T3@Elite                         10 tarefas     1.16 s trabalhando
```

Medido em uma máquina (2 fontes × 15 tarefas):

| Trabalhadores | Tempo total | Vazão |
|---:|---:|---:|
| 1 | 2,33 s | 12,9 tarefas/s |
| 3 | 1,16 s | 25,9 tarefas/s |

O socket `PUSH` distribui as tarefas em **rodízio** (*round-robin*) entre os
trabalhadores conectados, e não pela carga de cada um. Por isso cada trabalhador
recebeu exatamente 10 tarefas.

---

## Execução na AWS (máquinas diferentes)

1. Crie as instâncias EC2 (ex.: Ubuntu, `t2.micro`/`t3.micro`), todas na **mesma VPC**.
2. No **Security Group** das instâncias, libere entrada **TCP 4567–4571** com origem
   na própria VPC (ex.: `172.31.0.0/16`), além do SSH (22).
3. Em cada instância, siga a seção **Instalação**.
4. Descubra o **IP privado** de cada instância (console da EC2 ou `hostname -I`) e
   use-o nos comandos acima no lugar de `IP_A`, `IP_B`, etc. Entre instâncias da
   mesma VPC, use o IP privado (172.31.x.x). O IP público só é necessário para
   acessar de fora da AWS.

Sugestão de distribuição com 3 instâncias:

| Exemplo | Instância 1 | Instância 2 | Instância 3 |
|---|---|---|---|
| Cliente-servidor | `servidor.py --workers 4` | `cliente.py --host IP1 --auto 200 --clientes 4` | `cliente.py --host IP1` (interativo) |
| Publish-subscribe | `publicador.py --nome A` | `publicador.py --nome B` | `assinante.py --hosts IP1,IP2` |
| Pipeline | `coletor.py` + `fonte.py 1 --coletor IP1` | `fonte.py 2 --coletor IP1` + `trabalhador.py T1 --fontes IP1:4567,IP2:4568 --coletor IP1` | `trabalhador.py T2 ...` + `trabalhador.py T3 ...` |

As respostas do servidor e as mensagens dos publicadores e trabalhadores trazem o
**nome da máquina** (na AWS, algo como `ip-172-31-x-x`), o que confirma de qual
instância cada mensagem veio.

---

## Por que ZeroMQ (e não sockets puros)

- Os padrões (REQ/REP, PUB/SUB, PUSH/PULL) já trazem a lógica de comunicação: filas,
  filtragem por tópico, distribuição de tarefas entre trabalhadores e envio de
  mensagens inteiras (sem precisar separar bytes).
- `connect` pode ser feito **antes** de o outro lado existir: o ZeroMQ reconecta
  sozinho, então a ordem em que as máquinas sobem importa pouco.
- Um mesmo socket se conecta a vários pontos (o assinante a vários publicadores, o
  trabalhador a várias fontes) sem nenhum código extra.
