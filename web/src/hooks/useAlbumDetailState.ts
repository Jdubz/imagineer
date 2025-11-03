import { useReducer, useCallback, useRef, useEffect } from 'react'
import { logger } from '../lib/logger'

/**
 * Album image structure
 */
export interface AlbumImage {
  id?: number
  filename: string
  thumbnail_path?: string | null
  is_nsfw?: boolean
  labels?: Label[]
  label_count?: number
  manual_label_count?: number
}

/**
 * Label structure
 */
export interface Label {
  id: number
  image_id: number
  label_text: string
  confidence?: number | null
  label_type?: string | null
  source_model?: string | null
  source_prompt?: string | null
  created_by?: string | null
  created_at?: string | null
}

/**
 * State for the album detail view
 */
export interface AlbumDetailState {
  images: AlbumImage[]
  selectedImages: Set<string>
  nsfwSetting: 'hide' | 'blur' | 'show'
  labelInputs: Record<number, string>
  editingLabel: { imageId: number; labelId: number; value: string } | null
  labelError: string | null
  loadingStates: {
    removingImages: boolean
    addingLabel: Set<number> // Track per-image
    deletingLabel: Set<string> // Track by imageId-labelId key
    editingLabel: boolean
  }
  optimisticUpdates: {
    pendingLabelAdds: Map<number, string> // imageId -> label text
    pendingLabelDeletes: Set<string> // imageId-labelId keys
    pendingLabelEdits: Map<string, string> // imageId-labelId -> new text
  }
}

/**
 * Actions for state management
 */
type AlbumDetailAction =
  | { type: 'RESET'; images: AlbumImage[] }
  | { type: 'TOGGLE_IMAGE_SELECTION'; imageId: string }
  | { type: 'CLEAR_SELECTED_IMAGES' }
  | { type: 'SET_NSFW_SETTING'; setting: 'hide' | 'blur' | 'show' }
  | { type: 'UPDATE_LABEL_INPUT'; imageId: number; value: string }
  | { type: 'CLEAR_LABEL_INPUT'; imageId: number }
  | { type: 'SET_LABEL_ERROR'; error: string | null }
  | { type: 'START_EDITING_LABEL'; imageId: number; labelId: number; value: string }
  | { type: 'UPDATE_EDITING_LABEL'; value: string }
  | { type: 'CANCEL_EDITING_LABEL' }
  // Optimistic updates
  | { type: 'OPTIMISTIC_ADD_LABEL'; imageId: number; labelText: string }
  | { type: 'OPTIMISTIC_DELETE_LABEL'; imageId: number; labelId: number }
  | { type: 'OPTIMISTIC_EDIT_LABEL'; imageId: number; labelId: number; newText: string }
  // Confirm optimistic updates
  | { type: 'CONFIRM_ADD_LABEL'; imageId: number; newLabel: Label }
  | { type: 'CONFIRM_DELETE_LABEL'; imageId: number; labelId: number }
  | { type: 'CONFIRM_EDIT_LABEL'; imageId: number; labelId: number; newText: string }
  // Rollback optimistic updates
  | { type: 'ROLLBACK_ADD_LABEL'; imageId: number }
  | { type: 'ROLLBACK_DELETE_LABEL'; imageId: number; labelId: number; originalLabel: Label }
  | { type: 'ROLLBACK_EDIT_LABEL'; imageId: number; labelId: number; originalText: string }
  // Loading states
  | { type: 'SET_REMOVING_IMAGES'; isLoading: boolean }
  | { type: 'SET_ADDING_LABEL'; imageId: number; isLoading: boolean }
  | { type: 'SET_DELETING_LABEL'; imageId: number; labelId: number; isLoading: boolean }
  | { type: 'SET_EDITING_LABEL_LOADING'; isLoading: boolean }
  // Update images from server
  | { type: 'UPDATE_IMAGES'; images: AlbumImage[] }

/**
 * Initial state factory
 */
const createInitialState = (images: AlbumImage[]): AlbumDetailState => ({
  images,
  selectedImages: new Set(),
  nsfwSetting: 'blur',
  labelInputs: {},
  editingLabel: null,
  labelError: null,
  loadingStates: {
    removingImages: false,
    addingLabel: new Set(),
    deletingLabel: new Set(),
    editingLabel: false,
  },
  optimisticUpdates: {
    pendingLabelAdds: new Map(),
    pendingLabelDeletes: new Set(),
    pendingLabelEdits: new Map(),
  },
})

