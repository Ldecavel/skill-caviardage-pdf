#!/usr/bin/env python3
"""
audit_caviardage.py — Audit PDF trois couches avant caviardage
Skill caviardage-pdf / DPO PARTAGE

C1 : Données personnelles directement identifiantes (RGPD art. 4)
C2 : Quasi-identifiants / risque de réidentification (CNIL, considérant 26)
C3 : Secret des affaires (Loi 2018-670, L151-1 à L152-4 C. com.)
"""

import argparse, re, json, sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import fitz
except ImportError:
    print("ERREUR : PyMuPDF requis. pip install pymupdf --break-system-packages")
    sys.exit(1)

# ══════ C1 — Données personnelles directement identifiantes ══════

PROFILS_C1 = {
    "rgpd": {
        "NIR":                 r"\b[12][\s]?[0-9]{2}[\s]?[0-1][0-9][\s]?[0-9]{2}[\s]?[0-9]{3}[\s]?[0-9]{3}[\s]?[0-9]{2}\b",
        "SIRET":               r"\b\d{3}[\s]?\d{3}[\s]?\d{3}[\s]?\d{5}\b",
        "SIREN":               r"\b\d{3}[\s]?\d{3}[\s]?\d{3}\b",
        "Email":               r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        "Telephone FR":        r"\b0[1-9](?:[\s.\-]?\d{2}){4}\b",
        "IBAN FR":             r"\bFR\d{2}[\s]?(?:\d{4}[\s]?){5}\d{3}\b",
        "Date naissance":      r"\b(?:ne(?:e)?\s+le|ddn|date\s+de\s+naissance)[^\d]*\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b",
        "Adresse IP":          r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "Code postal":         r"\b\d{5}\s+[A-Za-z\-]+(?:\s+[A-Za-z\-]+){0,3}\b",
    },
    "medical": {
        "RPPS":                r"\b(?:RPPS|rpps)[\s:]*\d{11}\b",
        "ADELI":               r"\b(?:ADELI|adeli)[\s:]*\d{9}\b",
        "Numero patient":      r"\b(?:patient|dossier|IPP)[\s:]*[0-9A-Z]{5,12}\b",
        "CIM-10":              r"\b[A-Z]\d{2}(?:\.\d{1,2})?\b",
    },
    "spst": {
        "Numero adherent":     r"\b(?:adherent|code\s+adherent)[\s:]*[0-9A-Z]{4,15}\b",
        "APE/NAF":             r"\b\d{4}[A-Z]\b",
        "Aptitude":            r"\b(?:apte|inapte|apte\s+avec\s+restrictions?)(?:\s+au\s+poste)?\b",
    },
    "cada": {
        "Reference interne":   r"\b(?:ref|reference|dossier)[\s.:]*[A-Z0-9\/\-]{4,20}\b",
        "Deliberation":        r"\bDeliberation\s+n[o°]?\s*[\dA-Z\-]+",
    },
}
PROFILS_C1["medical"] = {**PROFILS_C1["rgpd"], **PROFILS_C1["medical"]}
PROFILS_C1["spst"]    = {**PROFILS_C1["medical"], **PROFILS_C1["spst"]}
PROFILS_C1["cada"]    = {**PROFILS_C1["rgpd"], **PROFILS_C1["cada"]}

# ══════ C2 — Quasi-identifiants (label, pattern, poids) ══════

QUASI_IDENTIFIANTS = {
    "Genre":               (r"\b(?:M\.|Mme\.?|Monsieur|Madame|masculin|feminin)\b", 1),
    "Tranche d'age":       (r"\b(?:ne(?:e)?\s+en\s+(?:19|20)\d{2}|age(?:e)?\s+de\s+\d{2}\s+ans?)\b", 2),
    "Profession":          (r"\b(?:medecin|infirmier|directeur|cadre|ouvrier|ingenieur|DRH|chef\s+de\s+service|technicien)\b", 2),
    "Region":              (r"\b(?:Ile-de-France|PACA|Bretagne|Normandie|Occitanie|Auvergne|Hauts-de-France)\b", 1),
    "Situation familiale": (r"\b(?:celibataire|marie(?:e)?|divorce(?:e)?|veuf|veuve|pacse(?:e)?|separe(?:e)?)\b", 2),
    "Nationalite":         (r"\b(?:nationalite|ressortissant|ne(?:e)?\s+a\s+l.etranger|double\s+nationalite)\b", 2),
    "Employeur nomme":     (r"\b(?:employeur|travaille\s+(?:chez|pour)|salarie\s+de)\s+[A-Z][a-z]{2,20}\b", 2),
    "Pathologie":          (r"\b(?:diabete|cancer|hypertension|depression|addiction|alcool|obesite|BPCO|asthme|epilepsie)\b", 3),
    "Handicap/RQTH":       (r"\b(?:RQTH|handicap|invalidite|AAH|travailleur\s+handicape|TH)\b", 3),
    "Adresse partielle":   (r"\b(?:rue|avenue|boulevard|allee|impasse|chemin)\s+(?:du|de\s+la|des|de\s+l.|le|les)?\s*[A-Za-z]{3,30}\b", 2),
}

