#!/usr/bin/env python3
"""
caviarder.py — Script de caviardage véritable de PDF
Skill caviardage-pdf / DPO PARTAGE

Usage :
    python3 caviarder.py --input doc.pdf --output doc_caviarde.pdf --profil rgpd
    python3 caviarder.py --input doc.pdf --output doc_caviarde.pdf --termes "Jean Dupont" "Cabinet X"
    python3 caviarder.py --input doc.pdf --output doc_caviarde.pdf --zones "0,72,100,300,120"
"""

import argparse
import re
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import fitz  # pymupdf
except ImportError:
    print("ERREUR : PyMuPDF requis. Exécuter : pip install pymupdf --break-system-packages")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Profils de patterns RGPD
# ─────────────────────────────────────────────────────────────────────────────

PROFILS = {
    "rgpd": {
        "NIR (numéro sécu)":   r"\b[12][\s]?[0-9]{2}[\s]?[0-1][0-9][\s]?[0-9]{2}[\s]?[0-9]{3}[\s]?[0-9]{3}[\s]?[0-9]{2}\b",
        "SIRET":               r"\b\d{3}[\s]?\d{3}[\s]?\d{3}[\s]?\d{5}\b",
        "SIREN":               r"\b\d{3}[\s]?\d{3}[\s]?\d{3}\b",
        "Email":               r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        "Téléphone FR":        r"\b0[1-9](?:[\s.\-]?\d{2}){4}\b",
        "IBAN FR":             r"\bFR\d{2}[\s]?(?:\d{4}[\s]?){5}\d{3}\b",
        "Date de naissance":   r"\b(?:né(?:e)?\s+le|ddn|date\s+de\s+naissance)[^\d]*\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b",
        "Adresse IP":          r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "Code postal + ville": r"\b\d{5}\s+[A-ZÀ-Ÿa-zà-ÿ\-]+(?:\s+[A-ZÀ-Ÿa-zà-ÿ\-]+){0,3}\b",
    },
    "medical": {
        # Hérite de rgpd
        "RPPS":                r"\b(?:RPPS|rpps)[\s:]*\d{11}\b",
        "ADELI":               r"\b(?:ADELI|adeli)[\s:]*\d{9}\b",
        "Numéro patient":      r"\b(?:patient|dossier|IPP)[\s:]*[0-9A-Z]{5,12}\b",
        "CIM-10":              r"\b[A-Z]\d{2}(?:\.\d{1,2})?\b",
        "Ordonnance":          r"\b(?:ordonnance|prescription)[\s:]*n°?\s*\d{4,}\b",
    },
    "spst": {
        # Hérite de medical
        "Numéro adhérent":     r"\b(?:adhérent|code\s+adhérent)[\s:]*[0-9A-Z]{4,15}\b",
        "APE/NAF":             r"\b\d{4}[A-Z]\b",
        "Résultat SMR":        r"\b(?:apte|inapte|apte\s+avec\s+restrictions?)(?:\s+au\s+poste)?\b",
    },
    "secret": {
        # Hérite de rgpd
        "Numéro contrat":      r"\b(?:contrat|marché|bon\s+de\s+commande)[\s:]*n°?\s*[\dA-Z\-]{4,20}\b",
        "Montant":             r"\b\d{1,3}(?:[\s\xa0]\d{3})*(?:[,\.]\d{2})?\s*(?:€|EUR|euros?)\b",
        "Numéro RCS":          r"\bRCS\s+[A-Z][a-zà-ÿ]+\s+[B-D]\s+\d{9}\b",
    },
    "cada": {
        # Éléments couverts par le secret (L311-6 CRPA)
        "Mention secret":      r"\b(?:confidentiel|secret|diffusion\s+restreinte|ne\s+pas\s+diffuser)\b",
        "Délibération numéro": r"\bDélibération\s+n°\s*[\dA-Z\-]+",
        "Référence interne":   r"\b(?:réf|référence|dossier)[\s.:]*[A-Z0-9\/\-]{4,20}\b",
    },
}

# Fusionner les profils héritiers
PROFILS["medical"] = {**PROFILS["rgpd"], **PROFILS["medical"]}
PROFILS["spst"]    = {**PROFILS["medical"], **PROFILS["spst"]}
PROFILS["secret"]  = {**PROFILS["rgpd"], **PROFILS["secret"]}
PROFILS["cada"]    = {**PROFILS["rgpd"], **PROFILS["cada"]}


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions principales
# ─────────────────────────────────────────────────────────────────────────────

def analyser_document(chemin: str) -> dict:
    """Analyse préalable du document."""
    doc = fitz.open(chemin)
    info = {
        "pages": len(doc),
        "metadata": doc.metadata,
        "pdf_natif": False,
        "pièces_jointes": doc.embfile_count(),
        "signé": False,
        "protégé": doc.is_encrypted,
    }
    # Vérifier si PDF natif ou image
    for page in doc:
        if page.get_text().strip():
            info["pdf_natif"] = True
            break
    # Vérifier signatures
    for page in doc:
        for annot in page.annots():
            if annot.type[0] in (fitz.PDF_ANNOT_WIDGET,):
                info["signé"] = True
    doc.close()
    return info


