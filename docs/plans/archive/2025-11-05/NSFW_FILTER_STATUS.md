# NSFW Filter - Implementation Status

**Last Updated:** 2025-10-29
**Status:** Partially Implemented - Works in AlbumsTab, needs global setting

---

## Current Implementation ✅

### Backend (Fully Implemented)
**Files:** `server/database.py`, `server/routes/images.py`

- `is_nsfw` boolean field on Image model (database column)
- API endpoint supports NSFW filtering: `GET /api/images?nsfw=hide|show`
- Labeling service can mark images as NSFW (via Claude analysis)
- Images serialize `is_nsfw` field in responses

### Frontend - AlbumsTab (Fully Implemented)
**Files:** `web/src/components/AlbumsTab.tsx`, `web/src/hooks/useAlbumDetailState.ts`

**Features:**
- NSFW filter dropdown with 3 options:
  - **Hide:** Completely hide NSFW images from view
  - **Blur:** Show NSFW images but blur them visually
  - **Show:** Display all images normally
- Visual blur effect applied to NSFW images when set to "blur"
- 18+ badge displayed on NSFW-marked images
- State managed via `useAlbumDetailState` hook
- Default setting: `"blur"`

**Implementation Details:**
```tsx
// State management
nsfwSetting: 'hide' | 'blur' | 'show'  // Default: 'blur'

// CSS classes applied
className={`image-card ${image.is_nsfw ? 'nsfw' : ''} ${nsfwSetting}`}
className={`${loadedImages.has(image.id) ? 'loaded' : 'loading'} ${image.is_nsfw && nsfwSetting === 'blur' ? 'blurred' : ''}`}

// Visual badge
{image.is_nsfw && <div className="nsfw-badge">18+</div>}
```

---

## What's Missing ❌

### Global NSFW Preference
**Current:** NSFW setting only exists within AlbumsTab view
**Needed:** Global user preference that applies across all image views

**Required Implementation:**

1. **Global State Management**
   - Create `NSFWContext` or add to existing user context
   - Store preference in localStorage for persistence
   - Default: `"blur"`

2. **Settings Menu Integration**
   - Add NSFW toggle to Settings Menu dropdown
   - Options: Hide / Blur / Show (or simple toggle Hide/Show)
   - Update global preference when changed
   - Persist to localStorage

3. **Apply to All Views**
   - AlbumsTab should use global setting (remove local state)
   - ImageGallery component should respect NSFW filter
   - BatchGallery should respect NSFW filter
   - Any other image display components

4. **API Integration**
   - When fetching images, pass `nsfw` parameter based on global setting
   - Client-side filtering as fallback for already-loaded images

---

## Recommended Implementation

### Phase 1: Global State (1-2 hours)
**File:** `web/src/contexts/NSFWContext.tsx` (new)

```tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

type NSFWSetting = 'hide' | 'blur' | 'show'

interface NSFWContextValue {
  nsfwSetting: NSFWSetting
  setNsfwSetting: (setting: NSFWSetting) => void
}

const NSFWContext = createContext<NSFWContextValue | undefined>(undefined)

const STORAGE_KEY = 'imagineer_nsfw_setting'

export const NSFWProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [nsfwSetting, setNsfwSettingState] = useState<NSFWSetting>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return (stored as NSFWSetting) || 'blur'
  })

  const setNsfwSetting = useCallback((setting: NSFWSetting) => {
    setNsfwSettingState(setting)
    localStorage.setItem(STORAGE_KEY, setting)
  }, [])

  return (
    <NSFWContext.Provider value={{ nsfwSetting, setNsfwSetting }}>
      {children}
    </NSFWContext.Provider>
  )
}

export const useNSFW = () => {
  const context = useContext(NSFWContext)
  if (!context) {
    throw new Error('useNSFW must be used within NSFWProvider')
  }
  return context
}
```

