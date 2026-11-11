# Mekorot
A Hebrew typeface in the Rashi style. Originally this project was part of an attempt to create a free version of the Hebrew Talmud, as PDF files, while keeping the page layout known as Tzurat Hadaf.

This project has been adapted from a previous [SourceForge archive](https://sourceforge.net/projects/mekorot/), based on the [original work by Dr. Alan Hoenig](https://ctan.org/tex-archive/language/hebrew/makor/).

In 2023 this project was reengineered and redrawn by Eli Heuer for inclusion in the Google Fonts catalog. The Latin typeface included is a fork of [Spectral](https://fonts.google.com/specimen/Spectral).

# Building

Fonts are built automatically by GitHub Actions - take a look in the "Actions" tab for the latest build.

If you want to build fonts manually on your own computer:

* `make build` will produce font files.
* `make test` will run [FontBakery](https://github.com/googlefonts/fontbakery)'s quality assurance tests.
* `make proof` will generate HTML proof files.

The proof files and QA tests are also available automatically via GitHub Actions. 

# License

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at
https://scripts.sil.org/OFL

# Repository Layout

This font repository structure is inspired by [Unified Font Repository v0.3](https://github.com/unified-font-repository/Unified-Font-Repository), modified for the [Google Fonts](https://github.com/googlefonts/googlefonts-project-template) workflow.

# Changelog
**5 July 2023. Version 2.000**
- Version 2.000 release

**1 March 2023. Version 0.001**
- Removed all Spectral related source files
- Started a clean fork of Crimson Pro for Latian coverage

**12 Jan 2023. Version 0.001**
- Updated repo to the new Google Fonts Project Template


## Fork: lighter weight, full niqqud and te'amim

This fork adds a family of static TTFs in `fonts/otzaria/`:
**Light, Regular, Medium, SemiBold, Bold, ExtraBold** (family name `Mekorot`).

Changes relative to upstream:

- **Light** (weight 300): the upstream variable font's `wght` axis continued below 400, so the original letterforms are kept with thinner strokes.
- Wider word space (250 -> 340 units) and +15 units of spacing on each Hebrew letter.
- Added missing punctuation: maqaf `U+05BE`, sof pasuq `U+05C3`, geresh `U+05F3`, gershayim `U+05F4`, paseq `U+05C0`, nun hafukha `U+05C6`, hyphen variants, and zero-width / bidi format characters. Maqaf, geresh, gershayim and sof pasuq are derived from the font's own hyphen, quotes and colon.
- Added all missing niqqud and te'amim (`U+0591`-`U+05C7`, 36 glyphs), positioned with GPOS mark-to-base and mark-to-mark. **These glyphs are taken from [Noto Rashi Hebrew](https://github.com/notofonts/hebrew)** (OFL 1.1, Copyright 2022 The Noto Project Authors), not drawn for Mekorot, and are placed with computed anchors, so fine tuning by a type designer is still needed.

Build: `python scripts/otzaria/build_family.py "fonts/variable/Mekorot[wght].ttf" NotoRashiHebrew-VariableFont_wght.ttf fonts/otzaria` (needs `fonttools`).

Licensed under the SIL Open Font License 1.1, see `OFL.txt`.
