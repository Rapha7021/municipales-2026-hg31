#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║  OUTIL DE SUIVI — MUNICIPALES 2026 — 2ÈME TOUR                 ║
║  Communes de Haute-Garonne (31)                                 ║
║  Cabinet de la Présidente de Région                             ║
╚══════════════════════════════════════════════════════════════════╝

Usage :
    python3 resultats_municipales_2026.py

    L'outil télécharge automatiquement les dernières données depuis
    data.gouv.fr, extrait les résultats des communes cibles, et
    produit un fichier CSV exploitable.

    Relancer régulièrement entre 18h et minuit pour obtenir les
    résultats au fur et à mesure de leur publication.
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    import requests
except ImportError:
    print("❌ Dépendances manquantes. Lancer :")
    print("   pip install pandas pyarrow requests openpyxl")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────

ID_ELECTION = "2026_muni_t2"
CODE_DEPARTEMENT = "31"

# URLs des fichiers Parquet sur data.gouv.fr
# Ces fichiers sont mis à jour en continu pour chaque tour ;
# le filtre id_election == ID_ELECTION sélectionne automatiquement le bon tour.
URL_GENERAL = "https://www.data.gouv.fr/api/1/datasets/r/ff16d511-10c0-405e-9b35-511723948fce"
URL_CANDIDATS = "https://www.data.gouv.fr/api/1/datasets/r/4d3b35f6-0b22-4415-a24c-419a676312e2"

# Communes cibles avec code INSEE et nombre de BV de référence (2020)
# Le nombre de BV sert à détecter si les résultats sont complets ou partiels
COMMUNES_CIBLES = {
    "31555": {"nom": "Toulouse",                  "bv_ref": 263},
    "31149": {"nom": "Colomiers",                 "bv_ref": 25},
    "31557": {"nom": "Tournefeuille",             "bv_ref": 21},
    "31069": {"nom": "Blagnac",                   "bv_ref": 22},
    "31157": {"nom": "Cugnaux",                   "bv_ref": 15},
    "31506": {"nom": "Saint-Orens-de-Gameville",  "bv_ref": 12},
    "31561": {"nom": "L'Union",                   "bv_ref": 11},
    "31417": {"nom": "Pibrac",                    "bv_ref": 8},
    "31490": {"nom": "Saint-Jory",                "bv_ref": 4},
    "31182": {"nom": "Fenouillet",                "bv_ref": 4},
    "31395": {"nom": "Muret",                     "bv_ref": 19},
    "31424": {"nom": "Plaisance-du-Touch",        "bv_ref": 15},
    "31113": {"nom": "Castanet-Tolosan",          "bv_ref": 10},
    "31446": {"nom": "Ramonville-Saint-Agne",     "bv_ref": 11},
    "31483": {"nom": "Saint-Gaudens",             "bv_ref": 10},
    "31033": {"nom": "Auterive",                  "bv_ref": 6},
    "31291": {"nom": "Léguevin",                  "bv_ref": 8},
    "31169": {"nom": "Escalquens",                "bv_ref": 7},
    "31107": {"nom": "Carbonne",                  "bv_ref": 4},
    "31396": {"nom": "Nailloux",                  "bv_ref": 2},
    "31203": {"nom": "Frouzins",                  "bv_ref": 6},
    "31042": {"nom": "Bagnères-de-Luchon",        "bv_ref": 3},
    "31167": {"nom": "Encausse-les-Thermes",      "bv_ref": 1},
}

# Dossier de sortie
OUTPUT_DIR = Path(__file__).parent / "resultats"


# ─────────────────────────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────────────────────────

