---
name: sigak-design
description: Use this skill to generate well-branded interfaces and assets for SIGAK (시각) — an AI personal image analysis service. Monochrome warm-beige + ink brand. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping Sia chat surfaces and sigak-web screens.
user-invocable: true
---

Read the README.md file within this skill for brand foundations, then explore colors_and_type.css, ui_kits/, and preview/ for ready-to-use tokens and components.

If creating visual artifacts (slides, mocks, throwaway prototypes), copy assets out of `assets/` and create static HTML files that import `colors_and_type.css`. If working on production code, lift the CSS vars and component patterns directly — they match `Sigak/sigak-web/app/globals.css` (MVP v1.2).

If the user invokes this skill without guidance, ask what they want to build (Sia onboarding screen? sigak-web landing? result screen?), gather a few questions, then act as an expert designer. Never invent new colors, accent hues, or emoji — SIGAK is strict monochrome paper + ink.
