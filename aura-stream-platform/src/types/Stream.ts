/**
 * Represents a "Stream" of Vibes on the VibeWeave platform.
 * Streams are dynamic collections of Vibes, either personalized or collective.
 */
export interface Stream {
    id: string; // Unique identifier for the Stream
    name: string; // Display name of the Stream (e.g., "Chill Vibe Weave", "My Personal Aura")
    type: 'personal' | 'collective'; // Type of stream

    // For 'personal' streams, this would be the user's ID (internal)
    // For 'collective' streams, this might be a category or theme ID
    associatedId: string; 

    // A dynamic list of Vibe IDs currently active in this stream.
    // This list would be constantly updated by the backend based on resonance, blending, and lifespan.
    currentVibeIds: string[]; 

    // Optional description for collective streams
    description?: string; 

    // Metadata for how the stream is curated/generated
    _internal: {
        // For personal streams, this might track the user's resonance history
        userResonanceHistory?: { vibeId: string; timestamp: number }[]; 
        // For collective streams, this might track dominant Vibe characteristics
        dominantVibeCharacteristics?: {
            paletteTendencies: { [color: string]: number };
            animationTendencies: { [type: string]: number };
            audioTendencies: { [type: string]: number };
        };
        lastUpdated: number; // Timestamp of last update
    };
}
