import { z } from "zod";

export const PhotoSchema = z.object({
  id: z.string(),
  src: z.string(),
  thumbnail: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  takenAt: z.string().datetime().optional(),
  camera: z.string().optional(),
  lens: z.string().optional(),
  focal: z.string().optional(),
  aperture: z.string().optional(),
  shutter: z.string().optional(),
  iso: z.number().int().positive().optional(),
  gps: z.object({ lat: z.number(), lng: z.number() }).optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
});

export type Photo = z.infer<typeof PhotoSchema>;

export const AlbumSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  description: z.string().optional(),
  cover: z.string().optional(),
  createdAt: z.string().datetime().optional(),
  updatedAt: z.string().datetime().optional(),
  photos: z.array(PhotoSchema).default([]),
});

export type Album = z.infer<typeof AlbumSchema>;

export const GalleryConfigSchema = z.object({
  enabled: z.boolean().default(true),
  layout: z.enum(["masonry", "grid", "columns"]).default("masonry"),
  columns: z.number().int().min(1).max(8).default(3),
  gap: z.number().int().nonnegative().default(12),
  lightbox: z.boolean().default(true),
  showExif: z.boolean().default(true),
  showCaption: z.boolean().default(true),
  showCounter: z.boolean().default(true),
  thumbnailQuality: z.number().int().min(1).max(100).default(80),
  lazyLoad: z.boolean().default(true),
  placeholder: z.boolean().default(true),
  sortBy: z.enum(["date-desc", "date-asc", "name", "manual"]).default("date-desc"),
  showAlbumListOnIndex: z.boolean().default(true),
  albums: z.array(AlbumSchema).default([]),
});

export type GalleryConfig = z.infer<typeof GalleryConfigSchema>;
