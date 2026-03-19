# Identification assistée par IA des zones à caviarder

## Pourquoi l'IA ?

Les patterns regex couvrent les données *structurées* (NIR, email, téléphone).
Mais un document peut contenir des données personnelles *non structurées* :
- Noms et prénoms dans du texte courant
- Adresses postales en format libre
- Références médicales contextuelles
- Opinions ou évaluations nominatives

L'IA (Claude) peut les détecter avec une précision que le regex ne peut pas atteindre.

---

## Workflow : extraction IA + caviardage

### Étape 1 — Extraire le texte du PDF

```python
import fitz

doc = fitz.open("document.pdf")
pages_texte = []
for i, page in enumerate(doc):
    pages_texte.append({"page": i, "texte": page.get_text()})
doc.close()
```

### Étape 2 — Soumettre à Claude pour détection

```python
import anthropic
import json

client = anthropic.Anthropic()

PROMPT_DETECTION = """Tu es un expert RGPD. Analyse le texte suivant et identifie TOUTES les données personnelles 
ou informations sensibles à caviarder. Réponds UNIQUEMENT en JSON valide, sans texte supplémentaire.

Format de réponse :
{
  "zones": [
    {"texte": "Jean Dupont", "categorie": "nom_prénom", "raison": "identité nominative"},
    {"texte": "12 rue de la Paix 75001 Paris", "categorie": "adresse", "raison": "domicile"},
    ...
  ]
}

Catégories possibles : nom_prénom, adresse, email, telephone, identifiant, 
donnee_medicale, donnee_financiere, opinion_nominative, autre_donnee_personnelle.

Texte à analyser (page {page}) :
{texte}"""

zones_ia = []
for item in pages_texte:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": PROMPT_DETECTION.format(
                page=item["page"] + 1,
                texte=item["texte"][:4000]  # Limiter par page
            )
        }]
    )
    try:
        data = json.loads(response.content[0].text)
        for zone in data.get("zones", []):
            zones_ia.append({"page": item["page"], **zone})
    except json.JSONDecodeError:
        print(f"[Avertissement] Réponse IA non parseable pour page {item['page']+1}")
```

### Étape 3 — Convertir en rects et caviarder

```python
import fitz

doc = fitz.open("document.pdf")
zones_fitz = []

for zone in zones_ia:
    page = doc[zone["page"]]
    terme = zone["texte"].strip()
    rects = page.search_for(terme)
    for r in rects:
        zones_fitz.append((zone["page"], r, f"IA:{zone['categorie']}"))

# Puis appeler appliquer_caviardage() normalement
```

---

## Conseils d'utilisation

- **Limiter la taille** : découper les pages longues par blocs de 4000 caractères
- **Vérifier les résultats** avant d'appliquer : l'IA peut sur- ou sous-détecter
- **Combiner** avec les patterns regex pour une couverture maximale
- **Ne jamais envoyer** le document original à une API externe sans accord du responsable de traitement
  - Utiliser des documents anonymisés pour les tests
  - Vérifier les conditions contractuelles de sous-traitance (article 28 RGPD)

---

## Modes de déploiement conformes RGPD

| Mode | Description | Conformité |
|------|-------------|------------|
| Claude via API Anthropic (Entreprise) | API avec DPA signé | À vérifier selon données |
| Modèle local (ex: Mistral, LLaMA) | Aucune transmission | Optimal pour données sensibles |
| Claude.ai direct | Pas adapté (données confidentielles) | À proscrire |

Pour les données de santé ou données sensibles (art. 9 RGPD), **privilégier un modèle local**.
