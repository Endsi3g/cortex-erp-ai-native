import { onMounted, ref, type Ref } from 'vue'

export interface ResourceState<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  /** True when the server has no endpoint for this feature: shown as "indisponible", never as empty data. */
  unavailable: Ref<boolean>
  reload: () => Promise<void>
}

export function useResource<T>(fetcher: () => Promise<T>, options: { immediate?: boolean } = {}): ResourceState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<string | null>(null)
  const unavailable = ref(false)

  async function reload(): Promise<void> {
    loading.value = true
    error.value = null
    unavailable.value = false
    try {
      data.value = await fetcher()
    } catch (cause) {
      const flagged = typeof cause === 'object' && cause !== null && (cause as { unavailable?: boolean }).unavailable === true
      unavailable.value = flagged
      error.value = cause instanceof Error ? cause.message : 'Chargement impossible.'
    } finally {
      loading.value = false
    }
  }

  if (options.immediate !== false) onMounted(reload)
  return { data, loading, error, unavailable, reload }
}
