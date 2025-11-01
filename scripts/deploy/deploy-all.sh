#!/bin/bash
# Comprehensive Deployment Orchestration Script for Imagineer
# Manages all deployment scripts for production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
WEB_DIR="$PROJECT_ROOT/web"

# Configuration
DRY_RUN=false
SKIP_CHECKS=false
DEPLOY_BACKEND=true
DEPLOY_TUNNEL=true
DEPLOY_INFRA=true
DEPLOY_FRONTEND=true

# Logging
LOG_FILE="$PROJECT_ROOT/logs/deployment-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$PROJECT_ROOT/logs"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local all_good=true

    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python3: $(python3 --version)"
    else
        print_error "Python3 not found"
        all_good=false
    fi

    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        print_success "Docker: $(docker --version | head -n1)"
    else
        print_warning "Docker not found (optional, systemd will be used)"
    fi

    # Check Docker Compose (optional)
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose: $(docker-compose --version)"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        print_success "Docker Compose (plugin): $(docker compose version)"
    else
        print_warning "Docker Compose not found (optional)"
    fi

    # Check Terraform
    if command -v terraform &> /dev/null; then
        print_success "Terraform: $(terraform version | head -n1)"
    else
        print_warning "Terraform not found (required for infrastructure deployment)"
        if [ "$DEPLOY_INFRA" = true ]; then
            all_good=false
        fi
    fi

    # Check cloudflared
    if command -v cloudflared &> /dev/null; then
        print_success "cloudflared: $(cloudflared --version 2>&1 | head -n1)"
    else
        print_warning "cloudflared not found (will be installed during tunnel setup)"
    fi

    # Check Firebase CLI
    if command -v firebase &> /dev/null; then
        print_success "Firebase CLI: $(firebase --version)"
    else
        print_warning "Firebase CLI not found (required for frontend deployment)"
        if [ "$DEPLOY_FRONTEND" = true ]; then
            print_status "Install with: npm install -g firebase-tools"
            all_good=false
        fi
    fi

    # Check Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node --version)"
    else
        print_warning "Node.js not found (required for frontend deployment)"
        if [ "$DEPLOY_FRONTEND" = true ]; then
            all_good=false
        fi
    fi

    # Check npm
    if command -v npm &> /dev/null; then
        print_success "npm: $(npm --version)"
    else
        print_warning "npm not found (required for frontend deployment)"
        if [ "$DEPLOY_FRONTEND" = true ]; then
            all_good=false
        fi
    fi

    # Check git
    if command -v git &> /dev/null; then
        print_success "git: $(git --version)"
    else
        print_error "git not found (required)"
        all_good=false
    fi

    if [ "$all_good" = false ]; then
        print_error "Some prerequisites are missing. Please install them before continuing."
        return 1
    fi

    print_success "All required prerequisites are installed"
    return 0
}

