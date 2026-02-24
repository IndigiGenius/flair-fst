/**
 * Zod Schemas for the API (client and server side)
 */

import { z } from "zod";

export const Gloss = z.object({
    gloss: z.string(),
    root: z.string().optional(),
    ref: z.string().default(""),
    page: z.string().optional(),
});
export const Glosses = z.record(z.string(), Gloss);

export const Source = z.object({
    abbrev: z.string(),
    url: z.string().optional(),
    cite: z.string(),
    pageOffset: z.number().default(0),
});
export const Sources = z.record(z.string(), Source);
