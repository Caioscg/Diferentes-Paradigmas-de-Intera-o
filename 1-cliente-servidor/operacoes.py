"""Operacoes oferecidas pelo servidor (funcionalidades novas)."""
import math
import time


def _num(x):
    return x if isinstance(x, (int, float)) else float(x) if "." in str(x) else int(x)


def soma(a, b):        return _num(a) + _num(b)
def subtrai(a, b):     return _num(a) - _num(b)
def multiplica(a, b):  return _num(a) * _num(b)


def divide(a, b):
    if _num(b) == 0:
        raise ValueError("divisao por zero")
    return _num(a) / _num(b)


def potencia(a, b):
    if abs(_num(b)) > 100:
        raise ValueError("expoente muito grande")
    return _num(a) ** _num(b)


def fatorial(n):
    n = int(n)
    if not 0 <= n <= 300:
        raise ValueError("n deve estar entre 0 e 300")
    return math.factorial(n)


def primo(n):
    n = int(n)
    return n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))


def inverte(*palavras):     return " ".join(map(str, palavras))[::-1]
def maiusculas(*palavras):  return " ".join(map(str, palavras)).upper()
def eco(*palavras):         return " ".join(map(str, palavras)) + "*"   # comportamento original
def hora():                 return time.asctime()


# nome -> (funcao, numero de argumentos ou None = variavel)
OPERACOES = {
    "SOMA": (soma, 2), "SUBTRAI": (subtrai, 2), "MULTIPLICA": (multiplica, 2),
    "DIVIDE": (divide, 2), "POTENCIA": (potencia, 2), "FATORIAL": (fatorial, 1),
    "PRIMO": (primo, 1), "INVERTE": (inverte, None), "MAIUSCULAS": (maiusculas, None),
    "ECO": (eco, None), "HORA": (hora, 0),
}


def executar(op, args):
    """Executa a operacao e devolve o resultado (ou lanca ValueError)."""
    if op not in OPERACOES:
        raise ValueError(f"operacao desconhecida: {op}")
    func, aridade = OPERACOES[op]
    if aridade is not None and len(args) != aridade:
        raise ValueError(f"{op} espera {aridade} argumento(s)")
    try:
        return func(*args)
    except (TypeError, OverflowError) as e:
        raise ValueError(str(e))
