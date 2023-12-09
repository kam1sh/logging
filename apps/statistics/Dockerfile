FROM docker.io/library/eclipse-temurin:17-jre-jammy AS build
WORKDIR /app
COPY . .
RUN ./gradlew install

FROM docker.io/library/eclipse-temurin:17-jre-jammy
COPY --from=build /app/build/install/statistics /app
CMD /app/bin/statistics 2>&1 > /logs/statistics.json
