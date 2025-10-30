# Imagineer Frontend Redesign Plan - shadcn/ui Implementation

**Design Vision:** Artistic & Creative gallery experience with separate public/admin interfaces

**Theme:** Vibrant, colorful, artistic design that showcases AI-generated images beautifully

**Generated:** 2025-10-30

---

## Design Philosophy

### Core Principles
1. **Gallery-First Design** - Images are the hero. Everything else supports showcasing them.
2. **Artistic Color Palette** - Move beyond purple gradient to a rich, creative color system
3. **Separate Experiences** - Public gallery = portfolio/gallery aesthetic, Admin tools = functional dashboard
4. **Accessibility** - WCAG 2.1 AA compliance, keyboard navigation, screen reader support
5. **Performance** - Progressive loading, optimized images, smooth animations

### Color System Proposal

**Primary Palette (Artistic & Vibrant):**
```
Primary:    #FF6B9D (Coral Pink) - warm, inviting, artistic
Secondary:  #4ECDC4 (Turquoise) - creative, energetic
Accent:     #FFE66D (Sunny Yellow) - highlights, CTAs
Success:    #95E1D3 (Mint) - confirmations
Warning:    #FFA07A (Light Coral) - alerts
Error:      #FF6B6B (Soft Red) - errors
```

**Neutral Palette:**
```
Background: #FAFAFA (Soft White)
Surface:    #FFFFFF (Pure White)
Border:     #E0E0E0 (Light Gray)
Text:       #2C3E50 (Dark Blue-Gray)
Muted:      #95A5A6 (Medium Gray)
```

**Dark Mode (Future):**
```
Background: #1A1F2E (Deep Navy)
Surface:    #242A3A (Slate)
Accent:     Maintain vibrant colors with adjusted saturation
```

---

## Implementation Phases

## Phase 1: Foundation & Design System Setup
**Priority:** P0 (Required for all subsequent work)
**Estimated Time:** 2-3 days

### Tasks

#### 1.1 Install shadcn/ui and Dependencies
```bash
cd web
npx shadcn@latest init
```

**Configuration:**
- Style: CSS variables
- Base color: Slate (will customize)
- CSS location: src/styles/globals.css
- Tailwind config: tailwind.config.js
- React Server Components: No
- Import alias: @/components

**Install core components:**
```bash
npx shadcn@latest add button card dialog dropdown-menu tabs toast
npx shadcn@latest add input label select textarea switch
npx shadcn@latest add avatar badge separator skeleton
npx shadcn@latest add tooltip popover sheet alert
```

#### 1.2 Configure Tailwind with Custom Theme
Update `tailwind.config.js`:
```js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#FF6B9D',
          50: '#FFF5F7',
          100: '#FFE1E9',
          200: '#FFC4D4',
          300: '#FFA6BE',
          400: '#FF88A9',
          500: '#FF6B9D',
          600: '#FF4D8F',
          700: '#FF2F80',
          800: '#E60066',
          900: '#B30050',
        },
        secondary: {
          DEFAULT: '#4ECDC4',
          50: '#F0FFFE',
          100: '#CCFBF7',
          200: '#99F6EF',
          300: '#5EEAD4',
          400: '#4ECDC4',
          500: '#2DD4BF',
          600: '#14B8A6',
          700: '#0D9488',
          800: '#0F766E',
          900: '#115E59',
        },
        accent: {
          DEFAULT: '#FFE66D',
          50: '#FFFEF0',
          100: '#FFFACC',
          200: '#FFF499',
          300: '#FFED66',
          400: '#FFE66D',
          500: '#FACC15',
          600: '#EAB308',
          700: '#CA8A04',
          800: '#A16207',
          900: '#854D0E',
        },
        success: '#95E1D3',
        warning: '#FFA07A',
        error: '#FF6B6B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Poppins', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: '1rem',
        md: '0.75rem',
        sm: '0.5rem',
      },
      boxShadow: {
        'soft': '0 2px 15px rgba(0, 0, 0, 0.08)',
        'medium': '0 4px 20px rgba(0, 0, 0, 0.12)',
        'strong': '0 10px 40px rgba(0, 0, 0, 0.15)',
        'glow': '0 0 20px rgba(255, 107, 157, 0.3)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
```

