# Endereco do publicador (ou do proxy). Na AWS, troque pelo IP privado da
# instancia (ou passe --hosts / --proxy na linha de comando).
HOST = "localhost"
PORT = "4567"           # publicador (modo direto)
PORT_XSUB = "4570"      # proxy: entrada dos publicadores
PORT_XPUB = "4571"      # proxy: saida para os assinantes
