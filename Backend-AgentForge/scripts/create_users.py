"""Crea usuarios en Supabase Auth (admin) para pruebas.

Uso:
    python scripts/create_users.py correo1 pass1 correo2 pass2 ...

Requiere SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY en .env.
Los usuarios quedan confirmados (email_confirm=True) y pueden loguear de inmediato.
"""
import sys

from app.db.supabase import get_supabase


def main(argv: list[str]) -> None:
    if len(argv) < 2 or len(argv) % 2 != 0:
        print("Uso: python scripts/create_users.py correo1 pass1 [correo2 pass2 ...]")
        raise SystemExit(1)

    sb = get_supabase()
    pairs = list(zip(argv[0::2], argv[1::2]))
    for email, password in pairs:
        try:
            res = sb.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
            uid = getattr(res.user, "id", "?") if getattr(res, "user", None) else "?"
            print(f"✅ Creado: {email}  (id={uid})")
        except Exception as e:  # noqa: BLE001
            print(f"❌ {email}: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
