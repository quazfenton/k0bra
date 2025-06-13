/**
 * Converts a hex color string to an RGB array.
 * @param hex Hex color string (e.g., "#RRGGBB" or "RRGGBB").
 * @returns [R, G, B] array, or null if invalid.
 */
export function hexToRgb(hex: string): [number, number, number] | null {
    const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
    hex = hex.replace(shorthandRegex, function(m, r, g, b) {
        return r + r + g + g + b + b;
    });

    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : null;
}

/**
 * Converts an RGB array to a hex color string.
 * @param r Red component (0-255).
 * @param g Green component (0-255).
 * @param b Blue component (0-255).
 * @returns Hex color string (e.g., "#RRGGBB").
 */
export function rgbToHex(r: number, g: number, b: number): string {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
}

/**
 * Linearly interpolates between two RGB colors.
 * @param color1 RGB array of the first color.
 * @param color2 RGB array of the second color.
 * @param factor Interpolation factor (0.0 to 1.0).
 * @returns Blended RGB array.
 */
export function interpolateRgb(color1: [number, number, number], color2: [number, number, number], factor: number): [number, number, number] {
    const result: [number, number, number] = [0, 0, 0];
    for (let i = 0; i < 3; i++) {
        result[i] = Math.round(color1[i] + factor * (color2[i] - color1[i]));
    }
    return result;
}

/**
 * Blends an array of hex colors into a new palette.
 * This is a simplified blending, taking a weighted average of colors.
 * @param hexColors Array of hex color strings.
 * @param numColors The desired number of colors in the blended palette.
 * @returns A new array of hex color strings.
 */
export function blendHexPalettes(hexColors: string[], numColors: number = 3): string[] {
    if (hexColors.length === 0) return [];
    if (hexColors.length === 1) return [hexColors[0]];

    const rgbColors = hexColors.map(hexToRgb).filter(Boolean) as [number, number, number][];
    if (rgbColors.length === 0) return [];

    const blendedPalette: string[] = [];

    // Simple average of all colors
    const avgR = Math.round(rgbColors.reduce((sum, c) => sum + c[0], 0) / rgbColors.length);
    const avgG = Math.round(rgbColors.reduce((sum, c) => sum + c[1], 0) / rgbColors.length);
    const avgB = Math.round(rgbColors.reduce((sum, c) => sum + c[2], 0) / rgbColors.length);
    
    blendedPalette.push(rgbToHex(avgR, avgG, avgB));

    // Add a few more colors by interpolating between random pairs
    for (let i = 1; i < numColors; i++) {
        const idx1 = Math.floor(Math.random() * rgbColors.length);
        let idx2 = Math.floor(Math.random() * rgbColors.length);
        // Ensure idx2 is different from idx1 if possible
        if (rgbColors.length > 1) {
            while (idx2 === idx1) {
                idx2 = Math.floor(Math.random() * rgbColors.length);
            }
        }
        const factor = Math.random(); // Random factor for interpolation
        const interpolated = interpolateRgb(rgbColors[idx1], rgbColors[idx2], factor);
        blendedPalette.push(rgbToHex(interpolated[0], interpolated[1], interpolated[2]));
    }

    // Ensure uniqueness and limit to numColors
    return Array.from(new Set(blendedPalette)).slice(0, numColors);
}
