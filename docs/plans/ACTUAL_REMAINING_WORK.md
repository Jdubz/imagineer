# Actual Remaining Frontend Work

**Date:** 2025-10-31
**Status:** Post-audit analysis based on user feedback

---

## 🔍 Investigation Results

### ✅ Bug Report UX - COMPLETE

The user asked "Report bug UX already exists, what needs to be implemented?"

**Investigation shows ALL features are already complete:**

1. ✅ **Settings Menu Integration** (SettingsMenu.tsx:143-159)
   - "Report Bug" button in gear menu
   - Admin-only access
   - Shows keyboard hint "Ctrl+Shift+B"

2. ✅ **Keyboard Shortcut** (App.tsx:46-52)
   ```tsx
   useKeyboardShortcut({
     key: 'b',
     ctrlKey: true,
     shiftKey: true,
     enabled: user?.role === 'admin',
     callback: openBugReport,
   })
   ```

3. ✅ **Error Boundary Integration** (ErrorBoundaryWithReporting.tsx)
   - Automatically shows "Report Bug" button for admins
   - Pre-fills description with error details
   - Includes error stack and component stack

4. ✅ **Bug Report Context** (BugReportContext.tsx)
   - Full implementation with collectors
   - Network activity tracking
   - Log collection
   - Application state capture

**Conclusion:** Task #33 is **COMPLETE**. No work needed.

---

## ❌ Common Image Component - MISSING

The user said: "NSFW filter should apply at the image level. We should be using a common image component that indicates if the image has label data, common click actions like opening a full screen display, etc."

**Current State:**

### AlbumsTab (GOOD - reference implementation)
- ✅ Shows NSFW badge (18+) when `is_nsfw === true`
- ✅ Shows label badge (🏷️) when labels exist
- ✅ Applies NSFW blur/hide based on `nsfwSetting`
- ✅ Click to open fullscreen
- ✅ Hover preloading

```tsx
// AlbumsTab.tsx:666-699
<div className={`image-card ${image.is_nsfw ? 'nsfw' : ''} ${nsfwSetting}`}>
  <img
    className={`preview-image ${image.is_nsfw && nsfwSetting === 'blur' ? 'blurred' : ''}`}
  />
  {image.is_nsfw && <div className="nsfw-badge">18+</div>}
  {labels.length > 0 && <div className="has-labels-badge">🏷️</div>}
</div>
```

### ImageGallery (INCOMPLETE)
- ❌ No NSFW badge
- ❌ No NSFW filtering/blurring
- ❌ No label badge
- ✅ Has click to open fullscreen
- ✅ Has hover preloading
- **Uses:** Custom ImageCard component (lines 22-62) within the file

### BatchGallery (INCOMPLETE)
- ❌ No NSFW badge
- ❌ No NSFW filtering/blurring
- ❌ No label badge
- ✅ Has click to open fullscreen
- ✅ Has hover preloading
- **Uses:** Custom BatchImageCard component within the file

### ImageGrid (INCOMPLETE)
- ❌ No NSFW badge
- ❌ No NSFW filtering/blurring
- ❌ No label badge
- ❌ No fullscreen modal
- **Status:** Appears to be a simple grid, may not need all features

---

## 🎯 Required Work

### Create Reusable Image Component

**Goal:** Extract common image display logic into a reusable component.

**New File:** `web/src/components/common/ImageCard.tsx`

**Features:**
1. **NSFW Handling** (image-level)
   - Accept `is_nsfw?: boolean` prop
   - Accept `nsfwFilter: 'show' | 'blur' | 'hide'` prop
   - Apply blur class when `is_nsfw && nsfwFilter === 'blur'`
   - Hide completely when `is_nsfw && nsfwFilter === 'hide'`
   - Show NSFW badge (18+) when `is_nsfw === true`

2. **Label Indicator**
   - Accept `hasLabels?: boolean` prop (or `labelCount?: number`)
   - Show label badge (🏷️) when labels exist
   - Optional: Show count (e.g., "🏷️ 3")

3. **Image Loading**
   - Responsive images with srcSet
   - Lazy loading
   - Hover preloading
   - Loading state

4. **Click Action**
   - Accept `onClick?: () => void` prop
   - Support fullscreen modal opening

5. **Styling**
   - Accept `className?: string` for custom styles
   - Support different sizes (thumbnail, medium, large)

