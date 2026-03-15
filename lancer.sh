#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  LANCER L'OUTIL — Municipales 2026 T1 — Haute-Garonne
# ═══════════════════════════════════════════════════════════════
#
#  Double-cliquer sur ce fichier ou lancer dans un terminal :
#     bash lancer.sh
#
#  L'outil télécharge les derniers résultats depuis data.gouv.fr
#  et produit un CSV + Excel dans le dossier "resultats/".
#
#  Relancer régulièrement ce soir entre 18h et minuit.
# ═══════════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Activer l'environnement Python
if [ ! -d "venv" ]; then
    echo "⚙️  Première utilisation : configuration en cours..."
    python3 -m venv venv
    source venv/bin/activate
    pip install pandas pyarrow requests openpyxl --quiet
else
    source venv/bin/activate
fi

# Lancer l'extraction
python3 resultats_municipales_2026.py

echo ""
echo "Appuyez sur Entrée pour fermer..."
read
