"""Valida rop-payload.json contra schemas/rop-payload.v0.json.

Falla el step (exit 1) si el payload que arma esta misma accion no cumple su
propio contrato - la CI no deberia poder enviar a rop-mock algo que ni ella
misma valida.
"""
import json
import sys

from jsonschema import Draft202012Validator, FormatChecker


def main():
    schema_path, payload_path = sys.argv[1], sys.argv[2]

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))

    if not errors:
        print(f"OK: {payload_path} cumple {schema_path}")
        return

    for error in errors:
        location = "/".join(str(p) for p in error.path) or "(raiz)"
        print(f"::error::Payload invalido en '{location}': {error.message}")

    sys.exit(1)


if __name__ == "__main__":
    main()
