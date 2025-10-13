# Display Recovery Guide

## What to Expect When Restarting GDM

**Normal restart time:** 5-15 seconds
- Screen goes black
- GDM login screen should appear
- You log in and desktop loads

**If you get stuck on black screen (no login appears):**
This means X11 failed to start with the new config.

---

## Emergency Recovery Steps

### Option 1: Switch to TTY (Text Console)
When you're stuck on black screen:

1. **Press:** `Ctrl + Alt + F3` (or F4, F5, F6)
   - This switches to a text-only terminal (TTY3)
   - You should see a login prompt

2. **Login with your username/password**

3. **Restore the backup config:**
   ```bash
   # Find the backup file
   ls -lt /etc/X11/xorg.conf.d/*.backup*

   # Copy the most recent backup (use the actual filename from above)
   sudo cp /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf.backup-YYYYMMDD-HHMMSS \
          /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf

   # Restart display manager
   sudo systemctl restart gdm
   ```

4. **Switch back to GUI:** `Ctrl + Alt + F2` (or F1)

### Option 2: Boot to Recovery Mode
If TTY doesn't work:

1. **Reboot:** Hold power button until system turns off, then power on
2. **In GRUB menu:** Select "Advanced options for Ubuntu"
3. **Select:** Recovery mode
4. **Choose:** "root - Drop to root shell prompt"
5. **Remount filesystem as read-write:**
   ```bash
   mount -o remount,rw /
   ```
6. **Restore backup (same commands as above)**
7. **Reboot:**
   ```bash
   reboot
   ```

### Option 3: Nuclear Option - Remove Config Entirely
If nothing else works, just delete the config and let NVIDIA auto-detect:

```bash
sudo rm /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf
sudo systemctl restart gdm
```

---

## Before You Restart - Safety Checklist

✓ Backup exists (script creates this automatically)
✓ You know how to access TTY: `Ctrl + Alt + F3`
✓ You know your login username and password
✓ You have this recovery guide open on another device (phone/laptop)

---

## Alternative: Test Without Full Restart

Instead of restarting GDM, you can:

1. **Logout** (don't restart GDM)
2. From GDM login screen, press `Ctrl + Alt + F3` to get to TTY
3. Run the fix script
4. Check logs for errors:
   ```bash
   sudo journalctl -u gdm -n 50
   ```
5. If logs look good, switch back to F2 and login
6. If logs show errors, restore backup before logging in

---

## How to Check Logs After Restart

```bash
# Check X11 startup logs
cat /var/log/Xorg.0.log | grep -E "(EE)|(WW)|NVIDIA"

# Check GDM service logs
journalctl -u gdm -n 100

# Check for config parsing errors
journalctl -b | grep -i "xorg.*error\|nvidia.*error"
```

---

## Current Backup Location

The script will save backup to:
`/etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf.backup-[TIMESTAMP]`

You can manually backup right now:
```bash
sudo cp /etc/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf \
       ~/xorg-backup-$(date +%Y%m%d-%H%M%S).conf
```
