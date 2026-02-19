# Analyse technique détaillée de l'API (angle Data Engineer)

## 1. Périmètre et méthode

Cette analyse couvre le code applicatif présent dans:
- `app/main.py`
- `app/database.py`
- `app/models/item.py`
- `app/schemas/item.py`
- `app/services/item_service.py`
- `app/routes/items.py`
- `docker-compose.yml`
- `Dockerfile`
- `pyproject.toml`

Objectif: évaluer la robustesse de l'API CRUD sous l'angle **fiabilité des données**, **contrats de schéma**, **exploitation**, **scalabilité** et **qualité CI/CD**.

## 2. Vue d'architecture actuelle

Architecture logique actuelle:
1. Client HTTP -> FastAPI (`app/main.py`)
2. Router -> Service (`app/routes/items.py` -> `app/services/item_service.py`)
3. Service -> SQLModel/SQLAlchemy Session (`app/database.py`)
4. PostgreSQL 16 via Docker Compose (`docker-compose.yml`)

Points positifs:
- Séparation route/service/modèle déjà en place.
- Session DB injectée via dépendance (`Depends(get_db)`), partiellement.
- Démarrage local et conteneurisé opérationnel après correction de configuration.

## 3. Analyse des contrats API

### Endpoints exposés
- `GET /` : message de base.
- `GET /health` : health statique.
- `GET /items/` : pagination offset/limit.
- `GET /items/{item_id}` : lecture par id.
- `POST /items/` : création.
- `PUT /items/{item_id}` : update.
- `DELETE /items/{item_id}` : suppression.

### Problèmes fonctionnels majeurs

1. Signature de `POST /items/` incorrecte
Référence: `app/routes/items.py:31-33`
- `create_item(item_data, db)` ne typpe pas `item_data` en `ItemCreate`.
- `db` n'est pas injecté via `Depends(get_db)`.
- Effet attendu: contrat OpenAPI dégradé, validation Pydantic absente, comportement runtime potentiellement erratique.

2. `item_id` non typé sur `GET /items/{item_id}`
Référence: `app/routes/items.py:20-22`
- `item_id` sans type -> pas de validation FastAPI (422) en amont.
- Risque de conversions implicites et erreurs de qualité d'entrée.

3. Pagination non bornée malgré constante déclarée
Référence: `app/routes/items.py:12`, `app/routes/items.py:15-17`
- `MAX_ITEMS_PER_PAGE = 1000` est défini mais jamais appliqué.
- Risque de requêtes lourdes (`limit` arbitrairement grand) et surcharge mémoire.

## 4. Modèle de données et gouvernance de schéma

### Modèle actuel
Référence: `app/models/item.py:4-9`
- `id` PK auto.
- `nom` indexé.
- `prix` en `float`.

### Risques data

1. Usage de `float` pour un prix
Références: `app/models/item.py:9`, `app/schemas/item.py:6`, `app/schemas/item.py:15`
- Le type flottant introduit des erreurs d'arrondi (IEEE 754).
- En contexte analytique/financier, préférer `Decimal` + `NUMERIC(p,s)`.

2. Contraintes principalement côté API, pas explicitement au niveau DB
- Validation `prix > 0` et longueur `nom` sont dans les schémas (`app/schemas/item.py:5-6`, `app/schemas/item.py:14-15`).
- Le modèle SQL ne déclare ni `max_length` ni contrainte SQL explicite.
- En ingestion hors API, la DB pourrait accepter des valeurs non conformes.

3. Absence de colonnes de traçabilité data
- Pas de `created_at`, `updated_at`, `source`, `deleted_at`.
- Limite l'observabilité des mutations et la reconstruction d'historique.

4. Pas de gestion de version de schéma
- `SQLModel.metadata.create_all(engine)` au startup (`app/main.py:17`).
- Pas de migrations outillées (type Alembic), donc dérive de schéma probable entre environnements.

## 5. Couche service et transactions

Points corrects:
- CRUD centralisé dans `ItemService` (bonne base de séparation de responsabilités).
- `commit`/`refresh` présents sur create/update.

Points à risque:

1. Pas de gestion d'erreurs transactionnelles
- Pas de `rollback` explicite sur exception DB.
- Pas de mapping d'erreurs techniques vers erreurs métier/API.

2. Pagination non déterministe
Référence: `app/services/item_service.py:35`
- `select(Item).offset(skip).limit(limit)` sans `order_by`.
- L'ordre de retour peut varier, ce qui casse la reproductibilité (problème important pour export/ETL incrémental).

3. Pas de stratégie de verrouillage/concurrence
- Update par lecture/modification/commit simple.
- Pas d'optimistic locking (versionning), ni check anti-écrasement.

## 6. Couche DB / configuration d'exécution

Référence: `app/database.py`

Constats:
- Chargement `.env` explicite désormais en place (`app/database.py:13-15`).
- Vérification de présence de `DATABASE_URL` ajoutée (`app/database.py:17-20`).

Lacunes:
- `POOL_SIZE` déclaré mais non utilisé (`app/database.py:22`).
- `create_engine(DATABASE_URL)` sans paramètres de résilience (`pool_pre_ping`, `pool_size`, `max_overflow`, `pool_recycle`).
- Timeout/keepalive non explicités.

Impacts data engineering:
- Risque de connexions mortes en run long.
- Variabilité de latence sous charge.

## 7. Observabilité et exploitation