/**
 * Helper to create label delete key
 */
const createLabelKey = (imageId: number, labelId: number): string =>
  `${imageId}-${labelId}`

/**
 * Reducer function for album detail state
 */
function albumDetailReducer(
  state: AlbumDetailState,
  action: AlbumDetailAction
): AlbumDetailState {
  switch (action.type) {
    case 'RESET':
      return createInitialState(action.images)

    case 'TOGGLE_IMAGE_SELECTION': {
      const newSelected = new Set(state.selectedImages)
      if (newSelected.has(action.imageId)) {
        newSelected.delete(action.imageId)
      } else {
        newSelected.add(action.imageId)
      }
      return { ...state, selectedImages: newSelected }
    }

    case 'CLEAR_SELECTED_IMAGES':
      return { ...state, selectedImages: new Set() }

    case 'SET_NSFW_SETTING':
      return { ...state, nsfwSetting: action.setting }

    case 'UPDATE_LABEL_INPUT':
      return {
        ...state,
        labelInputs: { ...state.labelInputs, [action.imageId]: action.value },
      }

    case 'CLEAR_LABEL_INPUT': {
      const newInputs = { ...state.labelInputs }
      delete newInputs[action.imageId]
      return { ...state, labelInputs: newInputs }
    }

    case 'SET_LABEL_ERROR':
      return { ...state, labelError: action.error }

    case 'START_EDITING_LABEL':
      return {
        ...state,
        editingLabel: {
          imageId: action.imageId,
          labelId: action.labelId,
          value: action.value,
        },
        labelError: null,
      }

    case 'UPDATE_EDITING_LABEL':
      return state.editingLabel
        ? {
            ...state,
            editingLabel: { ...state.editingLabel, value: action.value },
          }
        : state

    case 'CANCEL_EDITING_LABEL':
      return { ...state, editingLabel: null, labelError: null }

    // Optimistic updates
    case 'OPTIMISTIC_ADD_LABEL': {
      const newPendingAdds = new Map(state.optimisticUpdates.pendingLabelAdds)
      newPendingAdds.set(action.imageId, action.labelText)
      return {
        ...state,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelAdds: newPendingAdds,
        },
      }
    }

    case 'OPTIMISTIC_DELETE_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingDeletes = new Set(state.optimisticUpdates.pendingLabelDeletes)
      newPendingDeletes.add(key)
      return {
        ...state,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelDeletes: newPendingDeletes,
        },
      }
    }

    case 'OPTIMISTIC_EDIT_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingEdits = new Map(state.optimisticUpdates.pendingLabelEdits)
      newPendingEdits.set(key, action.newText)
      return {
        ...state,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelEdits: newPendingEdits,
        },
      }
    }

    // Confirm optimistic updates
    case 'CONFIRM_ADD_LABEL': {
      const newPendingAdds = new Map(state.optimisticUpdates.pendingLabelAdds)
      newPendingAdds.delete(action.imageId)

      // Add the confirmed label to images
      const newImages = state.images.map((img) =>
        img.id === action.imageId
          ? {
              ...img,
              labels: [...(img.labels || []), action.newLabel],
              label_count: (img.label_count || 0) + 1,
              manual_label_count: (img.manual_label_count || 0) + 1,
            }
          : img
      )

      return {
        ...state,
        images: newImages,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelAdds: newPendingAdds,
        },
      }
    }

    case 'CONFIRM_DELETE_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingDeletes = new Set(state.optimisticUpdates.pendingLabelDeletes)
      newPendingDeletes.delete(key)

      // Remove the label from images
      const newImages = state.images.map((img) =>
        img.id === action.imageId
          ? {
              ...img,
              labels: (img.labels || []).filter((l) => l.id !== action.labelId),
              label_count: Math.max((img.label_count || 0) - 1, 0),
              manual_label_count: Math.max((img.manual_label_count || 0) - 1, 0),
            }
          : img
      )

      return {
        ...state,
        images: newImages,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelDeletes: newPendingDeletes,
        },
      }
    }

    case 'CONFIRM_EDIT_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingEdits = new Map(state.optimisticUpdates.pendingLabelEdits)
      newPendingEdits.delete(key)

      // Update the label text
      const newImages = state.images.map((img) =>
        img.id === action.imageId
          ? {
              ...img,
              labels: (img.labels || []).map((l) =>
                l.id === action.labelId ? { ...l, label_text: action.newText } : l
              ),
            }
          : img
      )

      return {
        ...state,
        images: newImages,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelEdits: newPendingEdits,
        },
      }
    }

    // Rollback optimistic updates
    case 'ROLLBACK_ADD_LABEL': {
      const newPendingAdds = new Map(state.optimisticUpdates.pendingLabelAdds)
      newPendingAdds.delete(action.imageId)
      return {
        ...state,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelAdds: newPendingAdds,
        },
      }
    }

    case 'ROLLBACK_DELETE_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingDeletes = new Set(state.optimisticUpdates.pendingLabelDeletes)
      newPendingDeletes.delete(key)

      // Restore the label
      const newImages = state.images.map((img) =>
        img.id === action.imageId
          ? {
              ...img,
              labels: [...(img.labels || []), action.originalLabel],
              label_count: (img.label_count || 0) + 1,
              manual_label_count: (img.manual_label_count || 0) + 1,
            }
          : img
      )

      return {
        ...state,
        images: newImages,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelDeletes: newPendingDeletes,
        },
      }
    }

    case 'ROLLBACK_EDIT_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newPendingEdits = new Map(state.optimisticUpdates.pendingLabelEdits)
      newPendingEdits.delete(key)

      // Restore original text
      const newImages = state.images.map((img) =>
        img.id === action.imageId
          ? {
              ...img,
              labels: (img.labels || []).map((l) =>
                l.id === action.labelId ? { ...l, label_text: action.originalText } : l
              ),
            }
          : img
      )

      return {
        ...state,
        images: newImages,
        optimisticUpdates: {
          ...state.optimisticUpdates,
          pendingLabelEdits: newPendingEdits,
        },
      }
    }

    // Loading states
    case 'SET_REMOVING_IMAGES':
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          removingImages: action.isLoading,
        },
      }

    case 'SET_ADDING_LABEL': {
      const newAddingLabel = new Set(state.loadingStates.addingLabel)
      if (action.isLoading) {
        newAddingLabel.add(action.imageId)
      } else {
        newAddingLabel.delete(action.imageId)
      }
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          addingLabel: newAddingLabel,
        },
      }
    }

    case 'SET_DELETING_LABEL': {
      const key = createLabelKey(action.imageId, action.labelId)
      const newDeletingLabel = new Set(state.loadingStates.deletingLabel)
      if (action.isLoading) {
        newDeletingLabel.add(key)
      } else {
        newDeletingLabel.delete(key)
      }
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          deletingLabel: newDeletingLabel,
        },
      }
    }

    case 'SET_EDITING_LABEL_LOADING':
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          editingLabel: action.isLoading,
        },
      }

    case 'UPDATE_IMAGES':
      return {
        ...state,
        images: action.images,
      }

    default:
      return state
  }
}

