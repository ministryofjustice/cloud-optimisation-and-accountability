FROM maven:3.9.9-eclipse-temurin-17 AS build
COPY src /home/app/src
COPY pom.xml /home/app
RUN mvn -f /home/app/pom.xml clean package

FROM apache/spark:3.5.5-java17
COPY --from=build /home/app/target/coat-reports-1.0.jar /usr/local/lib/coat-reports-1.0.jar
