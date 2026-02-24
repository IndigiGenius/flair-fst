from typing import List, Literal

from setuptools.build_meta import *
from setuptools.dist import Distribution
from setuptools_rust import setuptools_ext, RustExtension

super_rust_extensions = setuptools_ext.rust_extensions


def rust_extensions(
    dist: Distribution, attr: Literal["rust_extensions"], value: List[RustExtension]
) -> None:
    """Post-process the Rust extension to replace its binary with rustfst-ffi"""
    super_rust_extensions(dist, attr, value)
    for ext in dist.rust_extensions:
        if ext.name != "flair_fst._rustfst_python":
            continue
        metadata = ext.metadata(quiet=True)
        for pkg in metadata["packages"]:
            if pkg["name"] == "rustfst-ffi":
                metadata["resolve"]["root"] = pkg["id"]
                break
        else:
            assert "Could not find rustfst-ffi in packages!"
        ext.metadata = lambda **kwargs: metadata


setuptools_ext.rust_extensions = rust_extensions
