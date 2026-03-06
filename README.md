# FLAIR-FST: Tools for building lexicons and/or morphological analysers

FLAIR-FST is (yet another) tool to build lexicons and morphological
analysers for natural language.

Its goals are similar to [GiellaLT](https://giellalt.uit.no) and
[Gramble](https://nrc-cnrc.github.io/gramble/), but its focus is on:

- A simplified workflow to create lexicons from tables of data (like
  Gramble), but...
- Output as WFST for use in speech recognizers and other NLP tools
  (like GiellaLT), but...
- Using the friendlier rule language used in
  [Pyfoma](https://github.com/mhulden/pyfoma), and...
- With a web component for querying the resulting lexicon, and...
- A Javascript runtime that can be used to build applications from
  your WFST running directly in the browser.

Please note that its AGPL-3.0 license requires you to publish source
code under a compatible license for any application you build with it!

## Quick Start

TODO

## Introduction

FLAIR-FST is a tool for creating lexicons, which can then be viewed
and explored interactively, and can also be used for autocompletion
and spell-checking.

There are generally three phases to creating a lexicon, you will:

- *Define* words, morphemes, spelling rules and approximate search
  rules.
- *Compile* to a weighted finite-state transducer (a model for fast,
  approximate look-up).
- *Test* the resulting model.

## Define a lexicon

A FLAIR-FST lexicon consists of four JSON files:

- `bibliography.json`: A bibliography of linguistic or community
  resources where words or morphemes are attested.
- `glossary.json`: A list of words (and morphemes) with *glosses*, that
  is, definitions in one or more languages.
- `orthography.json`: A weighted finite-state transducer which defines
  equivalent or approximate inputs for the writing system of the
  target language.  This allows you to define Latin characters that
  are approximately equivalent to hard-to-type symbols, but can also
  be used to define common misspellings.
- `morphology.json`: A (possibly weighted) finite-state transducer
  which defines the possible words of the language, optionally mapping
  each word to a morphological analyisis.  This is built from the list
  of words (and morphemes) as well as a set of *alternation rules*.

You almost certainly **do not** want to create these files yourself,
however!  Instead, you will *define* them through lists of:

- Words
- Prefixes
- Stems
- Suffixes
- Rules

This definition is then *compiled* to produce the data files noted
above.  We provide several ways to create the definition of your lexicon.

### From a spreadsheet

You can find the templates in `src/flair_fst/templates`, or, from the
command-line, you can create a copy of the template with:

```console
flair-fst new sample.ods
```

Once you have added the necessary content to the lexicon, you can run
the command-line interface to convert it to a lexicon:

```console
flair-fst compile sample.ods
```

This will create (provided it doesn't already exist) the directory
`sample.flairfst` next to your spreadsheet.  If you have defined a
test set in your spreadsheet (see the worksheet "Tests"), then these
tests will also be run, and any failures will be reported

### From CSV data files

Alternately, a lexicon can be defined from a set of CSV files.  These
are simply the data from the sheets in the spreadsheet, but the format
may be more portable and easier to create programmatically.  As above,
you can use `flair-fst new` to create such a directory - if no
extension is provided to its argument, it assumes that this is what
you want to do:

```console
flair-fst new sample
```

### From Python code

The data structures used to define a lexicon are defined in the
`flair_fst.compile.definition` module.

## Querying a lexicon in a web browser

If you've created a lexicon in `sample.flairfst`, you can view it in a
web browser using:

```console
flair-fst run sample.flairfst
```

To produce a standalone HTML file which you can share, that can simply
be opened from the Finder, Explorer or other file manager, you can run:

```console
flair-fst html sample.flairfst
```

By default this will create `sample.html`.

## Using the FLAIR-FST web component

FLAIR-FST also includes a web component that can be used in your own
web pages.  To include the lexicon search and browsing component,
simply copy the file `js/flair-fst.js` to the same directory as your
web page.  Assuming that your lexicon is called `sample.flairfst` and
you have also copied it to this directory, you can add this snippet to
the HTML code:

```html
<script type="module" src="flair-fst.js"></script>
<flair-fst base="sample.flairfst"></flair-fst>
```


## License

`flair-fst` is distributed under the terms of the [AGPL
3.0](https://spdx.org/licenses/AGPL-3.0-or-later.html) license, or any
later version.

Some code in `flair_fst.rustfst` is derived from
[rustfst](https://docs.rs/rustfst/latest/rustfst/) and
[pyfoma](https://mhulden.github.io/pyfoma/) and is distributed under
the terms of the [Apache-2.0](https://spdx.org/licenses/Apache-2.0)
license.  This code is clearly marked with comments indicating this
licensing difference.
