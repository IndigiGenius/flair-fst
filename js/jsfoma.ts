/**
 * Javascript runtime for pyfoma (including some other functionality).
 *
 * Originally based on foma_apply_down.js by Mans Hulden
 * <mans.hulden@gmail.com> but substantially rewritten by David
 * Huggins-Daines <dhd@ecolingui.ca>.
 *
 * Including code substantially inspired by pyfoma.
 *
 * © 2024 Mila - Institut québécois d’intelligence artificielle
 */

import {
    FST as FSTSchema,
    Finals as _Finals,
    Symbols as _Symbols,
    States as _States,
    State as _State,
    Target as _Target,
    Weight as _Weight,
} from "./jsfoma.zod.js";
import { z } from "zod";

export { FSTSchema };
export type FST = z.infer<typeof FSTSchema>;
export type Symbols = z.infer<typeof _Symbols>;
export type Target = z.infer<typeof _Target>;
export type Weight = z.infer<typeof _Weight>;
export type State = z.infer<typeof _State>;
export type States = z.infer<typeof _States>;
export type Finals = z.infer<typeof _Finals>;

function get_labels(label: string): [string, string] {
    // Split labels on | (which can be escaped)
    const labels = label.split(/(?<!\\)\|/).map((s) => s.replace("\\|", "|"));
    if (labels.length == 1)
        // acceptor
        labels.push(labels[0]);
    return [labels[0], labels[1]];
}

function make_labels(inLabel: string, outLabel: string): string {
    if (inLabel == outLabel) return inLabel.replace("|", "\\|");
    return [inLabel, outLabel].map((s) => s.replace("|", "\\|")).join("|");
}

export function tokenize(inString: string, vocab: Symbols): Array<string> {
    const tokens: Array<string> = [];
    let start = 0;
    while (start < inString.length) {
        // Single characters always become tokens even if not in the
        // vocabulary, to allow @UN@ matching
        let token = inString.substring(start, start + 1);
        for (let end = start + 2; end <= inString.length; end++) {
            let maybe = inString.substring(start, end);
            if (maybe in vocab) token = maybe;
        }
        tokens.push(token);
        start += token.length;
    }
    return tokens;
}

/**
 * Add a transition to an FST.
 */
function add_transition(
    fst: FST,
    fromState: State,
    toState: State,
    label: string,
    weight: number,
) {
    if (!(fromState in fst.t)) fst.t[fromState] = {};
    if (!(label in fst.t[fromState])) fst.t[fromState][label] = [];
    /* Need to match target *and* weight. Possibly slow. */
    for (const target of fst.t[fromState][label]) {
        const [targetState, transWeight] = unpack_target(target);
        if (toState == targetState && weight == transWeight) return;
    }
    if (weight == 0) fst.t[fromState][label].push(toState);
    else fst.t[fromState][label].push([toState, weight]);
}

function add_symbol(fst: FST, label: string) {
    if (!(label in fst.s)) fst.s[label] = Object.keys(fst.s).length + 3;
}

/**
 * Add a final `.*` to the end of an FST.  It's very advantageous to
 * do this *after* composition as `.`-matching is really slow at the
 * moment (FIXME: fix this).  Mutates its argument for extra speed.
 */
export function add_final_star(fst: FST, weight: Weight = 0.0) {
    for (const state in fst.f) {
        for (const c in fst.s) {
            if (c == "")
                // Don't create epsilon loops! Oops!
                continue;
            add_transition(fst, state, state, c, weight);
        }
        add_transition(fst, state, state, ".", weight);
    }
}

export function copy(fst: FST): FST {
    const newfst: FST = {
        t: {},
        s: {},
        f: {},
    };
    Object.assign(newfst.s, fst.s);
    Object.assign(newfst.f, fst.f);
    for (const state in fst.t)
        for (const label in fst.t[state])
            for (const target of fst.t[state][label]) {
                const [state, weight] = unpack_target(target);
                add_transition(newfst, state, state, label, weight);
            }
    return newfst;
}

/**
 * Construct a linear FST, optionally using a vocabulary of symbols
 * for tokenization, optionally adding '.*' to the end.
 */
export function linearFST(
    inString: string,
    inVocab: Symbols | null = null,
    prefix = false,
): FST {
    const states: States = {};
    const vocab: Symbols = {};
    if (inVocab === null) inVocab = vocab;
    let state = 0;
    for (const tok of tokenize(inString, inVocab)) {
        states[state] = {};
        states[state][tok] = [++state];
        if (!(tok in vocab)) vocab[tok] = Object.keys(vocab).length;
    }
    const finals: Finals = {};
    finals[state] = 0;
    const fst = {
        s: vocab,
        f: finals,
        t: states,
    };
    if (prefix) add_final_star(fst);
    return fst;
}

function matcher(fst1: FST, sym1: string, fst2: FST, sym2: string): boolean {
    if (sym1 == sym2) return true;
    // FIXME: This stuff here is realllly slow (and gets called lots)
    if (sym1 === "." && sym2 !== "" && !(sym2 in fst1.s)) return true;
    if (sym2 === "." && sym1 !== "" && !(sym1 in fst2.s)) return true;
    return false;
}

