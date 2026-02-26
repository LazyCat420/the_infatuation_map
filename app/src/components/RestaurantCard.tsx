import { formatDistance } from "../utils/distance";
import { resolveAssetPath } from "../utils/assetPath";
import type { RestaurantWithDistance } from "../schema";

interface RestaurantCardProps {
    restaurant: RestaurantWithDistance;
    isSelected: boolean;
    isFavorite: boolean;
    onToggleFavorite: (id: string) => void;
    onClick: () => void;
}

export default function RestaurantCard({
    restaurant,
    isSelected,
    isFavorite,
    onToggleFavorite,
    onClick,
}: RestaurantCardProps) {
    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(restaurant.address || restaurant.name)}`;

    return (
        <div
            className={`restaurant-card ${isSelected ? "selected" : ""}`}
            onClick={onClick}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onClick()}
        >
            {/* Hero image */}
            {restaurant.image_url && (
                <div className="card-image-wrap">
                    <img
                        src={resolveAssetPath(restaurant.image_url)}
                        alt={restaurant.name}
                        className="card-image"
                        loading="lazy"
                    />
                </div>
            )}

            <div className="card-body">
                <div className="card-header">
                    <h3 className="card-name">{restaurant.name}</h3>
                    <div className="card-header-actions">
                        {restaurant.distance != null && (
                            <span className="card-distance">{formatDistance(restaurant.distance)}</span>
                        )}
                        <button
                            className={`fav-btn ${isFavorite ? "fav-active" : ""}`}
                            onClick={(e) => {
                                e.stopPropagation();
                                onToggleFavorite(restaurant.id);
                            }}
                            aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
                            title={isFavorite ? "Remove from favorites" : "Add to favorites"}
                        >
                            {isFavorite ? "❤️" : "🤍"}
                        </button>
                    </div>
                </div>

                <p className="card-address">{restaurant.address || "Address not available"}</p>

                <div className="card-meta">
                    {restaurant.cuisine && (
                        <span className="card-tag cuisine-tag">{restaurant.cuisine}</span>
                    )}
                    {restaurant.neighborhood && (
                        <span className="card-tag neighborhood-tag">{restaurant.neighborhood}</span>
                    )}
                </div>

                {restaurant.tags && restaurant.tags.length > 0 && (
                    <div className="card-tags">
                        {restaurant.tags
                            .filter((t) => t !== restaurant.cuisine)
                            .slice(0, 3)
                            .map((tag) => (
                                <span key={tag} className="card-tag extra-tag">
                                    {tag}
                                </span>
                            ))}
                    </div>
                )}

                <div className="card-actions">
                    {restaurant.restaurant_url && (
                        <a
                            href={restaurant.restaurant_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="card-link infatuation"
                            onClick={(e) => e.stopPropagation()}
                        >
                            Infatuation →
                        </a>
                    )}
                    <a
                        href={directionsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="card-link directions"
                        onClick={(e) => e.stopPropagation()}
                    >
                        Directions →
                    </a>
                </div>
            </div>
        </div>
    );
}
