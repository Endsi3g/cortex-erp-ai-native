export class ScannerFeedback {
  private static audioCtx: AudioContext | null = null

  private static getAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null
    if (!this.audioCtx) {
      const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (AudioCtxClass) {
        this.audioCtx = new AudioCtxClass()
      }
    }
    return this.audioCtx
  }

  public static playSuccess(): void {
    try {
      const ctx = this.getAudioContext()
      if (!ctx) return
      if (ctx.state === 'suspended') {
        ctx.resume()
      }

      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(1200, ctx.currentTime)
      gain.gain.setValueAtTime(0.1, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1)

      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.1)

      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(50)
      }
    } catch {
      // Audio context might be restricted before user gesture
    }
  }

  public static playError(): void {
    try {
      const ctx = this.getAudioContext()
      if (!ctx) return
      if (ctx.state === 'suspended') {
        ctx.resume()
      }

      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(300, ctx.currentTime)
      gain.gain.setValueAtTime(0.15, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25)

      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + 0.25)

      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate([100, 50, 100])
      }
    } catch {
      // Audio context might be restricted
    }
  }
}

export function sanitizeBarcodeInput(raw: string): string {
  if (!raw) return ''
  return raw.trim().replace(/[\r\n\t]/g, '')
}

export function detectBarcodeType(barcode: string): 'serial' | 'item' | 'rental' | 'unknown' {
  const clean = sanitizeBarcodeInput(barcode)
  if (clean.startsWith('DEMO-SN-') || clean.startsWith('SN-')) return 'serial'
  if (clean.startsWith('DEMO-ITM-') || clean.startsWith('ITM-')) return 'item'
  if (clean.startsWith('DEMO-TRX-') || clean.startsWith('TRX-') || clean.startsWith('RN-')) return 'rental'
  return 'unknown'
}
