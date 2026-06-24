import json
import sys
from pathlib import Path

def main():
    locales_dir = Path(__file__).parent.parent / "locales"
    en_file = locales_dir / "en.json"
    es_file = locales_dir / "es.json"

    if not en_file.exists() or not es_file.exists():
        print("Error: Los archivos locales (en.json, es.json) no existen.")
        sys.exit(1)

    with open(en_file, "r", encoding="utf-8") as f:
        en_dict = json.load(f)
    
    with open(es_file, "r", encoding="utf-8") as f:
        es_dict = json.load(f)

    en_keys = set(en_dict.keys())
    es_keys = set(es_dict.keys())

    missing_in_es = en_keys - es_keys
    missing_in_en = es_keys - en_keys

    has_errors = False

    if missing_in_es:
        print("ERROR: Las siguientes llaves están en en.json pero FALTAN en es.json:")
        for k in sorted(missing_in_es):
            print(f"  - {k}")
        has_errors = True

    if missing_in_en:
        print("ERROR: Las siguientes llaves están en es.json pero FALTAN en en.json:")
        for k in sorted(missing_in_en):
            print(f"  - {k}")
        has_errors = True

    if has_errors:
        print("\nFallo en la verificación de i18n. Ambos archivos deben tener exactamente las mismas llaves.")
        sys.exit(1)
    
    print("✓ Verificación i18n exitosa: Todos los idiomas están sincronizados.")
    sys.exit(0)

if __name__ == "__main__":
    main()
