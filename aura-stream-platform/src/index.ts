import { handleCreateVibe, handleWeaveVibes, handleResonateVibe, handleGetVibe, handleGetStreamVibes, vibeStore, vibeProcessor, mockResponseFactory } from './api/auraRoutes';
import { Vibe } from './types/Vibe';

// --- Demonstration of VibeWeave Functionality ---

async function runDemo() {
    console.log("--- VibeWeave Demo Start ---");
    vibeStore.clear(); // Start with a clean slate

    // --- 1. Create Initial Vibes ---
    console.log("\n--- Creating Initial Vibes ---");

    const createVibe = async (name: string, body: any) => {
        const req = { body };
        const res = mockResponseFactory();
        await handleCreateVibe(req, res);
        console.log(`Created ${name}: Status ${res._status}, Data:`, res._json);
        return res._json?.vibe as Vibe | undefined;
    };

    const vibe1 = await createVibe("Vibe A (Chill)", {
        visual: { palette: ["#AEC6CF", "#ADD8E6"], animationType: "flow", intensity: 60 },
        audio: { loopUrl: "ambient_chill.mp3", volume: 70 },
        text: { content: "Calm", fontStyle: "sans-serif", color: "#333333" }
    });

    const vibe2 = await createVibe("Vibe B (Energetic)", {
        visual: { palette: ["#FF6347", "#FFD700"], animationType: "sparkle", intensity: 85 },
        audio: { loopUrl: "upbeat_synth.mp3", volume: 80 },
        haptic: { pattern: "short_buzz", intensity: 70 }
    });

    const vibe3 = await createVibe("Vibe C (Dreamy)", {
        visual: { palette: ["#8A2BE2", "#DA70D6"], animationType: "wave", intensity: 75 },
        audio: { loopUrl: "dreamy_pads.mp3", volume: 65 },
        text: { content: "Dream", fontStyle: "serif", color: "#FFFFFF" }
    });

    // Simulate some invalid creation attempts
    console.log("\n--- Invalid Vibe Creation Attempts ---");
    await createVibe("Invalid Vibe (missing audio)", { visual: { palette: ["#000"], animationType: "static", intensity: 50 } });
    await createVibe("Invalid Vibe (bad intensity)", { visual: { palette: ["#000"], animationType: "static", intensity: 150 }, audio: { loopUrl: "a.mp3", volume: 50 } });


    // --- 2. Resonate with Vibes ---
    console.log("\n--- Resonating with Vibes ---");

    const resonateVibe = async (vibeId: string, name: string) => {
        const req = { params: { vibeId } };
        const res = mockResponseFactory();
        await handleResonateVibe(req, res);
        console.log(`Resonated with ${name}: Status ${res._status}, Data:`, res._json);
    };

    if (vibe1) {
        await resonateVibe(vibe1.id, "Vibe A");
        await resonateVibe(vibe1.id, "Vibe A (again)"); // Resonate multiple times
    }
    if (vibe2) {
        await resonateVibe(vibe2.id, "Vibe B");
    }

    // Simulate resonating with a non-existent vibe
    console.log("\n--- Invalid Resonance Attempt ---");
    await resonateVibe("non-existent-vibe-id", "Non-existent Vibe");

    // --- 3. Weave New Vibes ---
    console.log("\n--- Weaving New Vibes ---");

    const weaveVibes = async (name: string, parentIds: string[]) => {
        const req = { body: { parentVibeIds: parentIds } };
        const res = mockResponseFactory();
        await handleWeaveVibes(req, res);
        console.log(`Weaved ${name}: Status ${res._status}, Data:`, res._json);
        return res._json?.vibe as Vibe | undefined;
    };

    let wovenVibe1: Vibe | undefined;
    if (vibe1 && vibe2) {
        wovenVibe1 = await weaveVibes("Woven Vibe 1 (A+B)", [vibe1.id, vibe2.id]);
    }

    let wovenVibe2: Vibe | undefined;
    if (vibe1 && vibe3) {
        wovenVibe2 = await weaveVibes("Woven Vibe 2 (A+C)", [vibe1.id, vibe3.id]);
    }

    // Simulate invalid weaving attempts
    console.log("\n--- Invalid Weaving Attempts ---");
    await weaveVibes("Invalid Weave (too many parents)", ["id1", "id2", "id3", "id4"]);
    await weaveVibes("Invalid Weave (non-existent parent)", ["non-existent-id", vibe1?.id || ""]);


    // --- 4. Get Individual Vibes ---
    console.log("\n--- Getting Individual Vibes ---");

    const getVibe = async (vibeId: string, name: string) => {
        const req = { params: { vibeId } };
        const res = mockResponseFactory();
        await handleGetVibe(req, res);
        console.log(`Get ${name}: Status ${res._status}, Data:`, res._json ? { id: res._json.vibe?.id, resonanceScore: res._json.vibe?._internal.resonanceScore, generation: res._json.vibe?._internal.generation } : res._json);
    };

    if (vibe1) await getVibe(vibe1.id, "Vibe A");
    if (wovenVibe1) await getVibe(wovenVibe1.id, "Woven Vibe 1");

    // Simulate getting a non-existent vibe
    console.log("\n--- Invalid Get Vibe Attempt ---");
    await getVibe("another-non-existent-id", "Non-existent Vibe");

    // --- 5. Simulate Decay ---
    console.log("\n--- Simulating Vibe Resonance Decay ---");
    // Manually trigger decay (in a real app, this would be a background job)
    vibeProcessor.decayVibeResonance(0.5); // High decay rate for demo
    if (vibe1) await getVibe(vibe1.id, "Vibe A (after decay)");


    // --- 6. Get Stream Vibes ---
    console.log("\n--- Getting Stream Vibes ---");

    const getStreamVibes = async (streamType: string, associatedId: string, limit: number = 5) => {
        const req = { params: { streamType, associatedId }, query: { limit: limit.toString() } };
        const res = mockResponseFactory();
        await handleGetStreamVibes(req, res);
        console.log(`Stream '${streamType}' for '${associatedId}': Status ${res._status}, Vibes Count: ${res._json?.vibes?.length || 0}`);
        if (res._json?.vibes) {
            res._json.vibes.forEach((v: Vibe) => console.log(`  - Vibe ID: ${v.id}, Resonance: ${v._internal.resonanceScore}, Gen: ${v._internal.generation}, Text: ${v.text?.content || 'N/A'}`));
        }
    };

    // Get collective stream (trending vibes)
    await getStreamVibes("collective", "global-trends", 5);

    // Get personal stream (simulated for a user)
    const mockUserId = "user-123";
    // To make personal stream more meaningful, let's resonate more with some vibes for this user
    if (vibe2) await resonateVibe(vibe2.id, "Vibe B (for user-123)");
    if (wovenVibe1) await resonateVibe(wovenVibe1.id, "Woven Vibe 1 (for user-123)");
    if (vibe3) await resonateVibe(vibe3.id, "Vibe C (for user-123)");

    await getStreamVibes("personal", mockUserId, 5);

    // Simulate invalid stream request
    console.log("\n--- Invalid Stream Request Attempt ---");
    await getStreamVibes("invalid-type", "some-id");


    // --- 7. Simulate Vibe Expiration ---
    console.log("\n--- Simulating Vibe Expiration ---");
    // Manually set a vibe to expire immediately for demonstration
    if (vibe1) {
        const expiredVibe = vibeStore.getVibe(vibe1.id);
        if (expiredVibe) {
            expiredVibe.expiresAt = Date.now() - 1; // Set to expire in the past
            vibeStore.saveVibe(expiredVibe);
            console.log(`Vibe A (${vibe1.id}) manually set to expired.`);
        }
    }
    vibeStore.deleteExpiredVibes(); // Trigger cleanup
    await getVibe(vibe1?.id || "", "Vibe A (after expiration cleanup)");


    console.log("\n--- VibeWeave Demo End ---");
}

runDemo();