function unpack_target(target: Target): [State, Weight] {
    if (target instanceof Array) return target as [State, Weight];
    else return [target, 0];
}

/**
 * Directly apply an FST to an input (or output) string, generating
 * input/output pairs in lowest-weighted/longest order. FIXME: will
 * hang on epsilon loops.
 *
 * Note that `apply_up`, `apply_down`, `generate` and `paradigm` are
 * just convenience wrappers around this function.
 */
export function* apply(
    net: FST,
    inString: string,
    direction: "up" | "down",
    prefix = false,
): Generator<[string, string, Weight]> {
    const tokens = tokenize(inString, net.s);
    type QElem = [State, Weight, number, string, string];
    const Q: Array<QElem> = [[0, 0.0, 0, "", ""]];
    const IN = direction === "down" ? 0 : 1;

    /**
     * Compare queue elements (lowest weight + longest)
     */
    function _better(a: QElem, b: QElem): boolean {
        if (a[1] == b[1]) return a[2] > b[2];
        return a[1] < b[1];
    }

    /**
     * Bubble last element to its rightful position
     */
    function _siftdown(Q: Array<QElem>, startpos: number, pos: number) {
        const newitem = Q[pos];
        while (pos > startpos) {
            const parentpos = (pos - 1) >> 1;
            const parent = Q[parentpos];
            if (_better(newitem, parent)) {
                Q[pos] = parent;
                pos = parentpos;
                continue;
            }
            break;
        }
        Q[pos] = newitem;
    }

    /**
     * Bubble first element to its rightful position
     */
    function _siftup(Q: Array<QElem>, pos: number) {
        const endpos = Q.length;
        const startpos = pos;
        const newitem = Q[pos];
        let childpos = 2 * pos + 1; /* first child element of pos */
        while (childpos < endpos) {
            /* second child element of pos */
            const rightpos = childpos + 1;
            /* better of the two children */
            if (rightpos < endpos && !_better(Q[childpos], Q[rightpos]))
                childpos = rightpos;
            Q[pos] = Q[childpos];
            pos = childpos;
            childpos = 2 * pos + 1;
        }
        Q[pos] = newitem;
        _siftdown(Q, startpos, pos);
    }

    /**
     * Push a transition onto the priority queue.  This is just
     * translated from Python's heapq.heappush for coherence with
     * pyfoma.
     */
    function _queue_push(
        target: State | [State, Weight],
        score: Weight,
        pos: number,
        input: string,
        output: string,
    ) {
        const [state, weight] = unpack_target(target);
        Q.push([state, score + weight, pos, input, output]);
        _siftdown(Q, 0, Q.length - 1);
    }
    /**
     * Pop the next state from the priority queue.  This is just
     * translated from Python's heapq.heappop for coherence with
     * pyfoma.
     */
    function _queue_pop(): QElem {
        const last = Q.pop()!; /* We! Know! It! Exists! */
        if (Q.length == 0) return last;
        const best = Q[0];
        Q[0] = last;
        _siftup(Q, 0);
        return best;
    }

    while (Q.length) {
        const [state, score, pos, input, output] = _queue_pop();
        if (state in net.f && pos == tokens.length)
            yield [input, output, score];
        for (const label in net.t[state]) {
            const labels = get_labels(label);
            if (prefix && pos === tokens.length) {
                /* Keep generating after prefix */
                for (const target of net.t[state][label]) {
                    _queue_push(
                        target,
                        score,
                        pos,
                        input + labels[0],
                        output + labels[1],
                    );
                }
            } else if (
                labels[IN] === "" ||
                matcher(net, labels[IN], net, tokens[pos])
            ) {
                for (const target of net.t[state][label]) {
                    const newpos = labels[IN] === "" ? pos : pos + 1;
                    const insym = labels[0] === "." ? tokens[pos] : labels[0];
                    const outsym = labels[1] === "." ? tokens[pos] : labels[1];
                    /* NOTE: can keep generating from epsilons at the end */
                    if (newpos <= tokens.length)
                        _queue_push(
                            target,
                            score,
                            newpos,
                            input + insym,
                            output + outsym,
                        );
                }
            }
        }
    }
}

/**
 * Generate entire output language of an FST (FIXME: will hang on
 * epsilon loops).
 */
export function* generate(net: FST): Generator<[string, string, Weight]> {
    yield* apply(net, "", "down", true);
}

/**
 * Generate up to `take` inputs of an FST for a given output, or all
 * inputs (beware!) if `take` is 0.  (FIXME: will hang on epsilon
 * loops)
 */
export function apply_up(
    net: FST,
    inString: string,
    take: number = 128,
): Array<string> {
    const inputs = [];
    let idx = 0;
    for (const [input, _o, _s] of apply(net, inString, "up")) {
        inputs.push(input);
        if (take && ++idx == take) break;
    }
    return inputs;
}