SEUILS_RISQUE = [
    (10, "critique",  "CRITIQUE",  "Reidentification tres probable — caviardage imperatif"),
    (6,  "eleve",     "ELEVE",     "Risque eleve — caviardage fortement recommande"),
    (3,  "modere",    "MODERE",    "Risque modere — examen recommande"),
    (0,  "faible",    "faible",    "Risque faible"),
]

# ══════ C3 — Secret des affaires (Loi 2018-670) ══════

SECRET_AFFAIRES = {
    "Strategie commerciale":  r"\b(?:strategie\s+commerciale|plan\s+de\s+developpement|roadmap|feuille\s+de\s+route|objectif\s+commercial)\b",
    "Donnees financieres":    r"\b(?:marge(?:\s+nette|\s+brute)?|chiffre\s+d.affaires|benefice\s+net|resultat\s+(?:net|operationnel)|EBITDA|EBE|valorisation)\b",
    "Tarification":           r"\b(?:grille\s+tarifaire|conditions\s+tarifaires|remise\s+(?:commerciale|exceptionnelle)|ristourne|prix\s+unitaire|taux\s+horaire)\b",
    "Portefeuille client":    r"\b(?:portefeuille\s+client|liste\s+de\s+clients?|fichier\s+client|base\s+client|CRM|grands\s+comptes?)\b",
    "Savoir-faire / R&D":     r"\b(?:procede\s+(?:exclusif|brevete|confidentiel)|savoir-faire|brevet|R&D|prototype|algorithme\s+proprietaire|formule)\b",
    "Negociation en cours":   r"\b(?:offre\s+en\s+cours|appel\s+d.offres|soumission|proposition\s+commerciale|avant-contrat|lettre\s+d.intention)\b",
    "Remunerations":          r"\b(?:remuneration\s+(?:brute|nette)|package\s+salarial|variable|bonus|interessement|participation|stock.?options?|BSPCE)\b",
    "Fournisseurs cles":      r"\b(?:fournisseur\s+(?:exclusif|strategique|reference)|contrat\s+cadre|conditions\s+d.achat|panel\s+fournisseur)\b",
    "Donnees de marche":      r"\b(?:part\s+de\s+marche|benchmark\s+(?:interne|confidentiel)|etude\s+de\s+marche\s+(?:interne|proprietaire)|veille\s+concurrentielle)\b",
}

COMBINAISONS_C3 = [
    ("client nomme + montant",  r"[A-Z][a-z]{2,}\s+(?:SAS|SA|SARL|SNC|GIE|CHU|CHRU).{0,80}\b\d[\d\s]{2,}\s*(?:EUR|k|M)?"),
    ("remise + client",         r"\b(?:remise|ristourne|rabais)\s+(?:de\s+)?\d+\s*%.{0,60}[A-Z]{2,}"),
    ("salaire + nom",           r"\b(?:salaire|remuneration|package)\s+(?:de\s+|:?\s*)[A-Z][a-z]{2,}"),
]


# ══════ Fonctions d'analyse ══════

def ctx(texte, match, n=50):
    d = max(0, match.start()-n); f = min(len(texte), match.end()+n)
    return f"...{texte[d:match.start()].replace(chr(10),' ').strip()} [{match.group().strip()}] {texte[match.end():f].replace(chr(10),' ').strip()}..."


