import { useEffect, useMemo, useRef, useCallback } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import type { RestaurantWithDistance } from "../schema";
import { formatDistance } from "../utils/distance";
import { resolveAssetPath } from "../utils/assetPath";
import "leaflet/dist/leaflet.css";

// Custom red pin icon
const PIN_ICON = L.divIcon({
    className: "custom-pin",
    html: `<svg width="28" height="36" viewBox="0 0 28 36" fill="none"><path d="M14 0C6.268 0 0 6.268 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.268 21.732 0 14 0z" fill="#FF4D4D"/><circle cx="14" cy="14" r="6" fill="white"/></svg>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -36],
});

const SELECTED_PIN_ICON = L.divIcon({
    className: "custom-pin selected-pin",
    html: `<svg width="34" height="44" viewBox="0 0 28 36" fill="none"><path d="M14 0C6.268 0 0 6.268 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.268 21.732 0 14 0z" fill="#FF8A50"/><circle cx="14" cy="14" r="6" fill="white"/></svg>`,
    iconSize: [34, 44],
    iconAnchor: [17, 44],
    popupAnchor: [0, -44],
});

const USER_ICON = L.divIcon({
    className: "user-location-icon",
    html: `<div class="user-dot"><div class="user-dot-inner"></div><div class="user-dot-pulse"></div></div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
});

interface MapViewProps {
    restaurants: RestaurantWithDistance[];
    center: { lat: number; lng: number };
    userPosition: { lat: number; lng: number } | null;
    maxDistance: number | null;
    selectedRestaurant: RestaurantWithDistance | null;
    onSelectRestaurant: (r: RestaurantWithDistance | null) => void;
    isFavorite: (id: string) => boolean;
    onToggleFavorite: (id: string) => void;
}

/** Subcomponent: flies to selected restaurant and opens its popup */
function MapController({
    selectedRestaurant,
    userPosition,
    nearMeActive,
    markerRefs,
}: {
    selectedRestaurant: RestaurantWithDistance | null;
    userPosition: { lat: number; lng: number } | null;
    nearMeActive: boolean;
    markerRefs: React.MutableRefObject<Record<string, L.Marker | null>>;
}) {
    const map = useMap();
    const hasFlownToUser = useRef(false);

    // Fly to selected restaurant
    useEffect(() => {
        if (selectedRestaurant?.lat && selectedRestaurant?.lng) {
            map.flyTo([selectedRestaurant.lat, selectedRestaurant.lng], 16, {
                duration: 0.8,
            });
            const timer = setTimeout(() => {
                const marker = markerRefs.current[selectedRestaurant.id];
                if (marker) {
                    marker.openPopup();
                }
            }, 850);
            return () => clearTimeout(timer);
        }
    }, [map, selectedRestaurant, markerRefs]);

    // Fly to user position when Near Me activates
    useEffect(() => {
        if (nearMeActive && userPosition) {
            if (!hasFlownToUser.current) {
                console.log("[Map] Flying to user position:", userPosition);
                map.flyTo([userPosition.lat, userPosition.lng], 14, { duration: 1.0 });
                hasFlownToUser.current = true;
            }
        }
        if (!nearMeActive) {
            hasFlownToUser.current = false;
        }
    }, [map, userPosition, nearMeActive]);

    return null;
}

