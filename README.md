# openshift-springboot-pipeline

Base v2 del laboratorio de Java/OpenShift — sucesor de `openshift-tomcat-demo`,
con los ajustes que salieron de comparar el laboratorio contra la evidencia
real de Banamex (fotos del 18-sep-2026, ver memoria `banamex_evidencia_docker_openshift_real`).

## Qué cambió respecto a `openshift-tomcat-demo`

1. **Un solo app por repo, en la raíz** (no monorepo con `apps/<nombre>/`) —
   así vive un app real en el banco, ya no hace falta el input `app_path`.
2. **`build` y `unit-test` se fusionaron en un solo job (`build-and-test`)** —
   nunca corrían en paralelo de verdad (`unit-test` siempre esperaba a
   `build` y descargaba su jar), así que separarlos solo pagaba dos arranques
   de máquina en vez de uno. GitHub Actions factura por minutos de CADA job,
   no por el reloj total del pipeline — fusionarlos reduce el costo sin
   perder tiempo real de espera.
3. **`sonar-analysis` ya no levanta un SonarQube local en Docker** — apunta
   directo a SonarCloud (servidor real, persistente), igual que el banco
   apunta a su propio `sonarqube04.nam.nsroot.net` en vez de crear uno nuevo
   por corrida. Esto quita ~40 líneas de arranque de contenedor, rotación de
   contraseña y generación de token a mano.
4. **`Dockerfile` multi-stage con usuario no-root (`1001`) y puerto `8443`** —
   replica el patrón real de los dos Dockerfile vistos en las fotos (CSI
   171097), con la sintaxis nueva de Spring Boot (`-Djarmode=tools`, la real
   del banco usa la deprecada `-Djarmode=layertools`). Usa imágenes públicas
   de Eclipse Temurin en vez de las internas del banco
   (`binaryrepo.nam.nsroot.net/...`), a las que no tenemos acceso.
5. El registro de imágenes sigue siendo `ghcr.io` (simulado) — JFrog
   Artifactory real pide tarjeta de crédito en su plan gratuito, así que esa
   parte se sigue simulando hasta que el banco dé acceso real.

## Antes de que el pipeline corra de verdad

- Configurar el Environment `ci-secrets` (Settings → Environments) con
  `SONAR_TOKEN` (de tu cuenta de SonarCloud) y, si se habilita, `SNYK_TOKEN`.
- Poner la clave de tu organización de SonarCloud en `ci.yml`
  (`sonar_organization:`).

## Las 3 capas

| Capa | Archivo | Qué hace |
|---|---|---|
| Capa 1 | `.github/workflows/capa1-java.yml` | Compila+prueba (fusionado), Sonar (real, SonarCloud), Trivy+Snyk, gitleaks, veredicto, payload a ROP, imagen de contenedor si aplica |
| Capa 2 | `.github/workflows/capa2-java-gradle.yml` | Valida catálogo de JDK aprobado, invoca Capa 1 |
| Capa 3 | `.github/workflows/ci.yml` | El manifiesto delgado — lo único que un equipo de aplicación real escribiría |

Piezas compartidas sin cambios: `actions/` y `schemas/rop-payload.v0.json`.
