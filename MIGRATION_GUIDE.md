# Component Migration Guide

## Phase 2: Core Component Migration Strategy

### Migration Order (by priority and dependencies)

1. **Button Components** ✓ (Current)
2. **Form Components** (Input, Label, Textarea, Select)
3. **Card Components**
4. **Toast/Toaster**
5. **Dialog/Modal**

---

## 1. Button Migration

### Current Usage Patterns

**CSS Classes:**
- `.auth-button`, `.auth-button--primary`, `.auth-button--secondary`
- `.refresh-btn`, `.back-button`, `.submit-btn`
- `.generate-seed-btn`, `.random-theme-btn`
- `.toggle-lora-btn`, `.add-lora-btn`, `.remove-lora-btn`
- `.modal-close`, `.collapse-btn`

**Component Usage:**
- AuthButton.tsx - Login/Logout buttons
- GenerateForm.tsx - Submit, seed generation
- ImageGrid.tsx - Refresh button
- BatchGallery.tsx - Back button
- LorasTab.tsx - Add/remove LoRA buttons
- Modal overlays - Close buttons

### Migration Strategy

**shadcn Button Variants:**
```tsx
variant="default"    // Primary actions (coral pink) - was .auth-button--primary
variant="secondary"  // Secondary actions (turquoise) - was .auth-button--secondary
variant="outline"    // Border buttons - was .refresh-btn
variant="ghost"      // Minimal buttons - was .collapse-btn
variant="destructive" // Delete/remove - was .remove-lora-btn
variant="link"       // Link-style buttons
```

**Size mapping:**
```tsx
size="sm"      // Small buttons
size="default" // Standard buttons
size="lg"      // Large submit buttons
size="icon"    // Icon-only buttons (close, etc.)
```

### Implementation Steps

1. **Create wrapper components for common patterns**
   - `RefreshButton.tsx` - Standardized refresh button
   - `BackButton.tsx` - Navigation back button
   - `SubmitButton.tsx` - Form submit button with loading state

2. **Migrate component by component**
   - Start with simple button-only components
   - Test each migration before moving to next
   - Update tests as needed

3. **Remove old CSS**
   - After migration complete, remove button styles from CSS files
   - Keep migration PR focused (don't migrate everything at once)

---

## 2. Form Components Migration

### Current Patterns
- Custom styled inputs with `.seed-input`, `.form-group input`
- Custom labels with `.form-group label`
- Custom textareas with `.form-group textarea`
- Custom selects with `.form-group select`

### shadcn Approach
```tsx
<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input id="email" placeholder="Enter email..." />
</div>
```

### Benefits
- Consistent focus states
- Built-in error handling
- Accessibility improvements
- Keyboard navigation

---

## 3. Card Migration

### Current Patterns
- `.generate-form` - Form containers
- `.batch-list` - List containers
- `.image-grid-container` - Grid containers
- `.config-display` - Configuration display
- `.modal-content` - Modal content

### shadcn Card Structure
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
  <CardFooter>
    {/* Actions */}
  </CardFooter>
</Card>
```

---

## 4. Toast Migration

### Current Implementation
- Custom Toast component with ToastContext
- Custom styling in Toast.css

### shadcn Toast (Sonner)
- Uses Radix UI primitives
- Better animations
- Multiple toasts stacking
- Action buttons support

### Migration Notes
- Keep existing `useToast` hook API if possible
- Update `ToastContext` to use shadcn toaster
- Gradual migration (both can coexist initially)

---

## 5. Dialog/Modal Migration

### Current Implementation
- Custom modal with `.modal`, `.modal-content`, `.modal-close`
- Portal-based rendering
- Backdrop click to close

### shadcn Dialog
- Built-in focus trapping
- Better accessibility
- Keyboard navigation (ESC to close)
- Animation support

---

## Testing Strategy

### For Each Migration:
1. **Visual Regression**
   - Take screenshots before/after
   - Verify colors, spacing, interactions

2. **Functionality Testing**
   - All click handlers work
   - Keyboard navigation works
   - Focus states correct
   - Loading states work

3. **Accessibility**
   - ARIA labels present
   - Tab order correct
   - Screen reader tested

4. **Responsive**
   - Mobile layouts work
   - Touch targets appropriate size

---

## Rollback Plan

If issues arise:
1. Keep old CSS files until migration complete
2. Use feature flags to toggle between old/new components
3. Git history allows easy revert
4. Incremental PR approach limits blast radius

---

## Success Criteria

Phase 2 Complete when:
- [ ] All buttons use shadcn Button
- [ ] All forms use shadcn Form components
- [ ] All containers use shadcn Card
- [ ] Toast system migrated to shadcn
- [ ] Modal/dialogs use shadcn Dialog
- [ ] Old CSS removed
- [ ] Tests passing
- [ ] No visual regressions
- [ ] Accessibility maintained/improved
