"""Arma el JSON de handoff GHA -> ROP segun schemas/rop-payload.v0.json.

Lee todo por variables de entorno (nunca por interpolacion directa en YAML/shell)
para no arrastrar caracteres raros de nombres de app, mensajes de commit, etc.
"""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone


def env(name, default=""):
    return os.environ.get(name, default)


def bool_env(name, default="true"):
    return env(name, default).strip().lower() == "true"


def result_gate(name, result, blocking):
    status = "pass" if result == "success" else "fail"
    return {
        "name": name,
        "value": 1.0 if result == "success" else 0.0,
        "threshold": 1.0,
        "operator": ">=",
        "status": status,
        "blocking": blocking,
    }


def build_gates():
    gates = [
        result_gate("build", env("BUILD_RESULT"), True),
        result_gate("unit-test", env("TEST_RESULT"), True),
    ]

    # secrets-scan es el unico gate sin excepcion: si el stack lo corrio, siempre
    # blocking=true. Si no lo corrio (SECRETS_RESULT vacio), no se reporta -
    # ROP no debe ver un gate fantasma para stacks que aun no lo migran.
    secrets_result = env("SECRETS_RESULT")
    if secrets_result:
        gates.append(result_gate("secrets-scan", secrets_result, True))

    hard_gating = bool_env("HARD_GATING")
    coverage, coverage_min = env("GATE_COVERAGE"), env("COVERAGE_MIN")
    if coverage and coverage_min:
        ok = float(coverage) >= float(coverage_min)
        gates.append({
            "name": "coverage",
            "value": float(coverage),
            "threshold": float(coverage_min),
            "operator": ">=",
            "status": env("GATE_STATUS") or ("pass" if ok else "fail"),
            "blocking": hard_gating,
        })

    density, density_min = env("GATE_DENSITY"), env("SUCCESS_DENSITY_MIN")
    if density and density_min:
        ok = float(density) >= float(density_min)
        gates.append({
            "name": "success_density",
            "value": float(density),
            "threshold": float(density_min),
            "operator": ">=",
            "status": env("GATE_STATUS") or ("pass" if ok else "fail"),
            "blocking": hard_gating,
        })

    if bool_env("SONAR_ENABLED"):
        # blocking=false por default (SONAR_BLOCKING) - Sonar es informativo,
        # ver decision documentada en consolidate-verdict/action.yml.
        gates.append(result_gate("sonar-quality-gate", env("SONAR_RESULT"), bool_env("SONAR_BLOCKING", "false")))

    if bool_env("SNYK_ENABLED"):
        gates.append(result_gate("trivy-critical", env("SNYK_RESULT"), True))

    return gates


def build_findings():
    """Normaliza el SARIF de Trivy al formato del contrato, deduplicado por fingerprint."""
    sarif_path = env("SARIF_PATH")
    if not sarif_path or not os.path.exists(sarif_path):
        return []

    with open(sarif_path, encoding="utf-8") as f:
        sarif = json.load(f)

    level_to_severity = {"error": "high", "warning": "medium", "note": "low", "none": "info"}
    trivy_severity = {"critical", "high", "medium", "low", "unknown"}
    seen = {}
    for run in sarif.get("runs", []):
        tool = run.get("tool", {}).get("driver", {}).get("name", "unknown")

        # Trivy pone la severidad real (CRITICAL/HIGH/MEDIUM/LOW) como tag de la
        # regla, no del resultado - el "level" generico de SARIF colapsa CRITICAL
        # y HIGH en el mismo "error", y CRITICAL es justo el umbral que bloquea
        # el gate, asi que hay que resolverla via las rules, no via el result.
        rule_severity, rule_cwe = {}, {}
        for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
            rid = rule.get("id")
            for tag in (rule.get("properties") or {}).get("tags", []):
                low = tag.lower()
                if low in trivy_severity:
                    rule_severity[rid] = "info" if low == "unknown" else low
                elif tag.upper().startswith("CWE"):
                    rule_cwe[rid] = tag

        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")
            severity = rule_severity.get(
                rule_id, level_to_severity.get(result.get("level", "warning"), "medium")
            )

            locations = result.get("locations", [])
            file_path = "unknown"
            if locations:
                file_path = (
                    locations[0]
                    .get("physicalLocation", {})
                    .get("artifactLocation", {})
                    .get("uri", "unknown")
                )

            cwe = rule_cwe.get(rule_id, "")
            if not cwe:
                props = result.get("properties") or {}
                for tag in props.get("tags", []):
                    if tag.upper().startswith("CWE"):
                        cwe = tag
                        break

            # sha256(rule_id + path normalizado + cwe) - nunca incluye numero de linea,
            # asi el mismo hallazgo no cambia de fingerprint si el archivo crece/encoge.
            basis = f"{rule_id}|{file_path}|{cwe}"
            fingerprint = hashlib.sha256(basis.encode("utf-8")).hexdigest()
            seen[fingerprint] = {
                "fingerprint": fingerprint,
                "tool": tool,
                "rule_id": rule_id,
                "cwe": cwe,
                "severity": severity,
                "path": file_path,
                "status": "open",
            }

    return list(seen.values())


