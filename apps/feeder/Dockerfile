FROM docker.io/library/golang:1.20-alpine AS build
WORKDIR /build
COPY . .
RUN go build .

FROM docker.io/library/alpine:latest
COPY --from=build /build/feeder /
CMD /feeder
