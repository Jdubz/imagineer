output "api_url" {
  description = "Full API URL"
  value       = "https://${var.api_subdomain}.${var.domain}"
}

output "zone_id" {
  description = "Cloudflare Zone ID"
  value       = data.cloudflare_zone.main.id
}

output "dns_record_id" {
  description = "API DNS record ID"
  value       = cloudflare_record.api.id
}

output "rate_limit_ids" {
  description = "Rate limit rule IDs"
  value = {
    generation = cloudflare_rate_limit.api_generation.id
    auth       = cloudflare_rate_limit.api_auth.id
  }
}

output "deployment_checklist" {
  description = "Next steps after Terraform apply"
  value = <<-EOT
    ✅ Terraform configuration applied successfully!

    Next steps:
    1. Create Cloudflare Tunnel (if not already created):
       cloudflared tunnel create imagineer-api

    2. Configure tunnel:
       Edit terraform/cloudflare-tunnel.yml with tunnel ID

    3. Start tunnel service:
       sudo systemctl start cloudflared-imagineer

    4. Verify API is accessible:
       curl https://${var.api_subdomain}.${var.domain}/api/health

    5. Deploy frontend to Firebase:
       make deploy-frontend-prod
  EOT
}
