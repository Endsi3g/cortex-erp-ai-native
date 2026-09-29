import { onBeforeUnmount, ref } from 'vue'

/** Countdown for « Renvoyer le lien » buttons: the button stays disabled until `remaining` reaches 0. */
export function useCooldown(seconds = 60) {
  const remaining = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null
  const stop = () => {
    if (timer) clearInterval(timer)
    timer = null
  }
  const start = () => {
    stop()
    remaining.value = seconds
    timer = setInterval(() => {
      remaining.value -= 1
      if (remaining.value <= 0) stop()
    }, 1000)
  }
  onBeforeUnmount(stop)
  return { remaining, start }
}
