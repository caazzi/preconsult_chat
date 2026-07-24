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
TARGET_URL=${CLOUD_RUN_TARGET_URL:-"preconsult-811607528687.us-central1.run.app"}

echo "🛰️ 1. Creating CNAME record for pre-consult.org -> $TARGET_URL (Proxied)..."
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

if echo "$DNS_RESPONSE" | grep -q '"success":true'; then
    echo "✅ DNS CNAME Record created successfully!"
else
    echo "⚠️ DNS creation response: $DNS_RESPONSE"
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

echo "🛡️ 3. Deploying Bot Shield WAF Custom Rule..."
WAF_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     --data "{
       \"name\": \"PreConsult Security Shield\",
       \"description\": \"Block vulnerability scanners targeting wp-admin, .env, and non-app endpoints\",
       \"kind\": \"zone\",
       \"phase\": \"http_request_firewall_custom\",
       \"rules\": [
         {
           \"action\": \"block\",
           \"expression\": \"(http.request.uri.path contains \\\"/wp-\\\") or (http.request.uri.path contains \\\".env\\\") or (http.request.uri.path contains \\\"xmlrpc\\\") or (http.request.uri.path contains \\\"phpmyadmin\\\")\",
           \"description\": \"Block automated vulnerability scanners\"
         }
       ]
     }")

if echo "$WAF_RESPONSE" | grep -q '"success":true'; then
    echo "✅ Bot Shield WAF Rule deployed successfully!"
else
    echo "ℹ️ WAF Rule status: $WAF_RESPONSE"
fi

echo "🎉 Configuration complete! Please ensure SSL/TLS settings are set to 'Full (strict)' in your Cloudflare dashboard."