/**
 * Generate up to `take` outputs of an FST for a given input, or all
 * outputs (beware!) if `take` is 0 (FIXME: will hang on epsilon
 * loops)
 */
export function apply_down(
    net: FST,
    inString: string,
    take: number = 128,
): Array<string> {
    const outputs = [];
    let idx = 0;
    for (const [_i, output, _s] of apply(net, inString, "down")) {
        outputs.push(output);
        if (take && ++idx == take) break;
    }
    return outputs;
}

/**
 * Generate up to `take` input/output pairs where the output begins with the
 * specified prefix, or all pairs if `take` is 0 (beware!)
 */
export function paradigm(
    net: FST,
    prefix: string,
    take: number = 128,
): Array<[string, string]> {
    const pairs = [];
    let idx = 0;
    for (const triple of apply(net, prefix, "up", true)) {
        const pair: [string, string] = [triple[0], triple[1]];
        pairs.push(pair);
        if (take && ++idx == take) break;
    }
    return pairs;
}

export function compose(fst1: FST, fst2: FST): FST {
    const newfst: FST = {
        t: {},
        s: {},
        f: {},
    };
    const Q: Array<[State, State, number]> = [[0, 0, 0]];
    const S: Map<string, State> = new Map();
    function get_state(A: State, B: State, mode: number): State {
        let newstate = S.get([A, B, mode].join("|"));
        if (newstate === undefined) {
            Q.push([A, B, mode]);
            newstate = S.size;
            S.set([A, B, mode].join("|"), newstate);
        }
        return newstate;
    }
    while (Q.length > 0) {
        const [A, B, mode] = Q.pop()!; // we! know! it's! not! empty!
        const currentstate = get_state(A, B, mode);
        if (A in fst1.f && B in fst2.f)
            newfst.f[currentstate] = fst1.f[A] + fst2.f[B];
        // FIXME: Refactor all this to be more like the Python code
        // because Flat is Better Than Nested
        for (const label in fst1.t[A]) {
            let [ain, aout] = get_labels(label);
            if (mode === 0 || aout !== "") {
                for (const target1 of fst1.t[A][label]) {
                    const [state1, weight1] = unpack_target(target1);
                    for (const label in fst2.t[B]) {
                        let [bin, bout] = get_labels(label);
                        if (!matcher(fst1, aout, fst2, bin)) continue;
                        for (const target2 of fst2.t[B][label]) {
                            const [state2, weight2] = unpack_target(target2);
                            const newstate = get_state(state1, state2, 0);
                            // Propagate symbols through . matches
                            if (bout === "." && !(bin in fst1.s)) bout = aout;
                            if (ain === "." && !(aout in fst2.s)) ain = bin;
                            const newlabel = make_labels(ain, bout);
                            // FIXME: Semantics of . are not properly
                            // preserved (NOTE: may wish to consider not
                            // treating . the same way as pyfoma)
                            add_symbol(newfst, ain);
                            add_symbol(newfst, bout);
                            add_transition(
                                newfst,
                                currentstate,
                                newstate,
                                newlabel,
                                weight1 + weight2,
                            );
                        }
                    }
                }
            }
        }
        for (const label in fst1.t[A]) {
            const [ain, aout] = get_labels(label);
            if (aout !== "") continue;
            if (mode === 2) break;
            const target2 = B;
            for (const target1 of fst1.t[A][label]) {
                const [state1, weight1] = unpack_target(target1);
                const newstate = get_state(state1, target2, 1);
                const newlabel = label;
                add_symbol(newfst, ain);
                add_transition(
                    newfst,
                    currentstate,
                    newstate,
                    newlabel,
                    weight1,
                );
            }
        }
        for (const label in fst2.t[B]) {
            const [bin, bout] = get_labels(label);
            if (bin !== "") continue;
            if (mode === 1) break;
            const target1 = A;
            for (const target2 of fst2.t[B][label]) {
                const [state2, weight2] = unpack_target(target2);
                const newstate = get_state(target1, state2, 2);
                const newlabel = label;
                add_symbol(newfst, bout);
                add_transition(
                    newfst,
                    currentstate,
                    newstate,
                    newlabel,
                    weight2,
                );
            }
        }
    }

    return newfst;
}

export function project(fst: FST, direction: "up" | "down"): FST {
    const newfst: FST = {
        t: {},
        s: {},
        f: {},
    };
    Object.assign(newfst.f, fst.f);
    const OUT = direction == "down" ? 1 : 0;
    for (const state in fst.t) {
        newfst.t[state] = {};
        for (const label in fst.t[state]) {
            const sym = get_labels(label)[OUT];
            add_symbol(newfst, sym);
            const newlabel = sym.replace("|", "\\|");
            for (const target of fst.t[state][label]) {
                const [targetState, transWeight] = unpack_target(target);
                add_transition(
                    newfst,
                    state,
                    targetState,
                    newlabel,
                    transWeight,
                );
            }
        }
    }
    // Preserve semantics of . (NOTE: may wish to consider not
    // treating . the same way as pyfoma)
    if ("." in fst.s) newfst.s = fst.s;
    return newfst;
}
