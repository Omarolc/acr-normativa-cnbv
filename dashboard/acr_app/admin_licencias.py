"""
admin_licencias.py — Generador y gestor de claves de prueba
ACR Normativa CNBV © Omar León Corona

USO:
  python admin_licencias.py generar --titular "Marcos Morales" --empresa "Gota de Agua" --usos 5 --expira 2026-08-31
  python admin_licencias.py listar
  python admin_licencias.py revocar --id ABC123

Requiere: ACR_LICENSE_SECRET en el entorno (la misma que usa Railway).
"""
import argparse, os, sys, sqlite3, json
from datetime import date, datetime

def get_secret():
    s = os.environ.get("ACR_LICENSE_SECRET","")
    if not s:
        print("ERROR: ACR_LICENSE_SECRET no está en el entorno.")
        print("Agrega la variable antes de correr este script.")
        sys.exit(1)
    return s

def cmd_generar(args):
    secret = get_secret()
    import hashlib, hmac, base64, secrets as _sec
    titular = f"{args.titular} — {args.empresa}" if args.empresa else args.titular
    expira  = date.fromisoformat(args.expira)
    payload = {
        "titular": titular,
        "max_usos": args.usos,
        "expira": str(expira),
        "id": _sec.token_hex(6).upper()
    }
    b64 = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()
    ).decode().rstrip("=")
    firma = hmac.new(secret.encode(), b64.encode(), hashlib.sha256).hexdigest()[:16].upper()
    clave = f"{b64}.{firma}"

    print("\n" + "="*70)
    print("  CLAVE DE LICENCIA DE PRUEBA — ACR Normativa CNBV")
    print("  © Omar León Corona")
    print("="*70)
    print(f"  Titular  : {titular}")
    print(f"  Usos máx : {args.usos}")
    print(f"  Expira   : {expira.strftime('%d/%m/%Y')}")
    print(f"  ID       : {payload['id']}")
    print()
    print(f"  CLAVE:")
    print(f"  {clave}")
    print("="*70)
    print()
    print("Instrucciones para compartir:")
    print(f"  1. Envía la CLAVE al titular.")
    print(f"  2. El titular la ingresa en el campo 'Clave de Licencia' del dashboard.")
    print(f"  3. Cada reporte descargado (PDF o Excel) consume 1 uso.")
    print(f"  4. Para revocar: python admin_licencias.py revocar --id {payload['id']}")
    print(f"     y agrega el ID a la variable ACR_REVOKED_IDS en Railway.")
    print()

    # Guardar en log local
    log_path = os.path.join(os.path.dirname(__file__), "licencias_emitidas.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "titular": titular,
            "id": payload["id"],
            "max_usos": args.usos,
            "expira": str(expira),
            "clave": clave,
        }, ensure_ascii=False) + "\n")
    print(f"Registro guardado en: {log_path}")

def cmd_listar(args):
    log_path = os.path.join(os.path.dirname(__file__), "licencias_emitidas.jsonl")
    if not os.path.exists(log_path):
        print("No hay licencias emitidas todavía.")
        return
    revocadas = set(os.environ.get("ACR_REVOKED_IDS","").upper().split(",")) - {""}
    print(f"\n{'ID':<14} {'TITULAR':<40} {'USOS':>5} {'EXPIRA':<12} {'ESTADO'}")
    print("-"*80)
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            estado = "REVOCADA" if r["id"] in revocadas else (
                "EXPIRADA" if date.fromisoformat(r["expira"]) < date.today() else "ACTIVA"
            )
            print(f"  {r['id']:<12} {r['titular'][:38]:<40} {r['max_usos']:>5} {r['expira']:<12} {estado}")
    print()

def cmd_revocar(args):
    print(f"\nPara revocar la licencia {args.id.upper()}:")
    print(f"1. Ve a Railway → tu servicio → Variables")
    print(f"2. Si ACR_REVOKED_IDS no existe, créala con valor: {args.id.upper()}")
    print(f"   Si ya existe, agrega el ID separado por coma: ID_ANTERIOR,{args.id.upper()}")
    print(f"3. Railway redespliega automáticamente.")
    print(f"4. La clave queda inválida de inmediato, sin redesplegar código.\n")

def main():
    ap = argparse.ArgumentParser(
        description="Admin de licencias ACR Normativa CNBV — Omar León Corona"
    )
    sub = ap.add_subparsers(dest="cmd")

    g = sub.add_parser("generar", help="Generar nueva clave de prueba")
    g.add_argument("--titular",  required=True, help="Nombre del titular")
    g.add_argument("--empresa",  default="",    help="Empresa o institución")
    g.add_argument("--usos",     type=int, default=5, help="Número máximo de reportes (default: 5)")
    g.add_argument("--expira",   default=str(date.today().replace(day=31, month=8)),
                   help="Fecha de expiración YYYY-MM-DD (default: 2026-08-31)")

    sub.add_parser("listar", help="Listar licencias emitidas")

    r = sub.add_parser("revocar", help="Instrucciones para revocar una licencia")
    r.add_argument("--id", required=True, help="ID de la licencia a revocar")

    args = ap.parse_args()
    if args.cmd == "generar":    cmd_generar(args)
    elif args.cmd == "listar":   cmd_listar(args)
    elif args.cmd == "revocar":  cmd_revocar(args)
    else: ap.print_help()

if __name__ == "__main__":
    main()
