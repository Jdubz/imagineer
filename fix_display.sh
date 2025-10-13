#!/bin/bash
# Script to fix Samsung S34J55x ultrawide monitor resolution
# This addresses the DisplayPort bandwidth detection issue

set -e

echo "=== Display Resolution Fix Script ==="
echo "This will update the NVIDIA X configuration to properly detect DisplayPort bandwidth"
echo ""

# Backup current config
BACKUP_FILE="/etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf.backup-$(date +%Y%m%d-%H%M%S)"
echo "1. Backing up current config to: $BACKUP_FILE"
cp /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf "$BACKUP_FILE"

# Create new config
echo "2. Writing new configuration..."
cat > /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf << 'EOF'
Section "OutputClass"
    Identifier "nvidia"
    MatchDriver "nvidia-drm"
    Driver "nvidia"
    Option "AllowEmptyInitialConfiguration"
    Option "PrimaryGPU" "yes"
    # Force NVIDIA to ignore bandwidth limits and accept higher resolutions
    Option "ModeValidation" "NoTotalSizeCheck, NoMaxPClkCheck, AllowNonEdidModes"
    Option "UseEDID" "TRUE"
    Option "UseEDIDFreqs" "FALSE"
    Option "ExactModeTimingsDVI" "TRUE"
EndSection
EOF

echo "3. Configuration updated successfully!"
echo ""
echo "Next steps:"
echo "  - Run: sudo systemctl restart gdm"
echo "  - Your display will restart"
echo "  - After logging back in, run: xrandr | grep -A 5 'DP-1 connected'"
echo "  - You should see 3440x1440 modes available"
echo ""
echo "If something goes wrong, restore backup with:"
echo "  sudo cp $BACKUP_FILE /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf"
echo "  sudo systemctl restart gdm"
