# Skill Claude — Caviardage de documents PDF

> Skill expert pour le caviardage conforme RGPD, CNIL et loi 2018-670 sur le secret des affaires.
> Analyse en **trois couches distinctes**, suppression véritable des données sous-jacentes.

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)](https://claude.ai)
[![Licence MIT](https://img.shields.io/badge/Licence-MIT-blue)](LICENSE)
[![RGPD](https://img.shields.io/badge/Conforme-RGPD-green)](https://www.cnil.fr)
[![Loi 2018--670](https://img.shields.io/badge/Secret%20des%20affaires-Loi%202018--670-purple)](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000037284097)

---

## Présentation

Ce skill enseigne à Claude comment caviarder des documents PDF de façon professionnelle et conforme, en distinguant trois natures d'information radicalement différentes :

| Couche | Fondement | Objet |
|--------|-----------|-------|
| **C1 — Données personnelles** | RGPD art. 4 + Loi IeL | Identifiants directs : NIR, email, téléphone, RPPS, IBAN… |
| **C2 — Quasi-identifiants** | CNIL, considérant 26 RGPD | Risque de réidentification par combinaison |
| **C3 — Secret des affaires** | Loi 2018-670 (L151-1 C. com.) | Données commerciales, financières, stratégiques |

### Ce que le skill fait concrètement

1. **Audit complet** du document — détecte toutes les données sensibles, couche par couche
2. **Score de risque de réidentification** — calcul CNIL (quasi-identifiants pondérés, seuil k=5)
3. **Alertes secret des affaires** — y compris les combinaisons critiques (client + montant, remise + client…)
4. **Sélection interactive** — l'utilisateur valide ou exclut chaque zone (ex : garder le nom de la personne concernée)
5. **Caviardage véritable** via PyMuPDF (`add_redact_annot` + `apply_redactions`) — données *physiquement supprimées*, non récupérables
6. **Rapport structuré** — traçabilité DPO, données conservées justifiées, risque résiduel

---

## Installation

### Dans Claude.ai (web/mobile/desktop)

1. Télécharger `caviardage-pdf.skill` depuis les [Releases](../../releases/latest)
2. Claude.ai → Paramètres → **Customize** → **Skills** → glisser le fichier
3. Activer « Code execution and file creation » si ce n'est pas déjà fait

> Nécessite un abonnement **Pro, Max, Team ou Enterprise**.

### Dans Claude Code

```bash
# Depuis le dépôt
git clone https://github.com/VOTRE_NOM/caviardage-pdf-skill.git
cp -r caviardage-pdf-skill/caviardage-pdf ~/.claude/skills/

# Ou via le marketplace (si disponible)
/plugin marketplace add caviardage-pdf
```

---

## Utilisation

Envoyer simplement le PDF dans le chat avec une phrase comme :

```
Caviarder ce document avant communication CADA
Prépare ce compte rendu de consultation pour communication externe
Analyse ce contrat au regard du secret des affaires
Anonymise ce document RH — conserver le nom du salarié mais retirer tout le reste
```

Le skill se déclenche automatiquement. Claude présente ensuite les résultats couche par couche et attend ta validation avant d'appliquer le caviardage.

---

## Couche C1 — Données personnelles

Patterns activés selon le profil choisi :

| Profil | Données détectées |
|--------|------------------|
| `rgpd` | NIR, email, téléphone, SIRET, IBAN, date de naissance, IP, code postal |
| `medical` | Profil rgpd + RPPS, ADELI, numéro patient, CIM-10 |
| `spst` | Profil medical + numéro adhérent, APE/NAF, résultat d'aptitude |
| `cada` | Profil rgpd + références internes, délibérations |

---

## Couche C2 — Risque de réidentification (CNIL)

Le skill détecte les **quasi-identifiants** (genre, profession, région, situation familiale, pathologie, RQTH, employeur nommé…) et calcule un **score de risque cumulé** :

```
Score  0–2  → Risque faible
Score  3–5  → Risque modéré    ⚠️  examen recommandé
Score  6–9  → Risque élevé     🔴  caviardage recommandé
Score ≥ 10  → Risque critique  🚨  réidentification très probable
```

Référence : Guide CNIL anonymisation (2019), k-anonymité (seuil k=5).

---

## Couche C3 — Secret des affaires (Loi 2018-670)

Détection des catégories protégées par la loi du 30 juillet 2018 :

- Stratégie commerciale, plans de développement
- Données financières non publiques (marges, EBITDA, valorisations)
- Tarification et conditions commerciales
- Portefeuille client, CRM
- Savoir-faire technique, brevets en cours, R&D
- Négociations et offres en cours
- Rémunérations individuelles
- Fournisseurs exclusifs

**Détection des combinaisons critiques** (client nommé + montant, remise + client, salaire + nom) — marquées automatiquement CRITIQUE.

> Pour les éléments C3, la décision de caviardage appartient au DPO et/ou à la direction.
> Le skill alerte, il ne décide pas.

---

## Exemple de rapport produit

```
[C1 — DONNÉES PERSONNELLES]
  CAVIARDÉ  p.2  Email    : jean.dupont@cabinet.fr
  CAVIARDÉ  p.2  NIR      : 1 78 06 75 108 333 42
  CONSERVÉ  p.1  Nom      : Jean DUPONT (personne concernée — décision manuelle)

[C2 — RISQUE DE RÉIDENTIFICATION]
  Score 7/15 — RISQUE ÉLEVÉ
  Quasi-identifiants : Directeur (2) + marié (2) + RQTH (3)
  Recommandation : caviarder au moins 2 quasi-identifiants pour k-anonymité acceptable.

[C3 — SECRET DES AFFAIRES]
  ALERTE CRITIQUE  p.4  Combinaison : Cabinet Conseil SAS — remise 18% — 480 000 EUR
  ALERTE           p.6  Tarification : grille tarifaire confidentielle 2025

[RISQUE RÉSIDUEL]
  1 quasi-identifiant conservé — surveiller les usages du document communicable.
```

---

## Structure du dépôt

```
caviardage-pdf/
├── SKILL.md                        — instructions principales + cadre normatif
├── scripts/
│   ├── audit_caviardage.py         — audit trois couches + sélection interactive
│   └── caviarder.py                — caviardage véritable (PyMuPDF)
└── references/
    ├── cadre_legal.md              — textes RGPD, CNIL, Loi 2018-670, CADA
    ├── caviardage-ia.md            — identification IA des données non structurées
    └── ocr-caviardage.md           — caviardage des PDF numérisés (Tesseract)
```

---

## Prérequis techniques

```bash
pip install pymupdf --break-system-packages
# Optionnel pour PDF numérisés :
apt-get install tesseract-ocr tesseract-ocr-fra
```

PyMuPDF (version ≥ 1.22) est la seule dépendance obligatoire.

---

## Pourquoi « caviardage véritable » ?

Un rectangle noir posé *par-dessus* du texte laisse les données lisibles dans le flux interne du PDF — elles sont sélectionnables, copiables, et indexées par les moteurs de recherche.

Ce skill utilise exclusivement `page.add_redact_annot()` + `page.apply_redactions()` de PyMuPDF, qui **supprime physiquement** le contenu sous-jacent (texte, vecteurs, images dans les zones ciblées). Les données caviardées ne sont pas récupérables, y compris par extraction programmatique.

La purge des métadonnées (auteur, créateur, XMP) est appliquée systématiquement.

---

## Auteur

**Laurent de CAVEL - DPO**
DPO externe certifié — [DPO PARTAGE](https://dpo-partage.fr) | [DPO FRANCE](https://dpo-france.com)

Spécialiste RGPD pour SPSTI, collectivités territoriales, CSE et établissements de santé.
Auteur de quatre ouvrages de référence sur la mise en conformité RGPD.

---

## Licence

MIT — voir [LICENSE](LICENSE)

Ce skill est fourni à titre informatif et professionnel. Il ne constitue pas un avis de droit.
Les décisions de caviardage restent sous la responsabilité du DPO ou du responsable de traitement.

---

## Contribuer

Les contributions sont bienvenues, notamment :
- Nouveaux profils sectoriels (notaires, experts-comptables, établissements scolaires…)
- Patterns supplémentaires (identifiants sectoriels, formats régionaux)
- Support d'autres langues européennes
- Amélioration de la détection OCR

Ouvrir une issue ou une pull request avec la description du cas d'usage.