/**
 * Options for the hook
 */
export interface UseAlbumDetailStateOptions {
  albumId: string
  initialImages: AlbumImage[]
  onRefresh: () => Promise<unknown>
  onRefreshAnalytics: () => Promise<unknown>
}

/**
 * Return type for the hook
 */
export interface UseAlbumDetailStateReturn {
  state: AlbumDetailState
  actions: {
    toggleImageSelection: (imageId: number) => void
    setNsfwSetting: (setting: 'hide' | 'blur' | 'show') => void
    updateLabelInput: (imageId: number, value: string) => void
    removeSelectedImages: () => Promise<void>
    addLabel: (imageId: number) => Promise<void>
    deleteLabel: (imageId: number, labelId: number) => Promise<void>
    startEditingLabel: (imageId: number, label: Label) => void
    updateEditingLabel: (value: string) => void
    cancelEditingLabel: () => void
    saveEditedLabel: () => Promise<void>
  }
  isLoading: {
    addingLabel: (imageId: number) => boolean
    deletingLabel: (imageId: number, labelId: number) => boolean
  }
}

/**
 * Custom hook for managing album detail state with proper synchronization
 * and optimistic updates.
 *
 * Features:
 * - useReducer for predictable state updates
 * - Optimistic updates for better UX
 * - AbortController for request cancellation
 * - Granular loading states per operation
 * - No race conditions
 *
 * @param options Configuration options
 * @returns State and actions for album detail management
 */