def print_banner():
    """Affiche le bandeau de bienvenue."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print()
    print("═" * 66)
    print("  MUNICIPALES 2026 — 2ÈME TOUR — HAUTE-GARONNE (31)")
    print(f"  Extraction lancée le {now}")
    print("═" * 66)
    print()


def telecharger_parquet(url, nom_fichier):
    """Télécharge un fichier Parquet depuis data.gouv.fr."""
    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(exist_ok=True)
    chemin = cache_dir / nom_fichier

    # Vérifier si le cache est récent (< 10 minutes)
    if chemin.exists():
        age_minutes = (time.time() - chemin.stat().st_mtime) / 60
        if age_minutes < 10:
            print(f"  ✓ {nom_fichier} (cache de {int(age_minutes)} min)")
            return chemin

    print(f"  ↓ Téléchargement de {nom_fichier}...", end=" ", flush=True)
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        # Écriture atomique via fichier temporaire
        fd, tmp_path = tempfile.mkstemp(dir=str(cache_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            os.replace(tmp_path, str(chemin))
        except Exception:
            os.unlink(tmp_path)
            raise
        taille_mo = chemin.stat().st_size / (1024 * 1024)
        print(f"OK ({taille_mo:.1f} Mo)")
        return chemin
    except requests.RequestException as e:
        print(f"ERREUR")
        print(f"    → {e}")
        return None


def charger_donnees():
    """Télécharge et charge les deux fichiers de données."""
    print("📥 Téléchargement des données depuis data.gouv.fr...")
    print()

    f_general = telecharger_parquet(URL_GENERAL, "general-results.parquet")
    f_candidats = telecharger_parquet(URL_CANDIDATS, "candidats-results.parquet")

    if not f_general or not f_candidats:
        print("\n❌ Impossible de télécharger les données. Vérifiez votre connexion.")
        sys.exit(1)

    print()
    print("📊 Chargement des données en mémoire...", end=" ", flush=True)

    df_general = pd.read_parquet(f_general)
    df_candidats = pd.read_parquet(f_candidats)

    print("OK")
    return df_general, df_candidats


def filtrer_election(df_general, df_candidats):
    """Filtre les données pour l'élection ciblée et le département 31."""
    # Filtrer par élection
    gen = df_general[
        (df_general["id_election"] == ID_ELECTION) &
        (df_general["code_departement"] == CODE_DEPARTEMENT)
    ].copy()

    cand = df_candidats[
        (df_candidats["id_election"] == ID_ELECTION) &
        (df_candidats["code_departement"] == CODE_DEPARTEMENT)
    ].copy()

    return gen, cand


def detecter_election_disponible(df_general):
    """Si les données 2026 ne sont pas encore disponibles, le signaler."""
    elections = sorted(df_general["id_election"].unique())
    muni_elections = [e for e in elections if "muni" in e]
    return muni_elections


def agreger_resultats(gen, cand):
    """
    Agrège les données par bureau de vote au niveau commune.
    Retourne les DataFrames de participation et de résultats candidats.
    """
    codes_cibles = set(COMMUNES_CIBLES.keys())

    # Filtrer les communes cibles
    gen_cibles = gen[gen["code_commune"].isin(codes_cibles)].copy()
    cand_cibles = cand[cand["code_commune"].isin(codes_cibles)].copy()

    # ── Participation par commune ──
    participation = gen_cibles.groupby("code_commune").agg(
        inscrits=("inscrits", "sum"),
        abstentions=("abstentions", "sum"),
        votants=("votants", "sum"),
        blancs=("blancs", "sum"),
        nuls=("nuls", "sum"),
        exprimes=("exprimes", "sum"),
        nb_bv=("code_bv", "nunique"),
    ).reset_index()

    participation["Taux d'abstention (%)"] = (
        (participation["abstentions"] / participation["inscrits"]) * 100
    ).round(2)

    # ── Résultats par candidat par commune ──
    # Identifier les candidats par un ensemble de colonnes stables
    candidat_cols = ["nom", "prenom"]
    if "liste" in cand_cibles.columns:
        candidat_cols.append("liste")
    if "nuance" in cand_cibles.columns:
        candidat_cols.append("nuance")

    group_cols = ["code_commune"] + candidat_cols
    resultats_cand = cand_cibles.groupby(group_cols, dropna=False).agg(
        voix=("voix", "sum"),
    ).reset_index()

    return participation, resultats_cand


def determiner_statut(code_commune, nb_bv_trouves):
    """Détermine si les résultats sont complets ou partiels."""
    ref = COMMUNES_CIBLES.get(code_commune, {})
    bv_ref = ref.get("bv_ref", 0)

    if bv_ref == 0:
        return "inconnu"
    elif nb_bv_trouves >= bv_ref:
        return "complet"
    else:
        return f"partiel ({nb_bv_trouves}/{bv_ref} BV)"


