# Phase 3: Frontend Implementation - IN PROGRESS

**Date**: 2025-11-04
**Status**: Types & API Client Complete ✅
**Dependencies**: Phase 1 ✅ | Phase 2 ✅

---

## Overview

Phase 3 implements the frontend UI for batch template management. This phase updates the React application to use the new batch template system and removes the old template-album confusion.

---

## Completed Work

### 1. TypeScript Types ✅

**File**: `web/src/types/models.ts`

**New Types Added**:

```typescript
export interface BatchTemplate {
  id: number
  name: string
  description?: string | null
  csv_path: string
  csv_data?: string | null
  csv_items?: unknown[]
  base_prompt?: string | null
  prompt_template: string
  style_suffix?: string | null
  example_theme?: string | null
  width: number
  height: number
  negative_prompt?: string | null
  lora_config?: string | null
  template_item_count: number
  template_items_preview?: unknown[]
  lora_count: number
  created_by?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface BatchGenerationRun {
  id: number
  template_id: number
  album_id?: number | null
  album_name: string
  user_theme: string
  steps?: number | null
  seed?: number | null
  width?: number | null
  height?: number | null
  guidance_scale?: number | null
  negative_prompt?: string | null
  status: 'queued' | 'running' | 'completed' | 'failed'
  total_items?: number | null
  completed_items: number
  failed_items: number
  created_by?: string | null
  created_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  error_message?: string | null
}

export interface BatchGenerateParams {
  album_name: string
  user_theme: string
  steps?: number
  seed?: number
  width?: number
  height?: number
  guidance_scale?: number
  negative_prompt?: string
}

export interface BatchGenerateResponse {
  run: BatchGenerationRun
  template: BatchTemplate
  message: string
}
```

**Album Type Updated**:
```typescript
export interface Album {
  // ... existing fields ...

  // NEW: Source tracking
  source_type?: 'manual' | 'batch_generation' | 'scrape'
  source_id?: number | null

  // DEPRECATED: Template fields (kept for backward compatibility)
  is_set_template?: boolean
  // ... other deprecated fields ...
}
```

### 2. API Client Methods ✅

**File**: `web/src/lib/api.ts`

**New Methods Added**:

```typescript
api.batchTemplates: {
  // List all templates
  getAll(signal?: AbortSignal): Promise<BatchTemplate[]>

  // Get template details
  getById(templateId: number, signal?: AbortSignal): Promise<BatchTemplate>

  // Create template (admin only)
  create(data: Partial<BatchTemplate>, signal?: AbortSignal): Promise<BatchTemplate>

  // Update template (admin only)
  update(templateId: number, data: Partial<BatchTemplate>, signal?: AbortSignal): Promise<BatchTemplate>

  // Delete template (admin only)
  delete(templateId: number, signal?: AbortSignal): Promise<{ message: string }>

  // Generate batch from template
  generate(templateId: number, params: BatchGenerateParams, signal?: AbortSignal): Promise<BatchGenerateResponse>

  // List generation runs
  getRuns(templateId: number, signal?: AbortSignal): Promise<{ runs: BatchGenerationRun[]; total: number }>
}
```

**Features**:
- ✅ Full CRUD operations
- ✅ Type-safe with TypeScript
- ✅ AbortSignal support for cancellation
- ✅ Consistent error handling
- ✅ Proper API URL routing

---

## Remaining Work

### 3. Create Batch Templates Page ⏳

**New File**: `web/src/pages/BatchTemplatesPage.tsx`

**Requirements**:
- List all batch templates in a grid/list view
- Show template cards with:
  - Name and description
  - Item count (e.g., "54 cards")
  - Dimensions (512×720)
  - LoRA count
  - Example theme
- "Generate Batch" button on each card
- Modal/form for batch generation:
  - Album name input
  - User theme textarea
  - Optional overrides (steps, seed, etc.)
- Recent generation runs list
- Admin: Create/Edit/Delete templates

### 4. Update Albums Tab ⏳

**File**: `web/src/components/AlbumsTab.tsx`

**Requirements**:
- Remove `is_set_template` filter (line 112)
- Add source type badges on album cards:
  - Manual: No badge (default)
  - Batch Generation: "🎨 Batch" badge
  - Scrape: "🌐 Scraped" badge
- Optional: Filter by source_type
- Click source badge → Navigate to source details:
  - Batch: Show BatchGenerationRun details
  - Scrape: Show ScrapeJob details

### 5. Update Generate Form ⏳

**File**: `web/src/components/GenerateForm.tsx`

**Requirements**:
- Remove batch generation state (lines 44-52)
- Remove template fetching logic (lines 54-77)
- Remove batch generation form UI
- Keep single image generation form
- Add link to Batch Templates page for batch generation

---

