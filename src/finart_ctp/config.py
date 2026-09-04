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

# Onde fica o que precisou de gente. Quando um arquivo da VOPRIX nao da
# para processar - grande demais, ilegivel -, o PDF que a Corel ja gerou
# e guardado aqui em vez de ser jogado fora. Assim o operador continua do
# ponto onde o programa parou (abre no Photoshop/InDesign, como sempre
# fez) sem converter o .cdr de novo, que e a parte demorada.
#
# Fica no disco local: esses arquivos passam de 500 MB e nao podem entupir
# a rede. Limpe a pasta de tempos em tempos.
PASTA_PENDENCIAS = r"C:\CTP\_pendencias"

# ----------------------------------------------------------------------
# SEGUNDO CLIENTE: VOPRIX
# ----------------------------------------------------------------------
# Mesma arvore de pastas da SOLIDA (dentro da base: MES\DIA), so que numa
# base propria. A diferenca esta no que chega e em como sai:
#
#   - a arte vem em .cdr, ja montada no tamanho da chapa. O CorelDRAW
#     desta maquina converte para PDF antes de qualquer coisa (corel.py);
#   - o nome de saida nao e por OS: e 510x400_CM_VOPRIX_Envelope_Saco.
#
# As chapas caem na MESMA pasta FIA do dia da SOLIDA - o proprio nome ja
# diz de quem e, entao nao ha o que confundir.
#
# Deixe None para o programa vigiar so a SOLIDA.
BASE_ENTRADA_VOPRIX = r"X:\VOPRIX"

# ----------------------------------------------------------------------
# TERCEIRO CLIENTE: FIALHO BRINDES
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA, base propria. O que muda e que o Fialho manda de
# tudo: PDF pronto no tamanho da chapa, PDF fora de tamanho, arquivo em
# Corel, arte que ainda precisa ser montada.
#
# PADRAO TEMPORARIO, combinado com o operador: so anda o que chega em PDF
# ja no tamanho final da chapa (510x400 ou 730x600). Qualquer outra coisa
# PARA e vira pendencia - nao se da andamento no servico. Conforme os
# casos forem aparecendo, a gente amplia.
#
# Deixe None para nao vigiar essa pasta.
BASE_ENTRADA_FIALHO = r"X:\FIALHO"

# ----------------------------------------------------------------------
# COMO O CORELDRAW DEVE PUBLICAR O PDF
# ----------------------------------------------------------------------
# O PublishToPDF nao escolhe nada sozinho: ele usa o que estiver marcado
# na janela de Publicar em PDF da maquina. E o que estava marcado era:
#
#     BitmapCompression   0      (nenhuma)
#     CompressText        False
#     DownsampleColor     False  <- com ColorResolution ja em 300, sem uso
#
# Ou seja, bitmap gravado CRU. Foi medido: um .cdr de 13 MB virou PDF de
# 1007 MB, e 1006 desses MB eram bitmap sem compactar. Nao e defeito da
# automacao - publicando pela janela da o mesmo, so que na mao o arquivo
# passa pelo Photoshop depois e ninguem ve o monstro do meio.
#
# Entao o programa passou a EXIGIR os ajustes, em vez de herdar:
#
# Sao dois ajustes, e os dois sao SEM PERDA: ZIP nos bitmaps e compressao
# nos comandos da pagina. Medido no Panfleto_M3RIN, o mesmo arquivo:
#
#     como estava        1007,5 MB
#     so ZIP               39,6 MB   <- 25x menor
#
# E o que sai e o MESMO arquivo: cobertura de tinta igual na quinta casa
# (C, M, Y e K com diferenca +0.00000) e a pagina rasterizada com
# 7.114.344 de 7.114.344 pixels identicos, diferenca maxima 0 de 255.
#
# NAO reamostramos, e isso foi decidido com numero na mesa. As imagens do
# cliente vem em ~1064 dpi no tamanho final, o que e mais do que a chapa
# grava (1000 dpi) e mais do que o offset usa (300-400). So que:
#
#   ZIP + 800 dpi   50,9 MB   MAIOR que sem reamostrar - a interpolacao
#                             inventa valores que comprimem pior
#   ZIP + 600 dpi   42,2 MB   idem
#   ZIP + 400 dpi   32,5 MB   7 MB a menos, e o QR CODE do panfleto sai
#                             borrado. Traco fino dentro do bitmap e o
#                             que quebra primeiro.
#
# Ou seja: reamostrar aqui custa qualidade e nao paga nada. A compressao
# ja faz o trabalho inteiro. Se um dia um arquivo passar do limite mesmo
# com ZIP, ai sim vale conversar sobre dpi - e olhando o QR code.
#
# Numeros do BitmapCompression, direto do CorelDRAW:
#   0 nenhuma   1 LZW   2 JPEG (com perda)   3 ZIP   4 JP2
PDF_CORELDRAW = {
    "BitmapCompression": 3,        # pdfZIP, sem perda
    "CompressText": True,
}