def detecter_c1(doc, profil, termes):
    patterns = PROFILS_C1.get(profil, PROFILS_C1["rgpd"])
    res, vus, idx = [], set(), 0
    for pn, page in enumerate(doc):
        t = page.get_text()
        if not t.strip(): continue
        for cat, pat in patterns.items():
            for m in re.finditer(pat, t, re.IGNORECASE):
                v = m.group().strip()
                if len(v) < 3: continue
                cle = (pn, v.lower())
                if cle in vus: continue
                vus.add(cle)
                rects = page.search_for(v)
                if not rects: continue
                r = rects[0]
                res.append({"id":idx,"couche":"C1","page":pn+1,"categorie":cat,"valeur":v,
                    "contexte":ctx(t,m),"rect":[round(r.x0,1),round(r.y0,1),round(r.x1,1),round(r.y1,1)],
                    "caviarder":True,"niveau_risque":"obligatoire","note":""})
                idx += 1
        for terme in (termes or []):
            for m in re.finditer(re.escape(terme), t, re.IGNORECASE):
                cle = (pn, terme.lower())
                if cle in vus: continue
                vus.add(cle)
                rects = page.search_for(terme)
                if not rects: continue
                r = rects[0]
                res.append({"id":idx,"couche":"C1","page":pn+1,"categorie":"Terme specifie","valeur":terme,
                    "contexte":ctx(t,m),"rect":[round(r.x0,1),round(r.y0,1),round(r.x1,1),round(r.y1,1)],
                    "caviarder":True,"niveau_risque":"obligatoire","note":""})
                idx += 1
    return res, idx


def detecter_c2(doc, id_start):
    res, vus, idx, score, qi_list = [], set(), id_start, 0, []
    for pn, page in enumerate(doc):
        t = page.get_text()
        if not t.strip(): continue
        for label, (pat, poids) in QUASI_IDENTIFIANTS.items():
            for m in re.finditer(pat, t, re.IGNORECASE):
                v = m.group().strip()
                if len(v) < 3: continue
                cle = (pn, label)
                if cle in vus: continue
                vus.add(cle)
                rects = page.search_for(v)
                r = rects[0] if rects else None
                score += poids
                if label not in qi_list: qi_list.append(label)
                niv = "eleve" if poids >= 3 else ("modere" if poids == 2 else "faible")
                res.append({"id":idx,"couche":"C2","page":pn+1,"categorie":label,"valeur":v,
                    "contexte":ctx(t,m),
                    "rect":[round(r.x0,1),round(r.y0,1),round(r.x1,1),round(r.y1,1)] if r else None,
                    "poids":poids,"caviarder":False,"niveau_risque":niv,
                    "note":f"Quasi-identifiant (poids {poids}) — decision manuelle"})
                idx += 1

    niveau = "faible"; icone = "INFO"; msg = "Risque faible"
    for seuil, niv, ico, m in SEUILS_RISQUE:
        if score >= seuil: niveau, icone, msg = niv, ico, m; break

    if niveau in ("critique", "eleve"):
        for r in res: r["caviarder"] = True; r["note"] = f"Risque {niveau} — caviardage propose"

    return res, idx, score, niveau, icone, msg, qi_list


def detecter_c3(doc, id_start):
    res, vus, idx = [], set(), id_start
    for pn, page in enumerate(doc):
        t = page.get_text()
        if not t.strip(): continue
        for cat, pat in SECRET_AFFAIRES.items():
            for m in re.finditer(pat, t, re.IGNORECASE):
                v = m.group().strip()
                if len(v) < 4: continue
                cle = (pn, v.lower()[:30])
                if cle in vus: continue
                vus.add(cle)
                rects = page.search_for(v)
                r = rects[0] if rects else None
                res.append({"id":idx,"couche":"C3","page":pn+1,"categorie":cat,"valeur":v,
                    "contexte":ctx(t,m),
                    "rect":[round(r.x0,1),round(r.y0,1),round(r.x1,1),round(r.y1,1)] if r else None,
                    "caviarder":False,"niveau_risque":"alerte",
                    "note":"Secret des affaires — decision DPO/direction requise"})
                idx += 1
        for label, pat in COMBINAISONS_C3:
            for m in re.finditer(pat, t, re.IGNORECASE):
                v = m.group().strip()
                cle = (pn, "comb_" + v.lower()[:20])
                if cle in vus: continue
                vus.add(cle)
                rects = page.search_for(v[:30])
                r = rects[0] if rects else None
                res.append({"id":idx,"couche":"C3","page":pn+1,
                    "categorie":f"Combinaison a risque : {label}","valeur":v[:80],
                    "contexte":ctx(t,m),
                    "rect":[round(r.x0,1),round(r.y0,1),round(r.x1,1),round(r.y1,1)] if r else None,
                    "caviarder":True,"niveau_risque":"critique",
                    "note":"Combinaison fortement identifiante — caviardage recommande"})
                idx += 1
    return res, idx


# ══════ Affichage ══════

C = {"R":"\033[91m","V":"\033[92m","J":"\033[93m","B":"\033[94m","M":"\033[95m",
     "G":"\033[90m","X":"\033[0m","N":"\033[1m"}
