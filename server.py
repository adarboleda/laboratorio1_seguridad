from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3


ROOT = Path(__file__).parent
DATABASE = ROOT / "participantes.db"
MAX_BODY_SIZE = 10_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombres TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                telefono TEXT NOT NULL,
                correo TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def validate_participant(data):
    if not isinstance(data, dict):
        raise ValueError("El cuerpo de la solicitud no es válido.")

    fields = ("nombres", "apellidos", "telefono", "correo")
    values = {field: str(data.get(field, "")).strip() for field in fields}
    if any(not values[field] for field in fields):
        raise ValueError("Todos los campos son obligatorios.")
    if len(values["nombres"]) > 100 or len(values["apellidos"]) > 100:
        raise ValueError("El nombre o apellido es demasiado largo.")
    if len(values["telefono"]) > 30:
        raise ValueError("El teléfono es demasiado largo.")
    if len(values["correo"]) > 254 or not EMAIL_PATTERN.fullmatch(values["correo"]):
        raise ValueError("Ingresa un correo electrónico válido.")

    return values


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/participantes":
            self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_SIZE:
            self.send_json(
                {"error": "El tamaño de la solicitud no es válido."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            data = json.loads(self.rfile.read(content_length))
            participant = validate_participant(data)
            with sqlite3.connect(DATABASE) as connection:
                connection.execute(
                    """
                    INSERT INTO participantes (nombres, apellidos, telefono, correo)
                    VALUES (:nombres, :apellidos, :telefono, :correo)
                    """,
                    participant,
                )
        except (json.JSONDecodeError, ValueError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except sqlite3.Error:
            self.send_json(
                {"error": "No fue posible guardar los datos en la base local."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self.send_json({"message": "Participante guardado correctamente."}, HTTPStatus.CREATED)

    def send_json(self, payload, status):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        if self.path.startswith("/api/"):
            return
        super().log_message(format, *args)


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler)
    print("Servidor disponible en http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()