def construire_tableau_final(participation, resultats_cand):
    """Construit le tableau CSV final avec toutes les colonnes demandées."""
    lignes = []

    for code, info in sorted(COMMUNES_CIBLES.items(), key=lambda x: x[1]["nom"]):
        nom_commune = info["nom"]

        # Données de participation
        part = participation[participation["code_commune"] == code]

        if part.empty:
            # Commune sans données
            lignes.append({
                "Commune": nom_commune,
                "Code_INSEE": code,
                "Nombre de votants": "",
                "Taux d'abstention (%)": "",
                "Candidat": "",
                "Nuance politique": "",
                "Liste": "",
                "Nombre de voix": "",
                "% voix sur exprimés": "",
                "Statut": "données non disponibles",
            })
            continue

        part_row = part.iloc[0]
        nb_votants = int(part_row["votants"])
        nb_inscrits = int(part_row["inscrits"])
        nb_exprimes = int(part_row["exprimes"])
        taux_abst = part_row["Taux d'abstention (%)"]
        nb_bv = int(part_row["nb_bv"])

        statut = determiner_statut(code, nb_bv)

        # Résultats candidats pour cette commune
        cand_commune = resultats_cand[resultats_cand["code_commune"] == code].copy()

        if cand_commune.empty:
            lignes.append({
                "Commune": nom_commune,
                "Code_INSEE": code,
                "Nombre de votants": nb_votants,
                "Taux d'abstention (%)": taux_abst,
                "Candidat": "(aucun candidat trouvé)",
                "Nuance politique": "",
                "Liste": "",
                "Nombre de voix": "",
                "% voix sur exprimés": "",
                "Statut": statut,
            })
            continue

        # Calcul du pourcentage sur exprimés
        cand_commune["pct_exprimes"] = (
            (cand_commune["voix"] / nb_exprimes) * 100
        ).round(2) if nb_exprimes > 0 else 0

        # Trier par voix décroissantes
        cand_commune = cand_commune.sort_values("voix", ascending=False)

        for _, row in cand_commune.iterrows():
            candidat_str = f"{row.get('prenom', '')} {row.get('nom', '')}".strip()
            nuance = row.get("nuance", "") or ""
            liste = row.get("liste", "") or ""

            lignes.append({
                "Commune": nom_commune,
                "Code_INSEE": code,
                "Nombre de votants": nb_votants,
                "Taux d'abstention (%)": taux_abst,
                "Candidat": candidat_str,
                "Nuance politique": nuance,
                "Liste": liste,
                "Nombre de voix": int(row["voix"]),
                "% voix sur exprimés": row["pct_exprimes"],
                "Statut": statut,
            })

    return pd.DataFrame(lignes)


def afficher_resume(df_final):
    """Affiche un résumé à l'écran."""
    print()
    print("═" * 66)
    print("  RÉSUMÉ PAR COMMUNE")
    print("═" * 66)

    communes_traitees = df_final["Commune"].unique()
    communes_avec_donnees = df_final[df_final["Statut"] != "données non disponibles"]["Commune"].unique()
    communes_sans = df_final[df_final["Statut"] == "données non disponibles"]["Commune"].unique()

    for commune in sorted(communes_avec_donnees):
        bloc = df_final[df_final["Commune"] == commune]
        first = bloc.iloc[0]
        statut = first["Statut"]
        icon = "✅" if statut == "complet" else "⏳"

        taux_abst_affiche = first["Taux d'abstention (%)"]
        print(f"\n  {icon} {commune} — {statut}")
        print(f"     Votants: {first['Nombre de votants']:,}"
              f"  |  Abstention: {taux_abst_affiche}%")

        candidats = bloc[bloc["Candidat"] != "(aucun candidat trouvé)"]
        if not candidats.empty:
            for _, c in candidats.iterrows():
                nuance_str = f" ({c['Nuance politique']})" if c["Nuance politique"] else ""
                print(f"     • {c['Candidat']}{nuance_str}: "
                      f"{int(c['Nombre de voix']):,} voix ({c['% voix sur exprimés']}%)")

    if len(communes_sans) > 0:
        print(f"\n  ⚠️  Communes sans données disponibles :")
        for c in sorted(communes_sans):
            print(f"     — {c}")

    print()


def ajuster_largeurs(worksheet, df):
    """Ajuste automatiquement la largeur des colonnes selon le contenu."""
    for i, col in enumerate(df.columns, 1):
        # Largeur max entre l'en-tête et le contenu le plus long
        max_len = len(str(col))
        for val in df[col].astype(str).fillna(""):
            max_len = max(max_len, len(val))
        # Marge de confort + plafond à 60
        worksheet.column_dimensions[worksheet.cell(1, i).column_letter].width = min(max_len + 3, 60)


