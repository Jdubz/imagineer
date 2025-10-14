variable "cloudflare_api_token" {
  description = "Cloudflare API token with DNS and Firewall edit permissions"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Root domain name (e.g., example.com)"
  type        = string
}

variable "api_subdomain" {
  description = "Subdomain for API endpoint"
  type        = string
  default     = "api"
}

variable "tunnel_id" {
  description = "Cloudflare Tunnel ID (get from: cloudflared tunnel list)"
  type        = string
}

variable "enable_geo_blocking" {
  description = "Enable geographic blocking for high-risk countries"
  type        = bool
  default     = false
}

variable "enable_cloudflare_access" {
  description = "Enable Cloudflare Access for additional authentication layer"
  type        = bool
  default     = false
}

variable "enable_logpush" {
  description = "Enable Cloudflare Logpush for log aggregation"
  type        = bool
  default     = false
}

variable "logpush_destination" {
  description = "Logpush destination (e.g., s3://bucket-name/path)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
}