# ----------------------------------------------------------------------
# QUARTO CLIENTE: EMPORIO PRINT
# ----------------------------------------------------------------------
# Mesma arvore MES\DIA, base propria. So manda PDF - nada de Corel - e o
# nome de entrada e "OS - descricao":
#
#     01995 - CHAPA CAIXA 4796.pdf
#     01965 - CHAPA - Maria Flor - Papel de Seda 45x65.pdf
#
# Entra como a SOLIDA (PDF pronto) e sai como a VOPRIX (formato, cores e
# cliente no nome). Deixe None para nao vigiar essa pasta.
BASE_ENTRADA_EMPORIO = r"X:\EMPORIO"

# ----------------------------------------------------------------------
# FORMATOS ACEITOS
# ----------------------------------------------------------------------
# (largura_mm, altura_mm): (dpi, sufixo_no_nome)

FORMATOS = {
    (510, 400): (1000, ""),
    (775, 635): (800,  "R1"),
}

# O Fialho tem a propria tabela: a chapa grande dele e 730x600, que nao
# existe na Solida. O formato entra no nome, entao aqui nao ha sufixo.
FORMATOS_FIALHO = {
    (510, 400): (1000, ""),
    (730, 600): (800,  ""),
}

# A chapa grande do Emporio e outra ainda: 660x605.
FORMATOS_EMPORIO = {
    (510, 400): (1000, ""),
    (660, 605): (800,  ""),
}

TOLERANCIA_MM = 3

# ENCAIXE (so FIALHO). Ate esta diferenca, arte que nao bate com nenhuma
# chapa entra CENTRALIZADA na chapa mais proxima: o que sobra e cortado
# igualmente dos dois lados, o que falta vira branco.
#
# Combinado com o operador para o caso real do 'CAPA Agenda PAULISTA
# 2027.pdf', que mede 520x400 e e chapa 510x400 - os 5 mm de cada lado
# nao tem nada. ACIMA deste limite ninguem adivinha o que pode ser
# cortado, entao vira pendencia como antes.
ENCAIXE_MAXIMO_MM = 15

# Etiqueta escrita no canto da folha de prova, fora da arte, para quem
# pega o papel saber de que chapa se trata.
ROTULOS_PROVA = {
    (510, 400): "SOLIDA F4",
    (775, 635): "SOLIDA F2",
}

# A mesma etiqueta, para as provas da VOPRIX. Uma tabela por cliente
# porque quem pega o papel precisa saber tambem de quem e a chapa.
ROTULOS_PROVA_VOPRIX = {
    (510, 400): "VOPRIX F4",
    (775, 635): "VOPRIX F2",
}

ROTULOS_PROVA_FIALHO = {
    (510, 400): "FIALHO F4",
    (730, 600): "FIALHO F2",
}

ROTULOS_PROVA_EMPORIO = {
    (510, 400): "EMPORIO F4",
    (660, 605): "EMPORIO F2",
}

# ----------------------------------------------------------------------
# NOME DE SAIDA DO EMPORIO PRINT
# ----------------------------------------------------------------------
# O padrao dos operadores, lido das chapas que eles fecharam a mao:
#
#     510x400_CMYK_EMPORIO_01987_Guia
#     660x605_GRAY_EMPORIO_01965_Maria Flor
#     510x400_CMYK_EMPORIO_01995_CAIXA 4796_1   (pagina 1)
#     510x400_GRAY_EMPORIO_01995_CAIXA 4796_2   (pagina 2)
#
# A OS identifica o servico, como o cliente identifica na VOPRIX. A
# descricao vem do nome do arquivo, sem as palavras que so dizem que
# aquilo e um trabalho de chapa - a mesma ideia do nome principal do
# Fialho. VERNIZ NAO entra nesta lista de proposito: chapa de verniz
# precisa aparecer no nome.
PALAVRAS_SERVICO_EMPORIO = {
    "CHAPA", "CHAPAS", "ARTE", "ARTES", "REGRAVAR", "REGRAVA", "REGRAVACAO",
    "FORMATO", "MODELO", "MODELOS", "GRADE",
}