# Function to check configuration files
check_configuration() {
    print_header "Checking Configuration Files"

    local all_good=true

    # Check .env.production
    if [ -f "$PROJECT_ROOT/.env.production" ]; then
        print_success "Found .env.production"

        # Check for required variables
        if grep -q "FLASK_ENV=production" "$PROJECT_ROOT/.env.production"; then
            print_success "  FLASK_ENV is set to production"
        else
            print_warning "  FLASK_ENV is not set to production"
        fi

        if grep -q "WEBHOOK_SECRET=" "$PROJECT_ROOT/.env.production" && ! grep -q "WEBHOOK_SECRET=your-webhook-secret-here" "$PROJECT_ROOT/.env.production"; then
            print_success "  WEBHOOK_SECRET is configured"
        else
            print_warning "  WEBHOOK_SECRET is not configured (required for auto-deployment)"
        fi
    else
        print_warning ".env.production not found"
        print_status "  Copy from .env.production.example and configure"
        all_good=false
    fi

    # Check web/.env.production
    if [ -f "$WEB_DIR/.env.production" ]; then
        print_success "Found web/.env.production"

        if grep -q "VITE_API_BASE_URL=https://api.imagineer.joshwentworth.com/api" "$WEB_DIR/.env.production"; then
            print_success "  VITE_API_BASE_URL is configured"
        else
            print_warning "  VITE_API_BASE_URL may need updating"
        fi

        if grep -q "VITE_APP_PASSWORD=" "$WEB_DIR/.env.production"; then
            print_warning "  VITE_APP_PASSWORD is deprecated—remove it from web/.env.production"
        else
            print_success "  Deprecated VITE_APP_PASSWORD not present"
        fi
    else
        print_warning "web/.env.production not found"
        all_good=false
    fi

    # Check terraform.tfvars
    if [ -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
        print_success "Found terraform/terraform.tfvars"

        if grep -q "cloudflare_api_token.*YOUR.*TOKEN" "$TERRAFORM_DIR/terraform.tfvars"; then
            print_warning "  Cloudflare API token is not configured"
            all_good=false
        else
            print_success "  Cloudflare API token appears to be configured"
        fi

        if grep -q "tunnel_id.*YOUR.*TUNNEL.*ID" "$TERRAFORM_DIR/terraform.tfvars"; then
            print_warning "  Tunnel ID is not configured (will be set during tunnel setup)"
        else
            print_success "  Tunnel ID appears to be configured"
        fi
    else
        print_warning "terraform/terraform.tfvars not found"
        print_status "  Copy from terraform/terraform.tfvars.example and configure"
        all_good=false
    fi

    # Check .firebaserc
    if [ -f "$PROJECT_ROOT/.firebaserc" ]; then
        print_success "Found .firebaserc"
    else
        print_warning ".firebaserc not found"
        all_good=false
    fi

    if [ "$all_good" = false ]; then
        print_warning "Some configuration files are missing or incomplete"
        print_status "Please review and configure before continuing"
        return 1
    fi

    print_success "All configuration files are present"
    return 0
}

# Function to deploy backend
deploy_backend() {
    print_header "Deploying Backend (Production Server)"

    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would run: bash $SCRIPT_DIR/setup-production.sh"
        return 0
    fi

    if [ -f "$SCRIPT_DIR/setup-production.sh" ]; then
        print_status "Running production setup script..."
        bash "$SCRIPT_DIR/setup-production.sh"

        # Verify backend is running
        sleep 5
        if curl -f http://localhost:10050/api/health &> /dev/null; then
            print_success "Backend is running and healthy"
        else
            print_warning "Backend may not be running or health check failed"
            print_status "Check with: make prod-status"
        fi
    else
        print_error "setup-production.sh not found at $SCRIPT_DIR"
        return 1
    fi
}

# Function to deploy Cloudflare Tunnel
deploy_tunnel() {
    print_header "Deploying Cloudflare Tunnel"

    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would run: bash $SCRIPT_DIR/setup-cloudflare-tunnel-custom.sh"
        return 0
    fi

    if [ -f "$SCRIPT_DIR/setup-cloudflare-tunnel-custom.sh" ]; then
        print_status "Running Cloudflare Tunnel setup script..."
        bash "$SCRIPT_DIR/setup-cloudflare-tunnel-custom.sh"

        # Get tunnel ID
        if command -v cloudflared &> /dev/null; then
            TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "imagineer-api" | awk '{print $1}')
            if [ -n "$TUNNEL_ID" ]; then
                print_success "Tunnel ID: $TUNNEL_ID"

                # Update terraform.tfvars if it exists
                if [ -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
                    if grep -q "tunnel_id.*YOUR.*TUNNEL.*ID" "$TERRAFORM_DIR/terraform.tfvars"; then
                        print_status "Updating terraform.tfvars with tunnel ID..."
                        sed -i "s/tunnel_id = \"YOUR_TUNNEL_ID_HERE\"/tunnel_id = \"$TUNNEL_ID\"/" "$TERRAFORM_DIR/terraform.tfvars"
                        print_success "Updated terraform.tfvars"
                    fi
                fi
            fi
        fi

        # Verify tunnel is running
        if sudo systemctl is-active --quiet cloudflared-imagineer-api; then
            print_success "Cloudflare Tunnel service is active"
        else
            print_warning "Cloudflare Tunnel service may not be running"
            print_status "Check with: sudo systemctl status cloudflared-imagineer-api"
        fi
    else
        print_error "setup-cloudflare-tunnel-custom.sh not found at $SCRIPT_DIR"
        return 1
    fi
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying Cloudflare Infrastructure (Terraform)"

    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would run: cd $TERRAFORM_DIR && terraform init && terraform plan"
        return 0
    fi

    if [ ! -d "$TERRAFORM_DIR" ]; then
        print_error "Terraform directory not found at $TERRAFORM_DIR"
        return 1
    fi

    cd "$TERRAFORM_DIR"

    # Initialize Terraform
    print_status "Initializing Terraform..."
    if terraform init; then
        print_success "Terraform initialized"
    else
        print_error "Terraform initialization failed"
        return 1
    fi

    # Validate configuration
    print_status "Validating Terraform configuration..."
    if terraform validate; then
        print_success "Terraform configuration is valid"
    else
        print_error "Terraform validation failed"
        return 1
    fi

    # Plan
    print_status "Running Terraform plan..."
    if terraform plan -out=tfplan; then
        print_success "Terraform plan completed"
    else
        print_error "Terraform plan failed"
        return 1
    fi

    # Ask for confirmation
    echo ""
    read -p "Apply Terraform changes? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Applying Terraform changes..."
        if terraform apply tfplan; then
            print_success "Terraform apply completed"
            rm -f tfplan
        else
            print_error "Terraform apply failed"
            return 1
        fi
    else
        print_status "Skipping Terraform apply"
        rm -f tfplan
    fi

    cd "$PROJECT_ROOT"
}

# Function to deploy frontend
deploy_frontend() {
    print_header "Deploying Frontend (Firebase Hosting)"

    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would run: cd $WEB_DIR && npm ci && npm run build && firebase deploy"
        return 0
    fi

    if [ ! -d "$WEB_DIR" ]; then
        print_error "Web directory not found at $WEB_DIR"
        return 1
    fi

    cd "$WEB_DIR"

    # Install dependencies
    print_status "Installing frontend dependencies..."
    if npm ci; then
        print_success "Dependencies installed"
    else
        print_error "npm ci failed"
        return 1
    fi

    # Build
    print_status "Building frontend..."
    if npm run build; then
        print_success "Frontend built successfully"
    else
        print_error "Frontend build failed"
        return 1
    fi

    # Deploy to Firebase
    print_status "Deploying to Firebase Hosting..."
    if firebase deploy --only hosting:imagineer; then
        print_success "Frontend deployed to Firebase"
        print_status "URLs:"
        print_status "  - https://imagineer-generator.web.app"
        print_status "  - https://imagineer-generator.firebaseapp.com"
    else
        print_error "Firebase deployment failed"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# Function to run health checks
run_health_checks() {
    print_header "Running Health Checks"

    # Check local backend
    print_status "Checking local backend..."
    if curl -f http://localhost:10050/api/health &> /dev/null; then
        print_success "Local backend is healthy"
    else
        print_warning "Local backend health check failed"
    fi

    # Check Cloudflare Tunnel service
    print_status "Checking Cloudflare Tunnel service..."
    if sudo systemctl is-active --quiet cloudflared-imagineer-api; then
        print_success "Cloudflare Tunnel service is active"
    else
        print_warning "Cloudflare Tunnel service is not active"
    fi

    # Check public API (may need DNS propagation time)
    print_status "Checking public API endpoint..."
    if curl -f https://api.imagineer.joshwentworth.com/api/health &> /dev/null 2>&1; then
        print_success "Public API is accessible"
    else
        print_warning "Public API not accessible yet (DNS may still be propagating)"
        print_status "  Wait 1-2 minutes and try: curl https://api.imagineer.joshwentworth.com/api/health"
    fi

    # Check frontend
    print_status "Checking frontend..."
    if curl -f https://imagineer-generator.web.app/ &> /dev/null 2>&1; then
        print_success "Frontend is accessible"
    else
        print_warning "Frontend not accessible"
    fi
}

# Function to print deployment summary
print_summary() {
    print_header "Deployment Summary"

    echo -e "${GREEN}Deployment completed!${NC}\n"

    echo "URLs:"
    echo "  API:      https://api.imagineer.joshwentworth.com/api"
    echo "  Frontend: https://imagineer-generator.web.app"
    echo ""

    echo "Management Commands:"
    echo "  Status:   make prod-status"
    echo "  Logs:     make prod-logs"
    echo "  Restart:  make prod-restart"
    echo "  Stop:     make prod-stop"
    echo ""

    echo "Tunnel Commands:"
    echo "  Status:   sudo systemctl status cloudflared-imagineer-api"
    echo "  Logs:     sudo journalctl -u cloudflared-imagineer-api -f"
    echo "  Restart:  sudo systemctl restart cloudflared-imagineer-api"
    echo ""

    echo "Testing:"
    echo "  Local:    curl http://localhost:10050/api/health"
    echo "  Public:   curl https://api.imagineer.joshwentworth.com/api/health"
    echo "  Frontend: open https://imagineer-generator.web.app"
    echo ""

    echo "Troubleshooting:"
    echo "  See: CLOUDFLARE_TUNNEL_SETUP.md"
    echo "  See: PRODUCTION_README.md"
    echo "  See: docs/DEPLOYMENT_GUIDE.md"
    echo ""

    print_status "Deployment log saved to: $LOG_FILE"
}

# Function to show usage
show_usage() {
    cat << EOF
Imagineer Deployment Orchestration Script

Usage: $0 [OPTIONS]

Options:
    --help                  Show this help message
    --dry-run              Show what would be done without executing
    --skip-checks          Skip prerequisite and configuration checks

    Component Selection (by default, all are deployed):
    --backend-only         Deploy backend only
    --tunnel-only          Deploy Cloudflare Tunnel only
    --infra-only           Deploy infrastructure (Terraform) only
    --frontend-only        Deploy frontend only

    --no-backend           Skip backend deployment
    --no-tunnel            Skip Cloudflare Tunnel deployment
    --no-infra             Skip infrastructure deployment
    --no-frontend          Skip frontend deployment

Examples:
    # Full deployment
    $0

    # Dry run to see what would happen
    $0 --dry-run

    # Deploy only backend and tunnel
    $0 --backend-only --tunnel-only

    # Deploy everything except frontend
    $0 --no-frontend

    # Quick redeploy of just the frontend
    $0 --frontend-only --skip-checks

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                exit 0
                ;;
            --dry-run)
                DRY_RUN=true
                print_warning "DRY RUN MODE - No changes will be made"
                ;;
            --skip-checks)
                SKIP_CHECKS=true
                print_warning "Skipping prerequisite and configuration checks"
                ;;
            --backend-only)
                DEPLOY_BACKEND=true
                DEPLOY_TUNNEL=false
                DEPLOY_INFRA=false
                DEPLOY_FRONTEND=false
                ;;
            --tunnel-only)
                DEPLOY_BACKEND=false
                DEPLOY_TUNNEL=true
                DEPLOY_INFRA=false
                DEPLOY_FRONTEND=false
                ;;
            --infra-only)
                DEPLOY_BACKEND=false
                DEPLOY_TUNNEL=false
                DEPLOY_INFRA=true
                DEPLOY_FRONTEND=false
                ;;
            --frontend-only)
                DEPLOY_BACKEND=false
                DEPLOY_TUNNEL=false
                DEPLOY_INFRA=false
                DEPLOY_FRONTEND=true
                ;;
            --no-backend)
                DEPLOY_BACKEND=false
                ;;
            --no-tunnel)
                DEPLOY_TUNNEL=false
                ;;
            --no-infra)
                DEPLOY_INFRA=false
                ;;
            --no-frontend)
                DEPLOY_FRONTEND=false
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
        shift
    done
}

