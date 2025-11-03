# Error Toast with Bug Reporting Integration

## Overview

Error toasts now include a "Report Bug" button that automatically populates a bug report with:
- Error message
- Trace ID (if available from API errors)
- HTTP status code
- Stack trace
- Response data
- User context

## Usage

### Basic Example

```typescript
import { useErrorToast } from '../hooks/use-error-toast'

function MyComponent() {
  const { showErrorToast } = useErrorToast()

  const handleAction = async () => {
    try {
      await api.someAction()
    } catch (error) {
      showErrorToast({
        context: 'Failed to perform action',
        error,
      })
    }
  }

  return <Button onClick={handleAction}>Do Something</Button>
}
```

### With Custom Title

```typescript
showErrorToast({
  title: 'Upload Failed',
  context: 'Could not upload image to album',
  error,
})
```

## Features

### Automatic Trace ID Display

If the error is an `ApiError` with a `traceId`, it will be displayed in the toast:

```
Failed to load album

Trace ID: abc123def456
```

### Pre-filled Bug Report

When the user clicks "Report Bug", the bug report modal opens with:

```
Failed to load album

Error: Album not found
Trace ID: abc123def456
HTTP Status: 404

Stack Trace:
Error: Album not found
    at fetchAlbum (api.ts:123)
    ...

Response Data:
{
  "error": "Album with ID 42 not found",
  "code": "ALBUM_NOT_FOUND"
}
```

## API

### `useErrorToast()`

Returns an object with:

#### `showErrorToast(options: ErrorToastOptions): void`

Shows an error toast with optional bug report button.

**Options:**
- `title?: string` - Toast title (default: "Error")
- `context?: string` - Context message describing what failed
- `error: unknown` - The error object (ApiError, Error, or any)

## Error Data Extraction

The hook automatically extracts:

1. **For ApiError instances:**
   - `message` - Error message
   - `traceId` - Backend trace ID for debugging
   - `status` - HTTP status code
   - `response` - Full API response body
   - `stack` - JavaScript stack trace

2. **For Error instances:**
   - `message` - Error message
   - `stack` - JavaScript stack trace

3. **For other types:**
   - Converts to string representation

## Migration Guide

### Before

```typescript
import { useToast } from '../hooks/use-toast'
import { formatErrorMessage } from '../lib/errorUtils'

const { toast } = useToast()

toast({
  title: 'Error',
  description: formatErrorMessage(error, 'Failed to load data'),
  variant: 'destructive'
})
```

### After

```typescript
import { useErrorToast } from '../hooks/use-error-toast'

const { showErrorToast } = useErrorToast()

showErrorToast({
  context: 'Failed to load data',
  error
})
```

## Benefits

1. **Faster Bug Reports** - One click to report with all context
2. **Better Debugging** - Trace IDs make backend correlation easy
3. **User Empowerment** - Users can self-report issues
4. **Consistent UX** - Standardized error handling across app
5. **Developer Friendly** - Simple API, auto-extracted data

## Implementation Details

### File Structure

```
web/src/
├── hooks/
│   ├── use-error-toast.tsx      # Main hook
│   └── use-toast.ts              # Base toast hook
├── lib/
│   └── errorUtils.ts             # Error extraction utilities
└── components/ui/
    └── toast.tsx                 # Toast UI components
```

### Dependencies

- `@radix-ui/react-toast` - Toast primitive
- BugReportContext - Bug report modal
- ApiError - Typed API errors with trace IDs

## Testing

To test the error toast flow:

1. Trigger any API error (e.g., try loading non-existent album)
2. Error toast appears with "Report Bug" button
3. Click "Report Bug"
4. Bug report modal opens with pre-filled error details
5. Verify trace ID and stack trace are included
6. Submit report (screenshot is auto-captured)
7. Report saved with all context

## Future Enhancements

- [ ] Add error categorization (network, validation, permission, etc.)
- [ ] Implement error retry button for transient failures
- [ ] Add "Copy Trace ID" button to toast
- [ ] Track error frequency for common issues
- [ ] Auto-dismiss on successful retry