**Signature:**
```tsx
interface ImageCardProps {
  image: GeneratedImage
  nsfwFilter?: 'show' | 'blur' | 'hide'
  onImageClick?: (image: GeneratedImage) => void
  size?: 'thumbnail' | 'medium' | 'large'
  className?: string
  showLabels?: boolean
  showNsfwBadge?: boolean
}

const ImageCard: React.FC<ImageCardProps> = ({ ... }) => {
  // Implementation using resolveImageSources, preloadImage
  // Apply NSFW filtering
  // Show badges
  // Handle click
}
```

---

## 📝 Implementation Plan

### Phase 1: Create Common ImageCard Component (4-6 hours)

1. **Create `web/src/components/common/ImageCard.tsx`**
   - Extract ImageCard logic from ImageGallery.tsx
   - Add NSFW badge rendering
   - Add label badge rendering
   - Add NSFW filter support (blur/hide)
   - Add configurable size support

2. **Create accompanying CSS**
   - `web/src/styles/ImageCard.css`
   - Styles for badges, blur effect, sizes

3. **Add tests**
   - `web/src/components/common/ImageCard.test.tsx`
   - Test NSFW filtering (show/blur/hide)
   - Test badge rendering
   - Test click handling

### Phase 2: Integrate into Galleries (2-3 hours)

1. **Update ImageGallery.tsx**
   - Replace internal ImageCard with common component
   - Pass nsfwFilter from AppContext
   - Enable NSFW and label badges

2. **Update BatchGallery.tsx**
   - Replace internal BatchImageCard with common component
   - Pass nsfwFilter from AppContext
   - Enable NSFW and label badges

3. **Update ImageGrid.tsx** (if applicable)
   - Use common ImageCard component
   - Add fullscreen modal if needed

4. **Update AlbumsTab.tsx**
   - Migrate to use common ImageCard component
   - Preserve existing functionality
   - Remove duplicate code

### Phase 3: Global NSFW Filter (2-3 hours)

**Note:** AppContext already has `nsfwEnabled` state, but it should be:
- Three-state: 'show' | 'blur' | 'hide'
- Persisted to localStorage
- Applied globally via common component

1. **Update AppContext.tsx**
   - Change `nsfwEnabled: boolean` to `nsfwFilter: 'show' | 'blur' | 'hide'`
   - Add localStorage persistence
   - Default to 'blur' for safety

2. **Update SettingsMenu.tsx**
   - Change checkbox to select dropdown
   - Options: Show All / Blur NSFW / Hide NSFW

3. **Propagate to all galleries**
   - All galleries read from AppContext
   - Pass to ImageCard component
   - Remove local NSFW state from AlbumsTab

---

## 📊 Estimated Total Time

| Task | Time |
|------|------|
| Create common ImageCard component | 4-6 hours |
| Integrate into galleries | 2-3 hours |
| Global NSFW filter refinement | 2-3 hours |
| **Total** | **8-12 hours** |

**Size:** Medium (1-2 days)

---

## 🎯 Success Criteria

1. ✅ Single reusable ImageCard component
2. ✅ NSFW filtering works at image level across all galleries
3. ✅ Label badges show in all galleries (when labels exist)
4. ✅ NSFW badges show in all galleries (when is_nsfw)
5. ✅ Global NSFW preference persists across sessions
6. ✅ All existing functionality preserved
7. ✅ Code duplication eliminated (3 ImageCard implementations → 1)
8. ✅ Tests cover all NSFW filter modes
9. ✅ All 238+ tests still passing

---

## 📋 Files to Create

- `web/src/components/common/ImageCard.tsx`
- `web/src/components/common/ImageCard.test.tsx`
- `web/src/styles/ImageCard.css`

## 📋 Files to Modify

- `web/src/components/ImageGallery.tsx`
- `web/src/components/BatchGallery.tsx`
- `web/src/components/AlbumsTab.tsx`
- `web/src/contexts/AppContext.tsx`
- `web/src/components/SettingsMenu.tsx`
- `web/src/components/SettingsMenu.test.tsx`

---

## 🚫 What NOT to Do

- ❌ Don't create NSFWContext (AppContext already handles it)
- ❌ Don't modify backend NSFW detection logic
- ❌ Don't add complex label fetching (labels come with image data)
- ❌ Don't break existing AlbumsTab functionality

---

## 🔗 References

- AlbumsTab NSFW implementation: `web/src/components/AlbumsTab.tsx:666-699`
- AppContext NSFW state: `web/src/contexts/AppContext.tsx`
- GeneratedImage type: `web/src/types/models.ts:33-55`
- Label type: `web/src/types/models.ts:144-154`
