"use client";

class AudioAlertService {
  private ctx: AudioContext | null = null;
  private soundEnabled: boolean = true;

  constructor() {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("mezflow_kds_sound");
      this.soundEnabled = saved !== "false";
    }
  }

  public isEnabled(): boolean {
    return this.soundEnabled;
  }

  public setEnabled(enabled: boolean) {
    this.soundEnabled = enabled;
    if (typeof window !== "undefined") {
      localStorage.setItem("mezflow_kds_sound", enabled ? "true" : "false");
    }
  }

  private initContext() {
    if (typeof window === "undefined") return null;
    if (!this.ctx) {
      const AudioCtx =
        window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
    return this.ctx;
  }

  /**
   * High-contrast two-tone kitchen bell for new incoming orders (880Hz -> 1320Hz)
   */
  public playNewOrderChime() {
    if (!this.soundEnabled) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const now = ctx.currentTime;

      // Note 1: A5 (880Hz)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(880, now);
      gain1.gain.setValueAtTime(0.3, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      osc1.start(now);
      osc1.stop(now + 0.35);

      // Note 2: E6 (1318.5Hz)
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(1320, now + 0.12);
      gain2.gain.setValueAtTime(0.35, now + 0.12);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.65);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc2.start(now + 0.12);
      osc2.stop(now + 0.65);
    } catch {
      // Audio autoplay policy catch
    }
  }

  /**
   * Crisp confirmation tick when a card is bumped (1046Hz)
   */
  public playBumpSound() {
    if (!this.soundEnabled) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(1046.5, now); // C6
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.15);
    } catch {}
  }

  /**
   * Low reminder tone for recalled tickets or warnings
   */
  public playWarningSound() {
    if (!this.soundEnabled) return;
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(440, now);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.25);
    } catch {}
  }
}

export const audioAlerts = new AudioAlertService();
