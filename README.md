# iPhone Deals Bot — Vinted V1

Surveille une recherche Vinted toutes les 5 minutes et envoie sur Discord les annonces où :

`prix total Vinted <= prix Cdiscount excellent état - 80 €`

## Installation

1. Crée un dépôt GitHub privé vide.
2. Décompresse le ZIP et importe **son contenu** à la racine.
3. Sur Vinted, crée une recherche `iPhone`, catégorie smartphones, livraison, tri plus récent et filtre `Simlockage : Non`.
4. Copie l'URL complète de la recherche.
5. Dans GitHub : `Settings > Secrets and variables > Actions`.
6. Ajoute `DISCORD_WEBHOOK_URL` avec ton webhook Discord.
7. Ajoute `VINTED_SEARCH_URL` avec l'URL de ta recherche Vinted.
8. Ouvre `config/cdiscount_prices.csv` et remplis la colonne `cdiscount_price_eur`.
9. Va dans `Actions > Surveillance iPhone Vinted > Run workflow`.

Le premier lancement mémorise les annonces déjà présentes. Les suivants alertent uniquement sur les nouvelles.

## Structure attendue

```text
.github/
config/
data/
src/
.gitignore
README.md
requirements.txt
```

## Important

- Une ligne de prix Cdiscount vide est ignorée.
- Vérifie sur les premières alertes que `total_item_price` correspond bien au coût total attendu, notamment la livraison.
- Le wrapper Vinted est non officiel et peut casser si Vinted modifie son fonctionnement.
- Ne mets jamais ton mot de passe Vinted ou tes cookies dans le dépôt.
- Leboncoin sera ajouté après validation de cette V1.
