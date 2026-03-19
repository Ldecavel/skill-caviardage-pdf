# Cadre normatif du caviardage — Textes de référence

## 1. RGPD et données personnelles

### Art. 4 RGPD — Définition de la donnée personnelle
Toute information se rapportant à une personne physique identifiée **ou identifiable**.
Est réputée identifiable la personne qui peut être identifiée, directement ou **indirectement**,
notamment par référence à un identifiant ou à un ou plusieurs éléments spécifiques.

### Considérant 26 RGPD — Risque de réidentification
Pour déterminer si une personne est identifiable, il convient de prendre en considération
l'ensemble des moyens raisonnablement susceptibles d'être utilisés par le responsable du traitement
ou par toute autre personne pour identifier la personne physique directement ou indirectement.

> **Conséquence pratique** : une information qui semble anodine (profession, région, situation
> familiale) devient une donnée personnelle si sa combinaison avec d'autres informations du
> même document ou accessibles en ligne permet de réidentifier une personne.

### Art. 9 RGPD — Données sensibles
Traitement interdit sauf exception (santé, origine ethnique, opinions politiques, etc.).
Pour ces données, le caviardage est une obligation renforcée.

### Art. 89 RGPD — Exceptions (archivage, recherche, statistiques)
Possibilité de communication avec anonymisation partielle, sous réserve de garanties
techniques et organisationnelles suffisantes.

---

## 2. Guide CNIL sur l'anonymisation (2019)

La CNIL distingue trois critères cumulatifs pour qu'une donnée soit réellement anonymisée :

| Critère | Description | Test pratique |
|---------|-------------|---------------|
| **Individualisation** | Impossible d'isoler une personne dans un ensemble | Peut-on trouver UN individu dans le document ? |
| **Corrélation** | Impossible de relier des jeux de données concernant la même personne | Peut-on croiser ce document avec d'autres sources ? |
| **Inférence** | Impossible de déduire des informations sur une personne | Peut-on deviner une information non divulguée ? |

### Notion de k-anonymité
Un ensemble de données respecte la k-anonymité si chaque individu est indiscernable d'au moins
k-1 autres individus. La CNIL recommande k ≥ 5 comme seuil minimal.

### Quasi-identifiants — Exemples documentés
La combinaison suivante permet d'identifier 87% des personnes aux États-Unis
(étude Sweeney, 2000, reprise par la CNIL) :
- Code postal + Date de naissance + Genre

En France, des combinaisons similaires sont efficaces pour les documents RH, médicaux et judiciaires.

---

## 3. Loi 2018-670 — Secret des affaires

### Art. L151-1 Code de commerce — Définition
Est protégée en tant que secret des affaires toute information qui réunit les trois conditions :
1. **Secret** : elle n'est pas généralement connue ou aisément accessible
2. **Valeur commerciale** : elle a une valeur commerciale, effective ou potentielle, du fait de son caractère secret
3. **Protection** : elle a fait l'objet de mesures de protection raisonnables

### Art. L152-1 — Exceptions légales
N'est pas protégé ce qui est divulgué pour révéler une activité illégale, une faute ou un
manquement, dans l'intérêt général (lanceurs d'alerte), ou dans le cadre d'une procédure judiciaire.

### Catégories couramment protégées
- Stratégies commerciales et plans de développement
- Données financières non publiques (marges, valorisations, EBITDA)
- Listes de clients et conditions tarifaires
- Procédés techniques et savoir-faire (même non brevetés)
- Données de rémunération individuelles ou globales
- Négociations en cours (offres, avant-contrats)

---

## 4. CADA — Communicabilité des documents administratifs

### Art. L311-6 CRPA — Documents non communicables à des tiers
Sont exclus de la communication :
- Les documents portant atteinte à la vie privée
- Les documents portant atteinte au secret médical
- Les documents portant atteinte au secret en matière commerciale et industrielle
- Les documents contenant des appréciations ou jugements de valeur sur une personne physique

### Art. L311-7 CRPA — Communication partielle
Un document partiellement communicable doit être communiqué après caviardage des mentions
non communicables. Le caviardage doit être véritable (pas de simple cache visuel).

### Jurisprudence CADA
- Avis 2019-3721 : rappel que le caviardage doit rendre les données définitivement inaccessibles
- Avis 2021-1842 : obligation de purger les métadonnées lors de la communication de fichiers PDF

---

## 5. Articulation des trois couches

```
Document à communiquer
│
├── Contient-il des DCP (art. 4 RGPD) ?
│   └─ OUI → Caviardage C1 obligatoire (sauf exception art. 89)
│
├── Contient-il des quasi-identifiants combinés ?
│   └─ OUI → Évaluation C2 requise (k-anonymité CNIL)
│             Score ≥ 6 → caviardage recommandé
│             Score ≥ 10 → caviardage impératif
│
└── Contient-il des informations de valeur commerciale ?
    └─ OUI → Analyse C3 : décision DPO + direction
              Combinaisons critiques → caviardage systématique
```

---

## 6. Références documentaires

- CNIL — Guide pratique sur l'anonymisation des données (2019)
- CNIL — Délibération 2019-053 sur le caviardage
- WP29 — Opinion 05/2014 on Anonymisation Techniques (révisée CEPD)
- CADA — Guide de la communicabilité (édition 2023)
- Loi n° 2018-670 du 30 juillet 2018 (transposition directive UE 2016/943)
- RGPD — Règlement UE 2016/679, considérants 26, 28, 29