#### 1.3 Set Up Design Tokens
Create `src/styles/tokens.css`:
```css
@layer base {
  :root {
    /* Spacing Scale */
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;

    /* Typography */
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
    --font-size-3xl: 1.875rem;
    --font-size-4xl: 2.25rem;

    /* Animation Durations */
    --duration-fast: 150ms;
    --duration-normal: 250ms;
    --duration-slow: 350ms;

    /* Easing Functions */
    --ease-in: cubic-bezier(0.4, 0, 1, 1);
    --ease-out: cubic-bezier(0, 0, 0.2, 1);
    --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
    --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }
}
```

#### 1.4 Create Component Library Documentation
Create `src/components/ui/README.md` documenting:
- Component usage patterns
- Accessibility guidelines
- Theme customization examples
- Animation standards

---

## Phase 2: Core Component Migration
**Priority:** P0
**Estimated Time:** 3-4 days

### 2.1 Button System
**Replace:** Custom button styles
**With:** shadcn Button with variants

**Variants to create:**
- `default` - Primary actions (coral pink)
- `secondary` - Secondary actions (turquoise)
- `accent` - Highlighted CTAs (yellow)
- `outline` - Outlined buttons
- `ghost` - Minimal buttons for menus
- `link` - Text-only buttons

**File:** `src/components/ui/button.tsx`

### 2.2 Card System
**Replace:** `.generate-form`, `.batch-list`, `.image-grid-container` styles
**With:** shadcn Card with custom styling

**Card Variants:**
- `elevated` - Raised cards with shadow (default)
- `flat` - No shadow, border only
- `glass` - Glassmorphism effect for overlays
- `gallery` - Special styling for image cards

**File:** `src/components/ui/card.tsx`

### 2.3 Form Components
**Replace:** Custom form inputs, labels, textareas
**With:** shadcn Form + Input + Label + Textarea + Select

**Features:**
- Consistent validation states
- Error message display
- Helper text support
- Loading states
- Disabled states with visual feedback

**Files:**
- `src/components/ui/input.tsx`
- `src/components/ui/textarea.tsx`
- `src/components/ui/select.tsx`
- `src/components/ui/label.tsx`
- `src/components/ui/form.tsx`

### 2.4 Dialog/Modal System
**Replace:** Custom modal styles
**With:** shadcn Dialog

**Features:**
- Image modal for full-size viewing
- Confirmation dialogs for destructive actions
- Form dialogs for quick inputs
- Responsive sizing
- Smooth animations

**File:** `src/components/ui/dialog.tsx`

### 2.5 Toast Notifications
**Replace:** Custom Toast component
**With:** shadcn Toast (Sonner integration)

**Enhancements:**
- Success, error, warning, info variants
- Action buttons in toasts
- Dismissible with swipe gesture
- Stack multiple toasts
- Position customization

**File:** `src/components/ui/toast.tsx`

### 2.6 Loading States
**Replace:** Custom Spinner component
**With:** shadcn Skeleton + custom Spinner variants

**Components:**
- `Skeleton` - For content placeholders
- `Spinner` - For inline loading
- `LoadingCard` - For card placeholders
- `LoadingGallery` - For gallery loading state

**Files:**
- `src/components/ui/skeleton.tsx`
- `src/components/ui/spinner.tsx`

---

## Phase 3: Public Gallery Redesign (Portfolio Experience)
**Priority:** P1
**Estimated Time:** 4-5 days

### Design Vision
Clean, portfolio-style gallery that puts images center stage. Think Behance, Dribbble, or Unsplash aesthetics.

### 3.1 Gallery Landing Page
**Route:** `/gallery`

