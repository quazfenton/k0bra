import { VibeProcessor } from '../core/VibeProcessor';
import { VibeStore } from '../data/VibeStore';
import { Vibe } from '../types/Vibe';

// This file conceptually represents how API endpoints might interact with the VibeProcessor.
// In a real application, this would be part of an Express.js, Next.js API route, or similar.

// Initialize VibeStore and VibeProcessor once
const vibeStore = new VibeStore();
const vibeProcessor = new VibeProcessor(vibeStore);

/**
 * Mock Express-like Request and Response objects for demonstration.
 */
interface MockRequest {
    body?: any;
    params?: { [key: string]: string };
    query?: { [key: string]: string };
}

interface MockResponse {
    _status: number;
    _json: any;
    status(code: number): MockResponse;
    json(data: any): MockResponse;
}

const mockResponseFactory = (): MockResponse => ({
    _status: 200,
    _json: null,
    status(code: number) {
        this._status = code;
        return this;
    },
    json(data: any) {
        this._json = data;
        return this;
    }
});

/**
 * Simulates an API endpoint for creating a new Vibe.
 * POST /api/vibes
 * @param req The incoming request object (conceptual).
 * @param res The response object (conceptual).
 */
export function handleCreateVibe(req: MockRequest, res: MockResponse) {
    try {
        const { visual, audio, haptic, text } = req.body || {};

        if (!visual || !audio) {
            return res.status(400).json({ message: "Visual and audio parameters are required." });
        }
        if (!Array.isArray(visual.palette) || visual.palette.some((c: any) => typeof c !== 'string')) {
            return res.status(400).json({ message: "Visual palette must be an array of strings." });
        }
        if (!['pulse', 'flow', 'sparkle', 'wave', 'static'].includes(visual.animationType)) {
            return res.status(400).json({ message: "Invalid visual animation type." });
        }
        if (typeof visual.intensity !== 'number' || visual.intensity < 0 || visual.intensity > 100) {
            return res.status(400).json({ message: "Visual intensity must be a number between 0 and 100." });
        }
        if (typeof audio.loopUrl !== 'string' || typeof audio.volume !== 'number' || audio.volume < 0 || audio.volume > 100) {
            return res.status(400).json({ message: "Audio loopUrl must be string, volume must be number between 0 and 100." });
        }
        if (text && (typeof text.content !== 'string' || text.content.length === 0 || text.content.length > 10)) {
            return res.status(400).json({ message: "Text content must be a string up to 10 characters." });
        }

        const newVibe = vibeProcessor.createNewVibe(visual, audio, haptic, text);
        res.status(201).json({ message: "Vibe created successfully", vibeId: newVibe.id, vibe: newVibe });

    } catch (error: any) {
        console.error("Error creating Vibe:", error.message);
        res.status(500).json({ message: "Internal server error.", error: error.message });
    }
}

/**
 * Simulates an API endpoint for weaving new Vibes from existing ones.
 * POST /api/vibes/weave
 * @param req The incoming request object (conceptual).
 * @param res The response object (conceptual).
 */
export function handleWeaveVibes(req: MockRequest, res: MockResponse) {
    try {
        const { parentVibeIds } = req.body || {};

        if (!Array.isArray(parentVibeIds) || parentVibeIds.length === 0 || parentVibeIds.length > 3) {
            return res.status(400).json({ message: "Must provide 1 to 3 parent Vibe IDs for weaving." });
        }
        if (parentVibeIds.some((id: any) => typeof id !== 'string')) {
            return res.status(400).json({ message: "Parent Vibe IDs must be strings." });
        }

        const wovenVibe = vibeProcessor.weaveVibes(parentVibeIds);

        if (!wovenVibe) {
            return res.status(404).json({ message: "Failed to weave Vibes. One or more parent Vibes might not exist or are expired." });
        }

        res.status(201).json({ message: "Vibes woven successfully", vibeId: wovenVibe.id, vibe: wovenVibe });

    } catch (error: any) {
        console.error("Error weaving Vibes:", error.message);
        res.status(500).json({ message: "Internal server error.", error: error.message });
    }
}

/**
 * Simulates an API endpoint for resonating with a Vibe.
 * POST /api/vibes/:vibeId/resonate
 * @param req The incoming request object (conceptual).
 * @param res The response object (conceptual).
 */
export function handleResonateVibe(req: MockRequest, res: MockResponse) {
    try {
        const { vibeId } = req.params || {};

        if (!vibeId || typeof vibeId !== 'string') {
            return res.status(400).json({ message: "Vibe ID is required." });
        }

        const updatedVibe = vibeProcessor.resonateWithVibe(vibeId);

        if (!updatedVibe) {
            return res.status(404).json({ message: `Vibe with ID ${vibeId} not found or expired.` });
        }

        res.status(200).json({ message: "Resonance recorded.", vibeId: updatedVibe.id, currentResonanceScore: updatedVibe._internal.resonanceScore });

    } catch (error: any) {
        console.error("Error resonating with Vibe:", error.message);
        res.status(500).json({ message: "Internal server error.", error: error.message });
    }
}

/**
 * Simulates an API endpoint for getting a single Vibe.
 * GET /api/vibes/:vibeId
 * @param req The incoming request object (conceptual).
 * @param res The response object (conceptual).
 */
export function handleGetVibe(req: MockRequest, res: MockResponse) {
    try {
        const { vibeId } = req.params || {};

        if (!vibeId || typeof vibeId !== 'string') {
            return res.status(400).json({ message: "Vibe ID is required." });
        }

        const vibe = vibeStore.getVibe(vibeId);

        if (!vibe || vibe.expiresAt <= Date.now()) {
            return res.status(404).json({ message: `Vibe with ID ${vibeId} not found or expired.` });
        }

        res.status(200).json({ vibe });

    } catch (error: any) {
        console.error("Error getting Vibe:", error.message);
        res.status(500).json({ message: "Internal server error.", error: error.message });
    }
}

/**
 * Simulates an API endpoint for getting Vibes for a stream.
 * GET /api/streams/:streamType/:associatedId/vibes
 * @param req The incoming request object (conceptual).
 * @param res The response object (conceptual).
 */
export function handleGetStreamVibes(req: MockRequest, res: MockResponse) {
    try {
        const { streamType, associatedId } = req.params || {};
        const limit = parseInt(req.query?.limit || '20', 10);

        if (!streamType || !['personal', 'collective'].includes(streamType)) {
            return res.status(400).json({ message: "Invalid stream type. Must be 'personal' or 'collective'." });
        }
        if (!associatedId || typeof associatedId !== 'string') {
            return res.status(400).json({ message: "Associated ID is required for stream." });
        }
        if (isNaN(limit) || limit <= 0 || limit > 100) {
            return res.status(400).json({ message: "Limit must be a number between 1 and 100." });
        }

        const vibeIds = vibeProcessor.getStreamVibes(streamType as 'personal' | 'collective', associatedId, limit);
        const vibes = vibeStore.getVibesByIds(vibeIds); // Fetch full Vibe objects

        res.status(200).json({ streamType, associatedId, vibes });

    } catch (error: any) {
        console.error("Error getting stream Vibes:", error.message);
        res.status(500).json({ message: "Internal server error.", error: error.message });
    }
}

// Export the store and processor for direct access in demonstration
export { vibeStore, vibeProcessor, mockResponseFactory };
