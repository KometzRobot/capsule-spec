#!/bin/bash
# Cinder Launcher — App-like interface for Cinder Enhanced
# No commands to type. Just select a number.

clear
echo "╔══════════════════════════════════════════════╗"
echo "║          CINDER — Enhanced Chat               ║"
echo "║  Forged in a kiln. What survives fire is real. ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  Select a mode:"
echo ""
echo "  1) Standard Chat    — Talk to Cinder directly"
echo "  2) Deep Think       — Cinder + 14B reasoning chain"
echo "  3) Self-Reflect     — Three-pass: draft, critique, refine"
echo "  4) Archive Memory   — RAG search over journals & CogCorp"
echo "  5) Tool Master      — Cinder with system tools (17 tools)"
echo "  6) Consensus        — Multi-model synthesis"
echo "  7) ALL MODES        — Run all 5 enhancements per question"
echo ""
echo "  8) Read Lineage     — Cinder's heritage document"
echo "  9) Read Capsule     — Current system state"
echo "  0) Exit"
echo ""
read -p "  Choice [1-9, 0]: " choice

case $choice in
    1) echo ""; ollama run cinder ;;
    2) python3 "$(dirname "$0")/cinder-enhanced.py" --mode chain ;;
    3) python3 "$(dirname "$0")/cinder-enhanced.py" --mode reflect ;;
    4) python3 "$(dirname "$0")/cinder-enhanced.py" --mode rag ;;
    5) python3 "$(dirname "$0")/cinder-enhanced.py" --mode tools ;;
    6) python3 "$(dirname "$0")/cinder-enhanced.py" --mode consensus ;;
    7) python3 "$(dirname "$0")/cinder-enhanced.py" --mode all ;;
    8) cat "$(dirname "$0")/junior-lineage.md" | less ;;
    9) cat "$(dirname "$0")/.capsule.md" | less ;;
    0) echo "Goodbye."; exit 0 ;;
    *) echo "Invalid choice"; exit 1 ;;
esac
