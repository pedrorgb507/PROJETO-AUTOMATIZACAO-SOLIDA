# -*- coding: utf-8 -*-
"""
Configuracao do FINART CTP.

Os valores aqui sao exemplos. Os caminhos reais de cada maquina ficam num
config_local.py ao lado deste, que nao vai para o controle de versao e
sobrescreve o que estiver aqui (veja o final do arquivo).
"""

# ----------------------------------------------------------------------
# PASTAS
# ----------------------------------------------------------------------

# Onde o cliente joga as artes. Dentro dela: MES\DIA
#   X:\ENTRADA\SETEMBRO\02
BASE_ENTRADA = r"X:\ENTRADA"

# Onde os PDFs prontos do CTP sao gravados:
#   Y:\CTP\SETEMBRO\03\FIA
# O programa acha a pasta do mes e do dia e cria a subpasta de saida
# dentro dela, do lado das pastas dos outros operadores.
BASE_CTP = r"Y:\CTP"
SUBPASTA_SAIDA = "FIA"

# Log, registro e arquivos temporarios ficam no PC. Os TIFFs da
# separacao chegam a varios GB: nao podem passar pela rede.
PASTA_CONTROLE = r"C:\CTP\_controle"

# ----------------------------------------------------------------------
# FORMATOS ACEITOS
# ----------------------------------------------------------------------
# (largura_mm, altura_mm): (dpi, sufixo_no_nome)

FORMATOS = {
    (510, 400): (1000, ""),
    (775, 635): (800,  "R1"),
}

TOLERANCIA_MM = 3

# ----------------------------------------------------------------------
# OPERACAO
# ----------------------------------------------------------------------

# A pasta de entrada e compartilhada: o programa NUNCA apaga nem move
# nada de la. O controle do que ja foi feito fica no _processados.json,
# dentro da PASTA_CONTROLE, aqui no PC.
REGISTRO = "_processados.json"

# PASSO 1 DO PROCESSO: cada arte aceita sai impressa (o arquivo ORIGINAL,
# nao a chapa) antes das chapas serem geradas. A chapa e maior que o papel
# da impressora, entao a prova sai reduzida, em A4 retrato.
# Deixe IMPRIMIR_ORIGINAL = False para desligar a impressao.
# Se a impressora falhar, a chapa NAO e gerada: o arquivo fica segurado
# e o programa tenta de novo de tempos em tempos, ate a prova sair.
IMPRIMIR_ORIGINAL = True
IMPRESSORA = "NOME DA IMPRESSORA NO WINDOWS"
ESPERA_IMPRESSORA = 300        # segundos entre tentativas (5 min)

# Se voce vira a noite, a pasta do dia so troca depois desta hora.
HORA_VIRADA = 0

# Segundos entre uma varredura e outra da pasta.
INTERVALO = 5

# Caminho fixo do Ghostscript. Deixe None para procurar sozinho.
GS_EXE = None

# Nomes dos meses, na ordem. Serve para achar a pasta do mes mesmo que ela
# esteja escrita diferente na rede (MARCO / MARÇO / Marco / marco).
MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

# ----------------------------------------------------------------------
# TABELAS DE TINTA (nao mexer)
# ----------------------------------------------------------------------

NOMES_TINTA = {"Cyan": "C", "Magenta": "M", "Yellow": "Y", "Black": "K"}
CMYK_PDF = {"C": "/Cyan", "M": "/Magenta", "Y": "/Yellow", "K": "/Black"}

# ----------------------------------------------------------------------
# Ajustes desta maquina, fora do controle de versao.
# ----------------------------------------------------------------------

try:
    from .config_local import *          # noqa: F401,F403
except ImportError:
    pass
