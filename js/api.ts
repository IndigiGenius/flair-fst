import {
    compose,
    generate,
    project,
    linearFST,
    add_final_star,
    FST,
} from "./jsfoma.js";

import express from "express";

// If we did not control this JSON, then we could use FSTSchema to
// validate it (keep in mind for future user-facing apps)
import _morphNet from "./morphology.json";
const morphNet = _morphNet as any as FST;
import _orthoNet from "./orthography.json";
const orthoNet = _orthoNet as any as FST;

const app = express();

app.get("/complete", (req, res) => {
    const text = req.query["t"]?.toString();
    if (text === undefined) {
        res.send([]);
        return;
    }
    if (text.length < 2) {
        res.send([]);
        return;
    }
    const approxForm = project(
        compose(linearFST(text, morphNet.s), orthoNet),
        "down",
    );
    add_final_star(approxForm, 1);
    const approxMatch = compose(morphNet, approxForm);
    const forms = [];
    const seen = new Set();
    let i = 0;
    for (const [_, form] of generate(approxMatch)) {
        if (seen.has(form)) continue;
        seen.add(form);
        if (i++ == 50) break;
        forms.push(form);
    }
    res.send(forms);
});

app.listen(3000, () => {
    console.log("Listening on port 3000");
});
