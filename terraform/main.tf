terraform {
  required_version = ">= 1.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }

  # Optional: Use remote state (uncomment when ready)
  # backend "s3" {
  #   bucket = "imagineer-terraform-state"
  #   key    = "production/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Data source: Get zone ID from domain
data "cloudflare_zone" "main" {
  name = var.domain
}

# DNS Record: API subdomain CNAME to Cloudflare Tunnel
resource "cloudflare_record" "api" {
  zone_id = data.cloudflare_zone.main.id
  name    = var.api_subdomain
  value   = "${var.tunnel_id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true
  comment = "Imagineer API - Managed by Terraform"
}

# Firewall Rule: Rate limiting for API endpoints
resource "cloudflare_rate_limit" "api_generation" {
  zone_id = data.cloudflare_zone.main.id

  threshold = 10
  period    = 60

  match {
    request {
      url_pattern = "${var.api_subdomain}.${var.domain}/api/generate*"
    }
  }

  action {
    mode    = "challenge"
    timeout = 3600
  }

  description = "Rate limit image generation endpoints"
}

# Firewall Rule: Rate limiting for auth endpoints
resource "cloudflare_rate_limit" "api_auth" {
  zone_id = data.cloudflare_zone.main.id

  threshold = 5
  period    = 60

  match {
    request {
      url_pattern = "${var.api_subdomain}.${var.domain}/api/auth/login"
    }
  }

  action {
    mode    = "block"
    timeout = 3600
  }

  description = "Rate limit login attempts"
}

# WAF Custom Rule: Block bad bots
resource "cloudflare_ruleset" "waf_custom" {
  zone_id     = data.cloudflare_zone.main.id
  name        = "Imagineer API Protection"
  description = "Custom WAF rules for Imagineer API"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  rules {
    action = "challenge"
    expression = "(cf.bot_management.score lt 30) and (http.host eq \"${var.api_subdomain}.${var.domain}\")"
    description = "Challenge low-score bots on API"
    enabled = true
  }

  rules {
    action = "block"
    expression = "(http.host eq \"${var.api_subdomain}.${var.domain}\") and (ip.geoip.country in {\"CN\" \"RU\" \"KP\"})"
    description = "Block high-risk countries (adjust as needed)"
    enabled = var.enable_geo_blocking
  }
}

# Page Rule: Security headers for API
resource "cloudflare_page_rule" "api_security_headers" {
  zone_id = data.cloudflare_zone.main.id
  target  = "${var.api_subdomain}.${var.domain}/*"
  priority = 1

  actions {
    security_level = "high"
    ssl            = "strict"

    # Enable Bot Fight Mode
    browser_check = "on"
  }
}

# Access Application: Optional - Add Cloudflare Access for extra security
resource "cloudflare_access_application" "api" {
  count = var.enable_cloudflare_access ? 1 : 0

  zone_id                   = data.cloudflare_zone.main.id
  name                      = "Imagineer API"
  domain                    = "${var.api_subdomain}.${var.domain}"
  type                      = "self_hosted"
  session_duration          = "24h"
  auto_redirect_to_identity = false

  # Optional: Add allowed email domains
  # allowed_idps = [var.cloudflare_access_idp]
}

# Logpush Job: Optional - Send logs to storage
resource "cloudflare_logpush_job" "api_logs" {
  count = var.enable_logpush ? 1 : 0

  zone_id         = data.cloudflare_zone.main.id
  name            = "Imagineer API Logs"
  enabled         = true
  dataset         = "http_requests"
  destination_conf = var.logpush_destination

  filter = "(http.host eq \"${var.api_subdomain}.${var.domain}\")"

  output_options {
    field_names = [
      "ClientIP",
      "ClientRequestHost",
      "ClientRequestMethod",
      "ClientRequestURI",
      "EdgeEndTimestamp",
      "EdgeResponseBytes",
      "EdgeResponseStatus",
      "EdgeStartTimestamp",
      "RayID"
    ]
  }
}

# Tunnel Configuration (documentation only - create via CLI)
# The Cloudflare Tunnel itself must be created via CLI:
# cloudflared tunnel create imagineer-api
#
# Then configure with terraform/cloudflare-tunnel.yml
# and start with: cloudflared tunnel run imagineer-api
