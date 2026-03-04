from pathlib import Path
from tempfile import NamedTemporaryFile

from flair_fst.rustfst.algorithms import transducer
from flair_fst.rustfst import DrawingConfig, SymbolTable


def test_transducer():
    symt = SymbolTable()
    symt.add_symbol("hello")
    symt.add_symbol("world")
    symt.add_symbol("coucou")
    symt.add_symbol("monde")

    f = transducer("hello world", "coucou monde", symt, symt)
    d = DrawingConfig()

    with NamedTemporaryFile() as tf:
        f.draw(tf.name, None, None, d)
        assert Path(tf.name).exists()
