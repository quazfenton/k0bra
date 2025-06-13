/**
 * Represents a single, abstract, multi-sensory "Vibe" on the VibeWeave platform.
 * Vibes are ephemeral and are not directly attributed to a user.
 */
export interface Vibe {
    id: string; // Unique identifier for the Vibe
    createdAt: number; // Timestamp of creation (Unix epoch)
    expiresAt: number; // Timestamp when the Vibe dissolves (e.g., 48 hours after creation)
    
    // Abstract visual properties
    visual: {
        palette: string[]; // Array of hex color codes
        animationType: 'pulse' | 'flow' | 'sparkle' | 'wave' | 'static';
        intensity: number; // 0-100, how strong the visual effect is
    };

    // Abstract auditory properties
    audio: {
        loopUrl: string; // URL to a short, ambient sound loop (e.g., generated synth, nature sound)
        volume: number; // 0-100
        pitchShift?: number; // Optional, for blending effects
    };

    // Abstract haptic properties (for mobile)
    haptic?: {
        pattern: 'short_buzz' | 'long_pulse' | 'gentle_throb' | 'random';
        intensity: number; // 0-100
    };

    // Optional, minimal textual element
    text?: {
        content: string; // A single word or emoji
        fontStyle: 'serif' | 'sans-serif' | 'monospace';
        color: string; // Hex color code
    };

    // Internal metadata for blending and resonance (not publicly visible)
    _internal: {
        parentVibeIds: string[]; // IDs of Vibes this Vibe was woven from
        resonanceScore: number; // Accumulated private resonance (influences propagation)
        generation: number; // How many times this Vibe has been blended/re-woven
    };
}
