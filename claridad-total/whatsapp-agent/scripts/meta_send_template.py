#!/usr/bin/env python3
"""Envía una plantilla aprobada (re-engagement fuera de la ventana de 24 h).

Uso:
  python -m scripts.meta_send_template <numero> <plantilla> [var1] [var2] ...

Ejemplos:
  python -m scripts.meta_send_template 5492610000000 recordatorio_visita \
      "Juan" "Depto en Godoy Cruz" "sábado 10 hs" "San Martín 1234"
  python -m scripts.meta_send_template 5492610000000 nueva_propiedad \
      "Juan" "Depto 3 amb con cochera" "Godoy Cruz" "119.000"
"""
from __future__ import annotations

import sys

from app.whatsapp import send_template


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    numero = sys.argv[1]
    plantilla = sys.argv[2]
    variables = sys.argv[3:]
    res = send_template(numero, plantilla, variables or None)
    print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
