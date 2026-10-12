# Enderecos das maquinas. Na AWS, troque pelos IPs privados das instancias
# (ou passe --fontes / --coletor na linha de comando).
SRC1  = "localhost"     # maquina da fonte de tarefas 1
SRC2  = "localhost"     # maquina da fonte de tarefas 2
SINK  = "localhost"     # maquina do coletor de resultados (novo)
PORT1 = "4567"          # fonte 1
PORT2 = "4568"          # fonte 2
PORT_RESULT = "4569"    # coletor: recebe os resultados
PORT_CTRL   = "4570"    # coletor: avisa os trabalhadores que acabou
