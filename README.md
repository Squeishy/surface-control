# Surface Control

Transforme une Surface RT (2012) en panneau de contrôle tactile pour le PC principal : un
Stream Deck, un Gestionnaire des tâches et une télécommande Unity réunis. Le PC fait tourner un
petit serveur ; la tablette affiche l'interface dans Internet Explorer 11 et envoie les commandes
par le réseau de la maison.

```
Surface RT (IE11)  ──Wi-Fi──>  PC : server/main.py  ──>  Windows, Unity, vos applis
```

## Prérequis

- **PC :** Windows 10/11 avec Python 3.8+ (lanceur `py`) et `psutil` (installé automatiquement au
  premier démarrage). Rien d'autre : l'intégration Windows utilise seulement `ctypes`.
- **Tablette :** n'importe quel navigateur sur le même réseau. L'interface est écrite en ES5 et en
  CSS compatible IE11 exprès pour la Surface RT.

## Démarrer

1. Double-cliquez sur **`Start Surface Control.cmd`**. La fenêtre affiche l'adresse à ouvrir et le
   **code PIN** à 6 chiffres.
2. La première fois, le Pare-feu Windows demande si Python peut accepter des connexions : cochez
   **Réseaux publics** et **privés**, puis **Autoriser**.
3. Sur la Surface, ouvrez Internet Explorer à l'adresse indiquée (ex. `http://192.168.1.42:8765`)
   et saisissez le code. La tablette reste appairée.

Si la fenêtre du pare-feu n'est pas apparue, lancez une fois dans un PowerShell **administrateur**
(n'autorise le port que depuis le réseau local) :

```powershell
New-NetFirewallRule -DisplayName "Surface Control" -Direction Inbound -Protocol TCP -LocalPort 8765 -RemoteAddress LocalSubnet -Action Allow
```

**Adresse fixe :** l'IP du PC est attribuée par la box internet et peut changer. Pour la garder,
réservez-la avec un bail DHCP statique dans l'interface de la box (ex. Freebox OS › Paramètres de la
Freebox › DHCP › Baux statiques).

**Démarrage automatique (facultatif) :** `Run at login (install).cmd` lance le serveur caché à chaque
ouverture de session ; `Run at login (remove).cmd` l'annule. Le code PIN est alors visible dans
Réglages en ouvrant `http://localhost:8765` sur le PC.

## L'interface

Navigation en haut ; **balayez à gauche/droite** pour passer d'une page à l'autre. Un appui long
(ou clic droit) sur une appli ou un lien ouvre ses options. L'interface s'adapte à la taille de
l'écran (réglable en plus dans Réglages › Taille de l'interface).

| Page | Contenu |
| --- | --- |
| **Accueil** | Jusqu'à 18 gros boutons au choix (crayon en haut à droite), plus la barre média : titre et barre de lecture du morceau en cours (déplaçable pour avancer), ou le curseur de volume quand rien ne joue, et toujours − / + / muet. Les applis n'affichent que leur logo : contour vert quand elles tournent, pastille avec le nombre de fenêtres s'il y en a plusieurs. |
| **Unity** | Trois onglets. **Ouvrir** : vos projets Unity Hub, ouverts dans la bonne version de l'éditeur (ou ramenés au premier plan s'ils sont déjà ouverts). **Actions** : Mode jeu, Édition, Build, Fenêtres, envoyés à la fenêtre Unity. **Console** : suit `Editor.log` (y compris le `Logs/Editor.log` par projet d'Unity 6) avec filtres erreurs/avertissements. |
| **Liens** | Sites (avec leur vrai logo), dossiers et fichiers à ouvrir sur le PC. |
| **Applis** | Vos applis en boutons-logos. Toucher : lancer ou basculer dessus. Appui long : basculer, nouvelle fenêtre, fermer, forcer l'arrêt, modifier, retirer. Ajout depuis le menu Démarrer ou par chemin. |
| **Tâches** | Processeur, mémoire, disque, réseau, et les processus regroupés comme dans le Gestionnaire des tâches (Applis d'abord), avec Basculer / Fermer / Terminer sur chaque ligne. Les processus essentiels de Windows sont protégés. |
| **Réglages** | Fond (7 couleurs, fond d'écran du PC ou image importée), assombrir, taille de l'interface, libellés, actualisation, confirmations, et en zone sensible l'appairage (code PIN, appareils). |

Internet Explorer ne sait pas flouter ce qui se trouve derrière un panneau : avec une image en fond,
l'interface peint une copie déjà floutée du fond d'écran sur chaque panneau. Ajoutez `?noblur` à
l'adresse dans un navigateur de bureau pour voir exactement le rendu de la Surface.

## Sécurité

- Seuls les appareils du **réseau local** peuvent se connecter ; le reste est refusé.
- Un appareil saisit le **code PIN** une fois puis reçoit son propre jeton. Révocable dans Réglages.
  Cinq codes erronés bloquent l'appairage une minute.
- La tablette ne peut déclencher que les commandes ci-dessus et les applis/liens configurés ;
  aucune commande système arbitraire.
- Le PC lui-même (`localhost`) est toujours autorisé ; mettez `"trust_localhost": false` dans
  `data/config.json` pour exiger l'appairage aussi.

## Fichiers

```
Start Surface Control.cmd     démarre le serveur (installe psutil si besoin)
server/main.py                serveur HTTP, routes, appairage
server/monitor.py             échantillonnage chaque seconde : CPU, mémoire, processus, volume
server/winapi.py              Win32 via ctypes : fenêtres, touches, audio, icônes, alimentation
server/unity.py               projets Unity Hub, éditeurs, état, raccourcis, journal
server/actions.py             commandes intégrées et historique
server/config.py              data/config.json, détection des applis, menu Démarrer
server/images.py              fonds d'écran (du PC ou importés) et logos des sites
web/                          l'interface de la tablette (index.html, app.css, app.js ; ES5 pour IE11)
data/                         créé au premier lancement : config.json, wallpaper.img, icons/, server.log
```

Options : `server\main.py --port 9000`, ou `--host 192.168.1.42` pour n'écouter qu'une adresse.

## Dépannage

- **La tablette ne se connecte pas :** même réseau des deux côtés ? Puis voir la section pare-feu.
  Sur le PC, `http://localhost:8765` doit s'ouvrir.
- **Les boutons Unity ne font rien :** l'éditeur doit être ouvert ; les commandes ramènent Unity au
  premier plan et utilisent ses raccourcis par défaut.
- **Pas de barre de lecture :** elle utilise les paquets `winrt` (installés par le lanceur) et ne
  s'affiche que pour les applis qui publient leur lecture à Windows (navigateurs, Spotify…).
- Les erreurs sont enregistrées dans `data/server.log`.
