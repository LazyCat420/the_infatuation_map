/**
 * distance.ts — Haversine distance and proximity utilities.
 *
 * All distances returned in miles.
 */

const EARTH_RADIUS_MILES = 3958.8;

function toRad(deg: number): number {
    return (deg * Math.PI) / 180;
}

/**
 * Calculate the great-circle distance between two points using Haversine.
 * Returns distance in miles.
 */
export function haversineDistance(
    lat1: number,
    lng1: number,
    lat2: number,
    lng2: number
): number {
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return EARTH_RADIUS_MILES * c;
}

/**
 * Sort items by distance from a reference point.
 */
export function sortByDistance<T extends { lat?: number | null; lng?: number | null }>(
    items: T[],
    refLat: number,
    refLng: number
): (T & { distance: number })[] {
    return items
        .filter((item): item is T & { lat: number; lng: number } =>
            item.lat != null && item.lng != null
        )
        .map((item) => ({
            ...item,
            distance: haversineDistance(refLat, refLng, item.lat, item.lng),
        }))
        .sort((a, b) => a.distance - b.distance);
}

/**
 * Filter items within a radius (in miles) from a reference point.
 */
export function filterWithinRadius<T extends { distance?: number }>(
    items: T[],
    maxMiles: number
): T[] {
    return items.filter((item) => item.distance != null && item.distance <= maxMiles);
}

/**
 * Format distance for display.
 */
export function formatDistance(miles: number): string {
    if (miles < 0.1) return "< 0.1 mi";
    if (miles < 1) return `${miles.toFixed(1)} mi`;
    return `${miles.toFixed(1)} mi`;
}
