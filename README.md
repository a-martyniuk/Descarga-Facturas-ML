# Mercado Libre Invoice Downloader & Sync

![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
![Tech](https://img.shields.io/badge/Stack-Python%20%7C%20Google%20Drive%20API-yellow?style=for-the-badge)

Automatización robusta para la gestión contable personal: descarga facturas de compras de **Mercado Libre**, las organiza localmente, sincroniza con **Google Drive** y notifica novedades por email.

---

## ✨ Características Principales

- **📥 Descarga Inteligente:** Obtiene facturas automáticamente usando la API oficial de Mercado Libre.
- **📂 Organización Jerárquica:** Clasifica archivos en carpetas locales `Año/Mes` (ej: `2024/01`).
- **☁️ Sincronización Cloud:** Respalda todo automáticamente en una carpeta específica de Google Drive.
- **📧 Alertas por Email:** Envía un resumen diario vía Gmail si se descargaron nuevas facturas.
- **🔄 Gestión de Sesión:** Manejo automático de Refresh Tokens para funcionar sin intervención manual indefinidamente.
- **⚡ Eficiencia:** Evita descargas duplicadas y verifica ejecuciones previas para no saturar la API.

## 🛠 Tecnologías

*   **Lenguaje:** Python 3.10+
*   **APIs:**
    *   Mercado Libre (OAuth 2.0)
    *   Google Drive API v3
    *   Gmail API
*   **Librerías Clave:** `requests`, `google-api-python-client`, `google-auth-oauthlib`.

## 🚀 Requisitos y Configuración

### 1. Prerrequisitos
*   Python 3.10 o superior instalado.
*   Una aplicación creada en [Mercado Libre Developers](https://developers.mercadolibre.com.ar/).
*   Un proyecto en Google Cloud Console con las APIs de **Drive** y **Gmail** habilitadas.

### 2. Instalación
```bash
git clone https://github.com/tu-usuario/Descarga-Facturas-ML.git
cd Descarga-Facturas-ML
pip install -r requirements.txt
```

### 3. Configuración de Credenciales

#### Mercado Libre
Crea un archivo `config_meli.json` en la raíz con tus datos:
```json
{
  "app_id": "TU_APP_ID",
  "client_secret": "TU_CLIENT_SECRET",
  "redirect_uri": "https://www.google.com/"
}
```

#### Google
Coloca tu archivo `credentials.json` (descargado de Google Cloud) en la raíz del proyecto.

### 4. Inicialización
Ejecuta el script por primera vez manualmente para realizar el flujo de autorización OAuth (se abrirá el navegador):
```bash
python meli_invoices.py
```

## 📅 Automatización

El proyecto incluye un archivo `run_daily.bat` diseñado para el Programador de Tareas de Windows.

1.  Abre el **Programador de Tareas**.
2.  Crea una nueva tarea básica.
3.  Configura el disparador (ej: Diariamente a las 4:00 AM).
4.  Acción: Iniciar programa -> selecciona `run_daily.bat`.

## 📊 Estructura del Proyecto
```
Descarga-Facturas-ML/
├── Facturas_Compras/       # Almacenamiento local (Año/Mes)
├── config_meli.json        # Configuración ML
├── credentials.json        # Credenciales Google OAuth
├── meli_tokens.json        # Tokens de sesión (Auto-generado)
├── token.pickle            # Token Google (Auto-generado)
├── meli_invoices.py        # Script Principal (Descarga)
└── drive_uploader.py       # Módulo Sincronización (Drive/Gmail)
```
