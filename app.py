#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║  DASHBOARD WEB — MUNICIPALES 2026 — 1ER TOUR                   ║
║  Communes de Haute-Garonne (31)                                 ║
║  Cabinet de la Présidente de Région                             ║
╚══════════════════════════════════════════════════════════════════╝

Lancer en local :
    streamlit run app.py

Déploiement (Streamlit Community Cloud) :
    1. Pousser ce dépôt sur GitHub
    2. Aller sur https://share.streamlit.io → New app → sélectionner app.py
"""

import hashlib
import io
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_PARIS = ZoneInfo("Europe/Paris")

import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────

ID_ELECTION = "2026_muni_t1"
CODE_DEPARTEMENT = "31"

URL_GENERAL   = "https://www.data.gouv.fr/api/1/datasets/r/ff16d511-10c0-405e-9b35-511723948fce"
URL_CANDIDATS = "https://www.data.gouv.fr/api/1/datasets/r/4d3b35f6-0b22-4415-a24c-419a676312e2"

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

# ─────────────────────────────────────────────────────────────────
# DÉTECTION DES MISES À JOUR (requêtes HEAD légères)
# ─────────────────────────────────────────────────────────────────

def recuperer_signatures_http() -> dict:
    """Requêtes HEAD légères pour détecter si les fichiers sources
    ont changé, sans télécharger le contenu."""
    signatures = {}
    for nom, url in [("general", URL_GENERAL), ("candidats", URL_CANDIDATS)]:
        try:
            resp = requests.head(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            sig = (resp.headers.get("Last-Modified", "")
                   + "|" + resp.headers.get("Content-Length", "")
                   + "|" + resp.headers.get("ETag", ""))
            signatures[nom] = sig
        except Exception:
            signatures[nom] = None
    return signatures


def calculer_hash_donnees(gen: pd.DataFrame, cand: pd.DataFrame) -> str:
    """Hash du contenu des DataFrames pour détecter des changements réels."""
    h = hashlib.md5(usedforsecurity=False)
    h.update(pd.util.hash_pandas_object(gen).values.tobytes())
    h.update(pd.util.hash_pandas_object(cand).values.tobytes())
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────
# TÉLÉCHARGEMENT AVEC CACHE STREAMLIT
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def charger_et_filtrer() -> tuple:
    """Télécharge les Parquet nationaux, filtre sur HG31 et retourne
    uniquement les DataFrames filtrés (légers).
    Cache 5 min — invalidé plus tôt si le HEAD détecte un changement.
    """
    resp_gen = requests.get(URL_GENERAL, timeout=120)
    resp_gen.raise_for_status()
    df_general = pd.read_parquet(io.BytesIO(resp_gen.content))
    del resp_gen  # libère les bytes bruts

    resp_cand = requests.get(URL_CANDIDATS, timeout=120)
    resp_cand.raise_for_status()
    df_candidats = pd.read_parquet(io.BytesIO(resp_cand.content))
    del resp_cand

    # Filtrer immédiatement sur l'élection + département
    gen = df_general[
        (df_general["id_election"] == ID_ELECTION) &
        (df_general["code_departement"] == CODE_DEPARTEMENT)
    ].copy()
    del df_general

    cand = df_candidats[
        (df_candidats["id_election"] == ID_ELECTION) &
        (df_candidats["code_departement"] == CODE_DEPARTEMENT)
    ].copy()
    del df_candidats

    return gen, cand


# ─────────────────────────────────────────────────────────────────
# TRAITEMENT DES DONNÉES (identique au script CLI)
# ─────────────────────────────────────────────────────────────────

def agreger_resultats(gen, cand):
    codes_cibles = set(COMMUNES_CIBLES.keys())

    gen_cibles  = gen[gen["code_commune"].isin(codes_cibles)].copy()
    cand_cibles = cand[cand["code_commune"].isin(codes_cibles)].copy()

    participation = gen_cibles.groupby("code_commune").agg(
        inscrits=("inscrits",    "sum"),
        abstentions=("abstentions", "sum"),
        votants=("votants",    "sum"),
        blancs=("blancs",     "sum"),
        nuls=("nuls",      "sum"),
        exprimes=("exprimes",   "sum"),
        nb_bv=("code_bv",   "nunique"),
    ).reset_index()

    participation["taux_abstention"] = (
        (participation["abstentions"]
         / participation["inscrits"].replace(0, float("nan"))) * 100
    ).round(2).fillna(0.0)

    candidat_cols = ["nom", "prenom"]
    if "liste"   in cand_cibles.columns: candidat_cols.append("liste")
    if "nuance"  in cand_cibles.columns: candidat_cols.append("nuance")

    group_cols = ["code_commune"] + candidat_cols
    resultats_cand = cand_cibles.groupby(group_cols, dropna=False).agg(
        voix=("voix", "sum"),
    ).reset_index()

    return participation, resultats_cand


def determiner_statut(code_commune, nb_bv_trouves):
    ref    = COMMUNES_CIBLES.get(code_commune, {})
    bv_ref = ref.get("bv_ref", 0)
    if bv_ref == 0:
        return "inconnu"
    elif nb_bv_trouves >= bv_ref:
        return "complet"
    else:
        return f"partiel ({nb_bv_trouves}/{bv_ref} BV)"


def construire_tableau_final(participation, resultats_cand):
    lignes = []
    for code, info in sorted(COMMUNES_CIBLES.items(), key=lambda x: x[1]["nom"]):
        nom_commune = info["nom"]
        part = participation[participation["code_commune"] == code]

        if part.empty:
            lignes.append({
                "Commune": nom_commune, "Code_INSEE": code,
                "Votants": None, "Taux abstention (%)": None,
                "Candidat": "", "Nuance": "", "Liste": "",
                "Voix": None, "% exprimés": None,
                "Statut": "données non disponibles",
            })
            continue

        row_p       = part.iloc[0]
        nb_votants  = int(row_p["votants"])
        nb_exprimes = int(row_p["exprimes"])
        taux_abst   = row_p["taux_abstention"]
        nb_bv       = int(row_p["nb_bv"])
        statut      = determiner_statut(code, nb_bv)

        cand_c = resultats_cand[resultats_cand["code_commune"] == code].copy()

        if cand_c.empty:
            lignes.append({
                "Commune": nom_commune, "Code_INSEE": code,
                "Votants": nb_votants, "Taux abstention (%)": taux_abst,
                "Candidat": "(aucun candidat trouvé)", "Nuance": "", "Liste": "",
                "Voix": None, "% exprimés": None,
                "Statut": statut,
            })
            continue

        cand_c["pct"] = (
            (cand_c["voix"] / nb_exprimes * 100).round(2)
            if nb_exprimes > 0 else 0
        )
        cand_c = cand_c.sort_values("voix", ascending=False)

        for _, r in cand_c.iterrows():
            lignes.append({
                "Commune": nom_commune,
                "Code_INSEE": code,
                "Votants": nb_votants,
                "Taux abstention (%)": taux_abst,
                "Candidat": f"{r.get('prenom', '')} {r.get('nom', '')}".strip(),
                "Nuance": r.get("nuance", "") or "",
                "Liste": r.get("liste", "") or "",
                "Voix": int(r["voix"]),
                "% exprimés": r["pct"],
                "Statut": statut,
            })

    return pd.DataFrame(lignes)


# ─────────────────────────────────────────────────────────────────
# EXPORT EXCEL EN MÉMOIRE (pour le bouton de téléchargement)
# ─────────────────────────────────────────────────────────────────

def generer_excel_bytes(df_final: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Résultats T1")
        ws = writer.sheets["Résultats T1"]
        for i, col in enumerate(df_final.columns, 1):
            col_lens = df_final[col].astype(str).str.len()
            max_len = max(len(str(col)), col_lens.max() if len(col_lens) > 0 else 0)
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(max_len + 3, 60)

        resume = df_final.drop_duplicates(subset=["Commune"])[
            ["Commune", "Code_INSEE", "Votants", "Taux abstention (%)", "Statut"]
        ].sort_values("Commune")
        resume.to_excel(writer, index=False, sheet_name="Synthèse participation")
        ws2 = writer.sheets["Synthèse participation"]
        for i, col in enumerate(resume.columns, 1):
            col_lens = resume[col].astype(str).str.len()
            max_len = max(len(str(col)), col_lens.max() if len(col_lens) > 0 else 0)
            ws2.column_dimensions[ws2.cell(1, i).column_letter].width = min(max_len + 3, 60)

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# INTERFACE STREAMLIT
# ─────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Municipales 2026 — Haute-Garonne",
        page_icon="🗳️",
        layout="wide",
    )

    st.title("🗳️ Municipales 2026 — 1er tour — Haute-Garonne (31)")
    st.caption("Données : data.gouv.fr · Vérification automatique toutes les 60 secondes")

    # ── Initialisation session state ───────────────────────────────
    if "hash_donnees" not in st.session_state:
        st.session_state.hash_donnees = None
    if "heure_maj" not in st.session_state:
        st.session_state.heure_maj = None
    if "donnees_nouvelles" not in st.session_state:
        st.session_state.donnees_nouvelles = False
    if "sigs_http" not in st.session_state:
        st.session_state.sigs_http = None

    # ── Vérification automatique des MAJ (toutes les 60s) ─────────
    @st.fragment(run_every="60s")
    def polling_mises_a_jour():
        """Requête HEAD légère toutes les 60s pour détecter un changement."""
        sigs = recuperer_signatures_http()
        anciennes = st.session_state.sigs_http
        st.session_state.sigs_http = sigs
        if anciennes is not None and sigs != anciennes:
            st.cache_data.clear()
            st.rerun(scope="app")

    polling_mises_a_jour()

    # ── Bouton de rafraîchissement manuel ──────────────────────────
    if st.button("🔄 Rafraîchir manuellement"):
        st.cache_data.clear()
        st.rerun()

    # ── Téléchargement + filtrage (cache 5 min, invalidé par HEAD) ─
    try:
        with st.spinner("Téléchargement des données depuis data.gouv.fr…"):
            gen, cand = charger_et_filtrer()
    except Exception as e:
        st.error(f"❌ Impossible de contacter data.gouv.fr : {e}")
        st.exception(e)
        st.stop()

    # ── Détection de changement réel (hash du contenu) ─────────────
    hash_actuel = calculer_hash_donnees(gen, cand)
    if hash_actuel != st.session_state.hash_donnees:
        if st.session_state.hash_donnees is not None:
            st.session_state.donnees_nouvelles = True
        st.session_state.hash_donnees = hash_actuel
        st.session_state.heure_maj = datetime.now(tz=TZ_PARIS)

    # ── Bandeau de statut ──────────────────────────────────────────
    heure = datetime.now(tz=TZ_PARIS).strftime("%H:%M:%S")
    heure_maj_str = (
        st.session_state.heure_maj.strftime("%d/%m/%Y à %H:%M:%S")
        if st.session_state.heure_maj
        else "—"
    )

    if st.session_state.donnees_nouvelles:
        st.success(
            f"🆕 **Mise à jour détectée le {heure_maj_str} !** "
            f"Les données ci-dessous sont à jour. Téléchargez le nouvel Excel."
        )
    else:
        st.info(f"Dernière vérification : {heure} · Dernière MAJ des données : {heure_maj_str}")

    if gen.empty:
        st.warning(
            f"⚠️ Aucune donnée disponible pour **{ID_ELECTION}**."
            f" Les résultats ne sont pas encore publiés.\n\n"
            f"Le dashboard vérifie automatiquement toutes les 60 secondes."
        )
        st.stop()

    # ── Traitement ─────────────────────────────────────────────────
    participation, resultats_cand = agreger_resultats(gen, cand)
    df_final = construire_tableau_final(participation, resultats_cand)

    # ── Métriques globales ─────────────────────────────────────────
    nb_complets = df_final[df_final["Statut"] == "complet"]["Commune"].nunique()
    nb_partiels = df_final["Statut"].str.startswith("partiel", na=False).pipe(
        lambda m: df_final[m]["Commune"].nunique()
    )
    nb_attente = df_final[df_final["Statut"] == "données non disponibles"]["Commune"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Communes suivies", len(COMMUNES_CIBLES))
    c2.metric("✅ Complets",       nb_complets)
    c3.metric("⏳ Partiels",       nb_partiels)
    c4.metric("⚠️ En attente",    nb_attente)

    st.divider()

    # ── Bouton téléchargement Excel (proéminent si MAJ) ────────────
    horodatage  = datetime.now(tz=TZ_PARIS).strftime("%Y%m%d_%H%M")
    excel_bytes = generer_excel_bytes(df_final)

    if st.session_state.donnees_nouvelles:
        st.download_button(
            label="📥 Télécharger le nouvel Excel (données mises à jour !)",
            data=excel_bytes,
            file_name=f"municipales_2026_T1_HG31_{horodatage}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            on_click=lambda: st.session_state.update(donnees_nouvelles=False),
        )
    else:
        st.download_button(
            label="📥 Télécharger Excel",
            data=excel_bytes,
            file_name=f"municipales_2026_T1_HG31_{horodatage}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.divider()

    # ── Tableau résultats par commune ──────────────────────────────
    st.subheader("Résultats détaillés par commune")

    communes_liste = ["Toutes"] + sorted(df_final["Commune"].unique().tolist())
    choix = st.selectbox("Filtrer par commune", communes_liste)

    df_affiche = df_final if choix == "Toutes" else df_final[df_final["Commune"] == choix]

    def colorier_statut(val):
        if val == "complet":
            return "background-color: #d4edda; color: #155724;"
        elif str(val).startswith("partiel"):
            return "background-color: #fff3cd; color: #856404;"
        elif val == "données non disponibles":
            return "background-color: #f8d7da; color: #721c24;"
        return ""

    st.dataframe(
        df_affiche.style.map(colorier_statut, subset=["Statut"]),
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    # ── Participation en un coup d'œil ─────────────────────────────
    st.subheader("Participation")
    synthese = df_final.drop_duplicates(subset=["Commune"])[[
        "Commune", "Votants", "Taux abstention (%)", "Statut"
    ]].sort_values("Taux abstention (%)").reset_index(drop=True)

    st.dataframe(
        synthese.style.map(colorier_statut, subset=["Statut"]),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
