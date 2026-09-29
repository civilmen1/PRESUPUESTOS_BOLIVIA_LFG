# 🚀 Despliegue en la nube — APU Bolivia Generator

Esta guía explica cómo publicar el sistema en internet para que **empresas y
proveedores reales** accedan a la **misma plataforma** con base de datos
compartida.

> **Concepto clave:** se despliega **una sola instancia** de la app con una
> base de datos en un **volumen/disco persistente**. Todos los usuarios
> (empresas y proveedores) se conectan a esa misma instancia, por lo que
> comparten datos: los materiales que difunde un comprador llegan a los
> proveedores, y los precios que responde un proveedor vuelven al APU.

---

## Opción A — Render.com (recomendada, más fácil) ⭐

1. Sube tu repositorio a **GitHub** (ya lo tienes).
2. Entra a https://render.com → **New +** → **Blueprint**.
3. Conecta tu repositorio. Render leerá `render.yaml` automáticamente y creará:
   - el servicio web (Docker),
   - un **disco persistente** de 1 GB montado en `/data` (la base de datos).
4. En el panel de Render, completa las variables marcadas (SMTP, VERIFIK_TOKEN).
5. **Deploy**. En unos minutos tendrás una URL pública `https://...onrender.com`.

`AUTH_SALT` lo genera Render automáticamente (seguro).

---

## Opción B — VPS propio con Docker (más control) 🐳

En un servidor Linux (DigitalOcean, Hetzner, AWS Lightsail, etc.) con Docker:

```bash
git clone <tu-repo> apu-bolivia
cd apu-bolivia
# edita docker-compose.yml: pon un AUTH_SALT secreto y, si quieres, SMTP real
docker compose up -d
```

La app queda en `http://TU_SERVIDOR:8501`. Datos persistentes en el volumen
`apu_data`.

### HTTPS (dominio propio)
Pon un **reverse proxy** (Caddy o Nginx) delante para servir por HTTPS:

```caddyfile
# Caddyfile
tudominio.com {
    reverse_proxy localhost:8501
}
```

---

## Opción C — Railway / Fly.io

Ambas detectan el `Dockerfile` automáticamente. Crea un volumen persistente
montado en `/data` y define `APU_DB_PATH=/data/proveedores.db`.

---

## Opción D — Streamlit Community Cloud (GRATIS) 🆓

Hosting gratuito de Streamlit, directo desde GitHub. **No usa el Dockerfile**:
instala `requirements.txt` (librerías Python) y `packages.txt` (Tesseract y
Poppler para el OCR).

1. Entra a <https://share.streamlit.io> e inicia sesión **con tu cuenta de GitHub**.
2. **Create app** → *Deploy a public app from GitHub*:
   - Repository: `civilmen1/PRESUPUESTOS_BOLIVIA_LFG`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: elige el nombre (p. ej. `frava` → `frava.streamlit.app`)
3. **Advanced settings** → Python version: **3.11**. En **Secrets** pega (ajusta
   los valores):

   ```toml
   AUTH_SALT = "una-frase-secreta-larga-y-unica"
   USAR_LLM = "true"
   GROQ_API_KEY = "gsk_..."          # tu clave de https://console.groq.com
   EMAIL_DRY_RUN = "true"
   AUTH_EMAIL_DRY_RUN = "true"       # "false" + SMTP_* para enviar correos reales
   SCRAPER_DRY_RUN = "true"
   # SMTP_HOST = "smtp.gmail.com"
   # SMTP_USER = "tu_correo@gmail.com"
   # SMTP_PASSWORD = "contraseña-de-aplicacion"
   ```

   `app.py` copia estos Secrets a variables de entorno antes de cargar la
   configuración, así que funcionan igual que en Render.
4. **Deploy**. La primera instalación tarda unos minutos.

**Limitaciones del plan gratis** (propias de la plataforma, no del código):

- **Los datos NO son permanentes**: la base SQLite, los documentos subidos y
  las exportaciones se **borran** cuando la app se reinicia o se redespliega.
  Descarga tus exportaciones y respalda lo importante.
- **Se duerme** tras varias horas sin visitas; al abrirla se despierta con un
  botón (tarda ~1 min).
- **No admite dominio propio** (`www.frava.tech`): queda en `*.streamlit.app`.
- Recursos limitados (~1 GB de RAM): evita subir PDF escaneados muy grandes.

Para datos permanentes y dominio propio usa la Opción A (Render) o B (VPS).

---

## Variables de entorno importantes

| Variable | Para qué | En producción |
|----------|----------|---------------|
| `APU_DB_PATH` | Ruta de la base de datos | `/data/proveedores.db` (en el volumen) |
| `AUTH_SALT` | Seguridad de contraseñas | **Un secreto único** (no el de ejemplo) |
| `AUTH_EMAIL_DRY_RUN` | Verificación de correo | `false` para enviar correos reales |
| `EMAIL_DRY_RUN` | Cotizaciones por correo | `false` para envíos reales |
| `SMTP_HOST/USER/PASSWORD/FROM` | Servidor de correo | Tu cuenta SMTP (Gmail app password, SendGrid, etc.) |
| `VERIFIK_TOKEN` | Verificación de NIT | Tu token de Verifik |

> Para que la **verificación de correo y las cotizaciones por email** funcionen
> de verdad en la nube, configura SMTP y pon `AUTH_EMAIL_DRY_RUN=false` y
> `EMAIL_DRY_RUN=false`.

---

## IA (Ollama) en la nube

La IA local Ollama necesita bastante RAM/GPU. Opciones:
- **No usar IA en la nube** (`USAR_LLM=false`): funciona el extractor offline
  por reglas. Recomendado para empezar.
- **Servidor con Ollama:** levanta un contenedor Ollama aparte y apunta
  `OLLAMA_HOST` a él (requiere instancia con ≥8 GB RAM).
- **LLM de pago por API** (OpenAI/Anthropic/Gemini): configura su API key; no
  consume recursos del servidor.

---

## Escala mayor: PostgreSQL

Para muchos usuarios concurrentes, el siguiente paso es migrar de SQLite a
**PostgreSQL** (la app ya usa SQL estándar y `DATABASE_URL` está previsto en la
configuración). Es una mejora futura; SQLite en disco persistente cubre bien el
arranque y escala pequeña/media.

---

## Lista de verificación antes de publicar

- [ ] `AUTH_SALT` cambiado a un valor secreto único.
- [ ] Disco/volumen persistente montado en `/data`.
- [ ] SMTP configurado y `AUTH_EMAIL_DRY_RUN=false` (si quieres verificación real).
- [ ] `VERIFIK_TOKEN` configurado (si quieres verificación de NIT real).
- [ ] HTTPS activo (dominio + reverse proxy o el HTTPS automático de Render).