### Phase 2: Connect to Settings Menu (30 min)
**File:** `web/src/components/SettingsMenu.tsx`

Update the NSFW toggle to use global context:

```tsx
import { useNSFW } from '../contexts/NSFWContext'

const SettingsMenu: React.FC = () => {
  const { nsfwSetting, setNsfwSetting } = useNSFW()

  const handleNsfwChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setNsfwSetting(e.target.value as NSFWSetting)
  }

  return (
    <div className="settings-dropdown">
      {/* ... */}
      <div className="settings-option">
        <label htmlFor="nsfw-filter">NSFW Filter:</label>
        <select
          id="nsfw-filter"
          value={nsfwSetting}
          onChange={handleNsfwChange}
        >
          <option value="hide">Hide</option>
          <option value="blur">Blur</option>
          <option value="show">Show All</option>
        </select>
      </div>
    </div>
  )
}
```

### Phase 3: Update AlbumsTab (15 min)
**File:** `web/src/components/AlbumsTab.tsx`

Remove local NSFW state and use global:

```tsx
import { useNSFW } from '../contexts/NSFWContext'

// Inside AlbumDetailView component:
const { nsfwSetting } = useNSFW()  // Remove from local state

// Remove local nsfwSetting state management
// Keep existing rendering logic (already works correctly)
```

### Phase 4: Apply to Other Views (1-2 hours)
Update other image display components to respect global NSFW setting:
- `web/src/components/ImageGallery.tsx`
- `web/src/components/BatchGallery.tsx`
- Any other components that display images

---

## Testing Checklist

- [ ] NSFW setting persists across page reloads (localStorage)
- [ ] Setting in dropdown updates all image views immediately
- [ ] Hide mode completely removes NSFW images
- [ ] Blur mode shows images with blur effect
- [ ] Show mode displays all images normally
- [ ] 18+ badge appears on NSFW images in all modes
- [ ] Default setting is "blur" for new users
- [ ] Setting syncs between tabs (via localStorage events)

---

## Current Behavior

**AlbumsTab:**
- ✅ NSFW filter dropdown works
- ✅ Hide/Blur/Show all functional
- ✅ 18+ badge displays correctly
- ⚠️ Setting is local to AlbumsTab (lost on navigation)

**Other Views:**
- ❌ No NSFW filtering applied
- ❌ All images shown regardless of is_nsfw flag

---

## For Settings Menu Implementation

When implementing the Settings Menu (per BUG_REPORT_IMPLEMENTATION_PLAN.md), the NSFW toggle can be:

**Option 1: Simple Toggle (Recommended for MVP)**
```tsx
<label className="settings-option settings-toggle">
  <span className="settings-option-label">Hide NSFW</span>
  <input
    type="checkbox"
    checked={nsfwSetting === 'hide'}
    onChange={(e) => setNsfwSetting(e.target.checked ? 'hide' : 'blur')}
  />
</label>
```

**Option 2: Dropdown (Full Feature)**
```tsx
<div className="settings-option">
  <label htmlFor="nsfw-setting">NSFW Filter:</label>
  <select
    id="nsfw-setting"
    value={nsfwSetting}
    onChange={(e) => setNsfwSetting(e.target.value as NSFWSetting)}
  >
    <option value="hide">Hide</option>
    <option value="blur">Blur (Default)</option>
    <option value="show">Show All</option>
  </select>
</div>
```

---

## Summary

**Current Status:**
- Backend: ✅ Fully implemented and working
- Frontend (AlbumsTab): ✅ Fully implemented, needs global state
- Frontend (Global): ❌ Not implemented

**To Complete:**
1. Create NSFWContext for global state management
2. Connect Settings Menu toggle to global context
3. Update AlbumsTab to use global setting
4. Apply to other image views (ImageGallery, BatchGallery)

**Estimated Time:** 2-3 hours to complete global implementation

---

**Document Version:** 1.0
**Next Steps:** Implement NSFWContext when building Settings Menu