export function useAlbumDetailState(
  options: UseAlbumDetailStateOptions
): UseAlbumDetailStateReturn {
  const { albumId, initialImages, onRefresh, onRefreshAnalytics } = options

  const [state, dispatch] = useReducer(
    albumDetailReducer,
    initialImages,
    createInitialState
  )

  // AbortController for canceling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null)

  // Reset state when album changes
  useEffect(() => {
    dispatch({ type: 'RESET', images: initialImages })

    // Cancel any in-flight requests when album changes
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    return () => {
      // Cleanup on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [albumId, initialImages])

  // Refresh album data from server
  const refreshAlbumData = useCallback(async (): Promise<void> => {
    await Promise.all([onRefresh(), onRefreshAnalytics()])
  }, [onRefresh, onRefreshAnalytics])

  // Toggle image selection
  const toggleImageSelection = useCallback((imageId: number): void => {
    dispatch({ type: 'TOGGLE_IMAGE_SELECTION', imageId: String(imageId) })
  }, [])

  // Set NSFW setting
  const setNsfwSetting = useCallback((setting: 'hide' | 'blur' | 'show'): void => {
    dispatch({ type: 'SET_NSFW_SETTING', setting })
  }, [])

  // Update label input
  const updateLabelInput = useCallback((imageId: number, value: string): void => {
    dispatch({ type: 'UPDATE_LABEL_INPUT', imageId, value })
  }, [])

  // Remove selected images
  const removeSelectedImages = useCallback(async (): Promise<void> => {
    if (state.selectedImages.size === 0) return

    dispatch({ type: 'SET_REMOVING_IMAGES', isLoading: true })

    try {
      const signal = abortControllerRef.current?.signal

      await Promise.all(
        Array.from(state.selectedImages).map((imageId) =>
          fetch(`/api/albums/${albumId}/images/${imageId}`, {
            method: 'DELETE',
            credentials: 'include',
            signal,
          }).catch((error) => {
            if (error.name !== 'AbortError') {
              logger.error(`Failed to remove image ${imageId}`, error)
            }
          })
        )
      )

      dispatch({ type: 'CLEAR_SELECTED_IMAGES' })
      await refreshAlbumData()
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        logger.error('Failed to remove images', error)
      }
    } finally {
      dispatch({ type: 'SET_REMOVING_IMAGES', isLoading: false })
    }
  }, [state.selectedImages, albumId, refreshAlbumData])

  // Add label with optimistic update
  const addLabel = useCallback(
    async (imageId: number): Promise<void> => {
      const value = (state.labelInputs[imageId] || '').trim()
      if (!value) {
        dispatch({ type: 'SET_LABEL_ERROR', error: 'Label text cannot be empty.' })
        return
      }

      dispatch({ type: 'SET_LABEL_ERROR', error: null })
      dispatch({ type: 'SET_ADDING_LABEL', imageId, isLoading: true })
      dispatch({ type: 'OPTIMISTIC_ADD_LABEL', imageId, labelText: value })

      try {
        const signal = abortControllerRef.current?.signal
        const response = await fetch(`/api/images/${imageId}/labels`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          signal,
          body: JSON.stringify({ text: value, type: 'manual' }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(
            typeof errorData.error === 'string' ? errorData.error : 'Failed to add label'
          )
        }

        const newLabel = (await response.json()) as Label

        dispatch({ type: 'CONFIRM_ADD_LABEL', imageId, newLabel })
        dispatch({ type: 'CLEAR_LABEL_INPUT', imageId })
        await refreshAlbumData()
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          dispatch({ type: 'ROLLBACK_ADD_LABEL', imageId })
          const message =
            error instanceof Error ? error.message : 'Failed to add label'
          dispatch({ type: 'SET_LABEL_ERROR', error: message })
          logger.error('Failed to add label:', error)
        }
      } finally {
        dispatch({ type: 'SET_ADDING_LABEL', imageId, isLoading: false })
      }
    },
    [state.labelInputs, refreshAlbumData]
  )

  // Delete label with optimistic update
  const deleteLabel = useCallback(
    async (imageId: number, labelId: number): Promise<void> => {
      if (!window.confirm('Remove this label?')) return

      // Find the original label for rollback
      const image = state.images.find((img) => img.id === imageId)
      const originalLabel = image?.labels?.find((l) => l.id === labelId)
      if (!originalLabel) return

      dispatch({ type: 'SET_LABEL_ERROR', error: null })
      dispatch({ type: 'SET_DELETING_LABEL', imageId, labelId, isLoading: true })
      dispatch({ type: 'OPTIMISTIC_DELETE_LABEL', imageId, labelId })

      try {
        const signal = abortControllerRef.current?.signal
        const response = await fetch(`/api/images/${imageId}/labels/${labelId}`, {
          method: 'DELETE',
          credentials: 'include',
          signal,
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(
            typeof errorData.error === 'string'
              ? errorData.error
              : 'Failed to remove label'
          )
        }

        dispatch({ type: 'CONFIRM_DELETE_LABEL', imageId, labelId })
        await refreshAlbumData()
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          dispatch({
            type: 'ROLLBACK_DELETE_LABEL',
            imageId,
            labelId,
            originalLabel,
          })
          const message =
            error instanceof Error ? error.message : 'Failed to remove label'
          dispatch({ type: 'SET_LABEL_ERROR', error: message })
          logger.error('Failed to remove label:', error)
        }
      } finally {
        dispatch({ type: 'SET_DELETING_LABEL', imageId, labelId, isLoading: false })
      }
    },
    [state.images, refreshAlbumData]
  )

  // Start editing label
  const startEditingLabel = useCallback((imageId: number, label: { id: number; label_text: string }): void => {
    dispatch({
      type: 'START_EDITING_LABEL',
      imageId,
      labelId: label.id,
      value: label.label_text,
    })
  }, [])

  // Update editing label value
  const updateEditingLabel = useCallback((value: string): void => {
    dispatch({ type: 'UPDATE_EDITING_LABEL', value })
  }, [])

  // Cancel editing label
  const cancelEditingLabel = useCallback((): void => {
    dispatch({ type: 'CANCEL_EDITING_LABEL' })
  }, [])

  // Save edited label with optimistic update
  const saveEditedLabel = useCallback(async (): Promise<void> => {
    if (!state.editingLabel) return

    const trimmed = state.editingLabel.value.trim()
    if (!trimmed) {
      dispatch({ type: 'SET_LABEL_ERROR', error: 'Label text cannot be empty.' })
      return
    }

    const { imageId, labelId } = state.editingLabel

    // Find original text for rollback
    const image = state.images.find((img) => img.id === imageId)
    const originalLabel = image?.labels?.find((l) => l.id === labelId)
    if (!originalLabel) return

    dispatch({ type: 'SET_LABEL_ERROR', error: null })
    dispatch({ type: 'SET_EDITING_LABEL_LOADING', isLoading: true })
    dispatch({
      type: 'OPTIMISTIC_EDIT_LABEL',
      imageId,
      labelId,
      newText: trimmed,
    })

    try {
      const signal = abortControllerRef.current?.signal
      const response = await fetch(`/api/images/${imageId}/labels/${labelId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal,
        body: JSON.stringify({ text: trimmed }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          typeof errorData.error === 'string'
            ? errorData.error
            : 'Failed to update label'
        )
      }

      dispatch({ type: 'CONFIRM_EDIT_LABEL', imageId, labelId, newText: trimmed })
      dispatch({ type: 'CANCEL_EDITING_LABEL' })
      await refreshAlbumData()
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        dispatch({
          type: 'ROLLBACK_EDIT_LABEL',
          imageId,
          labelId,
          originalText: originalLabel.label_text,
        })
        const message =
          error instanceof Error ? error.message : 'Failed to update label'
        dispatch({ type: 'SET_LABEL_ERROR', error: message })
        logger.error('Failed to update label:', error)
      }
    } finally {
      dispatch({ type: 'SET_EDITING_LABEL_LOADING', isLoading: false })
    }
  }, [state.editingLabel, state.images, refreshAlbumData])

  // Helper functions to check loading states
  const isAddingLabel = useCallback(
    (imageId: number): boolean => state.loadingStates.addingLabel.has(imageId),
    [state.loadingStates.addingLabel]
  )

  const isDeletingLabel = useCallback(
    (imageId: number, labelId: number): boolean =>
      state.loadingStates.deletingLabel.has(createLabelKey(imageId, labelId)),
    [state.loadingStates.deletingLabel]
  )

  return {
    state,
    actions: {
      toggleImageSelection,
      setNsfwSetting,
      updateLabelInput,
      removeSelectedImages,
      addLabel,
      deleteLabel,
      startEditingLabel,
      updateEditingLabel,
      cancelEditingLabel,
      saveEditedLabel,
    },
    isLoading: {
      addingLabel: isAddingLabel,
      deletingLabel: isDeletingLabel,
    },
  }
}
