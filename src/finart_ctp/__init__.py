# -*- coding: utf-8 -*-
"""
FINART - Automacao CTP (v3)
===========================
Vigia a pasta do dia do cliente (BASE_ENTRADA > MES > DIA). Para cada PDF novo:

  1. le o tamanho de cada pagina
  2. 510x400 mm -> 1000 dpi          (ex: 49513 capa.pdf)
     775x635 mm ->  800 dpi + "R1"   (ex: 49576R1 informativo.pdf)
     outro tamanho -> anota em _PENDENCIAS.txt
  3. detecta quais tintas cada pagina usa de verdade
  4. gera UM PDF por pagina, contendo APENAS essas tintas
     (arquivo de magenta e preto sai com magenta e preto dentro,
      sem ciano nem amarelo vazios sobrando)
  5. grava na pasta do CTP do dia

O ORIGINAL NUNCA E MOVIDO NEM APAGADO: a pasta de entrada e compartilhada.
O controle do que ja foi feito fica no _processados.json, na BASE_CTP.

Substitui o Photoshop e o InDesign.

Fluxo VOPRIX: uma segunda pasta (BASE_ENTRADA_VOPRIX) recebe .cdr ja montados
no tamanho da chapa. Cada um e convertido pelo proprio CorelDRAW da maquina e
segue o mesmo caminho. Ver corel.py e nomes.nome_saida_voprix.
"""

__version__ = "3.0.0"