def exporter(df_final):
    """Exporte en Excel (.xlsx)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M")

    xlsx_path = OUTPUT_DIR / f"municipales_2026_T2_HG31_{horodatage}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Résultats T2")
        ajuster_largeurs(writer.sheets["Résultats T2"], df_final)

        # Onglet résumé participation
        resume = df_final.drop_duplicates(subset=["Commune"])[
            ["Commune", "Code_INSEE", "Nombre de votants",
             "Taux d'abstention (%)", "Statut"]
        ].sort_values("Commune")
        resume.to_excel(writer, index=False, sheet_name="Synthèse participation")
        ajuster_largeurs(writer.sheets["Synthèse participation"], resume)

    print(f"  📊 Excel : {xlsx_path}")

    # Raccourci vers le dernier fichier
    latest = OUTPUT_DIR / "DERNIERS_RESULTATS.xlsx"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(xlsx_path.name)
    print(f"  🔗 Raccourci : {latest}")

    return xlsx_path


# ─────────────────────────────────────────────────────────────────
# PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def main():
    print_banner()

    # 1. Charger les données
    df_general, df_candidats = charger_donnees()

    # 2. Filtrer pour 2026 muni T1, département 31
    gen, cand = filtrer_election(df_general, df_candidats)

    print(f"\n📋 Élection ciblée : {ID_ELECTION}")
    print(f"   Département : {CODE_DEPARTEMENT} (Haute-Garonne)")
    print(f"   Communes suivies : {len(COMMUNES_CIBLES)}")

    if gen.empty:
        # Pas encore de données 2026
        elections_muni = detecter_election_disponible(df_general)
        print(f"\n⚠️  Aucune donnée trouvée pour '{ID_ELECTION}'.")
        print(f"   Les résultats ne sont pas encore publiés dans le dataset.")
        print(f"   Élections municipales disponibles : {elections_muni}")
        print(f"\n   → Relancez l'outil après la publication des premiers résultats.")
        print(f"   → Les résultats sont généralement publiés entre 18h et minuit.\n")

        # Produire quand même un CSV « en attente »
        df_final = construire_tableau_final(
            pd.DataFrame(columns=["code_commune", "inscrits", "abstentions",
                                   "votants", "blancs", "nuls", "exprimes",
                                   "nb_bv", "taux_abstention_pct",
                                   "taux_participation_pct"]),
            pd.DataFrame(columns=["code_commune", "nom", "prenom", "nuance",
                                   "liste", "voix"])
        )
        print("📁 Export des fichiers (en attente de résultats) :")
        exporter(df_final)
        return

    nb_bv_total = gen["id_brut_miom"].nunique()
    print(f"   Bureaux de vote trouvés (dept 31) : {nb_bv_total}")

    # 3. Agréger par commune
    participation, resultats_cand = agreger_resultats(gen, cand)

    communes_trouvees = set(participation["code_commune"].tolist())
    communes_manquantes = set(COMMUNES_CIBLES.keys()) - communes_trouvees

    print(f"   Communes avec données : {len(communes_trouvees)}/{len(COMMUNES_CIBLES)}")
    if communes_manquantes:
        noms = [COMMUNES_CIBLES[c]["nom"] for c in communes_manquantes]
        print(f"   ⚠️  En attente : {', '.join(sorted(noms))}")

    # 4. Construire le tableau final
    df_final = construire_tableau_final(participation, resultats_cand)

    # 5. Afficher le résumé
    afficher_resume(df_final)

    # 6. Exporter
    print("📁 Export des fichiers :")
    csv_path = exporter(df_final)

    # 7. Statistiques finales
    nb_complets = df_final[df_final["Statut"] == "complet"]["Commune"].nunique()
    nb_partiels = df_final[df_final["Statut"].str.startswith("partiel")]["Commune"].nunique()
    nb_manquants = df_final[df_final["Statut"] == "données non disponibles"]["Commune"].nunique()

    print()
    print("═" * 66)
    print(f"  ✅ Complets : {nb_complets}  |  ⏳ Partiels : {nb_partiels}"
          f"  |  ⚠️  En attente : {nb_manquants}")
    if nb_complets < len(COMMUNES_CIBLES):
        print(f"  → Relancez l'outil dans quelques minutes pour actualiser.")
    else:
        print(f"  → Tous les résultats sont complets !")
    print("═" * 66)
    print()


if __name__ == "__main__":
    main()
