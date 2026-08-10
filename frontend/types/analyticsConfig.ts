import { z } from "zod";

export const GoogleAnalyticsSchema = z.object({
  enabled: z.boolean().default(false),
  measurementId: z.string().default(""),
});

export const UmamiAnalyticsSchema = z.object({
  enabled: z.boolean().default(false),
  scriptUrl: z.string().url().default("https://cloud.umami.is/script.js"),
  websiteId: z.string().default(""),
  dataHostUrl: z.string().optional(),
});

export const ClarityAnalyticsSchema = z.object({
  enabled: z.boolean().default(false),
  projectId: z.string().default(""),
});

export const Analytics51laSchema = z.object({
  enabled: z.boolean().default(false),
  id: z.string().default(""),
});

export const PlausibleAnalyticsSchema = z.object({
  enabled: z.boolean().default(false),
  domain: z.string().default(""),
  scriptUrl: z.string().optional(),
});

export const AnalyticsConfigSchema = z.object({
  google: GoogleAnalyticsSchema.default({}),
  umami: UmamiAnalyticsSchema.default({}),
  clarity: ClarityAnalyticsSchema.default({}),
  _51la: Analytics51laSchema.default({}),
  plausible: PlausibleAnalyticsSchema.default({}),
  respectDNT: z.boolean().default(true),
  anonymizeIP: z.boolean().default(true),
  sendPageviews: z.boolean().default(true),
  sendEvents: z.boolean().default(true),
});

export type AnalyticsConfig = z.infer<typeof AnalyticsConfigSchema>;
