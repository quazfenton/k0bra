import { Vibe } from '../types/Vibe';
import { Stream } from '../types/Stream';
import { VibeStore } from '../data/VibeStore';
import { v4 as uuidv4 } from 'uuid';
import { blendHexPalettes } from '../utils/colorUtils';

/**
 * A conceptual class for processing and generating Vibes.
 * In a real application, this would involve complex generative art algorithms,
 * audio synthesis, and database interactions.
 */
export class VibeProcessor {
    private VIBE_LIFESPAN_MS = 48 * 60 * 60 * 1000; // 48 hours in milliseconds
    private vibeStore: VibeStore;

    constructor(vibeStore: VibeStore) {
        this.vibeStore = vibeStore;
    }

    /**
     * Creates a new Vibe from scratch based on user input (abstract parameters).
     * @param visualParams User's chosen visual properties.
     * @param audioParams User's chosen audio properties.
     * @param hapticParams User's chosen haptic properties.
     * @param textParams User's chosen text properties.
     * @returns A new Vibe object.
     */
    public createNewVibe(
        visualParams: Vibe['visual'],
        audioParams: Vibe['audio'],
        hapticParams?: Vibe['haptic'],
        textParams?: Vibe['text']
    ): Vibe {
        const now = Date.now();
        const newVibe: Vibe = {
            id: uuidv4(),
            createdAt: now,
            expiresAt: now + this.VIBE_LIFESPAN_MS,
            visual: visualParams,
            audio: audioParams,
            haptic: hapticParams,
            text: textParams,
            _internal: {
                parentVibeIds: [],
                resonanceScore: 0, // Starts at 0
                generation: 0,
                lastResonatedAt: now, // Initialize last resonated time
            },
        };
        this.vibeStore.saveVibe(newVibe);
        return newVibe;
    }

    /**
     * Blends multiple existing Vibes into a new, unique Vibe.
     * This is where the "avant-garde" generative aspect comes in.
     * @param parentVibeIds An array of 1 to 3 Vibe IDs to blend.
     * @returns A new, blended Vibe, or null if parents are invalid or not found.
     */
    public weaveVibes(parentVibeIds: string[]): Vibe | null {
        if (parentVibeIds.length === 0 || parentVibeIds.length > 3) {
            console.error("Cannot weave: Must provide 1 to 3 parent Vibe IDs.");
            return null;
        }

        const parentVibes = this.vibeStore.getVibesByIds(parentVibeIds);
        if (parentVibes.length !== parentVibeIds.length) {
            console.error("Cannot weave: One or more parent Vibes not found.");
            return null;
        }

        const now = Date.now();
        const newVibe: Vibe = {
            id: uuidv4(),
            createdAt: now,
            expiresAt: now + this.VIBE_LIFESPAN_MS,
            visual: this.blendVisuals(parentVibes.map(v => v.visual)),
            audio: this.blendAudios(parentVibes.map(v => v.audio)),
            haptic: this.blendHaptics(parentVibes.map(v => v.haptic).filter(Boolean) as Vibe['haptic'][]),
            text: this.blendTexts(parentVibes.map(v => v.text).filter(Boolean) as Vibe['text'][]),
            _internal: {
                parentVibeIds: parentVibes.map(v => v.id),
                resonanceScore: 0,
                generation: Math.max(...parentVibes.map(v => v._internal.generation)) + 1,
                lastResonatedAt: now,
            },
        };
        this.vibeStore.saveVibe(newVibe);
        return newVibe;
    }

    /**
     * Simulates a user resonating with a Vibe.
     * In a real system, this would update a private user profile's resonance history
     * and subtly increment the Vibe's internal resonance score.
     * @param vibeId The ID of the Vibe being resonated with.
     * @returns The updated Vibe, or null if not found.
     */
    public resonateWithVibe(vibeId: string): Vibe | null {
        const vibe = this.vibeStore.getVibe(vibeId);
        if (!vibe) {
            console.error(`Vibe with ID ${vibeId} not found for resonance.`);
            return null;
        }

        // This is a simplified representation. In reality, this would involve
        // complex backend logic to update a Vibe's "energy" and influence
        // its propagation without exposing public metrics.
        vibe._internal.resonanceScore += 1;
        vibe._internal.lastResonatedAt = Date.now();
        this.vibeStore.saveVibe(vibe); // Persist the updated score
        console.log(`[VibeProcessor] Vibe ${vibe.id} resonated. New score: ${vibe._internal.resonanceScore}`);
        return vibe;
    }

    /**
     * Simulates the decay of a Vibe's resonance over time.
     * This would typically run as a background process.
     * @param decayRate The rate at which resonance decays (e.g., 0.1 per hour).
     */
    public decayVibeResonance(decayRate: number = 0.01): void {
        const now = Date.now();
        this.vibeStore.getAllActiveVibes().forEach(vibe => {
            const hoursSinceLastResonance = (now - vibe._internal.lastResonatedAt) / (1000 * 60 * 60);
            if (hoursSinceLastResonance > 1) { // Only decay if it's been at least an hour
                const decayAmount = vibe._internal.resonanceScore * decayRate * hoursSinceLastResonance;
                vibe._internal.resonanceScore = Math.max(0, vibe._internal.resonanceScore - decayAmount);
                this.vibeStore.saveVibe(vibe); // Persist decay
            }
        });
        console.log("[VibeProcessor] Vibe resonance decay applied.");
    }

