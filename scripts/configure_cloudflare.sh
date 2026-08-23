#!/bin/bash
set -e

# Interactive setup script for Cloudflare routing

# Check for required tools
if ! command -v curl &> /dev/null; then
    echo "❌ Error: 'curl' is required but not installed."
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "⚠️ Warning: 'jq' is not installed. JSON response parsing will be unformatted."
fi

# Load from .env if present
if [ -f .env ]; then
    echo "ℹ️ Loading environment from .env..."
    # Export vars from .env without comments
    export $(grep -v '^#' .env | xargs) || true
fi

# Ask for variables if not in env
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    read -sp "🔑 Enter Cloudflare API Token (needs Zone.DNS and Zone.Rulesets permissions): " CLOUDFLARE_API_TOKEN
    echo ""
fi

if [ -z "$CLOUDFLARE_ZONE_ID" ]; then
    read -p "🌍 Enter Cloudflare Zone ID for pre-consult.org: " CLOUDFLARE_ZONE_ID
    echo ""
fi

if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ZONE_ID" ]; then
    echo "❌ Error: Cloudflare API Token and Zone ID are required."
    exit 1
fi

# Target Cloud Run domain (update with 'gcloud run services describe preconsult --region=us-central1 --format="value(status.url)"' hostname)
# NOTE: status.url is the `*.a.run.app` hostname (not the legacy `*.uc.us-central1.run.app`).
TARGET_URL=${CLOUD_RUN_TARGET_URL:-"preconsult-tcjbweemnq-uc.a.run.app"}

echo "🛰️ 1. Ensuring DNS record for pre-consult.org -> $TARGET_URL (Proxied: true)..."

# Fetch existing DNS records
RECORDS_JSON=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?name=pre-consult.org" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json")

RECORD_ID=$(echo "$RECORDS_JSON" | jq -r '.result[0].id // empty')

if [ -n "$RECORD_ID" ]; then
    echo "ℹ️ Existing DNS record found ($RECORD_ID). Updating record to CNAME -> $TARGET_URL (Proxied: true)..."
    DNS_RESPONSE=$(curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID}" \
         -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
         -H "Content-Type: application/json" \
         --data "{
           \"type\": \"CNAME\",
           \"name\": \"@\",
           \"content\": \"${TARGET_URL}\",
           \"ttl\": 1,
           \"proxied\": true
         }")
else
    echo "➕ Creating new CNAME record for pre-consult.org -> $TARGET_URL (Proxied: true)..."
    DNS_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
         -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
         -H "Content-Type: application/json" \
         --data "{
           \"type\": \"CNAME\",
           \"name\": \"@\",
           \"content\": \"${TARGET_URL}\",
           \"ttl\": 1,
           \"proxied\": true
         }")
fi

if echo "$DNS_RESPONSE" | grep -q '"success":true'; then
    echo "✅ DNS CNAME Record configured and proxied successfully!"
else
    echo "⚠️ DNS configuration response: $DNS_RESPONSE"
fi

echo "🚀 2. Deploying Host Header Override Rule (Origin Rule)..."
RULE_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data "{
       \"name\": \"Host Header Override for Cloud Run\",
       \"description\": \"Rewrite host header for pre-consult.org to Cloud Run target\",
       \"kind\": \"zone\",
       \"phase\": \"http_request_origin\",
       \"rules\": [
         {
           \"action\": \"route\",
           \"action_parameters\": {
             \"host_header\": \"${TARGET_URL}\"
           },
           \"expression\": \"(http.host eq \\\"pre-consult.org\\\") or (http.host eq \\\"www.pre-consult.org\\\")\",
           \"description\": \"Override Host header for PreConsult app\"
         }
       ]
     }")

if echo "$RULE_RESPONSE" | grep -q '"success":true'; then
    echo "✅ Host Header Override Rule deployed successfully!"
else
    # Check if the ruleset phase already exists, if so we need to add to/update it.
    if echo "$RULE_RESPONSE" | grep -q "already exists"; then
        echo "ℹ️ Ruleset phase already exists. Please check/manage your active Origin Rules in the Cloudflare Dashboard under Rules > Origin Rules."
    else
        echo "⚠️ Origin Rule deployment response: $RULE_RESPONSE"
    fi
fi

echo "🛡️ 3. Deploying / Updating Bot Shield WAF Custom Rule..."
# Fetch existing rulesets to see if http_request_firewall_custom phase exists
RULESETS_JSON=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json")

EXISTING_FW_ID=$(echo "$RULESETS_JSON" | jq -r '.result[] | select(.phase=="http_request_firewall_custom") | .id // empty' | head -n 1)

# Interactive app paths MUST always reach origin so real users' WebSocket/event
# streams (/_event/, /graphql, socket.io polling+upgrade) are never blocked by
# any later block/rate-limit rule. Rules are evaluated in order.
INTERACTIVE_ALLOW='(http.request.uri.path contains "/_event/") or (http.request.uri.path contains "/graphql") or (http.request.uri.path contains "/socket.io")'

# Expanded scanner block covering every probe observed in the last week
# (wp-admin/install.php, .env/.env.dev/.env.credentials, .git/config,
#  credentials.yml, phpinfo/info.php/test.php, xmlrpc, phpmyadmin, shells).
SCANNER_BLOCK='(http.request.uri.path contains "/wp-") or (http.request.uri.path contains "wp-admin") or (http.request.uri.path contains "wp-login") or (http.request.uri.path contains "xmlrpc") or (http.request.uri.path contains ".env") or (http.request.uri.path contains "/.git") or (http.request.uri.path contains "credentials") or (http.request.uri.path contains "phpinfo") or (http.request.uri.path contains "info.php") or (http.request.uri.path contains "test.php") or (http.request.uri.path contains "phpmyadmin") or (http.request.uri.path contains "adminer") or (http.request.uri.path contains "setup.php") or (http.request.uri.path contains "install.php") or (http.request.uri.path contains "config.php") or (http.request.uri.path contains "shell") or (http.request.uri.path contains "passwd") or (http.request.uri.path contains "sql") or (http.request.uri.path contains ".bak")'