# Main execution
main() {
    print_header "Imagineer Production Deployment"

    parse_args "$@"

    print_status "Starting deployment at $(date)"
    print_status "Log file: $LOG_FILE"
    echo ""

    # Run checks unless skipped
    if [ "$SKIP_CHECKS" = false ]; then
        if ! check_prerequisites; then
            print_error "Prerequisites check failed. Fix issues or use --skip-checks to bypass."
            exit 1
        fi

        if ! check_configuration; then
            print_warning "Configuration check found issues. Review before continuing."
            echo ""
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_status "Deployment cancelled"
                exit 1
            fi
        fi
    fi

    # Deploy components
    if [ "$DEPLOY_BACKEND" = true ]; then
        if ! deploy_backend; then
            print_error "Backend deployment failed"
            exit 1
        fi
    fi

    if [ "$DEPLOY_TUNNEL" = true ]; then
        if ! deploy_tunnel; then
            print_error "Cloudflare Tunnel deployment failed"
            exit 1
        fi
    fi

    if [ "$DEPLOY_INFRA" = true ]; then
        if ! deploy_infrastructure; then
            print_error "Infrastructure deployment failed"
            exit 1
        fi
    fi

    if [ "$DEPLOY_FRONTEND" = true ]; then
        if ! deploy_frontend; then
            print_error "Frontend deployment failed"
            exit 1
        fi
    fi

    # Run health checks
    if [ "$DRY_RUN" = false ]; then
        run_health_checks
    fi

    # Print summary
    print_summary

    print_success "Deployment completed at $(date)"
}

# Run main function
main "$@"
