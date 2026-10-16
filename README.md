# laboratorio1_seguridad

## Publicar el formulario con Supabase y Vercel

### 1. Crear la tabla en Supabase

En Supabase abre **SQL Editor**, pega el contenido de
[`supabase-schema.sql`](./supabase-schema.sql) y pulsa **Run**. La tabla
aparecerá en **Table Editor → participantes**.

### 2. Configurar Vercel

Importa este repositorio en Vercel y agrega estas variables en **Settings →
Environment Variables**:

```text
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-clave-publica-anon
```

La URL y la clave `anon` están en **Supabase → Project Settings → API**.
Nunca configures ni subas la clave `service_role` al navegador o al repositorio.

Después de guardar las variables, haz un nuevo deploy. El formulario usa
automáticamente la ruta [`api/participantes.py`](./api/participantes.py).

### 3. Consultar los datos

En Supabase abre **Table Editor → participantes**. La API solo permite
insertar mediante la política RLS; no expone una ruta pública para leer los
registros.

El servidor local anterior (`python server.py`) sigue disponible para probar
sin Vercel, usando SQLite. La versión publicada usa Supabase.

Esta implementación es únicamente para el entorno académico. No almacenes
datos reales sin autorización, aviso de privacidad y controles adicionales
contra abuso.