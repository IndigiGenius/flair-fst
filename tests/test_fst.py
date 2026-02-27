"""Unit testing for FST operations."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pyfoma import FST, algorithms
from flair_fst.fst import toatt, tojson, todict, fromdict, pairs


def make_simple_fst():
    return FST.rlg(
        {
            "Root": [
                ("foo", "Inf"),
                ("bar", "Inf"),
                ("baz", "Inf"),
                # This has length 6 in JS, not 5, because UTF-16
                ("'quux🤣'", "Inf"),
                # Make sure a literal | will not cause issues
                ("argle|bargle", "Inf"),
            ],
            "Inf": [
                ("", "#"),
                (("'+POSS'", r"\'s"), "#"),
            ],
        },
        "Root",
    )


def test_toatt():
    """Test AT&T files"""
    # Make a simple FST and test saving it
    g = make_simple_fst()
    # pyfoma currently does not actually do the right thing, but it
    # does have the right number of transitions :)
    bad_att_trs = str(g).strip().split("\n")
    with TemporaryDirectory() as tdir:
        tpath = Path(tdir)
        toatt(g, tpath / "foo.fst", state_symbols=True)
        with open(tpath / "foo.fst", "rt") as infh:
            good_att_trs = [spam.strip() for spam in infh]
            assert len(bad_att_trs) == len(good_att_trs)
        # Just verify that some stuff exists :)
        with open(tpath / "foo.isyms", "rt") as infh:
            eps = next(infh)
            assert eps == "@0@\t0\n"
        with open(tpath / "foo.osyms", "rt") as infh:
            eps = next(infh)
            assert eps == "@0@\t0\n"
        with open(tpath / "foo.ssyms", "rt") as infh:
            assert "Root\t0\n" in infh


def test_todict():
    """Test dictionary (pre-JSON) form"""
    g = make_simple_fst()
    d = todict(g)
    # Make sure bars are recognized
    assert r"|" in d["s"]
    found = False
    for src, arcs in d["t"].items():
        for tlabel, targets in arcs.items():
            # Make sure bars are escaped in labels
            if tlabel == r"\|":
                found = True
    assert found


def test_tojson():
    """Test JSON exporting."""
    g = make_simple_fst()
    j = tojson(g)
    _ = json.loads(j)


def test_fromjson():
    """Test JSON importing."""
    g = make_simple_fst()
    gg = fromdict(json.loads(tojson(g)))
    # It's a simple FST so we can just test that they generate the same language
    ggpairs = set(pairs(gg))
    assert ggpairs == set(pairs(g))
    # Make sure escaped bars can work
    assert ("argle|bargle", "argle|bargle") in ggpairs


def make_approx() -> FST:
    return FST.regex(r"""
    $^rewrite(
            s:?'š'<1>
            | c:?'č'<1>
            | \?:Ɂ
            | 7:Ɂ
            | ʔ:Ɂ
        )
    """)

APPROXFST = make_approx()


def test_tojson_repeat():
    """Ensure tojson gives consistent results across runs."""
    approx_json1 = tojson(APPROXFST, indent=2)
    approx_json2 = tojson(APPROXFST, indent=2)
    assert approx_json1 == approx_json2
    approxfst2 = make_approx()
    approx_json3 = tojson(approxfst2, indent=2)
    assert approx_json1 == approx_json3
