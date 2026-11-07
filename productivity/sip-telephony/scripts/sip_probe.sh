#!/usr/bin/env bash
# SIP probe: reachability -> digest auth -> optional REGISTER.
# Requires: sipsak (apt-get install -y sipsak)
# Credentials are read from a 0600 env file, never from argv or chat.
#   $HERMES_HOME/sip.env  (or ~/.hermes/.env) with:
#     SIP_SERVER   host or host:port of the registrar/server (no "sip:")
#     SIP_PROXY    optional, probed too when set
#     SIP_USER     SIP username
#     SIP_PASSWORD SIP password
#     SIP_NUMBER   DID in E.164, optional (defaults to SIP_USER)
# Usage: bash scripts/sip_probe.sh [--register]
# Never prints the password.
set -u
ENVF="${HERMES_HOME:-$HOME/.hermes}/sip.env"
[ -f "$ENVF" ] || ENVF="${HERMES_HOME:-$HOME/.hermes}/.env"
[ -f "$ENVF" ] && set -a && . "$ENVF" && set +a

: "${SIP_SERVER:?SIP_SERVER missing}"
SRV="${SIP_SERVER#sip:}"; SRV="${SRV%%;*}"
PROXY="${SIP_PROXY:-}"; PROXY="${PROXY#sip:}"; PROXY="${PROXY%%;*}"
USER_="${SIP_USER:?SIP_USER missing}"
PASS_="${SIP_PASSWORD:?SIP_PASSWORD missing}"
NUM="${SIP_NUMBER:-$USER_}"

echo "== number in use: $NUM"

probe_host() {  # $1 = host[:port]
  local h="$1" port=5060
  case "$h" in *:*) port="${h##*:}"; h="${h%%:*}";; esac
  echo "-- host: $h (port $port)"
  echo "   DNS: $(dig +short "$h" | tr '\n' ' ')"
  timeout 5 bash -c "cat < /dev/null > /dev/tcp/$h/$port" 2>/dev/null \
    && echo "   TCP $port: open" || echo "   TCP $port: closed/not offered"
  timeout 5 bash -c "cat < /dev/null > /dev/tcp/$h/5061" 2>/dev/null \
    && echo "   TCP 5061 (TLS): open" || echo "   TCP 5061 (TLS): closed/not offered"
  echo "   unauth OPTIONS:"
  sipsak -s "sip:$h" -H 6 2>&1 | sed -n '1,3p'
}

echo "== 1) reachability"
probe_host "$SRV"
[ -n "$PROXY" ] && probe_host "$PROXY"

echo "== 2) authenticated OPTIONS against sip:$USER_@$SRV"
sipsak -s "sip:$USER_@$SRV" -u "$USER_" -a "$PASS_" -H 6 2>&1 | sed -n '1,4p'

if [ "${1:-}" = "--register" ]; then
  echo "== 3) REGISTER (expires 60s), then unregister so no stale registration is left"
  sipsak -s "sip:$USER_@$SRV" -u "$USER_" -a "$PASS_" -x 60 -H 8 2>&1 | sed -n '1,6p'
  sipsak -U -s "sip:$USER_@$SRV" -u "$USER_" -a "$PASS_" -H 8 2>&1 | sed -n '1,4p'
  echo "-- next decisive test (not covered by sipsak): an authenticated INVITE from a client that never registered,"
  echo "   e.g. pjsua/baresip, to see whether a hosted BYO-SIP platform can dial this provider at all."
fi
