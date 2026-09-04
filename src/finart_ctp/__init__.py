# -*- coding: utf-8 -*-
"""
FINART - Automacao CTP (v3)
===========================
Vigia a pasta do dia de CADA cliente (BASE > MES > DIA). Para cada arte nova:

  1. le o tamanho de cada pagina
  2. escolhe o dpi pela chapa que a medida bate
  3. detecta quais tintas cada pagina usa de verdade
  4. gera UM PDF por pagina, contendo APENAS essas tintas
     (arquivo de magenta e preto sai com magenta e preto dentro,
      sem ciano nem amarelo vazios sobrando)
  5. grava na pasta FIA do CTP do dia - a mesma para todos

Sao tres clientes, e a diferenca entre eles esta so nas pontas:

  SOLIDA  PDF pronto     510x400 -> 1000 dpi     nome pela OS:  49576R1
                         775x635 ->  800 dpi + "R1"
  VOPRIX  .cdr           convertido pelo CorelDRAW desta maquina (corel.py);
                         nome pelo produto:  510x400_CM_VOPRIX_Envelope_Saco;
                         arte de uma cor sai em escala de cinza, e fora da
                         quadricromia o programa nao fecha sozinho
  FIALHO  PDF pronto     510x400 -> 1000 dpi, 730x600 -> 800 dpi;
                         nome pelo servico:  510x400_FIALHO_UNICIDADES 01;
                         arte alguns milimetros fora entra centralizada

No meio - prova impressa, separacao de tintas, uma chapa por pagina - o
caminho e o mesmo para os tres.

O ORIGINAL NUNCA E MOVIDO NEM APAGADO: a pasta de entrada e compartilhada.
O controle do que ja foi feito fica no _processados.json, na PASTA_CONTROLE,
no proprio PC. O que precisa de gente vira pendencia com aviso na tela.

Substitui o Photoshop e o InDesign.
"""

__version__ = "3.0.0"
