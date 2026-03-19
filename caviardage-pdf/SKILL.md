---
name: caviardage-pdf
description: >
  Skill expert pour le caviardage de documents PDF conforme CNIL, RGPD et loi 2018-670 sur le
  secret des affaires. Déclencher ce skill dès que l'utilisateur mentionne : caviarder, caviardage,
  occulter, anonymiser, masquer, noircir, redaction, données personnelles PDF, secret des affaires,
  préparer pour communication, CADA, réidentification, quasi-identifiants, communicabilité.
  Analyse en trois couches distinctes : (1) données personnelles directement identifiantes,
  (2) quasi-identifiants et risque de réidentification CNIL, (3) secret des affaires.
  Produit un PDF caviardé avec suppression véritable (données non récupérables), un rapport
  structuré par couche, et des alertes sur les risques résiduels. Gère PDF texte et numérisés (OCR).
  NE PAS utiliser pour de simples modifications visuelles sans suppression des données sous-jacentes.
---

# Skill — Caviardage de Documents PDF

## Cadre normatif

Ce skill applique trois corps de règles distincts, qui peuvent se combiner sur un même document.

| Couche | Fondement | Objet | Obligation |
|--------|-----------|-------|-----------|
| **C1** | RGPD art. 4 + Loi IeL | Données à caractère personnel directement identifiantes | Caviardage systématique sauf exception art. 89 |
| **C2** | RGPD considérant 26 + Guide CNIL anonymisation | Quasi-identifiants et risque de réidentification | Alerte + évaluation k-anonymité avant communication |
| **C3** | Loi 2018-670 (L151-1 à L152-4 C. com.) | Informations relevant du secret des affaires | Caviardage si divulgation nuit à l'organisme |

> **Principe CNIL (considérant 26 RGPD)** : une donnée qui semble anodine peut permettre
> la réidentification d'une personne lorsqu'elle est croisée avec d'autres informations
> accessibles. L'analyse ne se limite donc pas aux données directement identifiantes.

---

## Principe technique fondamental

> **Caviardage véritable ≠ masquage visuel.**
> Un rectangle noir posé sur du texte laisse les données lisibles dans le flux interne du PDF.
> Ce skill utilise systématiquement add_redact_annot() + apply_redactions() de PyMuPDF,
> qui supprime physiquement le contenu sous-jacent (texte, vecteurs, images).

---

## Workflow

```
1. Analyser le document (type, OCR, métadonnées, pièces jointes)
2. AUDIT C1 — données directement identifiantes (DPI)
3. AUDIT C2 — quasi-identifiants + score de risque de réidentification CNIL
4. AUDIT C3 — secret des affaires (loi 2018-670)
5. PRÉSENTER la liste complète, couche par couche, avec contexte et niveau de risque
6. SÉLECTION — valider ou exclure chaque zone (ex : nom de la personne concernée)
7. APPLIQUER le caviardage véritable sur les zones retenues
8. PURGER les métadonnées (auteur, créateur, XMP)
9. LIVRER le PDF + rapport structuré (traçabilité DPO)
```

**Commande d'audit complet (recommandé) :**

```bash
python3 scripts/audit_caviardage.py \
  --input document.pdf \
  --profil rgpd \
  --secret-affaires \
  --interactif \
  --export selection.json
```

**Commande de caviardage sur sélection validée :**

```bash
python3 scripts/caviarder.py \
  --input document.pdf \
  --output document_caviarde.pdf \
  --selection selection.json \
  --rapport rapport_caviardage.txt
```

---

## Couche C1 — Données personnelles directement identifiantes

Données visées par l'art. 4 RGPD permettant d'identifier directement une personne physique.

| Profil | Patterns activés |
|--------|-----------------|
| `rgpd` | Email, téléphone, NIR, SIRET, IBAN, date naissance, IP, code postal |
| `medical` | Profil rgpd + RPPS, ADELI, numéro patient, CIM-10 |
| `spst` | Profil medical + numéro adhérent, APE/NAF, résultat aptitude |
| `cada` | Profil rgpd + mentions secret, références internes, délibérations |

---

## Couche C2 — Quasi-identifiants et risque de réidentification

Référence : Guide CNIL anonymisation (2019), WP29/CEPD.

Un quasi-identifiant est une donnée qui, seule, ne permet pas d'identifier une personne,
mais dont la combinaison avec d'autres quasi-identifiants du même document peut permettre
une réidentification ("singling out", considérant 26 RGPD).

**Score de risque par quasi-identifiant détecté :**

```
Score 0-2  → Risque FAIBLE    — pas d'alerte
Score 3-5  → Risque MODÉRÉ   — alerte signalée
Score 6-9  → Risque ÉLEVÉ    — caviardage recommandé
Score ≥ 10 → Risque CRITIQUE — réidentification très probable, caviardage impératif
```

Règle CNIL k-anonymité : si un individu peut être isolé parmi moins de k=5 autres personnes
à partir des quasi-identifiants présents, le risque est inacceptable.

---

## Couche C3 — Secret des affaires

Référence : Loi n° 2018-670 du 30 juillet 2018, art. L151-1 à L152-4 du Code de commerce.

Trois conditions cumulatives pour qu'une information soit protégée :
1. Elle n'est pas généralement connue ou aisément accessible
2. Elle a une valeur commerciale du fait de son caractère secret
3. Son détenteur a pris des mesures de protection raisonnables

Catégories détectées : stratégie commerciale, données financières non publiques, tarification,
portefeuille client, savoir-faire technique, négociations en cours, rémunérations, fournisseurs.

Le script alerte en priorité sur les combinaisons client nommé + montant financier (réidentification
commerciale) et sur les procédés susceptibles de relever de la propriété industrielle.

---

## Rapport structuré (extrait)

```
[C1 — DONNÉES PERSONNELLES]
  CAVIARDÉ  p.2  Email    : jean.dupont@exemple.fr
  CONSERVÉ  p.1  Nom      : Jean DUPONT (personne concernée)

[C2 — RISQUE DE RÉIDENTIFICATION]
  Score 7/15 — RISQUE ÉLEVÉ
  Quasi-identifiants combinés : Genre + Profession + Région + Situation familiale
  Recommandation : caviarder au moins 2 quasi-identifiants pour k-anonymité acceptable.

[C3 — SECRET DES AFFAIRES]
  ALERTE  p.4  Tarification       : "grille tarifaire confidentielle 2025"
  ALERTE  p.6  Données financières: "marge nette 23,4 %"

[MÉTADONNÉES] Purgées (auteur, créateur, XMP)

[RISQUE RÉSIDUEL]
  2 quasi-identifiant(s) conservé(s) — surveiller les usages du document.
```

---

## Références complémentaires

- `scripts/audit_caviardage.py` — Audit trois couches + sélection interactive + export JSON
- `scripts/caviarder.py` — Caviardage véritable avec support --selection
- `references/cadre_legal.md` — Textes complets RGPD, loi 2018-670, CNIL, CRPA
- `references/caviardage-ia.md` — Identification IA des données non structurées
- `references/ocr-caviardage.md` — Caviardage des PDF numérisés (Tesseract)

### Format du fichier de sélection (selection.json)

Chaque entrée contient :
- `couche` : C1, C2 ou C3
- `caviarder` : true / false
- `note` : motif (traçabilité DPO)
- `niveau_risque` : faible, modere, eleve, critique (C2) ou alerte (C3)
- `valeur`, `categorie`, `contexte`, `page`, `rect`
