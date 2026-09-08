import { ref, computed, type Ref } from 'vue'

export interface VirtualMatrixOptions<T> {
  items: Ref<T[]>
  rowHeight: number
  viewportHeight: Ref<number>
  overscan?: number
}

export function useVirtualMatrix<T>(options: VirtualMatrixOptions<T>) {
  const scrollTop = ref(0)
  const overscan = options.overscan ?? 5

  const totalCount = computed(() => options.items.value.length)
  const totalHeight = computed(() => totalCount.value * options.rowHeight)

  const onScroll = (e: Event) => {
    const target = e.target as HTMLElement
    if (target) {
      scrollTop.value = target.scrollTop
    }
  }

  const startIndex = computed(() => {
    return Math.max(0, Math.floor(scrollTop.value / options.rowHeight) - overscan)
  })

  const endIndex = computed(() => {
    const visibleCount = Math.ceil(options.viewportHeight.value / options.rowHeight)
    return Math.min(totalCount.value, startIndex.value + visibleCount + overscan * 2)
  })

  const visibleItems = computed(() => {
    return options.items.value.slice(startIndex.value, endIndex.value).map((item, i) => ({
      item,
      index: startIndex.value + i,
      top: (startIndex.value + i) * options.rowHeight
    }))
  })

  const offsetY = computed(() => startIndex.value * options.rowHeight)

  return {
    scrollTop,
    totalHeight,
    startIndex,
    endIndex,
    visibleItems,
    offsetY,
    onScroll
  }
}