def col(t, c): return f"{C.get(c,'')}{t}{C['X']}"

ICONE_RISQUE = {"obligatoire": col("OBLIGATOIRE","R"), "critique": col("CRITIQUE","R"),
                "eleve": col("ELEVE","R"), "modere": col("MODERE","J"),
                "faible": col("faible","G"), "alerte": col("ALERTE","M")}

def afficher_couche(res, titre, couleur, extra=""):
    if not res:
        print(col(f"\n  {titre} — aucune detection", "G")); return
    print(); print(col(f"  {'='*66}", couleur))
    print(col(f"  {titre}  ({len(res)} occurrence(s))", "N"))
    if extra: print(col(f"  {extra}", couleur))
    print(col(f"  {'-'*66}", "G"))
    par_cat = defaultdict(list)
    for r in res: par_cat[r["categorie"]].append(r)
    for cat, items in sorted(par_cat.items()):
        print(col(f"\n  > {cat}  ({len(items)})", couleur))
        for item in items:
            dec = col("CAVIARDER", "R") if item["caviarder"] else col("conserver", "G")
            rq  = ICONE_RISQUE.get(item.get("niveau_risque",""), "")
            print(f"    [{item['id']:>3}] {dec}  p.{item['page']}  {rq}")
            print(col(f"          Valeur   : {item['valeur'][:70]}", "N"))
            print(col(f"          Contexte : {item['contexte'][:85]}", "G"))


def afficher_risque_c2(score, niveau, icone, msg, qi_list):
    print(); print(col("  "+"="*66, "J"))
    print(col("  C2 — RISQUE DE REIDENTIFICATION (CNIL, considerant 26 RGPD)", "N"))
    print(col(f"  Score cumule : {score}/15+  |  Niveau : {icone}", "J"))
    print(col(f"  {msg}", "J"))
    if qi_list: print(col(f"  Quasi-identifiants detectes : {', '.join(qi_list)}", "G"))
    print(col("  Regle CNIL k-anonymite : si un individu peut etre isole parmi", "G"))
    print(col("  moins de k=5 personnes a partir de ces QI, le risque est inacceptable.", "G"))


def afficher_resume(all_res, score_c2, niveau_c2):
    a_cav = [r for r in all_res if r["caviarder"]]
    cons  = [r for r in all_res if not r["caviarder"]]
    print(); print(col("="*70, "N"))
    print(col("  RESUME DE L'AUDIT", "N"))
    print(col("-"*70, "G"))
    for couche, label in [("C1","Donnees personnelles"),("C2","Quasi-identifiants"),("C3","Secret des affaires")]:
        sous = [r for r in all_res if r["couche"] == couche]
        n_cav = sum(1 for r in sous if r["caviarder"])
        print(f"  {couche}  {label:<35} {len(sous):>3} detection(s)  |  {n_cav:>3} a caviarder")
    if score_c2 > 0:
        print(col(f"\n  Risque reidentification global : {niveau_c2.upper()} (score {score_c2})", "J"))
    c3_alertes = [r for r in all_res if r["couche"] == "C3" and r["caviarder"]]
    if c3_alertes:
        print(col(f"  Secret des affaires : {len(c3_alertes)} zone(s) a caviarder", "M"))
    if cons:
        print(col(f"\n  Donnees conservees ({len(cons)}) :", "V"))
        for r in cons:
            note = f" — {r['note']}" if r.get("note") else ""
            print(col(f"    [{r['couche']}] p.{r['page']}  {r['categorie']}  |  {r['valeur'][:50]}{note}", "V"))
    print()
    print(f"  Total : {col(str(len(a_cav)),'R')} zone(s) a caviarder  |  {col(str(len(cons)),'V')} conservee(s)")
    print(col("="*70, "N"))


def mode_interactif(all_res):
    print(); print(col("="*70, "N"))
    print(col("  MODE INTERACTIF — VALIDATION ZONE PAR ZONE", "N"))
    print("  [Entree]=garder  o=caviarder  n=conserver  c=note  q=terminer")
    print(col("-"*70, "G"))
    for item in all_res:
        dec = col("CAVIARDER","R") if item["caviarder"] else col("CONSERVER","V")
        rq  = ICONE_RISQUE.get(item.get("niveau_risque",""), "")
        print()
        print(f"  [{item['couche']}] [{item['id']:>3}]  p.{item['page']}  {rq}")
        print(f"        {col(item['categorie'],'N')} : {col(item['valeur'][:60],'N')}")
        print(col(f"        {item['contexte'][:85]}", "G"))
        print(f"        Decision actuelle : {dec}")
        if item.get("note"): print(col(f"        Note : {item['note']}", "G"))
        try:
            rep = input("        -> o/n/c/[Entree]/q : ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nInterrompu."); break
        if rep == "q": break
        elif rep == "o": item["caviarder"] = True; item["note"] = item.get("note") or "Valide manuellement"
        elif rep == "n": item["caviarder"] = False; item["note"] = item.get("note") or "Conserve manuellement"
        elif rep == "c":
            try: item["note"] = input("        Note : ").strip()
            except (EOFError, KeyboardInterrupt): pass
    return all_res


