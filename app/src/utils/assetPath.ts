/**
 * Resolve an asset path relative to the Vite base URL.
 * Handles both absolute paths (e.g. "/images/foo.jpg") and
 * external URLs (e.g. "https://...") gracefully.
 */
export function resolveAssetPath(path: string): string {
    if (!path) return path;
    // External URLs pass through unchanged
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    // Strip leading slash and prepend BASE_URL (which always ends with /)
    const clean = path.startsWith("/") ? path.slice(1) : path;
    return `${import.meta.env.BASE_URL}${clean}`;
}
