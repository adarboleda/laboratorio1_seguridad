import json
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FIELDS = ("nombres", "apellidos", "telefono", "correo")


def validate_participant(data):
    if not isinstance(data, dict):
        raise ValueError("El cuerpo de la solicitud no es válido.")

    values = {field: str(data.get(field, "")).strip() for field in FIELDS}
    # El formulario envía el campo como "contrasena" (sin ñ); la columna de la
    # tabla es "contraseña" (con ñ). Se admiten ambas claves de entrada.
    contrasena = str(data.get("contrasena", data.get("contraseña", ""))).strip()
    if any(not values[field] for field in FIELDS) or not contrasena:
        raise ValueError("Todos los campos son obligatorios.")
    if len(values["nombres"]) > 100 or len(values["apellidos"]) > 100:
        raise ValueError("El nombre o apellido es demasiado largo.")
    if len(values["telefono"]) > 30:
        raise ValueError("El teléfono es demasiado largo.")
    if len(values["correo"]) > 254 or not EMAIL_PATTERN.fullmatch(values["correo"]):
        raise ValueError("Ingresa un correo electrónico válido.")
    if not 8 <= len(contrasena) <= 100:
        raise ValueError("La contraseña debe tener entre 8 y 100 caracteres.")
    values["contraseña"] = contrasena
    return values


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/participantes":
            self.send_json({"error": "Ruta no encontrada."}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 10_000:
                raise ValueError("El tamaño de la solicitud no es válido.")
            participant = validate_participant(
                json.loads(self.rfile.read(content_length))
            )
            self.save_participant(participant)
        except (json.JSONDecodeError, ValueError) as error:
            self.send_json({"error": str(error)}, 400)
            return
        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            print(f"Supabase respondió {error.code}: {error_body}", flush=True)
            self.send_json(
                {
                    "error": (
                        f"Supabase rechazó el registro (HTTP {error.code}). "
                        "Revisa las variables, la tabla y RLS."
                    )
                },
                502,
            )
            return
        except URLError as error:
            print(f"No se pudo conectar con Supabase: {error}", flush=True)
            self.send_json(
                {"error": f"No fue posible conectar con Supabase: {error.reason}"},
                502,
            )
            return

        self.send_json({"message": "Participante guardado correctamente."}, 201)

    def save_participant(self, participant):
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY", "")
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", supabase_url),
                ("SUPABASE_ANON_KEY", supabase_key),
            )
            if not value
        ]
        if missing:
            raise URLError(f"Faltan variables en Vercel: {', '.join(missing)}.")

        request = Request(
            f"{supabase_url}/rest/v1/participantes",
            data=json.dumps(participant).encode("utf-8"),
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="POST",
        )
        with urlopen(request, timeout=10):
            pass

    def send_json(self, payload, status):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return