def identifier_zones(
    doc: fitz.Document,
    profil: str = "rgpd",
    termes_supplementaires: list = None,
    zones_manuelles: list = None,
) -> list:
    """
    Retourne liste de (page_num, fitz.Rect, motif).
    """
    zones = []
    patterns = PROFILS.get(profil, PROFILS["rgpd"])

    for page_num, page in enumerate(doc):
        full_text = page.get_text()
        if not full_text.strip():
            print(f"  [Avertissement] Page {page_num+1} : aucun texte détecté (PDF image ?)")
            continue

        # Patterns du profil
        for motif, pattern in patterns.items():
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                terme = match.group().strip()
                if len(terme) < 3:
                    continue
                rects = page.search_for(terme)
                for r in rects:
                    zones.append((page_num, r, motif))

        # Termes supplémentaires (littéraux)
        if termes_supplementaires:
            for terme in termes_supplementaires:
                rects = page.search_for(terme)
                for r in rects:
                    zones.append((page_num, r, f"terme:{terme}"))

    # Zones manuelles (x0, y0, x1, y1 sur page donnée)
    if zones_manuelles:
        for z in zones_manuelles:
            page_num, x0, y0, x1, y1 = int(z[0]), float(z[1]), float(z[2]), float(z[3]), float(z[4])
            zones.append((page_num, fitz.Rect(x0, y0, x1, y1), "zone_manuelle"))

    # Dédoublonner
    seen = set()
    zones_uniq = []
    for (p, r, m) in zones:
        key = (p, round(r.x0), round(r.y0), round(r.x1), round(r.y1))
        if key not in seen:
            seen.add(key)
            zones_uniq.append((p, r, m))

    return zones_uniq


def appliquer_caviardage(
    doc: fitz.Document,
    zones: list,
    couleur_fond: tuple = (0, 0, 0),
    texte_remplacement: str = "",
    purger_metadata: bool = True,
) -> list:
    """Applique le caviardage véritable et retourne le rapport."""
    rapport = []

    for (page_num, rect, motif) in zones:
        page = doc[page_num]
        page.add_redact_annot(
            quad=rect,
            text=texte_remplacement,
            fontsize=9,
            fill=couleur_fond,
            text_color=(1, 1, 1) if texte_remplacement else (0, 0, 0),
        )
        rapport.append({
            "page": page_num + 1,
            "rect": f"({rect.x0:.0f},{rect.y0:.0f},{rect.x1:.0f},{rect.y1:.0f})",
            "motif": motif,
        })

    # Appliquer — suppression réelle du contenu
    for page in doc:
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_PIXELS,
            graphics=True,
        )

    if purger_metadata:
        doc.set_metadata({
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "Caviardage — DPO PARTAGE",
            "producer": "",
            "creationDate": "",
            "modDate": "",
        })
        doc.del_xml_metadata()

    return rapport


