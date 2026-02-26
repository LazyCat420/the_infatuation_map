import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "sf-eats-favorites";

/**
 * Hook to manage favorite restaurants via localStorage.
 * Persists across sessions, no backend needed.
 */
export function useFavorites() {
    const [favoriteIds, setFavoriteIds] = useState<Set<string>>(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                return new Set(JSON.parse(stored));
            }
        } catch {
            // Ignore parse errors
        }
        return new Set<string>();
    });

    // Persist to localStorage whenever favorites change
    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify([...favoriteIds]));
        } catch {
            // localStorage full or unavailable — silently fail
        }
    }, [favoriteIds]);

    const toggleFavorite = useCallback((id: string) => {
        setFavoriteIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const isFavorite = useCallback(
        (id: string) => favoriteIds.has(id),
        [favoriteIds]
    );

    return {
        favoriteIds,
        toggleFavorite,
        isFavorite,
        count: favoriteIds.size,
    };
}
