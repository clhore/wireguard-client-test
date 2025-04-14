FROM golang:1.24.1 AS builder

WORKDIR /srv
COPY ./srv/ ./

RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o wireguard-client ./cmd/main.go

#####################################################################################

FROM alpine:3.21.3

RUN apk add --no-cache wireguard-tools \
    iputils-ping && \
    rm -rf /var/cache/apk/* && \
    rm -rf /var/lib/apk/lists/*

RUN mkdir -p /etc/wireguard

WORKDIR /root/

COPY --from=builder /srv/wireguard-client .
COPY setup.sh /root/setup.sh

RUN chmod +x /root/setup.sh

CMD ["/root/setup.sh"]