### État actuel
- Endpoint `/health` statique (`app/main.py:36-38`), ne vérifie pas la DB.
- Pas de logs structurés par requête.
- Pas de métriques (latence, QPS, erreurs 4xx/5xx, temps DB).
- Pas de tracing distribué.

### Impact
- MTTD élevé (détection lente des pannes).
- Diagnostic production difficile.
- Impossible de piloter des SLO/API SLA fiables.

## 8. Sécurité et conformité

### Problèmes critiques

1. Secrets en dur dans le code
Références: `app/main.py:41-42`
- Exposition directe de clé/API token-like.
- Risque de fuite secret, non-conformité sécurité de base.

2. Hygiène code faible (code mort/variables inutilisées)
- Imports inutiles: `app/main.py:2-7`, `app/routes/items.py:3-4`.
- Variables inutilisées: `app/main.py:11-12`, `app/main.py:44`.
- Fonction legacy non utilisée: `app/routes/items.py:56-58`.

Ces marqueurs sont souvent intentionnels en exercice CI/CD pour vérifier l'efficacité des quality gates.

## 9. Qualité logicielle et CI/CD

### État observé
- Dossier `tests/` vide (seulement `.gitkeep`).
- Pas de pipeline CI visible dans ce dépôt (`.github/` absent).
- `README.md` non documenté (`A REMPLIR`).

### Risques
- Régressions silencieuses.
- Contrat API non protégé (pas de tests de schéma/réponses).
- Déploiement non sécurisé sans quality gates.

### Quality gates recommandés (minimum)
1. `ruff check .` (lint + imports morts + secrets hardcodés via règle dédiée)
2. `black --check .` (format)
3. `mypy app` (typage)
4. `pytest -q` (unit + intégration API + DB)
5. Scan sécurité dépendances (`pip-audit` ou `safety`)
6. Build conteneur + smoke test (`/health` + DB check)

## 10. Matrice de criticité (priorisée)

| Priorité | Sujet | Impact | Référence |
|---|---|---|---|
| P0 | Signature `POST /items/` invalide | Contrat API cassé / bug runtime | `app/routes/items.py:31-33` |
| P0 | Secrets hardcodés | Risque sécurité majeur | `app/main.py:41-42` |
| P0 | Pas de tests automatisés | Régressions non détectées | `tests/.gitkeep` |
| P1 | Prix en `float` | Erreurs de précision data | `app/models/item.py:9` |
| P1 | Pagination non bornée et non ordonnée | Perf + incohérence analytique | `app/routes/items.py:15`, `app/services/item_service.py:35` |
| P1 | Health check non dépendant DB | Faux positifs de disponibilité | `app/main.py:36-38` |
| P1 | `create_all` au startup | Drift de schéma / migrations non maîtrisées | `app/main.py:17` |
| P2 | Code mort/imports inutiles | Dette technique | `app/main.py`, `app/routes/items.py` |

## 11. Cible recommandée (niveau Data Engineer)

### Schéma et qualité des données
1. Remplacer `prix: float` par `Decimal` + colonne SQL `NUMERIC(12,2)`.
2. Ajouter contraintes DB:
   - `NOT NULL`
   - `CHECK (prix > 0)`
   - longueur `nom`
3. Ajouter colonnes d'audit:
   - `created_at TIMESTAMPTZ DEFAULT now()`
   - `updated_at TIMESTAMPTZ`
4. Introduire migrations Alembic versionnées.

### Contrat API et robustesse
1. Corriger signatures FastAPI (`ItemCreate`, `Depends(get_db)`, `item_id: int`).
2. Appliquer garde-fous pagination (`limit <= MAX_ITEMS_PER_PAGE`).
3. Ordonner les listes (`ORDER BY id`) pour pagination stable.
4. Implémenter gestion d'exception SQLAlchemy (`rollback` + erreurs HTTP propres).

### Exploitation
1. `/health` avec vérification DB (`SELECT 1`) + endpoint `/ready`.
2. Logs JSON structurés (request_id, route, durée, status).
3. Instrumentation Prometheus/OpenTelemetry.
4. SLO minimum:
   - disponibilité API
   - taux d'erreur
   - latence P95/P99
   - disponibilité DB pool.

## 12. Plan de remédiation concret

### Sprint 1 (stabilisation)
1. Corriger signatures routes + typage strict.
2. Supprimer secrets hardcodés + chargement via variables d'environnement.
3. Ajouter tests API CRUD nominaux + erreurs 404/422.
4. Ajouter health check DB réel.

### Sprint 2 (qualité data)
1. Migration `prix -> NUMERIC(12,2)` et ajout contraintes SQL.
2. Ajout colonnes d'audit et index utiles.
3. Pagination stable avec ordre + limite max.

### Sprint 3 (industrialisation CI/CD)
1. Pipeline CI complète (lint/type/test/scan/build).
2. Pipeline CD avec smoke tests post-déploiement.
3. Dashboard observabilité + alerting.

## 13. Conclusion

L'API fonctionne désormais au démarrage, mais son niveau de maturité reste **prototype pédagogique**.
Les anomalies observées (typage incomplet, secrets en dur, absence de tests, défauts de robustesse data) correspondent à des patterns fréquemment introduits dans des exercices CI/CD pour valider la capacité de diagnostic.

Avec les correctifs P0/P1 proposés, l'API peut atteindre un niveau **pré-production** cohérent pour un contexte Data Engineer.
