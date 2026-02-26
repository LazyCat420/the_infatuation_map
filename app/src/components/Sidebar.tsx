import RestaurantCard from "./RestaurantCard";
import type { RestaurantWithDistance } from "../schema";

interface SidebarProps {
    restaurants: RestaurantWithDistance[];
    totalCount: number;
    searchQuery: string;
    onSearchChange: (q: string) => void;
    allTags: string[];
    selectedTags: string[];
    onTagToggle: (tag: string) => void;
    allCuisines: string[];
    selectedCuisines: string[];
    onCuisineToggle: (cuisine: string) => void;
    allNeighborhoods: string[];
    selectedNeighborhood: string;
    onNeighborhoodChange: (n: string) => void;
    maxDistance: number;
    onMaxDistanceChange: (d: number) => void;
    nearMeActive: boolean;
    onNearMeToggle: () => void;
    geoLoading: boolean;
    geoError: string | null;
    selectedRestaurant: RestaurantWithDistance | null;
    onSelectRestaurant: (r: RestaurantWithDistance | null) => void;
    isOpen: boolean;
    onToggle: () => void;
    // Favorites
    isFavorite: (id: string) => boolean;
    onToggleFavorite: (id: string) => void;
    favoritesCount: number;
    showFavoritesOnly: boolean;
    onToggleShowFavorites: () => void;
}

export default function Sidebar({
    restaurants,
    totalCount,
    searchQuery,
    onSearchChange,
    allTags,
    selectedTags,
    onTagToggle,
    allCuisines,
    selectedCuisines,
    onCuisineToggle,
    allNeighborhoods,
    selectedNeighborhood,
    onNeighborhoodChange,
    maxDistance,
    onMaxDistanceChange,
    nearMeActive,
    onNearMeToggle,
    geoLoading,
    geoError,
    selectedRestaurant,
    onSelectRestaurant,
    isOpen,
    onToggle,
    isFavorite,
    onToggleFavorite,
    favoritesCount,
    showFavoritesOnly,
    onToggleShowFavorites,
}: SidebarProps) {
    return (
        <>
            <button
                className={`sidebar-toggle ${isOpen ? "open" : ""}`}
                onClick={onToggle}
                aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
            >
                {isOpen ? "◀" : "▶"}
            </button>

            <aside className={`sidebar ${isOpen ? "open" : "closed"}`}>
                {/* Header */}
                <div className="sidebar-header">
                    <h1 className="app-title">
                        <span className="title-icon">🍽️</span>
                        <span>SF Eats</span>
                    </h1>
                    <p className="app-subtitle">The Infatuation Map</p>
                </div>

                {/* Near Me + Favorites row */}
                <div className="action-row">
                    <button
                        className={`near-me-btn ${nearMeActive ? "active" : ""}`}
                        onClick={onNearMeToggle}
                        disabled={geoLoading}
                    >
                        <span className="near-me-icon">📍</span>
                        {geoLoading ? "Locating..." : nearMeActive ? "Near Me: ON" : "Near Me"}
                    </button>
                    <button
                        className={`favorites-btn ${showFavoritesOnly ? "active" : ""}`}
                        onClick={onToggleShowFavorites}
                        title="Show favorites only"
                    >
                        <span>❤️</span>
                        {favoritesCount > 0 && (
                            <span className="fav-count">{favoritesCount}</span>
                        )}
                    </button>
                </div>
                {geoError && <p className="geo-error">{geoError}</p>}

                {/* Distance slider (visible when near-me is active) */}
                {nearMeActive && (
                    <div className="distance-control">
                        <label className="distance-label">
                            Within <strong>{maxDistance}</strong> mile{maxDistance !== 1 ? "s" : ""}
                        </label>
                        <input
                            type="range"
                            min={1}
                            max={50}
                            value={maxDistance}
                            onChange={(e) => onMaxDistanceChange(Number(e.target.value))}
                            className="distance-slider"
                            aria-label="Maximum distance in miles"
                        />
                        <div className="distance-ticks">
                            <span>1 mi</span>
                            <span>25 mi</span>
                            <span>50 mi</span>
                        </div>
                    </div>
                )}

                {/* Search */}
                <div className="search-section">
                    <input
                        type="search"
                        className="search-input"
                        placeholder="Search restaurants..."
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && restaurants.length > 0) {
                                onSelectRestaurant(restaurants[0]);
                            }
                        }}
                    />
                </div>

                {/* Neighborhood filter */}
                <div className="filter-section">
                    <select
                        className="neighborhood-select"
                        value={selectedNeighborhood}
                        onChange={(e) => onNeighborhoodChange(e.target.value)}
                        title="Filter by neighborhood"
                    >
                        <option value="">All Neighborhoods</option>
                        {allNeighborhoods.map((n) => (
                            <option key={n} value={n}>
                                {n}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Cuisine filter */}
                {allCuisines.length > 0 && (
                    <div className="filter-group">
                        <span className="filter-label">🍽️ Food Type</span>
                        <div className="cuisine-chips">
                            {allCuisines.map((cuisine) => (
                                <button
                                    key={cuisine}
                                    className={`cuisine-chip ${selectedCuisines.includes(cuisine) ? "active" : ""}`}
                                    onClick={() => onCuisineToggle(cuisine)}
                                >
                                    {cuisine}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Tag filter chips */}
                {allTags.length > 0 && (
                    <div className="tag-chips">
                        {allTags.slice(0, 20).map((tag) => (
                            <button
                                key={tag}
                                className={`tag-chip ${selectedTags.includes(tag) ? "active" : ""}`}
                                onClick={() => onTagToggle(tag)}
                            >
                                {tag}
                            </button>
                        ))}
                    </div>
                )}

                {/* Results count */}
                <div className="results-count">
                    <span>
                        {showFavoritesOnly ? `❤️ ${restaurants.length} favorites` : `${restaurants.length} of ${totalCount} restaurants`}
                    </span>
                    {(searchQuery || selectedCuisines.length > 0 || selectedTags.length > 0 || selectedNeighborhood || nearMeActive || showFavoritesOnly) && (
                        <button
                            className="clear-filters"
                            onClick={() => {
                                onSearchChange("");
                                selectedCuisines.forEach(onCuisineToggle);
                                selectedTags.forEach(onTagToggle);
                                onNeighborhoodChange("");
                                if (showFavoritesOnly) onToggleShowFavorites();
                            }}
                        >
                            Clear filters
                        </button>
                    )}
                </div>

                {/* Restaurant list */}
                <div className="restaurant-list">
                    {restaurants.length === 0 ? (
                        <div className="empty-state">
                            {showFavoritesOnly ? (
                                <>
                                    <p>No favorites yet.</p>
                                    <p>Tap the 🤍 on a restaurant to save it!</p>
                                </>
                            ) : (
                                <>
                                    <p>No restaurants match your filters.</p>
                                    <p>Try adjusting your search or distance.</p>
                                </>
                            )}
                        </div>
                    ) : (
                        restaurants.map((r) => (
                            <RestaurantCard
                                key={r.id}
                                restaurant={r}
                                isSelected={selectedRestaurant?.id === r.id}
                                isFavorite={isFavorite(r.id)}
                                onToggleFavorite={onToggleFavorite}
                                onClick={() =>
                                    onSelectRestaurant(selectedRestaurant?.id === r.id ? null : r)
                                }
                            />
                        ))
                    )}
                </div>
            </aside>
        </>
    );
}