    /**
     * Generates a list of Vibe IDs for a given stream.
     * @param streamType The type of stream ('personal' or 'collective').
     * @param associatedId For 'personal', this is the userId; for 'collective', a category ID.
     * @param limit The maximum number of Vibes to return.
     * @returns An array of Vibe IDs.
     */
    public getStreamVibes(streamType: Stream['type'], associatedId: string, limit: number = 20): string[] {
        const allActiveVibes = this.vibeStore.getAllActiveVibes();

        if (streamType === 'personal') {
            // For a personal stream, we'd ideally use a user's resonance history
            // and preferences. For this conceptual example, we'll simulate by
            // picking vibes that have been resonated with by this 'user' (associatedId)
            // or vibes that are generally popular and align with a mock user profile.
            // Since we don't have user profiles, let's just return a mix of highly resonated
            // vibes and some random ones.
            const highlyResonated = allActiveVibes
                .sort((a, b) => b._internal.resonanceScore - a._internal.resonanceScore)
                .slice(0, Math.floor(limit * 0.7)); // 70% popular

            const randomVibes = allActiveVibes
                .filter(v => !highlyResonated.includes(v))
                .sort(() => 0.5 - Math.random()) // Shuffle
                .slice(0, limit - highlyResonated.length); // Remaining 30% random

            return Array.from(new Set([...highlyResonated, ...randomVibes].map(v => v.id)));

        } else if (streamType === 'collective') {
            // For collective streams, we'll sort by resonance score to simulate trending vibes.
            // In a real app, 'associatedId' could filter by theme/category.
            return allActiveVibes
                .sort((a, b) => b._internal.resonanceScore - a._internal.resonanceScore)
                .slice(0, limit)
                .map(v => v.id);
        }
        return [];
    }

    // --- Private blending helper methods (enhanced) ---

    private blendVisuals(visuals: Vibe['visual'][]): Vibe['visual'] {
        const avgIntensity = visuals.reduce((sum, v) => sum + v.intensity, 0) / visuals.length;
        
        // Weighted random selection for animation type based on parent resonance (conceptual)
        const animationTypes = visuals.map(v => v.animationType);
        const chosenAnimationType = animationTypes[Math.floor(Math.random() * animationTypes.length)]; // Still random for simplicity

        const allParentColors = visuals.flatMap(v => v.palette);
        const blendedPalette = blendHexPalettes(allParentColors, 3); // Generate 3 colors for the new palette

        return {
            palette: blendedPalette,
            animationType: chosenAnimationType,
            intensity: Math.min(100, Math.max(0, Math.round(avgIntensity))),
        };
    }

    private blendAudios(audios: Vibe['audio'][]): Vibe['audio'] {
        const avgVolume = audios.reduce((sum, a) => sum + a.volume, 0) / audios.length;
        const avgPitchShift = audios.reduce((sum, a) => sum + (a.pitchShift || 0), 0) / audios.length;
        
        // Pick the most common loop URL or a random one
        const loopUrls = audios.map(a => a.loopUrl);
        const chosenLoopUrl = loopUrls[Math.floor(Math.random() * loopUrls.length)];

        return {
            loopUrl: chosenLoopUrl,
            volume: Math.min(100, Math.max(0, Math.round(avgVolume))),
            pitchShift: avgPitchShift,
        };
    }

    private blendHaptics(haptics: Vibe['haptic'][]): Vibe['haptic'] | undefined {
        if (haptics.length === 0) return undefined;
        const avgIntensity = haptics.reduce((sum, h) => sum + h.intensity, 0) / haptics.length;
        
        const patterns = haptics.map(h => h.pattern);
        const chosenPattern = patterns[Math.floor(Math.random() * patterns.length)];

        return {
            pattern: chosenPattern,
            intensity: Math.min(100, Math.max(0, Math.round(avgIntensity))),
        };
    }

    private blendTexts(texts: Vibe['text'][]): Vibe['text'] | undefined {
        if (texts.length === 0) return undefined;
        
        // Pick a random word/emoji from parents
        const contents = texts.map(t => t.content);
        const chosenContent = contents[Math.floor(Math.random() * contents.length)];

        // Simple average for color (if multiple texts)
        const colors = texts.map(t => t.color);
        const blendedColor = colors[Math.floor(Math.random() * colors.length)]; // Still random for simplicity

        // Pick a random font style
        const fontStyles = texts.map(t => t.fontStyle);
        const chosenFontStyle = fontStyles[Math.floor(Math.random() * fontStyles.length)];

        return {
            content: chosenContent,
            fontStyle: chosenFontStyle,
            color: blendedColor,
        };
    }
}
