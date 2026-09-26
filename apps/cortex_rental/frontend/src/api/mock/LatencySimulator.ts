export type LatencyProfile = 'fast' | 'standard' | 'heavy' | 'mutation' | 'ai'

export class LatencySimulator {
  private static enabled = true

  public static setEnabled(enabled: boolean) {
    this.enabled = enabled
  }

  public static async inject(profile: LatencyProfile = 'standard'): Promise<void> {
    if (!this.enabled) return

    const delays: Record<LatencyProfile, [number, number]> = {
      fast: [10, 30],         // Fast local scans
      standard: [20, 50],     // Standard list/get
      heavy: [40, 80],        // Availability matrix
      mutation: [30, 70],     // Mutations
      ai: [60, 120]           // AI calls
    }

    const [min, max] = delays[profile]
    const ms = Math.floor(Math.random() * (max - min + 1)) + min
    await new Promise((resolve) => setTimeout(resolve, ms))
  }
}
