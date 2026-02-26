import { useState, useEffect, useMemo, useCallback } from "react";
import { RestaurantsArraySchema, type RestaurantWithDistance } from "./schema";
import { sortByDistance, filterWithinRadius } from "./utils/distance";
import { useGeolocation } from "./hooks/useGeolocation";
import { useFavorites } from "./hooks/useFavorites";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";
import "./App.css";

// Default: center of SF
const SF_CENTER = { lat: 37.7749, lng: -122.4194 };

function App() {
  const [allRestaurants, setAllRestaurants] = useState<RestaurantWithDistance[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedCuisines, setSelectedCuisines] = useState<string[]>([]);
  const [selectedNeighborhood, setSelectedNeighborhood] = useState("");
  const [maxDistance, setMaxDistance] = useState(15); // miles
  const [nearMeActive, setNearMeActive] = useState(false);
  const [selectedRestaurant, setSelectedRestaurant] = useState<RestaurantWithDistance | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [mobileView, setMobileView] = useState<"map" | "list">("map");

  const { position, error: geoError, loading: geoLoading, requestLocation } = useGeolocation();
  const { isFavorite, toggleFavorite, count: favoritesCount } = useFavorites();

  // Load restaurant data
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}restaurants.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const parsed = RestaurantsArraySchema.safeParse(data);
        if (!parsed.success) {
          console.error("Schema validation failed:", parsed.error);
          setLoadError("Restaurant data failed validation");
          return;
        }
        // Deduplicate by ID (safety net for pipeline data)
        const seen = new Set<string>();
        const unique = parsed.data.filter((r) => {
          if (seen.has(r.id)) return false;
          seen.add(r.id);
          return true;
        });
        setAllRestaurants(unique);
      })
      .catch((err) => {
        setLoadError(`Failed to load restaurants: ${err.message}`);
      });
  }, []);

  // Collect unique tags and neighborhoods for filters
  const { allTags, allCuisines, allNeighborhoods } = useMemo(() => {
    const tagSet = new Set<string>();
    const cuisineSet = new Set<string>();
    const neighborhoodSet = new Set<string>();
    allRestaurants.forEach((r) => {
      r.tags?.forEach((t) => { if (t) tagSet.add(t); });
      if (r.cuisine) cuisineSet.add(r.cuisine);
      if (r.neighborhood) neighborhoodSet.add(r.neighborhood);
    });
    return {
      allTags: Array.from(tagSet).sort(),
      allCuisines: Array.from(cuisineSet).sort(),
      allNeighborhoods: Array.from(neighborhoodSet).sort(),
    };
  }, [allRestaurants]);

  // Compute restaurants with distance when position is available
  const restaurantsWithDistance = useMemo(() => {
    if (position) {
      return sortByDistance(allRestaurants, position.lat, position.lng);
    }
    return allRestaurants.filter(
      (r): r is RestaurantWithDistance => r.lat != null && r.lng != null
    );
  }, [allRestaurants, position]);

  // Apply filters
  const filteredRestaurants = useMemo(() => {
    let result = [...restaurantsWithDistance];

    // Favorites filter
    if (showFavoritesOnly) {
      result = result.filter((r) => isFavorite(r.id));
    }

    // Distance filter (only when near-me is active and we have position)
    if (nearMeActive && position) {
      result = filterWithinRadius(result, maxDistance);
    }

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          r.address.toLowerCase().includes(q) ||
          r.cuisine?.toLowerCase().includes(q) ||
          r.neighborhood?.toLowerCase().includes(q)
      );
    }

    // Cuisine filter
    if (selectedCuisines.length > 0) {
      result = result.filter((r) =>
        r.cuisine && selectedCuisines.includes(r.cuisine)
      );
    }

    // Tag filter
    if (selectedTags.length > 0) {
      result = result.filter((r) =>
        selectedTags.some((tag) => r.tags?.includes(tag))
      );
    }

    // Neighborhood filter
    if (selectedNeighborhood) {
      result = result.filter((r) => r.neighborhood === selectedNeighborhood);
    }

    return result;
  }, [restaurantsWithDistance, searchQuery, selectedCuisines, selectedTags, selectedNeighborhood, nearMeActive, position, maxDistance, showFavoritesOnly, isFavorite]);

  const handleNearMe = useCallback(() => {
    if (!nearMeActive) {
      requestLocation();
      setNearMeActive(true);
    } else {
      setNearMeActive(false);
    }
  }, [nearMeActive, requestLocation]);

  const handleSelectRestaurantMobile = useCallback((r: RestaurantWithDistance | null) => {
    setSelectedRestaurant(r);
    if (r) setMobileView("map");
  }, []);

  const mapCenter = nearMeActive && position
    ? { lat: position.lat, lng: position.lng }
    : SF_CENTER;

  if (loadError) {
    return (
      <div className="error-screen">
        <h1>🍽️ Infatuation Map</h1>
        <p className="error-msg">{loadError}</p>
      </div>
    );
  }

  return (
    <div className={`app-container mobile-view-${mobileView}`}>
      <Sidebar
        restaurants={filteredRestaurants}
        totalCount={allRestaurants.length}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        allTags={allTags}
        selectedTags={selectedTags}
        onTagToggle={(tag: string) =>
          setSelectedTags((prev) =>
            prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
          )
        }
        allCuisines={allCuisines}
        selectedCuisines={selectedCuisines}
        onCuisineToggle={(cuisine: string) =>
          setSelectedCuisines((prev) =>
            prev.includes(cuisine) ? prev.filter((c) => c !== cuisine) : [...prev, cuisine]
          )
        }
        allNeighborhoods={allNeighborhoods}
        selectedNeighborhood={selectedNeighborhood}
        onNeighborhoodChange={setSelectedNeighborhood}
        maxDistance={maxDistance}
        onMaxDistanceChange={setMaxDistance}
        nearMeActive={nearMeActive}
        onNearMeToggle={handleNearMe}
        geoLoading={geoLoading}
        geoError={geoError}
        selectedRestaurant={selectedRestaurant}
        onSelectRestaurant={handleSelectRestaurantMobile}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        isFavorite={isFavorite}
        onToggleFavorite={toggleFavorite}
        favoritesCount={favoritesCount}
        showFavoritesOnly={showFavoritesOnly}
        onToggleShowFavorites={() => setShowFavoritesOnly(!showFavoritesOnly)}
      />
      <MapView
        restaurants={filteredRestaurants}
        center={mapCenter}
        userPosition={nearMeActive && position ? position : null}
        maxDistance={nearMeActive ? maxDistance : null}
        selectedRestaurant={selectedRestaurant}
        onSelectRestaurant={setSelectedRestaurant}
        isFavorite={isFavorite}
        onToggleFavorite={toggleFavorite}
      />

      {/* Mobile Bottom Nav */}
      <nav className="mobile-bottom-nav">
        <button
          className={`mobile-nav-btn ${mobileView === "map" ? "active" : ""}`}
          onClick={() => setMobileView("map")}
        >
          <span className="mobile-nav-icon">🗺️</span>
          <span className="mobile-nav-label">Map</span>
        </button>
        <button
          className={`mobile-nav-btn ${mobileView === "list" ? "active" : ""}`}
          onClick={() => setMobileView("list")}
        >
          <span className="mobile-nav-icon">📋</span>
          <span className="mobile-nav-label">List</span>
        </button>
        <button
          className={`mobile-nav-btn ${nearMeActive ? "active" : ""}`}
          onClick={handleNearMe}
          disabled={geoLoading}
        >
          <span className="mobile-nav-icon">{geoLoading ? "⏳" : "📍"}</span>
          <span className="mobile-nav-label">Near Me</span>
        </button>
        <button
          className={`mobile-nav-btn ${showFavoritesOnly ? "active" : ""}`}
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
        >
          <span className="mobile-nav-icon">{showFavoritesOnly ? "❤️" : "🤍"}</span>
          <span className="mobile-nav-label">Favs</span>
        </button>
      </nav>
    </div>
  );
}

export default App;
