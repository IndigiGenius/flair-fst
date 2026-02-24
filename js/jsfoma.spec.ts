import { FST, apply_up, apply_down, compose, paradigm, linearFST } from "./jsfoma.js";
import { it } from "mocha";
import { assert } from "chai";

// Test basic FST
const myNet1: FST = {
    t: {
        0: {
            "f|b": [1],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'bar'", () => {
    const reply = apply_down(myNet1, "foo");
    assert(reply[0] == "bar");
});

it("Should return 'foo'", () => {
    const reply = apply_up(myNet1, "bar");
    assert(reply[0] == "foo");
});

// Test acceptor arcs
const myNet2: FST = {
    t: {
        0: {
            "b": [1],
        },
        1: {
            "a": [2],
        },
        2: {
            "r|z": [3],
        },
    },
    s: {"b": 3, "a": 4, "r": 5, "z": 6},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'baz'", () => {
    const reply = apply_down(myNet2, "bar");
    assert(reply[0] == "baz");
});

// Test non-functional FST
const myNet3: FST = {
    t: {
        0: {
            "f": [4],
            "f|b": [1],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
        4: {
            "o": [5],
        },
        5: {
            "o": [3],
        }
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'foo' and 'bar'", () => {
    const reply = apply_down(myNet3, "foo");
    assert(reply.includes("foo"));
    assert(reply.includes("bar"));
});

// Test non-deterministic FST
const myNet4: FST = {
    t: {
        0: {
            "f|b": [1, 4],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
        4: {
            "o": [5],
        },
        5: {
            "o": [3],
        }
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'bar' and 'boo'", () => {
    const reply = apply_down(myNet4, "foo");
    assert(reply.includes("bar"));
    assert(reply.includes("boo"));
});

// Test escaped symbols
const myNet5: FST = {
    t: {
        0: {"a": [1]},
        1: {"b\\|c": [2]},
        2: {"d": [3]},
    },
    s: {"a":3, "b|c": 4, "d": 5},
    f: {3: 1},
    maxlen: 3
};
it("Should accept 'ab|cd'", () => {
    const reply = apply_down(myNet5, "ab|cd");
    assert(reply.includes("ab|cd"));
});

// Test generating from epsilon
const myNet6: FST = {
    t: {
        0: {"|f": [1]},
        1: {"|o": [2]},
        2: {"|o": [3]},
    },
    s: {"f": 3, "o": 4},
    f: {3: 1},
    maxlen: 1,
};
it("Should output 'foo'", () => {
    const reply = apply_down(myNet6, "");
    assert(reply.includes("foo"));
});

// Test "paradigm" generation
it("Should return 'foo:bar'", () => {
    const updown = paradigm(myNet1, "ba");
    assert(updown[0][0] == "foo");
    assert(updown[0][1] == "bar");
});

// Test composition
const myNet71: FST = {
    t: {
        0: {
            "f|b": [1],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};
const myNet72: FST = {
    t: {
        0: {
            "b": [1],
        },
        1: {
            "a": [2],
        },
        2: {
            "r|z": [3],
        },
    },
    s: {"b": 3, "a": 4, "r": 5, "z": 6},
    f: { 3: 1 },
    maxlen: 1,
};
it("Should output 'baz'", () => {
    const myNet7 = compose(myNet71, myNet72);
    let reply = apply_down(myNet7, "foo");
    assert(reply.includes("baz"));
    const myNet67 = compose(myNet6, myNet7);
    reply = apply_down(myNet67, "");
    assert(reply.includes("baz"));
});
const myNet81: FST = {
    t: {
        0: {
            "f|b": [1],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};
const myNet82: FST = {
    t: {
        0: {
            "|FOO": [1],
        },
        1: {
            "b": [2],
        },
        2: {
            "a": [3],
        },
        3: {
            "r|z": [4],
        },
    },
    s: {"b": 3, "a": 4, "r": 5, "z": 6, "FOO": 7},
    f: { 4: 1 },
    maxlen: 1,
};
const myNet8 = compose(myNet81, myNet82);
it("Should output 'FOObaz'", () => {
    let reply = apply_down(myNet8, "foo");
    assert(reply.includes("FOObaz"));
});

// Test rho-matchers
const myNet9: FST = {
    t: {
        0: {
            "f|b": [1],
        },
        1: {
            "o|a": [2],
            ".|a": [2],
        },
        2: {
            "o|r": [3],
        },
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'bar'", () => {
    const reply = apply_down(myNet9, "foo");
    assert(reply[0] == "bar");
});

it("Should also return 'bar'", () => {
    const reply = apply_down(myNet9, "fOo");
    assert(reply[0] == "bar");
});

// Test linear FST
it("Should return an fst that matches 'fooBAR'", () => {
    const fst = linearFST("fooBAR", { BAR: 3 });
    assert("BAR" in fst.s);
    const reply = apply_down(fst, "fooBAR");
    assert(reply[0] == "fooBAR");
});
it("Should also return an fst that matches 'fooBAR'", () => {
    const fst = linearFST("fooBAR");
    assert(!("BAR" in fst.s));
    const reply = apply_down(fst, "fooBAR");
    assert(reply[0] == "fooBAR");
});
it("Should return an fst that matches 'fooBARbazbaz'", () => {
    const fst = linearFST("fooBAR", {}, true);
    const reply = apply_down(fst, "fooBARbazbaz");
    assert(reply[0] == "fooBARbazbaz");
});

// Test weighted FST
const myNet10: FST = {
    t: {
        0: {
            "f|b": [[1, 1.0], 4],
        },
        1: {
            "o|a": [2],
        },
        2: {
            "o|r": [3],
        },
        4: {
            "o": [5],
        },
        5: {
            "o": [3],
        }
    },
    s: {"f": 3, "o": 4, "b": 5, "a": 6, "r": 7},
    f: { 3: 1 },
    maxlen: 1,
};

it("Should return 'boo' and 'bar' in that order", () => {
    const reply = apply_down(myNet10, "foo");
    assert(reply[0] == "boo");
    assert(reply[1] == "bar");
});