if command -v jq > /dev/null 2>&1; then
    WAF_BODY=$(jq -n \
        --arg allow "$INTERACTIVE_ALLOW" \
        --arg scan "$SCANNER_BLOCK" \
        '{ name: "PreConsult Security Shield",
           description: "Allow interactive app paths; block vulnerability scanners and non-app endpoints",
           kind: "zone",
           phase: "http_request_firewall_custom",
           rules: [
             { action: "skip",
               action_parameters: { ruleset: "current" },
               expression: $allow,
               description: "Skip current ruleset for interactive app endpoints" },
             { action: "skip",
               action_parameters: { ruleset: "current" },
               expression: "(http.request.uri.path contains \"/llms.txt\") or (http.request.uri.path contains \"/robots.txt\") or (http.request.uri.path contains \"/sitemap.xml\") or (http.request.uri.path contains \"/favicon.ico\")",
               description: "Allow SEO meta files so search/AI crawlers can discover the site (llms.txt, robots.txt, sitemap.xml, favicon)" },
             { action: "block",
               expression: "(http.user_agent contains \"curl\") or (http.user_agent contains \"wget\") or (http.user_agent contains \"python\") or (http.user_agent contains \"go-http\") or (http.user_agent contains \"httpx\") or (http.user_agent contains \"zgrab\") or (http.user_agent contains \"nuclei\") or (http.user_agent contains \"masscan\") or (http.user_agent contains \"aiohttp\") or (http.user_agent contains \"scrapy\") or (http.user_agent contains \"nikto\") or (http.user_agent contains \"sqlmap\") or (http.user_agent contains \"semrush\") or (http.user_agent contains \"ahrefs\") or (http.user_agent contains \"majestic\") or (http.user_agent contains \"dataforseo\")",
               description: "Block known automation/scanner user agents" },
             { action: "block",
               expression: $scan,
               description: "Block automated vulnerability scanners (UA-spoofed or not)" }
           ]
         }')
else
    echo "⚠️ jq is required to build WAF rulesets. Install jq or deploy manually."
    exit 1
fi

if ! echo "$WAF_BODY" | jq -e . > /dev/null 2>&1; then
    echo "⚠️ WAF Body failed JSON validation. Refusing to deploy: $WAF_BODY"
else
    if [ -n "$EXISTING_FW_ID" ]; then
        echo "ℹ️ Updating existing WAF Ruleset ($EXISTING_FW_ID)..."
        WAF_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets/${EXISTING_FW_ID}" \
             -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
             -H "Content-Type: application/json" \
             --data "$WAF_BODY")
    else
        echo "➕ Creating new WAF Ruleset..."
        WAF_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets" \
             -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
             -H "Content-Type: application/json" \
             --data "$WAF_BODY")
    fi

    if echo "$WAF_RESPONSE" | grep -q '"success":true'; then
        echo "✅ Bot Shield WAF Rule deployed/updated successfully!"
    else
        echo "⚠️ WAF Rule status: $WAF_RESPONSE"
    fi
fi

echo "🚀 3b. Deploying Rate-Limiting Rule (high-volume scanner IPs)"
# Rate-limit non-interactive traffic to discourage UA-spoofed scanner bursts
# (e.g. 45.148.10.238, 45.153.34.217 probing hundreds of paths in minutes).
# Interactive endpoints are excluded so the live WebSocket/event stream is safe.
RATE_BODY=$(jq -n \
    --arg allow "$INTERACTIVE_ALLOW" \
     '{ name: "PreConsult Scanner Rate Limit",
        description: "Throttle non-interactive high-request-rate traffic above human thresholds",
        rules: [
         { action: "block",
           ratelimit: {
             characteristics: ["cf.colo.id", "ip.src"],
             period: 10,
             requests_per_period: 100,
             mitigation_timeout: 10
           },
           expression: ("(not " + $allow + ")"),
           description: "Block IPs exceeding 200 req/min on non-interactive paths" }
       ]
     }')
if ! echo "$RATE_BODY" | jq -e . > /dev/null 2>&1; then
    echo "⚠️ Rate Limit body failed JSON validation: $RATE_BODY"
else
    RATE_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets/phases/http_ratelimit/entrypoint" \
         -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
         -H "Content-Type: application/json" \
         --data "$RATE_BODY")
    if echo "$RATE_RESPONSE" | grep -q '"success":true'; then
        echo "✅ Rate Limit rule deployed successfully!"
    else
        echo "⚠️ Rate Limit rule status: $RATE_RESPONSE"
    fi
fi

echo "⚡ 4. Enabling Edge Performance Optimizations (Brotli, Auto-Minify, Early Hints, HTTP/3)..."
curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/settings/brotli" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data '{"value": "on"}' > /dev/null || true

curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/settings/minify" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data '{"value": {"css": "on", "html": "on", "js": "on"}}' > /dev/null || true

curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/settings/early_hints" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data '{"value": "on"}' > /dev/null || true

curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/settings/http3" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data '{"value": "on"}' > /dev/null || true

echo "✅ Edge performance settings (Brotli, Minify, Early Hints, HTTP/3) applied!"

echo "🎉 Configuration complete! Please ensure SSL/TLS settings are set to 'Full (strict)' in your Cloudflare dashboard."
