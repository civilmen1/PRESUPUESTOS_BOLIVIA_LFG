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

## IA en la nube

> **Arranque recomendado: modo offline (`USAR_LLM=false`).** Es gratis ($0),
> no hace llamadas externas y la app funciona con el extractor por reglas. El
> `render.yaml` ya viene así. Activa la IA cuando valides el tráfico real.

Opciones de IA, de menor a mayor calidad/costo:

- **Offline por reglas** (`USAR_LLM=false`): gratis, sin dependencias. Ideal
  para lanzar. ⭐
- **Groq** (`USAR_LLM=true` + `GROQ_API_KEY`): IA en línea **gratis** y rápida.
  Buen escalón intermedio sin costo.
- **GLM-5.2 / Z.AI** (`USAR_LLM=true` + `GLM_API_KEY`): **máxima calidad**,
  ~$0.018 por APU. API compatible con OpenAI; no consume RAM del servidor.
- **OpenAI / Gemini** (`USAR_LLM=true` + su API key): alternativas de pago.

> ⚠️ **App pública:** con cualquier IA de pago, cada APU que genere un usuario
> cuesta dinero. Antes de activar GLM en abierto, considera un límite de uso
> (por sesión/día) para proteger la factura.

### Cómo activar GLM-5.2 después de lanzar
1. En Render → Environment, pega tu clave en `GLM_API_KEY`.
2. Cambia `USAR_LLM` a `true`.
3. Guarda y redeploy. El panel del asistente mostrará "GLM responde correctamente".

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
