# Dictum

Dictum es una aplicación de escritorio diseñada para **dictado de voz inteligente con reescritura semántica por Inteligencia Artificial**.
Sirve como una alternativa privada y personalizable a herramientas comerciales, permitiéndote hablar naturalmente mientras la IA se encarga de corregir muletillas, eliminar repeticiones y dar formato al texto, que luego se copia automáticamente a tu portapapeles.

## 🚀 ¿Qué debe hacer Dictum?
La misión principal de Dictum es hacer el dictado perfecto, perdonando los errores humanos:
- **Push-to-Talk Universal:** Permite usar una tecla de acceso rápido global (por defecto `Alt`) para grabar voz en cualquier momento, sin importar qué ventana de tu PC esté activa.
- **Transcripción Rápida (Voz a Texto):** Convierte el audio en texto crudo de forma rápida usando **Whisper** (preferiblemente de forma local usando aceleración de GPU).
- **Reescritura Semántica (Texto a Texto):** Toma la transcripción "sucia" (con errores o muletillas) y la pasa por un modelo de lenguaje (LLM) que limpia, da formato y corrige usando el contexto de tu profesión. 
- **Integración Transparente:** Al terminar, el texto procesado se guarda automáticamente en el portapapeles, listo para pegarse (`Ctrl + V`) en correos, editores de código o chats.

---

## 🎮 Cómo se debe manejar el programa (Guía de Uso)

### 1. El Flujo de Trabajo Diario
Manejar Dictum es muy sencillo:
1. Mantén presionada la tecla **Alt** (o la que hayas configurado).
2. Habla con naturalidad a tu micrófono. Puedes dudar, usar muletillas ("ehhh", "mmm") o corregirte sobre la marcha ("escribe hola, ah no espera, mejor escribe adiós").
3. Suelta la tecla **Alt**.
4. Verás una notificación en la interfaz o un icono en la bandeja del sistema procesando. Al terminar el procesamiento (usualmente un par de segundos), escucharás un sonido de éxito y el texto limpio estará en tu portapapeles.

### 2. Configuración Inicial (Pestaña "Ajustes")
Para que Dictum sea preciso, debes configurarlo desde su interfaz:

- **Configurar la Transcripción (Whisper):**
  Ve a la sección Whisper. Si tienes una tarjeta de video NVIDIA, elige el modo **Local** y el modelo `medium`. Esto te dará la máxima privacidad y buena velocidad.
  
- **Configurar la IA (El "Cerebro"):**
  Tienes dos opciones para la reescritura:
  - **Ollama (100% Privado y Local):** Necesitas tener Ollama instalado en tu PC. Descarga un modelo (ej. `ollama pull mistral`), presiona "Refrescar Modelos" en Dictum y selecciónalo.
  - **OpenRouter (Nube):** Si tu PC no es tan potente, crea una cuenta en [OpenRouter.ai](https://openrouter.ai), genera una API Key gratuita y pégala en los ajustes de Dictum.

- **Perfiles Personalizados:**
  Puedes configurar "Perfiles". Dile a Dictum a qué te dedicas (ej. "Desarrollador Web") y pásale términos técnicos que usas a diario. Así la IA no confundirá "React" con "Rial", o "Python" con "Paiton".

---

## ⚙️ Cómo instalarlo (Para Desarrolladores)

### Requisitos Previos
- Python 3.10 o superior.
- Una GPU NVIDIA con soporte CUDA 11.8+ (Recomendado).
- [Ollama](https://ollama.com/) (opcional, para modelos locales).

### Instalación Paso a Paso
Abre una terminal, ubícate en la carpeta del proyecto y sigue estos comandos:

```bash
# 1. Crear y activar el entorno virtual (Recomendado)
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
# source .venv/bin/activate

# 2. Instalar las dependencias base
pip install -r requirements.txt

# 3. Instalar PyTorch con soporte CUDA (Necesario para usar tu GPU con Whisper)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Ejecución
Una vez instaladas las dependencias, simplemente ejecuta:
```bash
python main.py
```

---

## 🧰 Scripts de Utilidad (.bat)

El repositorio incluye varios archivos `.bat` diseñados con rutas dinámicas (`%~dp0`), lo que significa que **puedes ejecutar el proyecto desde cualquier carpeta o pendrive** sin tener que modificar el código.

- **`setup.bat`**: Prepara todo el entorno automáticamente. Crea el entorno virtual, lo activa e instala todas las librerías necesarias de `requirements.txt` (incluyendo PyTorch con soporte para CUDA). Ideal para la primera vez que clonas el proyecto.
- **`build.bat`**: Automatiza la compilación del proyecto. Limpia archivos residuales y usa PyInstaller con el archivo `Dictum.spec` para generar un ejecutable (`.exe`) listo para usar o distribuir.
- **`Dictum.bat`**: Un lanzador silencioso. Inicia la aplicación usando `pythonw.exe`, lo que permite que el programa corra nativamente en segundo plano sin dejar una ventana negra de la terminal abierta.
- **`dev.bat`**: Script para desarrolladores. Ejecuta la aplicación utilizando `watchmedo`. Si modificas cualquier archivo `.py` en VS Code, el script detectará el cambio y reiniciará la aplicación automáticamente, ahorrándote tiempo durante el desarrollo.

---

## 🏗️ Cómo lo hace (Arquitectura del Código)

Dictum está estructurado de manera limpia, separando la interfaz de la lógica:

1. **Captura de Teclas y Audio (`core/audio_capture.py`):** 
   Utiliza la librería `keyboard` a nivel de sistema operativo para saber cuándo presionas `Alt`. Mientras la presionas, la librería `sounddevice` graba el audio desde tu micrófono por defecto.
2. **Transcripción (`core/transcriber.py`):** 
   Ese audio se envía a la librería `faster-whisper`. Esta herramienta carga un modelo de IA de OpenAI directamente en tu tarjeta de video para convertir la voz en texto muy rápido.
3. **Reescritura por IA (`core/rewriter.py`):** 
   Aquí ocurre la magia. El texto bruto se manda a Ollama (local) o OpenRouter (nube) usando la librería `httpx`. Dictum inyecta un *System Prompt* estricto (instrucciones maestras) que le prohíben a la IA "conversar" contigo, obligándola únicamente a limpiar muletillas, arreglar errores gramaticales y aplicar los términos técnicos de tu Perfil.
4. **Interfaz Gráfica (`gui/`):** 
   Toda la ventana, configuraciones y botones están construidos con **PyQt6**. La aplicación maneja procesos en segundo plano usando Hilos (`QRunnable` y `QThreadPool`) para que la ventana nunca se quede "congelada" mientras la IA procesa el texto. Todo se guarda automáticamente en `~/.voicedraft/config.json`.

