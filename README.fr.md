# Live Subtitles pour macOS

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · **Français** · [日本語](README.ja.md) · [한국어](README.ko.md)

Sous-titres en temps réel pour **tout ce que joue votre Mac** : YouTube, films, Zoom, jeux. Ils s'affichent dans une barre transparente qui reste au-dessus de toutes les applications, même au-dessus de Chrome en plein écran.

- **100 % hors ligne.** La reconnaissance vocale tourne en local avec [faster-whisper](https://github.com/SYSTRAN/faster-whisper), sans aucun service cloud.
- **Le son du système, pas seulement le micro.** L'enregistrement de la sortie des haut-parleurs passe par le pilote gratuit [BlackHole](https://github.com/ExistentialAudio/BlackHole).
- **Sous-titres en anglais**, ou **traduction vers l'anglais** depuis le français, le chinois et environ 95 autres langues.
- **Faible latence.** Les mots apparaissent pendant qu'ils sont prononcés.

---

## Obtenir et installer (étape par étape)

Configuration requise : macOS 12 ou plus récent (Apple Silicon ou Intel) et environ 1,5 Go d'espace libre.

### Étape 1 : télécharger le projet

Ouvrez le **Terminal** et lancez :

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

Sans git : sur GitHub, cliquez sur **Code → Download ZIP**, décompressez l'archive, puis allez dans le dossier avec `cd`.

### Étape 2 : lancer l'installateur

```bash
./install.sh                 # installation normale
./install.sh --translate     # ajoute le modèle multilingue pour traduire vers l'anglais
```

L'installateur :
1. installe Homebrew s'il manque ;
2. installe `portaudio`, `python@3.12` et le pilote **BlackHole 2ch** (macOS demande votre mot de passe une fois) ;
3. crée un environnement Python dans `.venv` et y installe tout le contenu de `requirements.txt` ;
4. télécharge une seule fois le modèle Whisper. Ensuite, tout fonctionne hors ligne.

### Étape 3 : redémarrer le Mac

BlackHole n'apparaît qu'après un redémarrage.

### Étape 4 : envoyer le son du système vers BlackHole

1. Ouvrez **Configuration audio et MIDI** (Cmd+Espace, puis tapez « Audio MIDI »).
2. Cliquez sur **+** en bas à gauche, puis sur **Créer un périphérique à sortie multiple**.
3. Cochez vos **haut-parleurs ou votre casque**, ainsi que **BlackHole 2ch**.
4. Choisissez vos haut-parleurs comme **périphérique principal**. Activez la **correction de dérive** uniquement sur BlackHole et réglez les deux périphériques sur **48 000 Hz**.
5. Dans **Réglages Système → Son → Sortie**, choisissez le **périphérique à sortie multiple**.

> Avec un périphérique à sortie multiple, les touches de volume ne fonctionnent plus : c'est une limite de macOS. Réglez le volume dans le lecteur.

### Étape 5 : donner les autorisations au Terminal

Dans **Réglages Système → Confidentialité et sécurité** :
- **Microphone** : activez **Terminal**. Sans cette autorisation, l'application n'enregistre que du silence.
- **Surveillance de l'entrée** : activez **Terminal**. C'est facultatif ; cela ne sert qu'aux raccourcis globaux Ctrl+Option.

Ensuite, quittez puis rouvrez le Terminal.

### Étape 6 : tester et lancer

```bash
./run.sh --list-devices     # "BlackHole 2ch" doit apparaître comme entrée
./run.sh --test-audio       # lancez une vidéo : la barre de niveau doit bouger
./run.sh                    # démarre les sous-titres
```

---

## Utilisation

| Je veux… | Commande |
|---|---|
| Des sous-titres en anglais | `./run.sh` |
| **Une vidéo en français → des sous-titres en anglais** | `./run.sh --translate --language fr --model small` |
| N'importe quelle langue → l'anglais (détection automatique) | `./run.sh --translate --model small` |
| Des sous-titres en français (sans traduction) | `./run.sh --language fr --model small` |
| Voir toutes les options | `./run.sh --help` |

## Raccourcis

| Touches | Action |
|---|---|
| **Ctrl+Option+Q** | quitter |
| **Ctrl+Option+P** | mettre en pause ou reprendre |
| **Ctrl+Option+H** | masquer ou afficher la barre |
| **Ctrl+C** (dans le Terminal) | quitter |

## Problèmes fréquents

| Problème | Solution |
|---|---|
| BlackHole est introuvable | Redémarrez le Mac, ou lancez `sudo killall coreaudiod`. |
| `--test-audio` reste à 0 | La sortie n'est pas le périphérique multiple, BlackHole n'y est pas coché, ou le Terminal n'a pas l'autorisation Microphone. |
| Plus de son | Choisissez le périphérique à sortie multiple, pas BlackHole seul. |
| Les sous-titres sont en retard | Prenez un `--model` plus petit, ou ajoutez `--cpu-threads 8`. |

Le guide complet (en anglais) se trouve dans [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).