**Layout:**
```
┌─────────────────────────────────────────┐
│  HEADER (minimal, transparent)          │
│  Logo     Search Bar        Settings    │
└─────────────────────────────────────────┘
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   HERO IMAGE CAROUSEL             │ │
│  │   Featured / Recent Highlights    │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌─────────┐ Filter Chips:            │
│  │ Filters │ [All] [Recent] [Popular] │
│  └─────────┘ [Sets] [Training Runs]   │
│                                         │
│  ╔═══════╗ ╔═══════╗ ╔═══════╗       │
│  ║ Image ║ ║ Image ║ ║ Image ║       │
│  ║   1   ║ ║   2   ║ ║   3   ║       │
│  ╚═══════╝ ╚═══════╝ ╚═══════╝       │
│                                         │
│  ╔═══════╗ ╔═══════╗ ╔═══════╗       │
│  ║ Image ║ ║ Image ║ ║ Image ║       │
│  ║   4   ║ ║   5   ║ ║   6   ║       │
│  ╚═══════╝ ╚═══════╝ ╚═══════╝       │
│                                         │
│  [Load More / Infinite Scroll]         │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  FOOTER                          │   │
│  │  About · Privacy · GitHub        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Components to Build:**
- `PublicGalleryLayout.tsx` - Wrapper with minimal header
- `HeroCarousel.tsx` - Featured images carousel
- `FilterBar.tsx` - shadcn Tabs + Badge chips
- `MasonryGrid.tsx` - Responsive masonry layout
- `ImageCard.tsx` - Hover effects, info overlay
- `ImageLightbox.tsx` - Full-screen image viewer with metadata

**Key Features:**
- Masonry grid (variable height cards)
- Smooth hover transitions
- Lazy loading with blur-up placeholders
- Infinite scroll
- Keyboard navigation (arrow keys in lightbox)
- Share buttons (copy link, download)

### 3.2 Image Card Design
**Component:** `ImageCard.tsx`

```tsx
// Hover State: Reveal metadata overlay
<Card variant="gallery" className="group">
  <div className="relative overflow-hidden">
    {/* Image with blur-up effect */}
    <img
      src={thumbnail}
      className="transition-transform group-hover:scale-105"
    />

    {/* Gradient Overlay (appears on hover) */}
    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent
                    opacity-0 group-hover:opacity-100 transition-opacity">
      <div className="p-4">
        <Badge variant="secondary">{metadata.model}</Badge>
        <p className="text-white text-sm mt-2 line-clamp-2">{prompt}</p>
        <div className="flex gap-2 mt-2">
          <Button size="sm" variant="ghost">
            <IconExpand /> View
          </Button>
          <Button size="sm" variant="ghost">
            <IconShare /> Share
          </Button>
        </div>
      </div>
    </div>
  </div>
