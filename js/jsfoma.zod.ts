/**
 * Zod schemas for FST library
 */
 
import { z } from "zod";

export const State = z.union([z.string(), z.number().gte(0)]);
export const Weight = z.number().gte(0);
export const Target = z.union([State, z.tuple([State, Weight])]);
export const Transitions = z.record(z.string(), z.array(Target));
export const States = z.record(State, Transitions);
export const Symbols = z.record(z.string(), z.number().gte(3));
export const Finals = z.record(State, z.number().gte(0));

export const FST = z.object({
    t: States,
    s: Symbols,
    f: Finals,
    maxlen: z
        .number()
        .gt(0)
        .describe("Length in UTF-16 code units of longest symbol")
        .optional(),
}).describe("Finite-State Transducer");
