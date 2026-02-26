import { z } from "zod";

export const RestaurantSchema = z.object({
    id: z.string(),
    slug: z.string().optional(),
    name: z.string(),
    address: z.string(),
    neighborhood: z.string().optional().default(""),
    cuisine: z.string().optional().default(""),
    restaurant_url: z.string().optional().default(""),
    image_url: z.string().optional().default(""),
    source_url: z.string().optional().default(""),
    source_urls: z.array(z.string()).optional().default([]),
    lat: z.number().nullable().optional(),
    lng: z.number().nullable().optional(),
    tags: z.array(z.string()).optional().default([]),
    last_seen_at: z.string().optional(),
    source: z.string().optional().default("theinfatuation"),
    place_id: z.string().optional(),
    geocode_confidence: z.string().optional(),
});

export type Restaurant = z.infer<typeof RestaurantSchema>;

export const RestaurantsArraySchema = z.array(RestaurantSchema);

export type RestaurantWithDistance = Restaurant & {
    distance?: number; // miles
};
