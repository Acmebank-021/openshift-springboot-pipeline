# Multi-stage "layered jar" - replica el patron real visto en los Dockerfile
# de Banamex (CSI 171097), usando imagenes publicas de Eclipse Temurin en vez
# de las internas del banco (binaryrepo.nam.nsroot.net/.../oracle-jdk-rhel8),
# a las que no tenemos acceso desde el laboratorio.
FROM eclipse-temurin:17-jdk AS builder
WORKDIR /builder
COPY build/libs/*.jar app.jar
# Sintaxis nueva (Spring Boot 3.2+). La real del banco usaba "-Djarmode=layertools",
# que Spring Boot ya marca como deprecada en runtime - "-Djarmode=tools" es su
# reemplazo oficial.
RUN java -Djarmode=tools -jar app.jar extract --layers --launcher --destination extracted

FROM eclipse-temurin:17-jre
# Usuario fijo no-root (1001), mismo patron que ambos Dockerfile reales vistos -
# necesario porque OpenShift normalmente prohibe correr contenedores como root.
RUN useradd --uid 1001 --gid 0 --create-home appuser
WORKDIR /application
COPY --from=builder --chown=1001:0 /builder/extracted/dependencies/ ./
COPY --from=builder --chown=1001:0 /builder/extracted/spring-boot-loader/ ./
COPY --from=builder --chown=1001:0 /builder/extracted/snapshot-dependencies/ ./
COPY --from=builder --chown=1001:0 /builder/extracted/application/ ./
USER 1001
EXPOSE 8443
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
