import glob
import os
import sys
import xml.etree.ElementTree as ET


def read_test_results(reports_path):
    """Lee reportes de resultados de pruebas en formato JUnit XML.

    Lo produce Surefire (Java) y jest-junit (Node) con un <testsuite> suelto
    como raiz, con los atributos tests/failures/errors ahi mismo. pytest
    --junitxml (Python), en cambio, envuelve eso en un <testsuites> (el
    formato "xunit2", default desde hace varias versiones) - la raiz queda
    vacia y los atributos reales viven en el/los <testsuite> de adentro. Se
    manejan ambas formas explicitamente en vez de asumir una sola.
    """
    total_tests = 0
    total_failures = 0
    total_errors = 0

    for f in glob.glob(os.path.join(reports_path, "**", "*.xml"), recursive=True):
        root = ET.parse(f).getroot()
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        for suite in suites:
            total_tests += int(suite.attrib.get("tests", 0))
            total_failures += int(suite.attrib.get("failures", 0))
            total_errors += int(suite.attrib.get("errors", 0))

    if total_tests == 0:
        return 0.0, total_tests, total_failures, total_errors

    success_density = (total_tests - total_failures - total_errors) / total_tests * 100
    return success_density, total_tests, total_failures, total_errors


def read_coverage(coverage_xml_path):
    """Lee cobertura de lineas desde JaCoCo (Java) o Cobertura XML (Node,
    Python) - son los dos esquemas mas comunes, y se distinguen por el
    nombre del elemento raiz del XML.
    """
    if not os.path.isfile(coverage_xml_path):
        return 0.0, 0, 0

    root = ET.parse(coverage_xml_path).getroot()

    if root.tag == "report":
        # JaCoCo: <report><counter type="LINE" covered="X" missed="Y"/></report>
        covered = 0
        missed = 0
        for counter in root.findall("counter"):
            if counter.attrib.get("type") == "LINE":
                covered = int(counter.attrib.get("covered", 0))
                missed = int(counter.attrib.get("missed", 0))
        total = covered + missed

    elif root.tag == "coverage":
        # Cobertura: <coverage lines-covered="X" lines-valid="Y" ...>
        covered = int(float(root.attrib.get("lines-covered", 0)))
        total = int(float(root.attrib.get("lines-valid", 0)))
        missed = total - covered

    else:
        raise ValueError(f"Formato de cobertura desconocido: raiz <{root.tag}>")

    coverage = (covered / total * 100) if total > 0 else 0.0
    return coverage, covered, missed


def main():
    surefire_path = sys.argv[1]
    jacoco_xml_path = sys.argv[2]
    coverage_min = float(sys.argv[3])
    success_density_min = float(sys.argv[4])
    hard_gating = sys.argv[5].strip().lower() == "true"

    success_density, tests, failures, errors = read_test_results(surefire_path)
    coverage, covered, missed = read_coverage(jacoco_xml_path)

    coverage_ok = coverage >= coverage_min
    density_ok = success_density >= success_density_min
    status = "pass" if (coverage_ok and density_ok) else "fail"

    print("== Quality Gate ==")
    print(f"Pruebas: {tests} totales, {failures} fallidas, {errors} con error")
    print(
        f"Densidad de exito: {success_density:.1f}% "
        f"(minimo {success_density_min}%) -> {'OK' if density_ok else 'FALLA'}"
    )
    print(
        f"Cobertura de lineas: {coverage:.1f}% ({covered} cubiertas / {missed} sin cubrir) "
        f"(minimo {coverage_min}%) -> {'OK' if coverage_ok else 'FALLA'}"
    )
    print(f"hard_gating={hard_gating}")
    print(f"Veredicto del gate: {status}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"coverage={coverage:.1f}\n")
            fh.write(f"success_density={success_density:.1f}\n")
            fh.write(f"status={status}\n")

    if hard_gating and status == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
