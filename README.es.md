# Live Subtitles para macOS

[English](README.md) · [简体中文](README.zh-CN.md) · **Español** · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

Subtítulos en tiempo real para **todo lo que suena en tu Mac**: YouTube, películas, Zoom o juegos. Aparecen en una barra transparente que flota sobre todas las apps, incluso sobre Chrome en pantalla completa.

- **100 % sin conexión.** El reconocimiento de voz se hace en tu Mac con [faster-whisper](https://github.com/SYSTRAN/faster-whisper), sin servicios en la nube.
- **Audio del sistema, no solo el micrófono.** Graba la salida de los altavoces con el controlador gratuito [BlackHole](https://github.com/ExistentialAudio/BlackHole).
- **Subtítulos en inglés**, o **traducción al inglés** desde el español, el chino y unos 95 idiomas más.
- **Baja latencia.** Las palabras aparecen mientras se pronuncian.

---

## Cómo obtenerlo e instalarlo (paso a paso)

Requisitos: macOS 12 o posterior (Apple Silicon o Intel) y unos 1,5 GB libres.

### Paso 1: descargar el proyecto

Abre **Terminal** y ejecuta:

```bash
git clone https://github.com/Helloworldceo/live_subtitles.git
cd live_subtitles
```

Si no tienes git, en GitHub pulsa **Code → Download ZIP**, descomprime el archivo y entra en la carpeta con `cd`.

### Paso 2: ejecutar el instalador

```bash
./install.sh                 # instalación normal
./install.sh --translate     # además, el modelo multilingüe para traducir al inglés
```

El instalador:
1. instala Homebrew si no lo tienes;
2. instala `portaudio`, `python@3.12` y el controlador **BlackHole 2ch** (macOS pedirá tu contraseña una vez);
3. crea un entorno de Python en `.venv` e instala todo lo que hay en `requirements.txt`;
4. descarga el modelo de Whisper una sola vez. Después todo funciona sin conexión.

### Paso 3: reiniciar el Mac

BlackHole solo aparece después de reiniciar.

### Paso 4: enviar el audio del sistema a BlackHole

1. Abre **Configuración de Audio MIDI** (Cmd+Espacio y escribe "Audio MIDI").
2. Pulsa **+** abajo a la izquierda y elige **Crear dispositivo de salida múltiple**.
3. Marca tus **altavoces o auriculares** y **BlackHole 2ch**.
4. Elige tus altavoces como **dispositivo principal**. Activa la **corrección de deriva** solo en BlackHole y pon los dos a **48.000 Hz**.
5. En **Ajustes del Sistema → Sonido → Salida**, elige el **dispositivo de salida múltiple**.

> Con un dispositivo de salida múltiple, las teclas de volumen no funcionan; es una limitación de macOS. Ajusta el volumen desde el reproductor.

### Paso 5: dar permisos a Terminal

En **Ajustes del Sistema → Privacidad y seguridad**:
- **Micrófono:** activa **Terminal**. Sin este permiso solo se graba silencio.
- **Monitorización de entrada:** activa **Terminal**. Es opcional y solo hace falta para los atajos globales Ctrl+Opción.

Después, cierra y vuelve a abrir Terminal.

### Paso 6: probar y ejecutar

```bash
./run.sh --list-devices     # debe aparecer "BlackHole 2ch" como entrada
./run.sh --test-audio       # reproduce un vídeo: la barra de nivel debe moverse
./run.sh                    # inicia los subtítulos
```

---

## Uso

| Quiero… | Comando |
|---|---|
| Subtítulos en inglés | `./run.sh` |
| **Vídeo en español → subtítulos en inglés** | `./run.sh --translate --language es --model small` |
| Cualquier idioma → inglés (detección automática) | `./run.sh --translate --model small` |
| Subtítulos en español (sin traducir) | `./run.sh --language es --model small` |
| Ver todas las opciones | `./run.sh --help` |

## Atajos de teclado

| Teclas | Acción |
|---|---|
| **Ctrl+Opción+Q** | salir |
| **Ctrl+Opción+P** | pausar o reanudar |
| **Ctrl+Opción+H** | ocultar o mostrar la barra |
| **Ctrl+C** (en Terminal) | salir |

## Problemas frecuentes

| Problema | Solución |
|---|---|
| No aparece BlackHole | Reinicia el Mac o ejecuta `sudo killall coreaudiod`. |
| `--test-audio` se queda en 0 | La salida no es el dispositivo múltiple, BlackHole no está marcado en él o Terminal no tiene permiso de micrófono. |
| No se oye nada | Elige el dispositivo de salida múltiple, no solo BlackHole. |
| Los subtítulos van con retraso | Usa un `--model` más pequeño o añade `--cpu-threads 8`. |

Tienes la guía completa (en inglés) en [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).
