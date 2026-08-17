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

## Quick Start
### 1. Open the Font Package file
<img width="946" height="533" alt="image" src="https://github.com/user-attachments/assets/2697fc95-9fae-458a-a2cd-7cd839871bd0" />

### 2. Select the Character You Want and Export It
<img width="700" height="492" alt="image" src="https://github.com/user-attachments/assets/4bb3e893-24b2-4fdd-bfec-abb973c1ebb3" />
<img width="946" height="533" alt="image" src="https://github.com/user-attachments/assets/53148f5e-a311-456a-8e24-80b172a86d9b" />

### 3. Edit
<img width="760" height="760" alt="changed" src="https://github.com/user-attachments/assets/d5a17e9c-d3d2-43c7-bf27-4c5e0fe2782f" />

### 4. Import
<img width="700" height="492" alt="image" src="https://github.com/user-attachments/assets/184caadb-f74b-403c-86cf-cecb193301d7" />

### 5. Build and Replace the Font Package
<img width="946" height="533" alt="image" src="https://github.com/user-attachments/assets/bf2bc19c-65a9-4f95-ad40-6460449223ab" />

### Result
<img width="870" height="663" alt="result" src="https://github.com/user-attachments/assets/b8c634a7-0470-4201-a303-1c03b5cf3712" />

## Notes About Fonts
+ **Rider Number:** Bike Number characters are exported as RGBA PNGs. The visible grayscale
appearance is stored in RGB and the character coverage is stored in alpha.
Editing the exported PNG in a graphics editor and importing it back preserves
both parts of the character.

+ **Rider Name:** Rider Name characters are displayed and exported as grayscale artwork with
zero-valued background pixels transparent. Rider Number characters remain
RGBA, with plane 0 providing intensity and plane 1 providing coverage.