</Card>
```

### 3.3 Album/Batch View
**Route:** `/gallery/:batchId`

**Layout:**
```
┌─────────────────────────────────────────┐
│  ← Back to Gallery                      │
│                                         │
│  Album Title                    🔗 Share│
│  54 images · Created Oct 30, 2025       │
│  ─────────────────────────────────────  │
│                                         │
│  [Grid View] [List View] [Slideshow]   │
│                                         │
│  ╔═══════╗ ╔═══════╗ ╔═══════╗       │
│  ║ Image ║ ║ Image ║ ║ Image ║       │
│  ╚═══════╝ ╚═══════╝ ╚═══════╝       │
│                                         │
│  Bulk Actions: [Download All] [Share]  │
└─────────────────────────────────────────┘
```

**Components:**
- `AlbumHeader.tsx` - Title, metadata, actions
- `ViewToggle.tsx` - Switch between grid/list/slideshow
- `BulkActions.tsx` - Batch operations

---

## Phase 4: Admin Dashboard Redesign
**Priority:** P1
**Estimated Time:** 5-6 days

### Design Vision
Functional, clean dashboard interface with clear sections for different admin tasks.

### 4.1 Dashboard Layout
**New Component:** `AdminLayout.tsx`

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR (collapsible)      │  MAIN CONTENT             │
│  ┌─────────────────────┐    │                           │
│  │ 🎨 Generate          │    │  ┌──────────────────┐    │
│  │ 📁 Albums            │    │  │  Active Jobs     │    │
│  │ 🕷️  Scraping          │    │  │  Queue: 3        │    │
│  │ 🚀 Training          │    │  └──────────────────┘    │
│  │ 📋 Queue             │    │                           │
│  │ 🎭 LoRAs             │    │  ┌──────────────────┐    │
│  │ ⚙️  Settings          │    │  │  Recent Images   │    │
│  └─────────────────────┘    │  │                   │    │
│                              │  └──────────────────┘    │
│  ┌─────────────────────┐    │                           │
│  │ System Status        │    │  [Tab-specific content]  │
│  │ ✅ API: Online       │    │                           │
│  │ ✅ GPU: Available    │    │                           │
│  └─────────────────────┘    │                           │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- `AdminSidebar.tsx` - shadcn Sheet (mobile) + fixed sidebar (desktop)
- `DashboardHeader.tsx` - Breadcrumbs, quick actions, user menu
- `StatusWidget.tsx` - Real-time system status
- `QuickActions.tsx` - Frequent task shortcuts

### 4.2 Generate Tab Redesign
**Component:** `GenerateTab.tsx` (redesigned)

**Layout Improvements:**
- Two-column layout: Form on left, preview/queue on right
- Collapsible sections for advanced settings
- Real-time parameter preview (show what each slider does)
- LoRA builder with visual previews
- Template system (save commonly used settings)

**Components:**
- `GenerateForm.tsx` - Main form with shadcn inputs
- `ParameterPreview.tsx` - Visual feedback for settings
- `LoRABuilder.tsx` - Drag-and-drop LoRA configuration
- `TemplateSelector.tsx` - Quick-load saved configs
- `QueueSidebar.tsx` - Live queue updates

### 4.3 Training Tab Redesign
**Component:** `TrainingTab.tsx` (redesigned)

**Features:**
- Training wizard (step-by-step)
- Dataset preview
- Progress visualization
- Training metrics chart
- Model comparison tool

**Components:**
- `TrainingWizard.tsx` - Multi-step form
- `DatasetPreview.tsx` - Image grid with captions
- `TrainingProgress.tsx` - Progress bar + live logs
- `MetricsChart.tsx` - Loss curve visualization
- `ModelCard.tsx` - Trained model display

### 4.4 Scraping Tab Redesign
**Component:** `ScrapingTab.tsx` (redesigned)

**Features:**
- URL input with validation
- Scraping rules builder
- Progress tracking
- Results preview
- Error handling UI

**Components:**
- `ScraperConfig.tsx` - Form with validation
- `RulesBuilder.tsx` - Visual rule configuration
- `ScrapingProgress.tsx` - Live progress
- `ResultsPreview.tsx` - Preview scraped images

---

## Phase 5: Enhanced Features
**Priority:** P2
**Estimated Time:** 3-4 days

### 5.1 Image Interactions
- ❤️ Like/favorite system (client-side for now)
- 💬 Comments (if backend supports)
- 🏷️ Tag filtering
- 🔍 Search by prompt/metadata

### 5.2 Animations & Micro-interactions
- Framer Motion integration
- Page transitions
- Hover effects
- Loading animations
- Success celebrations (confetti on generation complete)

### 5.3 Responsive Design
- Mobile-optimized gallery (swipe gestures)
- Tablet layouts
- Touch-friendly controls
- Responsive typography

### 5.4 Accessibility
- ARIA labels throughout
- Keyboard shortcuts guide
- Screen reader announcements
- Focus management
- Color contrast compliance

---

## Phase 6: Polish & Optimization
**Priority:** P2
**Estimated Time:** 2-3 days

### 6.1 Performance
- Image optimization (WebP, AVIF)
- Code splitting
- Bundle size analysis
- Lazy loading
- Prefetching

### 6.2 Testing
- Component tests for shadcn components
- Integration tests for workflows
- Accessibility tests
- Visual regression tests

### 6.3 Documentation
- Component usage guide
- Design system documentation
- Contribution guidelines
- Style guide

---

## Migration Strategy

### Incremental Approach
1. **Install shadcn** - Phase 1
2. **Create parallel components** - Build new shadcn versions alongside existing
3. **Migrate page by page** - Start with Gallery, then Admin tabs
4. **Remove old components** - Clean up after migration
5. **Test thoroughly** - Ensure feature parity

### Feature Flags (Optional)
Add ability to toggle between old/new UI during migration:
```tsx
const USE_NEW_DESIGN = import.meta.env.VITE_NEW_DESIGN === 'true'
```

---

## File Structure (Post-Migration)

```
web/src/
├── components/
│   ├── ui/                    # shadcn components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── gallery/               # Gallery-specific components
│   │   ├── PublicGalleryLayout.tsx
│   │   ├── HeroCarousel.tsx
│   │   ├── ImageCard.tsx
│   │   ├── MasonryGrid.tsx
│   │   └── ImageLightbox.tsx
│   ├── admin/                 # Admin-specific components
│   │   ├── AdminLayout.tsx
│   │   ├── AdminSidebar.tsx
│   │   ├── DashboardHeader.tsx
│   │   └── StatusWidget.tsx
│   ├── generate/              # Generation components
│   │   ├── GenerateForm.tsx
│   │   ├── LoRABuilder.tsx
│   │   └── TemplateSelector.tsx
│   ├── training/              # Training components
│   │   ├── TrainingWizard.tsx
│   │   ├── MetricsChart.tsx
│   │   └── ModelCard.tsx
│   └── shared/                # Shared components
│       ├── ErrorBoundary.tsx
│       ├── LoadingStates.tsx
│       └── ...
├── styles/
│   ├── globals.css            # Global styles + shadcn
│   ├── tokens.css             # Design tokens
│   └── animations.css         # Animation utilities
├── lib/
│   ├── utils.ts               # shadcn utils (cn helper)
│   └── ...
└── hooks/
    ├── useMediaQuery.ts       # Responsive hooks
    └── ...
