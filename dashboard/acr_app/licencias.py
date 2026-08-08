"""
licencias.py — Sistema de licencias de prueba
ACR Normativa CNBV © Omar León Corona

Características:
  - Claves firmadas con HMAC-SHA256 (no falsificables sin la clave maestra)
  - Límite de usos por licencia
  - Fecha de expiración
  - Kill switch por ID de licencia
  - Marca de agua en todos los reportes de prueba
  - Registro de uso en SQLite local

La clave maestra vive en la variable de entorno ACR_LICENSE_SECRET.
Nunca en el código, nunca en el repo.
"""
import hashlib, hmac, json, base64, sqlite3, os
from datetime import date, datetime
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────
DB_PATH = Path(os.environ.get("ACR_LICENSE_DB", "/tmp/acr_licencias.db"))
SECRET  = os.environ.get("ACR_LICENSE_SECRET", "")

# IDs de licencias revocadas (kill switch) — se actualiza sin redesplegar
# También puede vivir en variable de entorno ACR_REVOKED_IDS="ID1,ID2"
REVOCADAS = set(
    os.environ.get("ACR_REVOKED_IDS", "").upper().split(",")
) - {""}


# ── Base de datos de usos ─────────────────────────────────────────────────────
def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS usos (
            id_licencia TEXT NOT NULL,
            titular     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            ip          TEXT,
            PRIMARY KEY (id_licencia, timestamp)
        )
    """)
    con.commit()
    return con


def _contar_usos(con, id_licencia: str) -> int:
    row = con.execute(
        "SELECT COUNT(*) FROM usos WHERE id_licencia = ?", (id_licencia,)
    ).fetchone()
    return row[0] if row else 0


def _registrar_uso(con, id_licencia: str, titular: str, ip: str = ""):
    con.execute(
        "INSERT INTO usos VALUES (?,?,?,?)",
        (id_licencia, titular, datetime.utcnow().isoformat(), ip)
    )
    con.commit()


# ── Verificación de licencia ──────────────────────────────────────────────────
class LicenciaInvalida(Exception):
    pass

class LicenciaExpirada(Exception):
    pass

class LicenciaAgotada(Exception):
    pass

class LicenciaRevocada(Exception):
    pass


def _decodificar(clave: str) -> dict:
    """Verifica firma HMAC y retorna el payload."""
    if not SECRET:
        raise LicenciaInvalida("El servidor no tiene configurada la clave maestra (ACR_LICENSE_SECRET).")
    try:
        partes = clave.strip().rsplit(".", 1)
        if len(partes) != 2:
            raise ValueError
        payload_b64, firma_recibida = partes
        # Rellenar padding base64
        padding = 4 - len(payload_b64) % 4
        payload_b64_pad = payload_b64 + "=" * (padding % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_pad).decode())
        # Verificar firma
        firma_esperada = hmac.new(
            SECRET.encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()[:16].upper()
        if not hmac.compare_digest(firma_recibida.upper(), firma_esperada):
            raise LicenciaInvalida("Clave de licencia inválida o modificada.")
        return payload
    except (ValueError, KeyError, Exception) as e:
        raise LicenciaInvalida(f"Clave de licencia no reconocida: {e}")


def verificar_licencia(clave: str, ip: str = "") -> dict:
    """
    Verifica la licencia, registra el uso y retorna el payload.
    Lanza excepciones descriptivas si algo falla.
    Retorna: {"titular", "max_usos", "expira", "id", "usos_restantes"}
    """
    payload = _decodificar(clave)
    lid = payload["id"].upper()

    # Kill switch
    if lid in REVOCADAS:
        raise LicenciaRevocada(
            f"La licencia {lid} ha sido revocada. "
            "Contacta a Omar León Corona para más información."
        )

    # Expiración
    hoy = date.today()
    expira = date.fromisoformat(payload["expira"])
    if hoy > expira:
        raise LicenciaExpirada(
            f"La licencia expiró el {expira.strftime('%d/%m/%Y')}. "
            "Contacta a Omar León Corona para renovación."
        )

    # Usos
    con = _init_db()
    usos_actuales = _contar_usos(con, lid)
    max_usos = payload["max_usos"]
    if usos_actuales >= max_usos:
        raise LicenciaAgotada(
            f"Esta licencia de prueba ya consumió sus {max_usos} reportes permitidos. "
            "Contacta a Omar León Corona para acceso completo."
        )

    # Registrar uso
    _registrar_uso(con, lid, payload["titular"], ip)
    con.close()

    return {
        **payload,
        "usos_restantes": max_usos - usos_actuales - 1,
    }


# ── Generador de claves (solo para uso de Omar) ───────────────────────────────
def generar_clave(titular: str, max_usos: int, fecha_expiracion: date) -> str:
    """
    Genera una clave de licencia firmada.
    Requiere que ACR_LICENSE_SECRET esté en el entorno.
    """
    import secrets as _secrets
    if not SECRET:
        raise RuntimeError("ACR_LICENSE_SECRET no está configurada.")
    payload = {
        "titular": titular,
        "max_usos": max_usos,
        "expira": str(fecha_expiracion),
        "id": _secrets.token_hex(6).upper()
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()
    ).decode().rstrip("=")
    firma = hmac.new(
        SECRET.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()[:16].upper()
    return f"{payload_b64}.{firma}"


# ── Texto de marca de agua ────────────────────────────────────────────────────
MARCA_AGUA_TEXTO = (
    "VERSIÓN DE PRUEBA — Sistema desarrollado por Omar León Corona. "
    "Uso autorizado exclusivamente para evaluación. "
    "Se requieren permisos del autor para uso comercial o institucional. "
    "contacto: omar@acrnormativa.mx"
)

LEYENDA_AUTORIA = (
    "Desarrollado por Omar León Corona © 2026 | "
    "ACR Normativa CNBV | REPORTE DE PRUEBA — No válido para entrega oficial"
)
