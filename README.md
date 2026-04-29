# FL Studio Producer Brain

> **English** | [Español](#español)

An MCP (Model Context Protocol) server that gives Claude full knowledge of your FL Studio setup. Claude can scan your sample library, read your installed VST plugins, find and install presets, send MIDI patterns, and read your project files — all from a single conversation.

---

## What it does

- Scans and classifies your entire sample library (kick, snare, 808, hi-hat, loop, vocal, etc.) using a three-tier ML classifier
- Reads all your installed VST plugins from FL Studio's database and system VST folders
- Looks up synthesis type, genre recommendations, and useful links for each plugin
- Searches PresetShare, ADSR Sounds, and manufacturer pages for free presets matching your plugin and genre
- Downloads and installs presets into the correct FL Studio folder automatically
- Opens the FL Studio browser and positions presets for drag-and-drop (via UI automation)
- Sends MIDI note patterns directly to FL Studio via a virtual MIDI port
- Parses `.flp` project files and extracts BPM, channels, plugins, patterns, and mixer layout

---

# Installation Guide (English)

## Requirements

| Requirement | Windows | Mac |
|-------------|---------|-----|
| FL Studio 20 / 21 / 2024 | Yes | Yes (native since v20.9) |
| Python 3.11+ | [python.org](https://www.python.org/downloads/) | [python.org](https://www.python.org/downloads/) |
| Claude Desktop or Claude Code | Either one | Either one |
| Virtual MIDI port | LoopMIDI | IAC Driver (built-in) |

> **Linux:** FL Studio does not run on Linux natively, so this server is not supported there.

---

## Windows Installation

### Step 1 — Install Python 3.11+

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download Python 3.11 or newer.
2. Run the installer. On the first screen, check **"Add Python to PATH"** before clicking Install.
3. Verify it works: open Command Prompt and run:
   ```
   python --version
   ```
   You should see `Python 3.11.x` or higher.

### Step 2 — Install LoopMIDI (for MIDI features)

LoopMIDI creates a virtual MIDI cable that lets Claude send notes directly into FL Studio.

1. Download from [tobias-erichsen.de/software/loopmidi.html](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Install and open LoopMIDI.
3. In the bottom-left field, type `loopMIDI Port` and click `+`.
4. The port appears in the list — leave LoopMIDI running in the system tray.

In FL Studio: **Options → MIDI Settings → Input tab** → find `loopMIDI Port` → enable it (green checkmark) → set Port to `0`.

### Step 3 — Download or clone this project

**Option A — Download ZIP:**
Click **Code → Download ZIP** on GitHub, extract the folder anywhere (e.g. `C:\Tools\fl-studio-mcp`).

**Option B — Git:**
```
git clone https://github.com/yourusername/fl-studio-mcp.git
```

### Step 4 — Run the installer

Navigate to the `fl-studio-mcp` folder in File Explorer and **double-click `install.bat`**.

The installer will:
- Check your Python version
- Create a virtual environment (`venv/`)
- Install all dependencies
- Copy `config.example.json` to `config.json` and fill in your username automatically
- Print the exact snippet you need to connect Claude

If you see a blue "Windows protected your PC" warning, click **More info → Run anyway**. The script only installs Python packages and creates files in its own folder.

### Step 5 — Connect to Claude Desktop

1. Open (or create) the file at:
   ```
   C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json
   ```
   The `AppData` folder is hidden — paste the path directly into the File Explorer address bar.

2. Add this block (the installer prints the exact paths for you):
   ```json
   {
     "mcpServers": {
       "fl-studio-producer-brain": {
         "command": "C:\\Tools\\fl-studio-mcp\\venv\\Scripts\\python.exe",
         "args": ["C:\\Tools\\fl-studio-mcp\\server.py"]
       }
     }
   }
   ```
   Replace `C:\\Tools\\fl-studio-mcp` with the actual folder where you extracted the project. Use double backslashes `\\` in JSON.

3. Save the file and **restart Claude Desktop**.

4. Open a new conversation — you should see a hammer icon (🔨) in the bottom-right of the chat input. Click it to verify the `fl-studio-producer-brain` tools are listed.

### Step 5 (alternative) — Connect to Claude Code (CLI)

If you use Claude Code in the terminal instead of Claude Desktop, run this once:

```bash
claude mcp add fl-studio-producer-brain "C:\Tools\fl-studio-mcp\venv\Scripts\python.exe" "C:\Tools\fl-studio-mcp\server.py"
```

Or add to `.claude/mcp.json` inside any project folder:

```json
{
  "mcpServers": {
    "fl-studio-producer-brain": {
      "command": "C:\\Tools\\fl-studio-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\Tools\\fl-studio-mcp\\server.py"]
    }
  }
}
```

### Step 6 — Edit config.json (optional)

Open `config.json` and adjust these fields if needed:

```json
{
  "fl_studio": {
    "user_data_folder": "C:\\Users\\YourName\\Documents\\Image-Line\\FL Studio",
    "install_folder": "C:\\Program Files\\Image-Line\\FL Studio 2024",
    "vst_folders": [
      "C:\\Program Files\\Common Files\\VST3",
      "C:\\Program Files\\VSTPlugins",
      "C:\\Program Files (x86)\\VSTPlugins"
    ]
  },
  "samples": {
    "scan_folders": [
      "C:\\Users\\YourName\\Music\\Samples"
    ]
  },
  "midi": {
    "port_name": "loopMIDI Port"
  }
}
```

The installer fills your username automatically. The only thing you may need to change is `scan_folders` if your samples are on a different drive (e.g. `D:\\Samples`).

---

## Mac Installation

FL Studio has supported macOS natively since version 20.9 (2022). All features of this server work on Mac, with two differences: the folder paths are Unix-style, and instead of LoopMIDI you use the IAC Driver that ships with macOS.

### Step 1 — Install Python 3.11+

**Option A — python.org (simplest):**
1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the macOS installer.
2. Run the `.pkg` file and follow the prompts.
3. Open Terminal and verify:
   ```bash
   python3 --version
   ```

**Option B — Homebrew (recommended if you already use it):**
```bash
brew install python@3.11
```

### Step 2 — Enable the IAC Driver (virtual MIDI — for MIDI features)

The IAC Driver is Apple's built-in virtual MIDI bus. No download needed.

1. Open **Audio MIDI Setup** (search with Spotlight: `⌘ Space` → type `Audio MIDI Setup`).
2. In the menu bar: **Window → Show MIDI Studio**.
3. Double-click **IAC Driver**.
4. Check **"Device is online"**.
5. Click `+` under Ports to add a port. Name it `loopMIDI Port` (same name the config expects by default — this avoids having to edit `config.json`).
6. Click Apply.

In FL Studio: **Options → MIDI Settings → Input** → enable `IAC Driver Bus 1` (or whatever you named it) → set Port to `0`.

### Step 3 — Download or clone the project

```bash
git clone https://github.com/yourusername/fl-studio-mcp.git ~/fl-studio-mcp
cd ~/fl-studio-mcp
```

Or download the ZIP from GitHub and extract it to your home folder.

### Step 4 — Run the installer script

```bash
cd ~/fl-studio-mcp
bash install.sh
```

If `install.sh` doesn't exist yet, run the steps manually (takes about 2 minutes):

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy config
cp config.example.json config.json
```

Then edit `config.json` for Mac paths (see Step 6).

### Step 5 — Connect to Claude Desktop

1. Open Terminal and run:
   ```bash
   open ~/Library/Application\ Support/Claude/
   ```
2. Open (or create) `claude_desktop_config.json` in that folder.
3. Add:
   ```json
   {
     "mcpServers": {
       "fl-studio-producer-brain": {
         "command": "/Users/yourname/fl-studio-mcp/venv/bin/python3",
         "args": ["/Users/yourname/fl-studio-mcp/server.py"]
       }
     }
   }
   ```
   Replace `/Users/yourname/fl-studio-mcp` with the actual path. To get the exact path, run `pwd` inside the project folder in Terminal.

4. Save and **restart Claude Desktop** (quit fully from the menu bar icon, then reopen).

### Step 5 (alternative) — Connect to Claude Code (CLI)

```bash
claude mcp add fl-studio-producer-brain \
  "$HOME/fl-studio-mcp/venv/bin/python3" \
  "$HOME/fl-studio-mcp/server.py"
```

### Step 6 — Edit config.json for Mac paths

Open `config.json` and replace the Windows paths:

```json
{
  "fl_studio": {
    "user_data_folder": "/Users/yourname/Documents/Image-Line/FL Studio",
    "install_folder": "/Applications/FL Studio.app",
    "vst_folders": [
      "/Library/Audio/Plug-Ins/VST3",
      "/Library/Audio/Plug-Ins/VST",
      "~/Library/Audio/Plug-Ins/VST3"
    ]
  },
  "samples": {
    "scan_folders": [
      "/Users/yourname/Music/Samples"
    ]
  },
  "midi": {
    "port_name": "loopMIDI Port"
  }
}
```

Replace `yourname` with your macOS username (run `whoami` in Terminal if unsure).

FL Studio on Mac stores user data at:
```
~/Documents/Image-Line/FL Studio/
```

---

## Verifying it works

Once connected, open a Claude conversation and type:

> "What FL Studio tools do you have available?"

Claude should list all 10 tools. Then try:

> "Read my plugins from FL Studio"

or

> "Suggest tracks for a UK drill beat"

---

## Available tools (quick reference)

| Tool | What it does |
|------|-------------|
| `scan_samples` | Scan a folder and classify all audio files by type |
| `get_samples` | Query your classified sample library with filters |
| `read_plugins` | List all installed VST plugins |
| `research_plugin` | Get genre/synthesis info about a specific plugin |
| `find_presets` | Search online for free presets matching plugin + genre |
| `install_preset` | Download and install a preset to the right folder |
| `load_preset_in_fl` | Load a preset into FL Studio via UI automation |
| `send_notes` | Send a MIDI pattern to FL Studio via virtual port |
| `read_project` | Parse a `.flp` project file and extract its contents |
| `suggest_for_genre` | Full recommendation: samples + plugins + presets for a genre |

---

## Training the sample classifier (optional)

The server works out of the box using filename and spectral heuristics. To train a proper Random Forest model on your own labelled samples:

1. Create a `training_data/` folder next to `server.py`.
2. Add sub-folders named after each type: `kick/`, `snare/`, `hihat_closed/`, `hihat_open/`, `clap/`, `808/`, `loop/`, etc.
3. Drop at least 50 `.wav` files into each folder.
4. Run:

   **Windows:**
   ```bash
   venv\Scripts\activate
   python -m classifier.train --data_dir training_data/
   ```

   **Mac:**
   ```bash
   source venv/bin/activate
   python -m classifier.train --data_dir training_data/
   ```

The model saves to `classifier/drum_classifier.joblib` and loads automatically at next startup.

---

## Troubleshooting

**"FL Studio tools not showing in Claude"**
Restart Claude Desktop fully (quit from the menu bar / system tray, not just close the window). Check that the paths in `claude_desktop_config.json` use the correct separators (`\\` on Windows, `/` on Mac) and that the `venv/Scripts/python.exe` (Windows) or `venv/bin/python3` (Mac) file actually exists.

**"python-rtmidi fails to install" (Windows)**
You need Microsoft C++ Build Tools. Download from [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), install the "Desktop development with C++" workload, then re-run `pip install -r requirements.txt`.

**"python-rtmidi fails to install" (Mac)**
Run `xcode-select --install` in Terminal first, then retry `pip install -r requirements.txt`.

**"No LoopMIDI port found" (Windows)**
Make sure LoopMIDI is running (check the system tray). The port name in LoopMIDI must match `midi.port_name` in `config.json` exactly.

**"No LoopMIDI port found" (Mac)**
Make sure the IAC Driver port is named `loopMIDI Port` in Audio MIDI Setup and that "Device is online" is checked.

**"FL Studio is not open" when loading presets**
`load_preset_in_fl` requires FL Studio to already be running. Open FL Studio first, then ask Claude to load the preset.

**"pyflp failed to parse .flp"**
pyflp supports FL Studio 20 and 21 best. If you are on FL Studio 2024, some features may not parse correctly. The tool returns a clear error message in that case.

**Samples not found after scan**
Check that the `scan_folders` in `config.json` points to the right drive/path. On Mac, remember paths are case-sensitive: `~/Music/Samples` and `~/music/samples` are different.

---

## License

MIT — free to use, modify, and distribute.

---
---

# Español

Una guía de instalación completa en español para **FL Studio Producer Brain**.

---

# Guía de Instalación (Español)

## ¿Qué es esto?

FL Studio Producer Brain es un servidor MCP (Model Context Protocol) que le da a Claude conocimiento completo de tu setup de FL Studio. Una vez conectado, Claude puede:

- Escanear y clasificar toda tu librería de samples (kick, snare, 808, hi-hat, loop, vocal...)
- Leer todos tus plugins VST instalados
- Buscar y descargar presets gratuitos online por género
- Enviar patrones MIDI directamente a FL Studio
- Leer archivos de proyecto `.flp`
- Recomendarte samples, plugins y presets según el género que quieres hacer

> **Linux:** FL Studio no funciona en Linux de forma nativa, así que este servidor no es compatible.

---

## Requisitos

| Requisito | Windows | Mac |
|-----------|---------|-----|
| FL Studio 20 / 21 / 2024 | Sí | Sí (nativo desde v20.9) |
| Python 3.11+ | [python.org](https://www.python.org/downloads/) | [python.org](https://www.python.org/downloads/) |
| Claude Desktop o Claude Code | Cualquiera | Cualquiera |
| Puerto MIDI virtual | LoopMIDI (descargar) | IAC Driver (ya viene en Mac) |

---

## Instalación en Windows

### Paso 1 — Instala Python 3.11 o superior

1. Ve a [python.org/downloads](https://www.python.org/downloads/) y descarga Python 3.11 o más reciente.
2. Ejecuta el instalador. En la primera pantalla, marca **"Add Python to PATH"** antes de hacer clic en Install. Ese paso es importante — sin él, nada va a funcionar.
3. Abre el Símbolo del sistema (busca `cmd` en el menú Inicio) y escribe:
   ```
   python --version
   ```
   Deberías ver `Python 3.11.x` o mayor.

### Paso 2 — Instala LoopMIDI (para enviar notas MIDI)

LoopMIDI crea un cable MIDI virtual que permite a Claude enviar notas directamente a FL Studio.

1. Descárgalo de [tobias-erichsen.de/software/loopmidi.html](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Instálalo y ábrelo.
3. En el campo de texto abajo a la izquierda escribe `loopMIDI Port` y haz clic en `+`.
4. El puerto aparece en la lista. Deja LoopMIDI abierto en la bandeja del sistema.

En FL Studio: **Options → MIDI Settings → pestaña Input** → encuentra `loopMIDI Port` → actívalo (palomita verde) → pon Port en `0`.

### Paso 3 — Descarga el proyecto

**Opción A — Descargar ZIP:**
Haz clic en **Code → Download ZIP** en GitHub, extrae la carpeta donde quieras (por ejemplo `C:\Tools\fl-studio-mcp`).

**Opción B — Git:**
```
git clone https://github.com/yourusername/fl-studio-mcp.git
```

### Paso 4 — Ejecuta el instalador

Abre la carpeta `fl-studio-mcp` en el Explorador de archivos y haz **doble clic en `install.bat`**.

El instalador hace automáticamente:
- Verifica tu versión de Python
- Crea un entorno virtual (`venv/`)
- Instala todas las dependencias
- Copia `config.example.json` a `config.json` y rellena tu nombre de usuario
- Imprime el snippet exacto para conectar Claude

Si aparece la pantalla azul de "Windows protegió su equipo", haz clic en **Más información → Ejecutar de todas formas**. El script solo instala paquetes de Python en su propia carpeta, no modifica el sistema.

### Paso 5 — Conecta Claude Desktop

1. Abre esta carpeta (pega la ruta en el Explorador de archivos):
   ```
   C:\Users\TuNombre\AppData\Roaming\Claude\
   ```
   La carpeta `AppData` está oculta. Pega la ruta directamente en la barra de dirección del Explorador.

2. Abre (o crea) el archivo `claude_desktop_config.json` y agrega:
   ```json
   {
     "mcpServers": {
       "fl-studio-producer-brain": {
         "command": "C:\\Tools\\fl-studio-mcp\\venv\\Scripts\\python.exe",
         "args": ["C:\\Tools\\fl-studio-mcp\\server.py"]
       }
     }
   }
   ```
   Cambia `C:\\Tools\\fl-studio-mcp` por la ruta real donde extrajiste el proyecto. En JSON las rutas de Windows llevan doble barra invertida `\\`.

3. Guarda el archivo y **reinicia Claude Desktop** completamente (ciérralo desde la bandeja del sistema, no solo la ventana).

4. Abre una conversación nueva. Deberías ver un ícono de martillo (🔨) en la esquina inferior derecha del campo de texto. Haz clic para verificar que aparecen las herramientas de `fl-studio-producer-brain`.

### Paso 5 (alternativa) — Conecta Claude Code (CLI)

Si usas Claude Code en la terminal en lugar de Claude Desktop:

```bash
claude mcp add fl-studio-producer-brain "C:\Tools\fl-studio-mcp\venv\Scripts\python.exe" "C:\Tools\fl-studio-mcp\server.py"
```

### Paso 6 — Edita config.json (opcional)

Abre `config.json`. El instalador ya rellenó tu nombre de usuario. Solo necesitas cambiar `scan_folders` si tus samples están en otra unidad:

```json
{
  "samples": {
    "scan_folders": [
      "C:\\Users\\TuNombre\\Music\\Samples",
      "D:\\Mi Libreria de Samples"
    ]
  }
}
```

---

## Instalación en Mac

FL Studio tiene soporte nativo para macOS desde la versión 20.9 (2022). Todas las funciones de este servidor funcionan en Mac. Las dos diferencias respecto a Windows son: las rutas usan formato Unix, y en lugar de LoopMIDI se usa el IAC Driver que ya viene integrado en macOS.

### Paso 1 — Instala Python 3.11 o superior

**Opción A — python.org (más sencillo):**
1. Ve a [python.org/downloads](https://www.python.org/downloads/) y descarga el instalador para macOS.
2. Ejecuta el `.pkg` y sigue los pasos.
3. Abre la Terminal (Spotlight: `⌘ Espacio` → escribe `Terminal`) y verifica:
   ```bash
   python3 --version
   ```

**Opción B — Homebrew (si ya lo usas):**
```bash
brew install python@3.11
```

### Paso 2 — Activa el IAC Driver (MIDI virtual)

El IAC Driver es el cable MIDI virtual de Apple. Ya viene instalado en macOS, solo hay que activarlo.

1. Abre **Configuración de Audio MIDI** (Spotlight: `⌘ Espacio` → escribe `Audio MIDI`).
2. En la barra de menú: **Ventana → Mostrar estudio MIDI**.
3. Haz doble clic en **IAC Driver**.
4. Marca la casilla **"El dispositivo está conectado"**.
5. Haz clic en `+` bajo Puertos y nombra el puerto `loopMIDI Port` (así coincide con el nombre que espera el config por defecto).
6. Haz clic en Aplicar.

En FL Studio: **Options → MIDI Settings → Input** → activa `IAC Driver Bus 1` → Port `0`.

### Paso 3 — Descarga el proyecto

```bash
git clone https://github.com/yourusername/fl-studio-mcp.git ~/fl-studio-mcp
cd ~/fl-studio-mcp
```

O descarga el ZIP desde GitHub y extráelo en tu carpeta home.

### Paso 4 — Instala las dependencias

Abre la Terminal, navega a la carpeta del proyecto y ejecuta:

```bash
cd ~/fl-studio-mcp

# Crea el entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instala dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Copia la config
cp config.example.json config.json
```

Si `pip install` falla con algún error de compilación, ejecuta primero:
```bash
xcode-select --install
```
Luego vuelve a intentar `pip install -r requirements.txt`.

### Paso 5 — Conecta Claude Desktop

1. En la Terminal ejecuta:
   ```bash
   open ~/Library/Application\ Support/Claude/
   ```
2. Abre (o crea) el archivo `claude_desktop_config.json` en esa carpeta.
3. Agrega esto (reemplaza `tunombre` con tu usuario de Mac — usa `whoami` en Terminal si no estás seguro):
   ```json
   {
     "mcpServers": {
       "fl-studio-producer-brain": {
         "command": "/Users/tunombre/fl-studio-mcp/venv/bin/python3",
         "args": ["/Users/tunombre/fl-studio-mcp/server.py"]
       }
     }
   }
   ```
   Para obtener la ruta exacta, ejecuta `pwd` dentro de la carpeta del proyecto en Terminal.

4. Guarda el archivo y **cierra Claude Desktop completamente** (clic derecho en el ícono del Dock → Salir), luego vuelve a abrirlo.

### Paso 5 (alternativa) — Conecta Claude Code (CLI)

```bash
claude mcp add fl-studio-producer-brain \
  "$HOME/fl-studio-mcp/venv/bin/python3" \
  "$HOME/fl-studio-mcp/server.py"
```

### Paso 6 — Edita config.json para Mac

Abre `config.json` y reemplaza las rutas de Windows:

```json
{
  "fl_studio": {
    "user_data_folder": "/Users/tunombre/Documents/Image-Line/FL Studio",
    "install_folder": "/Applications/FL Studio.app",
    "vst_folders": [
      "/Library/Audio/Plug-Ins/VST3",
      "/Library/Audio/Plug-Ins/VST",
      "~/Library/Audio/Plug-Ins/VST3"
    ]
  },
  "samples": {
    "scan_folders": [
      "/Users/tunombre/Music/Samples"
    ]
  },
  "midi": {
    "port_name": "loopMIDI Port"
  }
}
```

FL Studio en Mac guarda los datos del usuario en:
```
~/Documents/Image-Line/FL Studio/
```

---

## Verificación

Una vez conectado, abre una conversación en Claude y escribe:

> "What FL Studio tools do you have available?"

Claude debe listar las 10 herramientas disponibles. Luego prueba:

> "Escanea mis samples de [ruta a tu carpeta]"

o

> "Quiero hacer un beat de UK drill, qué me recomiendas?"

---

## Solución de problemas

**"Las herramientas no aparecen en Claude"**
Reinicia Claude Desktop por completo (desde la bandeja del sistema en Windows, o clic derecho → Salir en Mac). Verifica que las rutas en `claude_desktop_config.json` sean correctas y que el archivo `python.exe` (Windows) o `python3` (Mac) dentro de `venv/` exista realmente.

**"python-rtmidi falla al instalar" (Windows)**
Necesitas las herramientas de compilación de C++. Descárgalas de [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), instala el componente "Desarrollo para el escritorio con C++" y vuelve a ejecutar `pip install -r requirements.txt`.

**"python-rtmidi falla al instalar" (Mac)**
Ejecuta `xcode-select --install` en Terminal y vuelve a intentarlo.

**"No LoopMIDI port found" (Windows)**
Verifica que LoopMIDI esté corriendo (ícono en la bandeja del sistema). El nombre del puerto debe coincidir exactamente con `midi.port_name` en `config.json`.

**"No LoopMIDI port found" (Mac)**
Verifica que el IAC Driver esté activo en Configuración de Audio MIDI y que el puerto se llame exactamente `loopMIDI Port`.

**"FL Studio is not open"**
`load_preset_in_fl` requiere que FL Studio esté abierto antes de llamar la herramienta. Ábrelo primero.

**Los samples no se encuentran después de escanear**
Verifica que `scan_folders` en `config.json` apunte a la ruta correcta. En Mac las rutas son sensibles a mayúsculas: `/Users/yo/Music/Samples` y `/Users/yo/music/samples` son carpetas distintas.

---

## Licencia

MIT — libre de usar, modificar y distribuir.