export default function MapView({
    restaurants,
    center,
    userPosition,
    maxDistance,
    selectedRestaurant,
    onSelectRestaurant,
    isFavorite,
    onToggleFavorite,
}: MapViewProps) {
    // Store refs to all markers so we can open popups programmatically
    const markerRefs = useRef<Record<string, L.Marker | null>>({});

    // Callback to store marker ref
    const setMarkerRef = useCallback((id: string, marker: L.Marker | null) => {
        markerRefs.current[id] = marker;
    }, []);

    // Memoize so markers don't re-create on every render
    const validRestaurants = useMemo(
        () =>
            restaurants.filter(
                (r): r is RestaurantWithDistance & { lat: number; lng: number } =>
                    r.lat != null && r.lng != null
            ),
        [restaurants]
    );

    return (
        <div className="map-container">
            <MapContainer
                center={[center.lat, center.lng]}
                zoom={12}
                scrollWheelZoom={true}
                zoomControl={true}
                style={{ width: "100%", height: "100%" }}
            >
                {/* CartoDB Dark Matter tiles — free, no API key, matches dark UI */}
                <TileLayer
                    attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />

                {/* Map controller for flyTo + popup opening */}
                <MapController
                    selectedRestaurant={selectedRestaurant}
                    userPosition={userPosition}
                    nearMeActive={userPosition !== null}
                    markerRefs={markerRefs}
                />

                {/* User location marker */}
                {userPosition && (
                    <>
                        <Marker
                            position={[userPosition.lat, userPosition.lng]}
                            icon={USER_ICON}
                        >
                            <Popup>📍 You are here</Popup>
                        </Marker>

                        {/* Radius circle */}
                        {maxDistance && (
                            <Circle
                                center={[userPosition.lat, userPosition.lng]}
                                radius={maxDistance * 1609.34}
                                pathOptions={{
                                    color: "#FF4D4D",
                                    fillColor: "#FF4D4D",
                                    fillOpacity: 0.06,
                                    weight: 2,
                                    opacity: 0.3,
                                }}
                            />
                        )}
                    </>
                )}

                {/* Restaurant markers */}
                {validRestaurants.map((restaurant) => {
                    const isSelected = selectedRestaurant?.id === restaurant.id;
                    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(restaurant.address || restaurant.name)}`;

                    return (
                        <Marker
                            key={restaurant.id}
                            position={[restaurant.lat, restaurant.lng]}
                            icon={isSelected ? SELECTED_PIN_ICON : PIN_ICON}
                            ref={(ref) => setMarkerRef(restaurant.id, ref as unknown as L.Marker | null)}
                            eventHandlers={{
                                click: () => onSelectRestaurant(restaurant),
                            }}
                        >
                            <Popup maxWidth={280}>
                                <div className="info-window">
                                    {restaurant.image_url && (
                                        <img
                                            src={resolveAssetPath(restaurant.image_url)}
                                            alt={restaurant.name}
                                            className="info-image"
                                            loading="lazy"
                                        />
                                    )}
                                    <h3 className="info-name">{restaurant.name}
                                        <button
                                            className={`info-fav-btn ${isFavorite(restaurant.id) ? "fav-active" : ""}`}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onToggleFavorite(restaurant.id);
                                            }}
                                            aria-label="Toggle favorite"
                                        >
                                            {isFavorite(restaurant.id) ? "❤️" : "🤍"}
                                        </button>
                                    </h3>
                                    <p className="info-address">
                                        {restaurant.address || "Address not available"}
                                    </p>
                                    {restaurant.cuisine && (
                                        <p className="info-cuisine">{restaurant.cuisine}</p>
                                    )}
                                    {restaurant.neighborhood && (
                                        <p className="info-neighborhood">
                                            📍 {restaurant.neighborhood}
                                        </p>
                                    )}
                                    {restaurant.distance != null && (
                                        <span className="info-distance">
                                            {formatDistance(restaurant.distance)}
                                        </span>
                                    )}
                                    <div className="info-links">
                                        {restaurant.restaurant_url && (
                                            <a
                                                href={restaurant.restaurant_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="info-link infatuation-link"
                                            >
                                                View on Infatuation
                                            </a>
                                        )}
                                        <a
                                            href={directionsUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="info-link directions-link"
                                        >
                                            Get Directions
                                        </a>
                                    </div>
                                </div>
                            </Popup>
                        </Marker>
                    );
                })}
            </MapContainer>
        </div>
    );
}
