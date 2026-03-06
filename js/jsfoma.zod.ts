/**
 * Zod schemas for FST library
 */
 
import { z } from "zod";

export const StateSchema = z.union([z.string(), z.number().gte(0)]);
export type State = z.infer<typeof StateSchema>;

export const WeightSchema = z.number().gte(0);
export type Weight = z.infer<typeof WeightSchema>;

export const TargetSchema = z.union([StateSchema, z.tuple([StateSchema, WeightSchema])]);
export type Target = z.infer<typeof TargetSchema>;

export const TransitionsSchema = z.record(z.string(), z.array(TargetSchema));
export type Transitions = z.infer<typeof TransitionsSchema>;

export const StatesSchema = z.record(StateSchema, TransitionsSchema);
export type States = z.infer<typeof StatesSchema>;

export const SymbolsSchema = z.record(z.string(), z.number().gte(3));
export type Symbols = z.infer<typeof SymbolsSchema>;

export const FinalsSchema = z.record(StateSchema, z.number().gte(0));
export type Finals = z.infer<typeof FinalsSchema>;

export const FSTSchema = z.object({
    t: StatesSchema,
    s: SymbolsSchema,
    f: FinalsSchema,
    maxlen: z
        .number()
        .gt(0)
        .describe("Length in UTF-16 code units of longest symbol")
        .optional(),
}).describe("Finite-State Transducer");

export type FST = z.infer<typeof FSTSchema>;