# Trabalho que NUNCA fecha sozinho, por mais que o resto esteja em ordem.
# Pedido do operador: verniz se confere antes.
PALAVRAS_QUE_PEDEM_OLHO = {"VERNIZ"}

# ----------------------------------------------------------------------
# NOME DE SAIDA DO FIALHO
# ----------------------------------------------------------------------
# A chapa dele se chama pelo NOME PRINCIPAL do servico - quase sempre o
# cliente final:
#
#     FORRO AGENDA unicidades 2027.pdf  ->  510x400_FIALHO_UNICIDADES 01
#
# 'forro', 'miolo', 'capa' sao tipo de material, nao nome de servico. A
# lista abaixo e o que o programa joga fora ao procurar o nome principal;
# numero solto e medida (48x66) tambem caem. Se nao sobrar nada, o nome do
# arquivo inteiro vira o nome, em maiuscula e sem acento.
#
# ESTA LISTA E PARA CRESCER: toda vez que uma chapa sair com nome errado,
# a correcao costuma ser acrescentar a palavra aqui.
PALAVRAS_MATERIAL = {
    # material e tipo de peca
    "FORRO", "MIOLO", "CAPA", "PASTA", "DIVISORIA", "INTRODUCAO", "AGENDA",
    "CADERNO", "CALENDARIO", "ENVELOPE", "BLOCO", "BLOCOS", "GRADE", "DOBRA",
    "FOLHA", "FOLHAS", "ADESIVO", "CARTAO", "TAG", "ETIQUETA", "PANFLETO",
    # o que se faz com a peca
    "MONTAGEM", "MONTAGEN", "CORRECAO", "PROVA", "REGISTRO", "GABARITO",
    "FRENTE", "VERSO", "FINAL", "NOVO", "NOVA", "MODELO", "COLORIDA",
    "COLORIDO", "EMPRESARIAL", "DADOS", "PESSOAIS", "PROTOCOLO", "JANELA",
    # palavras de medida e contagem
    "FORMATO", "IMAGEM", "IMAGENS", "CHAPA", "CHAPAS", "PAGINA", "PAGINAS",
    "TAMANHO", "COPIA", "SEGURANCA",
    # ligacao
    "DE", "DA", "DO", "DAS", "DOS", "E", "COM", "SEM", "PARA", "POR", "EM",
    "A", "O", "AS", "OS", "NO", "NA",
}

# ----------------------------------------------------------------------
# OPERACAO
# ----------------------------------------------------------------------

# A pasta de entrada e compartilhada: o programa NUNCA apaga nem move
# nada de la. O controle do que ja foi feito fica no _processados.json,
# dentro da PASTA_CONTROLE, aqui no PC.
REGISTRO = "_processados.json"

# Acima disso o arquivo nao e processado: vira pendencia com aviso na
# tela. Nasceu de um .cdr de 375 MB que a Corel exportou como um PDF de
# 2,2 GB - tamanho que trava a leitura do arquivo e inviabiliza gerar a
# chapa. Ajuste se a maquina aguentar mais.
TAMANHO_MAXIMO_MB = 500

# PASSO 1 DO PROCESSO: cada arte aceita sai impressa (o arquivo ORIGINAL,
# nao a chapa) antes das chapas serem geradas. A chapa e maior que o papel
# da impressora, entao a prova sai reduzida, em A4 retrato.
# Deixe IMPRIMIR_ORIGINAL = False para desligar a impressao.
# Se a impressora falhar, a chapa NAO e gerada: o arquivo fica segurado
# e o programa tenta de novo de tempos em tempos, ate a prova sair.
IMPRIMIR_ORIGINAL = True
IMPRESSORA = "NOME DA IMPRESSORA NO WINDOWS"
ESPERA_IMPRESSORA = 300        # segundos entre tentativas (5 min)

# A VOPRIX so fecha sozinha o que vem em quadricromia. Arte de 1, 2 ou 3
# cores - ou em escala de cinza - PARA antes de gerar a chapa: a prova sai
# do mesmo jeito, o PDF convertido fica guardado na PASTA_PENDENCIAS e o
# aviso aparece na tela, com a cobertura de cada tinta, para alguem
# conferir. Quem manda fechar depois e gente.
#
# Pedido do operador: em quadricromia o caminho e sempre o mesmo, mas arte
# de uma cor ou de duas e onde a decisao muda de trabalho para trabalho.
AVISAR_QUANDO_NAO_FOR_CMYK = True

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
