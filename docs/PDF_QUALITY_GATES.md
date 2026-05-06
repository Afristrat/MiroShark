# PDF Quality Gates — Bassira PDF Pipeline

Documentation des gates qualité associées au pipeline de génération PDF Bassira.

---

## 1. Tests E2E du pipeline (`test_pdf_pipeline_e2e.py`)

Exercice complet du pipeline : Loader → Enricher → `render_md()` → `render_pdf()`.

### Prérequis

| Dépendance | Rôle | Skip si absent |
|---|---|---|
| WeasyPrint ≥ 60 + GTK/Pango | Rendu PDF | Oui (tests `render_pdf`) |
| pypdf ≥ 4 | Lecture métadonnées | Oui (tests métadonnées) |
| LanguageTool (localhost:8010) | Normalisation texte | Auto-mockée en test |

### Lancer les tests

```bash
cd backend
uv run pytest tests/test_pdf_pipeline_e2e.py -v
```

Résultats attendus :
- Windows sans GTK : 7 tests pass + 5 skips (WeasyPrint)
- Linux avec GTK : 12 tests pass

---

## 2. Tests de régression visuelle (`test_pdf_visual_regression.py`)

### Niveau 1 — Hash texte extrait (pypdf)

Compare le SHA-256 du texte extrait via pypdf. Stable si le contenu textuel
du PDF ne change pas entre deux renders déterministes.

**Golden masters** : `backend/tests/fixtures/pdf_golden/<name>.hash`

Comportement :
- Si le fichier `.hash` est **absent** : il est créé (mode « record ») et le test est skipped.
- Si le fichier `.hash` est **présent** : comparaison stricte → fail si régression.

### Ajouter un nouveau golden master

```bash
# Supprimer l'existant pour régénérer
rm backend/tests/fixtures/pdf_golden/report_fr.hash

# Lancer : la première exécution crée le golden (test skipped)
cd backend && uv run pytest tests/test_pdf_visual_regression.py::TestGoldenHashText::test_golden_hash_fr -v

# Deuxième exécution : validation de la stabilité
uv run pytest tests/test_pdf_visual_regression.py::TestGoldenHashText::test_golden_hash_fr -v
```

### Niveau 2 — Comparaison pixel (pdf2image + Pillow)

Convertit le PDF en image via poppler et compare pixel par pixel.

**Tolérance** : 0,5 % des pixels peuvent différer (anti-aliasing, rendu police).

**Prérequis** : `poppler-utils` installé sur le système + `pdf2image` Python.

```bash
# Installation poppler
# Ubuntu/Debian : sudo apt-get install poppler-utils
# macOS : brew install poppler
# Windows : https://github.com/oschwartz10612/poppler-windows/releases

# Installation pdf2image
pip install pdf2image

# Lancer les tests visuels
cd backend && uv run pytest tests/test_pdf_visual_regression.py::TestGoldenPixel -v
```

**Golden masters PNG** : `backend/tests/fixtures/pdf_golden/<name>_p1.png`

### Déboguer une régression visuelle

1. Identifier le fichier `.hash` ou `.png` qui a changé.
2. Générer un diff visuel :

```python
from PIL import Image, ImageChops
import matplotlib.pyplot as plt

golden = Image.open("tests/fixtures/pdf_golden/report_fr_p1.png")
current = Image.open("/tmp/current_report_fr.png")  # sauvegarder le current

diff = ImageChops.difference(current.convert("RGB"), golden.convert("RGB"))
plt.imshow(diff)
plt.savefig("/tmp/diff_fr.png")
```

3. Si la régression est **intentionnelle** (nouveau template, changement palette) :
   - Supprimer le golden master concerné.
   - Relancer une fois pour régénérer (test skipped).
   - Relancer une deuxième fois pour valider.
   - Committer le nouveau golden master.

---

## 3. Linter palette WCAG AA (`scripts/lint_palette_contrast.py`)

Vérifie que les couleurs Causse Warm Intelligence respectent le ratio de
contraste WCAG AA (Section 1.4.3).

### Seuils

| Contexte | Ratio minimum |
|---|---|
| Texte normal (< 18pt ou < 14pt bold) | ≥ 4.5:1 |
| Texte large (≥ 18pt ou ≥ 14pt bold) | ≥ 3.0:1 |

### Paires vérifiées

| Premier plan | Arrière-plan | Type texte | Seuil |
|---|---|---|---|
| WI_CHARCOAL (#241915) | WI_CREAM (#FAF7F2) | normal | 4.5:1 |
| WI_INK (#1A0F0A) | WI_CREAM (#FAF7F2) | normal | 4.5:1 |
| WI_ORANGE (#FF8551) | WI_CREAM (#FAF7F2) | large | 3.0:1 |
| WI_MINT (#006D44) | WI_CREAM (#FAF7F2) | normal | 4.5:1 |
| WI_TERRA (#A13F0F) | WI_CREAM (#FAF7F2) | large | 3.0:1 |

### Utilisation

```bash
cd backend

# Check silencieux (exit 0 = OK, exit 1 = échec)
uv run python scripts/lint_palette_contrast.py

# Rapport détaillé
uv run python scripts/lint_palette_contrast.py --verbose
```

---

## 4. Vérification PDF/UA (accessibilité)

### Niveau basique (sans veraPDF)

Vérifié dans `test_pdf_pipeline_e2e.py` :
- `lang` meta injectée dans le `<head>` HTML avant rendu WeasyPrint
- `/Producer` présent dans les métadonnées PDF (via pypdf)
- `/MarkInfo` (Tagged PDF) — documentaire, skip si absent

### Niveau avancé (veraPDF)

Si veraPDF est disponible (jar ou CLI), le check PDF/UA-1 complet peut être
intégré via subprocess :

```python
import subprocess
import shutil

def check_vera_pdf(pdf_path: str) -> bool:
    """Lance veraPDF sur le PDF et retourne True si PDF/UA-1 conforme."""
    vera = shutil.which("verapdf") or "verapdf"
    try:
        result = subprocess.run(
            [vera, "--flavour", "ua1", pdf_path],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False  # veraPDF absent → skip
```

Installation veraPDF :

- Télécharger : https://verapdf.org/home/
- Linux/macOS : `brew install verapdf` ou package manager
- Windows : https://github.com/veraPDF/veraPDF-apps/releases

---

## 5. Dépendances complètes

### Runtime (production)

```
weasyprint>=60       # Rendu PDF (nécessite GTK/Pango sur Linux/Windows)
markdown-it-py>=3    # Markdown → HTML
pypdf>=4             # Lecture/inspection PDF
pillow>=12.0.0       # Traitement images (charts)
```

### GTK/Pango (Linux)

```bash
sudo apt-get install -y libgobject-2.0-0 libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libgdk-pixbuf-2.0-0 libffi-dev
```

### Tests uniquement (optionnel)

```
pdf2image    # Comparaison pixel (nécessite poppler-utils système)
```

---

## 6. Intégration CI

Exemple de configuration GitHub Actions :

```yaml
- name: Install GTK/Pango (Ubuntu)
  if: runner.os == 'Linux'
  run: |
    sudo apt-get update
    sudo apt-get install -y libgobject-2.0-0 libpango-1.0-0 libpangoft2-1.0-0 \
      libcairo2 libgdk-pixbuf-2.0-0 poppler-utils

- name: Run PDF pipeline tests
  run: |
    cd backend
    uv run pytest tests/test_pdf_pipeline_e2e.py tests/test_pdf_visual_regression.py \
      --tb=short -v

- name: Lint palette contrast
  run: |
    cd backend
    uv run python scripts/lint_palette_contrast.py --verbose
```
