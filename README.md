[![Python](https://img.shields.io/badge/Python-3.x-3776AB)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6)](https://github.com/daniilkorochansky/reflex-font-package-viewer)
[![Build](https://github.com/daniilkorochansky/reflex-font-package-viewer/actions/workflows/build.yml/badge.svg)](https://github.com/daniilkorochansky/reflex-font-package-viewer/actions/workflows/build.yml)
[![Latest Release](https://img.shields.io/github/v/release/daniilkorochansky/reflex-font-package-viewer?display_name=tag)](https://github.com/daniilkorochansky/reflex-font-package-viewer/releases)
[![License](https://img.shields.io/github/license/daniilkorochansky/reflex-font-package-viewer)](https://github.com/daniilkorochansky/reflex-font-package-viewer/blob/main/LICENSE)

# Reflex Font Package Viewer
<img width="700" height="492" alt="overview" src="https://github.com/user-attachments/assets/1bfc5c81-963e-4bca-aeac-5b58b557a527" />

A tool for viewing and replacing character resources in the data.fpack file for the game MX vs ATV: Reflex

## Features

+ Export and import сharacter кesources
+ Character resource viewer
+ Build data.fpack
+ Open data.fpack

## Fonts
+ **Rider Number:** Bike Number characters are exported as RGBA PNGs. The visible grayscale
appearance is stored in RGB and the character coverage is stored in alpha.
Editing the exported PNG in a graphics editor and importing it back preserves
both parts of the character.

+ **Rider Name:** Rider Name characters are displayed and exported as grayscale artwork with
zero-valued background pixels transparent. Rider Number characters remain
RGBA, with plane 0 providing intensity and plane 1 providing coverage.
