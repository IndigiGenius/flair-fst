/**
 * Zod Schemas for the API (client and server side)
 */

import { z } from "zod";

export const GlossSchema = z.object({
    gloss: z.string(),
    root: z.string().optional(),
    ref: z.string().default(""),
    page: z.string().optional(),
});
export type Gloss = z.infer<typeof GlossSchema>;

export const GlossarySchema = z.record(z.string(), z.record(z.string(), GlossSchema));
export type Glossary = z.infer<typeof GlossarySchema>;

export const SourceSchema = z.object({
    url: z.string().optional(),
    citation: z.string(),
    pageOffset: z.number().default(0),
});
export type Source = z.infer<typeof SourceSchema>;

export const BibliographySchema = z.record(z.string(), SourceSchema);
export type Bibliography = z.infer<typeof BibliographySchema>;
