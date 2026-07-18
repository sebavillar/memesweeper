#!/usr/bin/env python3
"""REPL para conversar con el agente en la terminal, sin WhatsApp.

Uso:
    cd claridad-total/whatsapp-agent
    python -m scripts.chat_cli            # conversación interactiva
    python -m scripts.chat_cli "hola, busco 3 amb en Godoy Cruz hasta 120 mil"

Requiere ANTHROPIC_API_KEY en el entorno o en .env.
"""
from __future__ import annotations

import sys

from app import agent

WA_ID = "cli-tester"


def main() -> None:
    if len(sys.argv) > 1:
        print(agent.responder(WA_ID, " ".join(sys.argv[1:])))
        return
    print("Agente Claridad Total (CLI). Escribí un mensaje, 'salir' para terminar.\n")
    while True:
        try:
            texto = input("Comprador> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if texto.lower() in {"salir", "exit", "quit"}:
            break
        if not texto:
            continue
        print(f"Agente> {agent.responder(WA_ID, texto)}\n")


if __name__ == "__main__":
    main()
