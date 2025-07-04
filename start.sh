#!/bin/bash

# Script de démarrage pour l'application Flask lancée par cron
cd ~/rascrypto/cotation || exit

# 2. Exporter les variables d'environnement (c'est ici qu'on doit le faire pour cron)
export GMAIL_USER="MONEMAIL@GMAIL.COM"
export GMAIL_APP_PASS="MON PASSWORD APPPLICATIF GMAIL"

# 3. Lancer l'application Python et rediriger TOUTE la sortie (prints et erreurs) vers un fichier log.
#    Ceci est ESSENTIEL pour pouvoir déboguer ce qui se passe après le démarrage.
echo "Lancement de l'application rascrypto via start.sh à $(date)" > ~/rascrypto/cotation/rascrypto.log 2>&1
~/.venv/bin/python appl.py >> ~/rascrypto/cotation/rascrypto.log 2>&1
