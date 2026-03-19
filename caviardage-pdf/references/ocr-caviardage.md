# Caviardage des PDF numérisés (OCR)

## Problématique

Un PDF numérisé est une image photographique d'un document.
PyMuPDF ne peut pas y chercher du texte directement.
Il faut d'abord faire de l'OCR pour localiser les zones de texte.

---

## Option 1 — OCR intégré PyMuPDF (recommandé)

PyMuPDF 1.22+ intègre un moteur OCR (via Tesseract si installé).

```bash
# Installer Tesseract + langue française
apt-get install tesseract-ocr tesseract-ocr-fra -y
```

```python
import fitz
import re

doc = fitz.open("scan.pdf")
zones = []

for page_num, page in enumerate(doc):
    # OCR de la page (retourne un textpage avec coordonnées)
    tp = page.get_textpage_ocr(
        flags=fitz.TEXT_PRESERVE_WHITESPACE,
        dpi=300,
        full=True,
        language="fra"
    )
    
    # Extraction avec positions
    blocks = page.get_text("words", textpage=tp)
    full_text = page.get_text(textpage=tp)
    
    # Chercher des patterns dans le texte OCR
    patterns = {
        "NIR": r"\b[12][0-9]{2}[0-1][0-9][0-9]{2}[0-9]{3}[0-9]{3}[0-9]{2}\b",
        "Email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    }
    
    for motif, pattern in patterns.items():
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            terme = match.group().strip()
            rects = page.search_for(terme, textpage=tp)
            for r in rects:
                zones.append((page_num, r, motif))

# Appliquer le caviardage normalement
for (page_num, rect, motif) in zones:
    doc[page_num].add_redact_annot(quad=rect, fill=(0, 0, 0))

for page in doc:
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS, graphics=True)

doc.save("scan_caviarde.pdf", garbage=4, deflate=True, clean=True)
doc.close()
```

---

## Option 2 — pdf2image + pytesseract (alternative)

```bash
pip install pdf2image pytesseract --break-system-packages
apt-get install poppler-utils tesseract-ocr tesseract-ocr-fra -y
```

```python
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageDraw
import fitz
import re

# Convertir en images
images = convert_from_path("scan.pdf", dpi=300)

# OCR avec positions
zones_par_page = []
for page_num, img in enumerate(images):
    data = pytesseract.image_to_data(img, lang="fra", output_type=pytesseract.Output.DICT)
    
    # Reconstruire le texte et localiser les patterns
    n = len(data["text"])
    for i in range(n):
        mot = data["text"][i].strip()
        if not mot:
            continue
        # Vérifier si le mot fait partie d'un pattern
        if re.match(r"\b\d{15}\b", mot):  # NIR simplifié
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            # Convertir pixels image -> points PDF
            # (dpi=300, PDF en 72 dpi) -> ratio = 72/300 = 0.24
            ratio = 72 / 300
            zones_par_page.append((
                page_num,
                x * ratio, y * ratio,
                (x + w) * ratio, (y + h) * ratio,
                "NIR"
            ))

# Appliquer via PyMuPDF
doc = fitz.open("scan.pdf")
for (page_num, x0, y0, x1, y1, motif) in zones_par_page:
    rect = fitz.Rect(x0, y0, x1, y1)
    doc[page_num].add_redact_annot(quad=rect, fill=(0, 0, 0))

for page in doc:
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

doc.save("scan_caviarde.pdf", garbage=4, deflate=True, clean=True)
doc.close()
```

---

## Conseils pour PDFs numérisés

- **Qualité du scan** : minimum 200 DPI pour un OCR fiable, 300 DPI recommandé
- **Orientation** : redresser les pages de travers avant OCR (`fitz.Page.set_rotation()`)
- **Vérification manuelle** : l'OCR n'est pas infaillible, relire après caviardage
- **Tester le résultat** : sélectionner la zone caviardée dans un lecteur PDF doit être impossible
- **Pièges courants** :
  - Le scan peut avoir du bruit (pixels parasites) qui gêne l'OCR
  - Les polices stylisées (manuscrit, tampon) sont moins bien reconnues
  - Préférer caviarder "large" (agrandir légèrement les rects) pour les zones critiques
