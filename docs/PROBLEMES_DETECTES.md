# Problemes Detectes

Analyse de qualite du code de l'API Items CRUD.

---

## 1. Securite

| Fichier | Ligne | Probleme |
|---------|-------|----------|
| `app/main.py` | 41 | Secret en dur : `secret = "fezffzefzefzlfzhfzfzfjzfzfzfdzgerg54g651fzefg51zeg5g"` |
| `app/main.py` | 42 | Cle API en dur : `API_KEY = "sk-1234567890abcdef"` |
| `.env` | - | Contient des placeholders pour credentials sensibles (APP_ID, PRIVATE_KEY, AZURE_CREDENTIALS) qui ne doivent pas etre commites |
| `docker-compose.yml` | 6-7 | Mot de passe PostgreSQL en dur (`postgres/postgres`) sans variable d'environnement externe |

**Impact** : Fuite de secrets si le code est pousse sur un depot public. Les secrets doivent etre dans des variables d'environnement ou un gestionnaire de secrets.

---

## 2. Imports inutilises

Detectes par `ruff check .` (7 erreurs F401) :

| Fichier | Ligne | Import inutilise |
|---------|-------|------------------|
| `app/main.py` | 2 | `import os` |
| `app/main.py` | 3 | `import sys` |
| `app/main.py` | 6 | `import json` |
| `app/main.py` | 7 | `from typing import Dict` |
| `app/main.py` | 7 | `from typing import Any` |
| `app/models/item.py` | 2 | `from typing import Optional` |
| `app/schemas/item.py` | 2 | `from typing import Optional` |

---

## 3. Formatage

| Fichier | Ligne | Probleme |
|---------|-------|----------|
| `app/main.py` | 44 | Ligne trop longue (depasse 88 caracteres) : `very_long_variable_name_that_exceeds_line_length = "Cette ligne est..."` |
| `app/schemas/item.py` | 17-18 | Ligne vide superflue entre `ItemUpdate` et `ItemResponse` |

---

## 4. Code mort / Variables inutilisees

| Fichier | Ligne | Probleme |
|---------|-------|----------|
| `app/main.py` | 11 | `DEBUG_MODE = True` defini mais jamais utilise |
| `app/main.py` | 12 | `UNUSED_VAR = "cette variable n'est jamais utilisee"` jamais referencee |
| `app/main.py` | 41-42 | `secret` et `API_KEY` definis mais jamais utilises dans le code |
| `app/main.py` | 44 | `very_long_variable_name_that_exceeds_line_length` definie mais jamais utilisee |
| `app/models/item.py` | 11-12 | `_legacy_method()` : methode vide (`pass`) jamais appelee |
| `app/database.py` | 22 | `POOL_SIZE = 10` defini mais jamais passe a `create_engine()` |

---

## 5. Types

Detecte par `mypy app/` (1 erreur) :

| Fichier | Ligne | Probleme |
|---------|-------|----------|
| `app/services/item_service.py` | 35 | Type incompatible pour `order_by(Item.id)` : `int | None` n'est pas un type valide pour `order_by` |
| `app/routes/items.py` | 32-35 | Fonctions `root()` et `health()` (dans main.py L32, L37) sans annotation de type retour |
| `app/routes/items.py` | 49-56 | `delete_item()` sans type de retour explicite ni `return` explicite |

---

## 6. Documentation

| Fichier | Ligne | Probleme |
|---------|-------|----------|
| `app/main.py` | 32 | `root()` : pas de docstring |
| `app/main.py` | 37 | `health()` : pas de docstring |
| `app/main.py` | 16 | `lifespan()` : docstring manquante |
| `app/routes/items.py` | 23 | `get_item()` : pas de docstring |
| `app/routes/items.py` | 34 | `create_item()` : pas de docstring |
| `app/routes/items.py` | 39 | `update_item()` : pas de docstring |
| `app/routes/items.py` | 50 | `delete_item()` : pas de docstring |
| `app/models/item.py` | 4 | Classe `Item` : pas de docstring |

---

## 7. Tests

| Probleme | Detail |
|----------|--------|
| Aucun test existant | `pytest` collecte 0 tests (`collected 0 items`) |
| Pas de dossier `tests/` | Aucune couverture de test pour les routes, services ou modeles |

---

## 8. Resume des outils

| Outil | Resultat |
|-------|----------|
| `ruff check .` | **7 erreurs** (toutes F401 - imports inutilises) |
| `mypy app/` | **1 erreur** (type incompatible dans `order_by`) |
| `pytest` | **0 tests** collectes |

---

## 9. Questions de reflexion

### Le code fonctionne, mais :

1. **Est-il maintenable ?**
   - La separation en couches (models/routes/schemas/services) est bonne
   - Cependant, le code mort et les variables inutilisees polluent la lisibilite
   - L'absence de tests rend toute modification risquee

2. **Est-il securise ?**
   - Non : des secrets sont en dur dans le code source (`main.py` L41-42)
   - Le fichier `.env` contient des placeholders pour des credentials sensibles
   - Le mot de passe PostgreSQL est en dur dans `docker-compose.yml`

3. **Est-il bien documente ?**
   - `item_service.py` est bien documente (docstrings completes avec Args/Returns/Example)
   - `database.py` a une bonne docstring de module
   - Les routes et le main manquent de documentation

### Comment detecter ces problemes automatiquement ?

- **Linting** : `ruff` (imports, formatage, code mort)
- **Type checking** : `mypy` (erreurs de types)
- **Tests** : `pytest` (couverture fonctionnelle)
- **Secrets** : `gitleaks`, `trufflehog`, ou `detect-secrets` (secrets dans le code)
- **Quand les executer** : dans un pipeline CI/CD (pre-commit hooks + GitHub Actions)
