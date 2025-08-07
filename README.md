# FLAIR-FST: Tools for building lexicons and/or morphological analysers

## Quick Start

To launch notebooks for experimentation and documentation:

```console
hatch run notebooks:lab
```

To launch the viewer (follow the instructions to access with your browser):

```
npm install
npm start
```

## Introduction

FLAIR-FST is a tool for creating lexicons, which can then be viewed
and explored interactively, and can also be used for autocompletion
and spell-checking.

There are generally three phases to creating a lexicon, you will:

- *Define* words, morphemes, spelling rules and approximate search rules
- *Compile* to a weighted finite-state transducer (a model for fast,
  approximate look-up)
- *Test* the resulting model

## Define a lexicon

A FLAIR-FST lexicon consists of four JSON files:

- `bibliography.json`: A bibliography of linguistic or community
  resources where words or morphemes are attested.
- `lexicon.json`: A list of words (and morphemes) with *glosses*, that
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

### From a spreadsheet

While it is theoretically possible to construct these yourself (they
do have JSON schemas, so you can even edit them easily in VS.Code or
another intelligent editor) we provide a means to build them from a
spreadsheet, for easier editing.  A template spreadsheet in Excel
format is provided which contains a trivial example lexicon (French
words with glosses in English and Spanish) and some basic alternation
rules.

### From a MinCourse

If you have created a minimal course in the [MinCourse
XML](https://github.com/IndigiGenius/MinCourse) format, a template
spreadsheet or an initial lexicon can also be induced from the words
and glosses used there.

## Compile the lexicon


## Test the lexicon


## License

`flair-fst` is distributed under the terms of the [AGPL
3.0](https://spdx.org/licenses/AGPL-3.0-or-later.html) license, or any
later version.