def exporter_selection(all_res, chemin, meta):
    data = {"meta":{**meta,"date_audit":datetime.now().isoformat(),
                    "total":len(all_res),
                    "a_caviarder":sum(1 for r in all_res if r["caviarder"]),
                    "conserves":sum(1 for r in all_res if not r["caviarder"]),
                    "par_couche":{"C1":sum(1 for r in all_res if r["couche"]=="C1"),
                                  "C2":sum(1 for r in all_res if r["couche"]=="C2"),
                                  "C3":sum(1 for r in all_res if r["couche"]=="C3")}},
            "detections":all_res}
    with open(chemin,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    print(col(f"\n  Selection exportee : {chemin}", "V"))
    print(f"  A caviarder : {data['meta']['a_caviarder']}  |  Conserves : {data['meta']['conserves']}")
    print(col(f"\n  python3 caviarder.py --input {meta['source']} --output OUTPUT.pdf --selection {chemin}", "B"))


# ══════ CLI ══════

def main():
    p = argparse.ArgumentParser(description="Audit PDF trois couches : C1/C2/C3")
    p.add_argument("--input",           required=True)
    p.add_argument("--profil",          default="rgpd", choices=list(PROFILS_C1.keys()))
    p.add_argument("--termes",          nargs="*", default=[])
    p.add_argument("--secret-affaires", action="store_true")
    p.add_argument("--interactif",      action="store_true")
    p.add_argument("--export",          default="")
    args = p.parse_args()

    if not Path(args.input).exists():
        print(f"ERREUR : fichier introuvable : {args.input}"); sys.exit(1)

    print(); print(col("="*70,"N"))
    print(col("  AUDIT CAVIARDAGE — TROIS COUCHES","N"))
    print(col(f"  {args.input}  |  profil : {args.profil}","G"))
    print(col("="*70,"N"))

    doc = fitz.open(args.input)

    # C1
    print(col("\n  Analyse C1 — Donnees personnelles...", "R"))
    res_c1, idx = detecter_c1(doc, args.profil, args.termes)
    afficher_couche(res_c1, "C1 — DONNEES PERSONNELLES DIRECTEMENT IDENTIFIANTES", "R")

    # C2
    print(col("\n  Analyse C2 — Quasi-identifiants et risque de reidentification...", "J"))
    res_c2, idx, score_c2, niveau_c2, icone_c2, msg_c2, qi_list = detecter_c2(doc, idx)
    afficher_risque_c2(score_c2, niveau_c2, icone_c2, msg_c2, qi_list)
    afficher_couche(res_c2, "C2 — QUASI-IDENTIFIANTS", "J",
                    extra=f"Score : {score_c2}  |  {icone_c2}")

    # C3
    res_c3 = []
    if args.secret_affaires:
        print(col("\n  Analyse C3 — Secret des affaires (Loi 2018-670)...", "M"))
        res_c3, idx = detecter_c3(doc, idx)
        afficher_couche(res_c3, "C3 — SECRET DES AFFAIRES (Loi 2018-670)", "M")
    else:
        print(col("\n  C3 non active — ajouter --secret-affaires", "G"))

    doc.close()
    all_res = res_c1 + res_c2 + res_c3

    if not all_res:
        print(col("\n  Aucune donnee detectee.", "V")); sys.exit(0)

    afficher_resume(all_res, score_c2, niveau_c2)

    if args.interactif:
        all_res = mode_interactif(all_res)
        afficher_resume(all_res, score_c2, niveau_c2)

    if args.export:
        exporter_selection(all_res, args.export,
            {"source":args.input,"profil":args.profil,
             "secret_affaires":args.secret_affaires,
             "score_reidentification":score_c2,
             "niveau_reidentification":niveau_c2})
    else:
        print(col("  Conseil : ajouter --export selection.json", "J"))

if __name__ == "__main__":
    main()
