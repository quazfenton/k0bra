import { Vibe } from '../types/Vibe';

/**
 * In-memory data store for Vibe objects.
 * Simulates a database for persistence and retrieval.
 */
export class VibeStore {
    private vibes: Map<string, Vibe>; // Stores Vibes by their ID

    constructor() {
        this.vibes = new Map<string, Vibe>();
        // Optionally, set up a periodic cleanup for expired vibes
        setInterval(() => this.deleteExpiredVibes(), 60 * 60 * 1000); // Every hour
    }

    /**
     * Saves a Vibe to the store. If a Vibe with the same ID exists, it will be updated.
     * @param vibe The Vibe object to save.
     */
    public saveVibe(vibe: Vibe): void {
        this.vibes.set(vibe.id, vibe);
        console.log(`[VibeStore] Vibe saved: ${vibe.id}`);
    }

    /**
     * Retrieves a Vibe by its ID.
     * @param id The ID of the Vibe to retrieve.
     * @returns The Vibe object, or undefined if not found.
     */
    public getVibe(id: string): Vibe | undefined {
        return this.vibes.get(id);
    }

    /**
     * Retrieves multiple Vibes by their IDs.
     * @param ids An array of Vibe IDs to retrieve.
     * @returns An array of Vibe objects that were found.
     */
    public getVibesByIds(ids: string[]): Vibe[] {
        return ids.map(id => this.vibes.get(id)).filter(Boolean) as Vibe[];
    }

    /**
     * Retrieves all currently active (not expired) Vibes.
     * @returns An array of active Vibe objects.
     */
    public getAllActiveVibes(): Vibe[] {
        const now = Date.now();
        return Array.from(this.vibes.values()).filter(vibe => vibe.expiresAt > now);
    }

    /**
     * Deletes a Vibe from the store by its ID.
     * @param id The ID of the Vibe to delete.
     * @returns True if the Vibe was deleted, false otherwise.
     */
    public deleteVibe(id: string): boolean {
        const deleted = this.vibes.delete(id);
        if (deleted) {
            console.log(`[VibeStore] Vibe deleted: ${id}`);
        }
        return deleted;
    }

    /**
     * Deletes all Vibes that have passed their expiration time.
     */
    public deleteExpiredVibes(): void {
        const now = Date.now();
        let deletedCount = 0;
        for (const [id, vibe] of this.vibes.entries()) {
            if (vibe.expiresAt <= now) {
                this.vibes.delete(id);
                deletedCount++;
            }
        }
        if (deletedCount > 0) {
            console.log(`[VibeStore] Cleaned up ${deletedCount} expired Vibes.`);
        }
    }

    /**
     * Clears all Vibes from the store (for testing/resetting).
     */
    public clear(): void {
        this.vibes.clear();
        console.log("[VibeStore] All Vibes cleared.");
    }
}