## Testing Checklist

- ✅ TypeScript types compile without errors
- ✅ API client methods type-check correctly
- ⏳ Batch Templates page loads and displays templates
- ⏳ Generate batch form works
- ⏳ Batch generation creates run record
- ⏳ Albums tab shows correct source badges
- ⏳ Template filtering removed from albums
- ⏳ Generate form no longer has batch option

---

## Files Modified

### Completed
1. **`web/src/types/models.ts`** ✅
   - Added BatchTemplate interface
   - Added BatchGenerationRun interface
   - Added BatchGenerateParams interface
   - Added BatchGenerateResponse interface
   - Updated Album interface with source_type

2. **`web/src/lib/api.ts`** ✅
   - Added api.batchTemplates object
   - 7 new methods for template management

### Pending
3. **`web/src/pages/BatchTemplatesPage.tsx`** ⏳ (NEW)
   - Batch template list view
   - Generation form modal

4. **`web/src/components/AlbumsTab.tsx`** ⏳
   - Remove is_set_template filter
   - Add source badges

5. **`web/src/components/GenerateForm.tsx`** ⏳
   - Remove batch generation UI

6. **`web/src/App.tsx`** ⏳
   - Add route for /batch-templates

---

## UI Design Notes

### Batch Templates Page

**Layout**:
```
┌─────────────────────────────────────────────┐
│  Batch Templates                     [+ New] │
├─────────────────────────────────────────────┤
│                                               │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │ Playing   │  │ Tarot     │  │ Zodiac   ││
│  │ Card Deck │  │ Major     │  │ Signs    ││
│  │           │  │ Arcana    │  │          ││
│  │ 54 items  │  │ 22 items  │  │ 12 items ││
│  │ 512×720   │  │ 512×896   │  │ 512×768  ││
│  │ 1 LoRA    │  │ 0 LoRAs   │  │ 0 LoRAs  ││
│  │           │  │           │  │          ││
│  │ [Generate]│  │ [Generate]│  │ [Generate ││
│  └───────────┘  └───────────┘  └──────────┘│
│                                               │
└─────────────────────────────────────────────┘
```

**Generation Modal**:
```
┌─────────────────────────────────────────────┐
│  Generate: Playing Card Deck          [×]   │
├─────────────────────────────────────────────┤
│                                               │
│  Album Name: *                                │
│  ┌─────────────────────────────────────────┐│
│  │ My Steampunk Cards                      ││
│  └─────────────────────────────────────────┘│
│                                               │
│  Theme: *                                     │
│  ┌─────────────────────────────────────────┐│
│  │ steampunk aesthetic with brass gears    ││
│  │ and Victorian industrial design         ││
│  └─────────────────────────────────────────┘│
│                                               │
│  ▼ Advanced Options                          │
│    Steps: [25]  Seed: [Random]               │
│    Width: [512]  Height: [720]               │
│                                               │
│  Will generate 54 images                     │
│                                               │
│           [Cancel]  [Generate Batch]          │
└─────────────────────────────────────────────┘
```

### Album Source Badges

```
┌────────────────────────────────────┐
│  My Steampunk Cards    🎨 Batch    │
│  72 images                          │
│  [View]                             │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  Pinterest Inspiration 🌐 Scraped  │
│  45 images                          │
│  [View]                             │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  My Manual Collection               │
│  12 images                          │
│  [View]                             │
└────────────────────────────────────┘
```

---

## Next Steps

1. **Create BatchTemplatesPage.tsx**
   - Template grid view
   - Generation modal
   - Run history

2. **Update AlbumsTab.tsx**
   - Remove template filter
   - Add source badges
   - Filter by source_type

3. **Update GenerateForm.tsx**
   - Remove batch generation UI
   - Add link to templates page

4. **Update App.tsx**
   - Add /batch-templates route

5. **Testing**
   - Test template list loads
   - Test batch generation
   - Test source badges display

---

## Success Criteria

- ✅ TypeScript types defined
- ✅ API client methods implemented
- ⏳ Batch Templates page functional
- ⏳ Albums tab updated
- ⏳ Generate form simplified
- ⏳ All tests passing
- ⏳ No template/album confusion in UI

---

## Current Status

**Phase 3 Progress**: 40% Complete

**Completed**:
- ✅ TypeScript types (100%)
- ✅ API client (100%)

**Remaining**:
- ⏳ Batch Templates page (0%)
- ⏳ Albums tab updates (0%)
- ⏳ Generate form updates (0%)
- ⏳ Routing (0%)

**Estimated Time**: 2-3 hours for remaining UI work

---

**Status**: ✅ **TYPES & API READY FOR UI DEVELOPMENT**

**Implemented By**: Claude Code (AI Assistant)
**Last Updated**: 2025-11-04