```

---

## Design Examples

### Color Usage Guidelines

**Primary (Coral Pink):**
- Primary CTAs (Generate button, Save button)
- Active states
- Important badges

**Secondary (Turquoise):**
- Secondary actions
- Info badges
- Links

**Accent (Yellow):**
- Highlights
- New/Featured badges
- Success states

**When to use what:**
```tsx
// Primary - Main actions
<Button variant="default">Generate Image</Button>

// Secondary - Supporting actions
<Button variant="secondary">Save Template</Button>

// Accent - Special highlights
<Badge variant="accent">Featured</Badge>

// Outline - Less prominent actions
<Button variant="outline">Cancel</Button>

// Ghost - Menu items, subtle actions
<Button variant="ghost">Settings</Button>
```

---

## Accessibility Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible and clear
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Alt text for all images
- [ ] ARIA labels for icons
- [ ] Screen reader announcements for dynamic content
- [ ] Skip navigation links
- [ ] Semantic HTML throughout
- [ ] Form validation accessible
- [ ] Modal focus trap implemented

---

## Success Metrics

### Performance
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s
- [ ] Lighthouse Performance > 90
- [ ] Bundle size < 500KB (gzipped)

### Accessibility
- [ ] Lighthouse Accessibility > 95
- [ ] Keyboard navigation test passed
- [ ] Screen reader test passed

### UX
- [ ] Mobile-friendly (responsive design)
- [ ] Touch targets ≥ 44px
- [ ] Smooth animations (60fps)
- [ ] Fast image loading (blur-up effect)

---

## Open Questions / Decisions Needed

1. **Font Choice:** Keep Inter or switch to something more artistic (e.g., DM Sans, Plus Jakarta)?
2. **Dark Mode:** Implement now or Phase 2?
3. **Animation Library:** Framer Motion or CSS-only?
4. **Image Lazy Loading:** Native lazy loading or intersection observer?
5. **State Management:** Keep current or add Zustand/Jotai?
6. **Testing Strategy:** Which test types are priorities?

---

## Next Steps

1. Review this plan and provide feedback
2. Prioritize any specific features
3. Approve color palette or suggest changes
4. Begin Phase 1: Foundation setup
5. Create design mockups (optional - can use Figma/screenshots)

---

## Notes

- NSFW filtering already in settings menu - will maintain that pattern
- Current backend auth flow (OAuth) will remain unchanged
- All existing features will be preserved
- Focus on visual redesign, not functional changes
- Progressive enhancement approach (works without JS for public gallery)

---

**Estimated Total Time:** 19-25 days (4-5 weeks)

**Recommended Approach:** Start with Phase 1 (Foundation), get approval on design tokens/colors, then proceed phase by phase with regular check-ins.
