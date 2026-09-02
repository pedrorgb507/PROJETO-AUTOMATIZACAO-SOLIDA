# -*- coding: utf-8 -*-
"""
Ponto de entrada do FINART CTP.

Rode por aqui (ou clique duas vezes em iniciar_ctp.bat):
    python run_ctp.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from finart_ctp.monitor import main  # noqa: E402

if __name__ == "__main__":
    main()