def sauvegarder_rapport(rapport: list, chemin: str, profil: str, source: str):
    """Enregistre le rapport de caviardage (traçabilité DPO)."""
    lignes = [
        "=" * 60,
        "RAPPORT DE CAVIARDAGE",
        "=" * 60,
        f"Document source    : {source}",
        f"Profil appliqué    : {profil}",
        f"Date opération     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Zones caviardées   : {len(rapport)}",
        "",
        f"{'Page':>6}  {'Motif':<35} Zone (x0,y0,x1,y1)",
        "-" * 60,
    ]
    for item in rapport:
        lignes.append(f"  {item['page']:>4}  {item['motif']:<35} {item['rect']}")
    lignes.append("")
    lignes.append("Fin du rapport.")

    content = "\n".join(lignes)
    print(content)
    if chemin:
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nRapport enregistré : {chemin}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Caviardage véritable de PDF (suppression des données sous-jacentes)"
    )
    parser.add_argument("--input",   required=True, help="PDF source")
    parser.add_argument("--output",  required=True, help="PDF caviardé (sortie)")
    parser.add_argument("--profil",  default="rgpd",
                        choices=list(PROFILS.keys()) + ["aucun"],
                        help="Profil de patterns à appliquer")
    parser.add_argument("--termes",  nargs="*", default=[],
                        help="Termes littéraux supplémentaires à caviarder")
    parser.add_argument("--zones",   nargs="*", default=[],
                        help="Zones manuelles : 'page,x0,y0,x1,y1' (ex: '0,72,100,300,120')")
    parser.add_argument("--couleur", default="noir",
                        choices=["noir", "blanc", "gris"],
                        help="Couleur du caviardage")
    parser.add_argument("--texte",   default="",
                        help="Texte de remplacement visible (ex: [CAVIARDÉ])")
    parser.add_argument("--rapport", default="",
                        help="Chemin du rapport de caviardage (optionnel)")
    parser.add_argument("--selection", default="",
                        help="Fichier JSON produit par audit_caviardage.py (sélection manuelle)")
    parser.add_argument("--no-metadata", action="store_true",
                        help="Ne pas purger les métadonnées")
    parser.add_argument("--analyser", action="store_true",
                        help="Analyser seulement, sans caviarder")

    args = parser.parse_args()

    # Vérification entrée
    if not Path(args.input).exists():
        print(f"ERREUR : fichier introuvable : {args.input}")
        sys.exit(1)

    # Analyse préalable
    print(f"\nAnalyse de : {args.input}")
    info = analyser_document(args.input)
    print(f"  Pages          : {info['pages']}")
    print(f"  PDF natif      : {info['pdf_natif']}")
    print(f"  Pièces jointes : {info['pièces_jointes']}")
    print(f"  Protégé        : {info['protégé']}")
    print(f"  Signé          : {info['signé']}")
    if info['signé']:
        print("  [Avertissement] Le PDF contient des signatures — le caviardage les invalidera.")

    if args.analyser:
        print("\nMode --analyser : aucune modification effectuée.")
        sys.exit(0)

    # Couleur
    couleurs = {"noir": (0, 0, 0), "blanc": (1, 1, 1), "gris": (0.5, 0.5, 0.5)}
    couleur = couleurs[args.couleur]

    # ── Mode sélection (fichier JSON d'audit_caviardage.py) ──────────────────
    if args.selection:
        if not Path(args.selection).exists():
            print(f"ERREUR : fichier de sélection introuvable : {args.selection}")
            sys.exit(1)
        with open(args.selection, "r", encoding="utf-8") as f:
            data = json.load(f)
        detections = data.get("detections", [])
        a_caviarder = [d for d in detections if d.get("caviarder", True)]
        print(f"\nMode sélection : {len(a_caviarder)} zone(s) retenues sur {len(detections)} détectées.")
        if not a_caviarder:
            print("Aucune zone à caviarder dans la sélection. Document non modifié.")
            sys.exit(0)

        doc = fitz.open(args.input)
        zones = []
        for d in a_caviarder:
            r = d["rect"]  # [x0, y0, x1, y1]
            zones.append((d["page"] - 1, fitz.Rect(r[0], r[1], r[2], r[3]), d["categorie"]))

        rapport = appliquer_caviardage(
            doc, zones,
            couleur_fond=couleur,
            texte_remplacement=args.texte,
            purger_metadata=not args.no_metadata,
        )
        doc.save(args.output, garbage=4, deflate=True, clean=True)
        doc.close()
        print(f"  PDF caviardé enregistré : {args.output}")

        # Afficher les données conservées
        conserves = [d for d in detections if not d.get("caviarder", True)]
        if conserves:
            print(f"\n  Données conservées (non caviardées) :")
            for d in conserves:
                note = f" — {d['note']}" if d.get("note") else ""
                print(f"    p.{d['page']} | {d['categorie']} | {d['valeur']}{note}")

        sauvegarder_rapport(rapport, args.rapport, data.get("meta", {}).get("profil", "selection"), args.input)
        return

    # ── Mode automatique (profil + termes + zones manuelles) ─────────────────
    # Zones manuelles parsées
    zones_manuelles = []
    for z in args.zones:
        parts = z.split(",")
        if len(parts) == 5:
            zones_manuelles.append([float(p) for p in parts])
        else:
            print(f"[Avertissement] Zone ignorée (format invalide) : {z}")

    doc = fitz.open(args.input)

    print(f"\nIdentification des zones ({args.profil})...")
    profil_effectif = args.profil if args.profil != "aucun" else None
    zones = identifier_zones(
        doc,
        profil=profil_effectif or "rgpd",
        termes_supplementaires=args.termes,
        zones_manuelles=zones_manuelles,
    )
    if args.profil == "aucun":
        zones = [z for z in zones if z[2].startswith("terme:") or z[2] == "zone_manuelle"]

    print(f"  {len(zones)} zone(s) identifiée(s)")

    if not zones:
        print("\nAucune zone à caviarder détectée. Document non modifié.")
        doc.close()
        sys.exit(0)

    print(f"\nApplication du caviardage...")
    rapport = appliquer_caviardage(
        doc, zones,
        couleur_fond=couleur,
        texte_remplacement=args.texte,
        purger_metadata=not args.no_metadata,
    )

    doc.save(args.output, garbage=4, deflate=True, clean=True)
    doc.close()
    print(f"  PDF caviardé enregistré : {args.output}")

    sauvegarder_rapport(rapport, args.rapport, args.profil, args.input)


if __name__ == "__main__":
    main()