def build_timings():
    finished_at = datetime.now(timezone.utc)
    started_raw = env("STARTED_AT")
    try:
        started_at = (
            datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
            if started_raw
            else finished_at
        )
    except ValueError:
        started_at = finished_at

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return {
        "queued_at": started_at.strftime(fmt),
        "started_at": started_at.strftime(fmt),
        "finished_at": finished_at.strftime(fmt),
        "duration_s": max((finished_at - started_at).total_seconds(), 0.0),
    }


def build_artifact():
    artifact_id = env("ARTIFACT_ID")
    image = env("CONTAINER_IMAGE")
    digest = env("CONTAINER_DIGEST")

    if image and digest:
        # Java - OpenShift (Microservicios/Aplicaciones): imagen real publicada en este mismo run,
        # el digest es el hash real de lo que se subio - no hace falta derivarlo de nada.
        return {
            "id": artifact_id,
            "coordinates": f"{image}@{digest}",
            "version": env("COMMIT_SHA")[:7],
            "sha256": digest.removeprefix("sha256:"),
            "registry_url": f"https://{image}",
            # attestation real (Sprint 3, attest-build-provenance) sigue pendiente incluso para
            # apps con contenedor - el sufijo deja claro que no es una URL real todavia.
            "attestation_url": f"https://{image}/pending-sprint3-attestation",
        }

    return {
        "id": artifact_id,
        "coordinates": f"{env('APP')}@{env('COMMIT_SHA')[:7]}",
        "version": env("COMMIT_SHA")[:7],
        # "Publish Artifact" sigue siendo un placeholder (Sprint 3 punto 1: attest-build-provenance).
        # Estos dos campos son sinteticos hasta que exista publicacion inmutable real con hash del
        # binario publicado; hoy son derivados de artifact_id solo para poder cumplir el contrato.
        "sha256": hashlib.sha256(artifact_id.encode("utf-8")).hexdigest(),
        "registry_url": "https://registry.acmebank-021.internal/pending-sprint3",
        "attestation_url": "https://registry.acmebank-021.internal/pending-sprint3/attestation",
    }


def build_source():
    repo_full = env("REPO_FULL")
    repo_name = repo_full.split("/")[-1] if "/" in repo_full else repo_full
    return {
        "org": env("ORG"),
        "repo": repo_name,
        "commit_sha": env("COMMIT_SHA"),
        "ref": env("REF"),
        "run_id": env("RUN_ID"),
    }


def main():
    payload = {
        "schema_version": "0.1.0",
        "correlation_id": str(uuid.uuid4()),
        "source": build_source(),
        "artifact": build_artifact(),
        "gates": build_gates(),
        "findings": build_findings(),
        "timings": build_timings(),
        "verdict": env("VERDICT"),
    }

    with open("rop-payload.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print("::group::ROP payload (schemas/rop-payload.v0.json)")
    print(json.dumps(payload, indent=2))
    print("::endgroup::")


if __name__ == "__main__":
    main()
