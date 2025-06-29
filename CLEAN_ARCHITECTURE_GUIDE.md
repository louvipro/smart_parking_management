# Guide de Refactoring : Clean Architecture, Datetime, Asynchrone et Tests

Ce document sert de référence pour le refactoring du projet vers une Clean Architecture, en abordant spécifiquement les défis liés à la gestion des dates/heures, à la programmation asynchrone et aux tests.

## 1. Principes de la Clean Architecture et Stratégie de Refactoring

### Objectif
Séparer les préoccupations pour une meilleure maintenabilité, testabilité et flexibilité. Le principe clé est la "Règle de Dépendance" : les dépendances ne peuvent aller que vers l'intérieur. Les couches externes dépendent des couches internes, jamais l'inverse.

### Les Couches (du plus interne au plus externe)

1.  **Domain (Entités, Règles Métier)**
    *   **Rôle :** Le cœur de l'application. Indépendant de toute technologie. Contient les entités (ex: `Vehicle`, `ParkingSpot`, `ParkingSession`) et les règles métier pures.
    *   **Exemples dans le projet :** `src/domain/entities.py`, `src/domain/common.py`
    *   **Dépendances :** Aucune dépendance externe.

2.  **Application (Cas d'Utilisation, Services, Interfaces/Ports)**
    *   **Rôle :** Orchestre le domaine pour réaliser les fonctionnalités. Contient les interfaces (appelées "ports") pour les dépendances externes (base de données, ML, etc.) et les implémentations des services applicatifs (cas d'utilisation).
    *   **Exemples dans le projet :** `src/application/services/parking_service.py`, `src/application/repositories/` (où les interfaces comme `AbstractVehicleRepository` devraient être définies).
    *   **Dépendances :** Dépend du `Domain`.

3.  **Infrastructure (Implémentations, Adaptateurs)**
    *   **Rôle :** Contient les détails d'implémentation des interfaces définies dans la couche `Application`. C'est ici que se trouvent les bases de données concrètes (SQLAlchemy), les API externes, les frameworks UI (Streamlit) et ML (CrewAI, LiteLLM).
    *   **Exemples dans le projet :** `src/infrastructure/persistence/` (implémentations des dépôts SQLAlchemy), `src/infrastructure/api/`, `src/infrastructure/ml_agents/`, `src/infrastructure/ui/`.
    *   **Dépendances :** Dépend de l'`Application` et du `Domain`.

### Stratégie de Refactoring

1.  **Identifier les violations :** Cherchez les imports qui vont dans le mauvais sens (ex: `src/domain` qui importe depuis `src/infrastructure`).
2.  **Déplacer le code :** Assurez-vous que chaque morceau de code est dans la bonne couche.
3.  **Créer des interfaces (Ports) :** Pour les dépendances externes (ex: `AbstractVehicleRepository` dans `src/application/repositories`), et les implémentations concrètes dans `src/infrastructure/persistence/sqlalchemy_repositories`.
4.  **Injecter les dépendances :** Utiliser l'injection de dépendances (souvent via le constructeur des services) pour fournir les implémentations concrètes aux services applicatifs.

## 2. Gestion des Dates et Heures (`datetime`)

### Le Problème
Les objets `datetime` sont complexes à cause des fuseaux horaires (`timezone-aware` vs `naive`). SQLite stocke souvent sans fuseau horaire, ce qui peut entraîner des incohérences. Votre besoin est de ne considérer que la date, l'heure, les minutes et les secondes.

### La Solution Recommandée

1.  **Utiliser UTC partout en interne :** Toutes les opérations et stockages de `datetime` doivent être en UTC (Coordinated Universal Time) et `timezone-aware`. Cela élimine l'ambiguïté liée aux fuseaux horaires locaux.
    *   Utilisez `datetime.now(timezone.utc)` pour obtenir l'heure actuelle.
    *   Assurez-vous que les `datetime` lues de la base de données sont correctement converties en UTC `timezone-aware` (le type `UTCDateTime` de SQLAlchemy est conçu pour cela).

2.  **Standardiser le format d'affichage/stockage (pour votre besoin spécifique) :**
    *   **En interne :** Continuez à utiliser des objets `datetime` complets (avec microsecondes et fuseau horaire UTC). La précision est importante pour les calculs (durée de stationnement, etc.).
    *   **Lors de la conversion en chaîne de caractères pour l'affichage, les logs ou les comparaisons (notamment dans les tests) :** Utilisez `strftime('%Y-%m-%d %H:%M:%S')`. Cela tronquera les microsecondes et le fuseau horaire pour la représentation textuelle, tout en conservant la précision en interne.
    *   **Ne pas créer de `datetime_format` global comme variable :** C'est une mauvaise pratique car cela rend le code moins lisible et peut entraîner des erreurs si le format change. Préférez l'utilisation explicite de `strftime` ou des méthodes de sérialisation/désérialisation (par exemple, via Pydantic si vous exposez des dates dans des API).

### Implémentation

*   Vérifier que toutes les `datetime` lues de la DB sont bien `timezone-aware` (UTC).
*   S'assurer que les `datetime` écrites en DB sont correctement gérées par `UTCDateTime` (qui convertit en UTC `naive` pour le stockage et reconvertit en UTC `timezone-aware` à la lecture).
*   Dans les tests et les logs, utiliser `strftime('%Y-%m-%d %H:%M:%S')` pour les comparaisons ou l'affichage afin de correspondre à votre besoin de précision.

## 3. Phase de Vérification et Commit Incrémental

Après avoir refactoré une section majeure (par exemple, une couche entière, ou la gestion des `datetime` dans un module clé), il est crucial de vérifier la stabilité du projet et de sauvegarder votre travail.

### Étapes de Vérification

1.  **Exécuter tous les tests :**
    ```bash
    make test
    ```
    Assurez-vous que tous les tests passent. Si des tests échouent, corrigez-les immédiatement. C'est votre filet de sécurité.

2.  **Vérifier le fonctionnement de l'application (si applicable) :**
    Lancez l'application Streamlit pour une vérification rapide des fonctionnalités clés.
    ```bash
    make run-app
    ```
    Assurez-vous que l'interface utilisateur se charge et que les interactions de base fonctionnent comme prévu.

### Sauvegarde et Commit

Si toutes les vérifications sont positives :

1.  **Stager vos changements :**
    ```bash
    git add .
    ```

2.  **Créer un commit significatif :**
    ```bash
    git commit -m "refactor: [Description concise de la phase terminée]"
    ```
    Exemple : `git commit -m "refactor: Implement initial Domain layer and entities"` ou `git commit -m "refactor: Standardize datetime handling in ParkingService"`

3.  **Pousser sur GitHub :**
    ```bash
    git push origin votre-branche-de-refactoring
    ```
    Cela garantit que votre travail est sauvegardé et que vous avez un point de restauration stable.

---

## 4. Programmation Asynchrone (`async/await`)

### Quand l'utiliser ?
Pour les opérations bloquantes (I/O bound) comme les requêtes réseau (appels à des API externes, LLM) et les accès base de données. L'asynchrone permet à votre application de gérer plusieurs tâches I/O "simultanément" sans bloquer le thread principal.

### Principes Clés

*   Toute fonction qui effectue une opération I/O bloquante doit être déclarée avec `async def`.
*   Toute fonction `async def` doit être `await`-ée lorsqu'elle est appelée. Oublier `await` est une erreur courante qui conduit à des coroutines non exécutées.
*   Les fonctions `async` doivent être appelées depuis un "event loop" (souvent géré par `asyncio.run()` pour les scripts simples, ou par le framework lui-même comme Streamlit ou FastAPI).

### Problèmes Courants

*   **Oubli de `await` :** La coroutine est créée mais jamais exécutée.
*   **Mélanger `async` et synchrone :** Appeler du code synchrone bloquant dans une fonction asynchrone peut bloquer l'event loop. Utilisez `await asyncio.to_thread(sync_function)` si vous devez exécuter du code synchrone bloquant dans un contexte asynchrone.
*   **Gestion des contextes de base de données asynchrones :** Assurez-vous d'utiliser `AsyncSessionLocal` et de gérer correctement les sessions asynchrones.

## 4. Tests Asynchrones

### Outils Indispensables

*   **`pytest-asyncio` :** Indispensable pour tester le code asynchrone avec `pytest`.
    *   Marquez vos fonctions de test asynchrones avec `@pytest.mark.asyncio`.
    *   Utilisez `await` dans vos tests pour appeler le code asynchrone.

### Mocking des Dépendances Asynchrones

*   Pour les dépendances asynchrones (ex: appels à la DB, API externes), utilisez `unittest.mock.AsyncMock` ou `mocker.AsyncMock` (si vous utilisez `pytest-mock`).
*   Cela permet de tester votre logique sans réellement toucher à la base de données ou faire des appels réseau.

### Tests de `datetime`

*   **Figer le temps :** Utilisez la bibliothèque `freezegun` pour figer le temps dans vos tests. C'est crucial pour tester la logique basée sur le temps (calcul de durée, etc.) de manière reproductible.
*   **Comparaisons robustes :** Assurez-vous que les comparaisons de `datetime` dans les tests sont robustes :
    *   Soit en comparant des objets `datetime` `timezone-aware` en UTC.
    *   Soit en comparant des chaînes formatées de manière cohérente en utilisant `strftime('%Y-%m-%d %H:%M:%S')`.

## 5. Stratégie de Refactoring et Vérification Continue

1.  **Prioriser les couches internes :** Commencez par le `Domain`, puis l'`Application`, puis l'`Infrastructure`. Assurez-vous que chaque couche est propre et testée avant de passer à la suivante.
2.  **Refactoring incrémental :** Ne tentez pas de tout refactorer d'un coup. Prenez une petite partie (ex: un service, une entité), refactorez-la, testez-la, et commitez.
3.  **Tests comme filet de sécurité :** Avant de refactorer une section, assurez-vous qu'elle est couverte par des tests unitaires. Si ce n'est pas le cas, écrivez-les d'abord (TDD).
4.  **Vérification continue :**
    *   **Exécutez les tests régulièrement :** Lancez `make test` après chaque changement significatif.
    *   **Vérifiez les imports :** Assurez-vous qu'il n'y a pas de dépendances inversées (ex: `infrastructure` qui importe `application`).
    *   **Vérifiez la cohérence des `datetime` :** Ajoutez des assertions spécifiques dans vos tests pour vérifier que les `datetime` sont bien gérées (UTC, formatage).
    *   **Vérifiez l'asynchrone :** Assurez-vous que toutes les opérations I/O sont `await`-ées et que l'event loop est correctement géré.
