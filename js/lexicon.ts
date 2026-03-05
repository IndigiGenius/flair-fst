/**
 * FLAIR-FST lexicon format.
 */

import { z } from "zod";

import { FST } from "./jsfoma.zod.js";
import { Glossary, Bibliography, Gloss } from "./api.zod.js";

interface Lexicon {
    morphology: z.infer<typeof FST>;
    orthography: z.infer<typeof FST>;
    glossary: z.infer<typeof Glossary>;
    bibliography: z.infer<typeof Bibliography>;
}
