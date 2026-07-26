# PAINDICATOR — Final Report Outline (Section-by-Section)

> **What this is.** A complete, ready-to-execute structure for the final academic report (BME capstone,
> Tel Aviv University). For every section it says: the **goal**, **what to write**, **which facts to
> pull from `context_pack.md`** (cited as `CP §n`), a **length guide**, and **pitfalls**.
>
> **How to drive ChatGPT with it.** Paste `context_pack.md` first (ground truth), then this outline,
> then say:
> *"Draft Section X of my final report using ONLY facts from the context pack. Academic tone, third
> person, past tense for what was built. Where the outline says 'cite CP §n', use those exact facts.
> Flag anywhere you'd need a real external citation with [REF]."*
> Work **one section at a time** — it keeps the model accurate and lets you review as you go.
>
> **Global writing rules** (tell ChatGPT once):
> - Honest medical framing everywhere: **decision support, not a diagnostic device** (CP §16).
> - Past tense for what was designed/built; present tense for what the system *does*.
> - Define every clinical term on first use (CP §17 glossary).
> - Never invent metrics, numbers, or citations. Exact formulas/thresholds come from CP §8.
> - Target length depends on your faculty's template — ranges below assume ~30–45 pages total.

---

## Front matter

**Goal:** identify the work and its people.
**Write:** title; authors **Amit Bezalel & Shachar Guttman**; supervisor **Prof. Mickey Scheinowitz**;
**Tel Aviv University, Biomedical Engineering**; clinical partner **Loewenstein Rehabilitation Medical
Center (Clalit Health Services)**; date; the project logo (`docs/logo.png`).
**Cite:** CP §1.
**Length:** 1 page. **Pitfall:** make the title descriptive ("A 3D Digital Pain-Mapping and Dermatome-
Analysis System for Clinical Documentation"), not just "PAINDICATOR."

## Abstract

**Goal:** the whole project in one paragraph a judge/examiner reads first.
**Write:** problem (pain documentation is subjective/untrackable) → solution (paint pain on a 3D body,
per-vertex → dermatome metrics + rule-based report) → how it was built (PyQt6/VTK, tablet, offline) →
outcome (a complete, deployable prototype, co-developed with Loewenstein) → honest limitation (decision
support, not validated diagnosis).
**Cite:** CP §1, §2, §8, §16, §18.
**Length:** 150–250 words. **Pitfall:** no jargon without a one-word gloss; include the disclaimer in
one clause.

## Table of contents / list of figures & tables
Auto-generated. Plan figures early: architecture diagram, dermatome pipeline, the 4 screenshots
(`docs/screenshots/`), a metrics table, a sample report.

---

## 1. Introduction

**Goal:** motivate the project and state exactly what it set out to do.
**Write:**
- 1.1 **Clinical motivation** — pain is ubiquitous and poorly documented; the four weaknesses of paper/
  verbal pain reporting (subjective, unstructured, not comparable over time, anatomically imprecise);
  the clinician's real task is localizing pain to a spinal level.
- 1.2 **Project goal & objectives** — digitize pain mapping; enable quantitative dermatome analysis;
  support (not replace) clinical reasoning; track pain over time.
- 1.3 **Scope** — what's in (patient + clinician flows, dermatome engine, rule-based report, tablet app)
  and out (no diagnosis, no validated ML, no cloud).
- 1.4 **Report structure** — one sentence per chapter.
**Cite:** CP §1, §2.
**Length:** 2–3 pages. **Pitfall:** keep objectives measurable and modest; don't over-claim clinical proof.

## 2. Background & literature review

**Goal:** situate the work in clinical and technical prior art; show the gap.
**Write:**
- 2.1 **Pain & its assessment** — VAS and self-report; the traditional paper "pain drawing" / body
  chart and its documented limitations. [REF]
- 2.2 **Dermatomes & neuroanatomy** — what a dermatome is; C1–S5; how root compression (e.g. disc
  herniation) produces dermatomal pain; that dermatome maps vary between references (Keegan & Garrett,
  etc.). [REF]
- 2.3 **Digital pain-mapping / EMR body charts** — existing 2D click-region tools; what they capture vs
  miss. [REF]
- 2.4 **Gap analysis** — none combine **per-vertex 3D capture + automatic dermatome mapping +
  quantitative per-nerve metrics + an explainable report + longitudinal storage**. This is PAINDICATOR's niche.
**Cite:** CP §2, §7, §17; positioning from CP §15/§16.
**Length:** 4–6 pages. **Pitfall:** every clinical claim here needs a real citation — mark each `[REF]`
and fill from PubMed/textbooks; do **not** let ChatGPT fabricate references.

## 3. Requirements & design goals

**Goal:** translate the clinical need into engineering requirements.
**Write:**
- 3.1 **Stakeholders** — patient (self-report on a tablet), clinician (review station), the hospital
  (documentation workflow). Note the Loewenstein collaboration shaped these.
- 3.2 **Functional requirements** — guided patient flow; paint/erase/undo at 3 intensities; dermatome
  analytics; clinician review with toggle/identify/overlay; questionnaire; save/load.
- 3.3 **Non-functional requirements** — tablet-first touch/stylus; **offline** operation; **bilingual
  EN/HE + RTL**; **local/private** data; reliable VTK interaction; deployable as a single EXE.
- 3.4 **Constraints** — Windows tablet; model topology must match the dermatome map; VTK lifecycle
  fragility; backward-compatible saved sessions.
**Cite:** CP §3, §4, §13, §14, §16.
**Length:** 2–3 pages. **Pitfall:** phrase as requirements ("the system shall…"), then later show how
each was met (forward-reference §8 Results/Discussion).

## 4. System architecture & design

**Goal:** the big picture before the details.
**Write:**
- 4.1 **Layered architecture** — the code map and ownership rules: `SessionManager` = single source of
  truth; `RendererScene` = sole VTK owner; `CustomInteractorStyle` = sole interaction owner; screens =
  UI/flow only. Include the architecture **table/diagram**.
- 4.2 **Data flow** — patient paints → `point_levels` → coverage engine → clinician panel + JSON
  (reproduce the pipeline diagram).
- 4.3 **Technology choices & justification** — why native PyQt6 + VTK (smooth stylus/touch 3D, offline
  EXE) over a web app; why a VTK-free pure-math analysis core (testability, portability).
**Cite:** CP §12, §8 (pipeline), §13.
**Length:** 3–4 pages. **Pitfall:** draw the architecture diagram yourself; describe responsibilities,
not line-by-line code.

## 5. Methods / implementation

The technical heart. Six subsections.

- 5.1 **3D model & dermatome mapping** — the male/female meshes (~200k vertices); the `.u8` per-vertex
  ID file (1 byte/vertex); the ID table (0=UNASSIGNED, 1=C1…30=S5); the **topology constraint**; the
  `DermatomeMapper` and its meta formats. **Cite:** CP §7, §14.
- 5.2 **3D interaction engine** — per-vertex "Paint V2"; radius brush + screen-space interpolation;
  **normal gating** (dot(normal, view) threshold) to prevent painting through the body; per-stroke undo
  dict; the four modes (VIEW/MARK/ERASE/NONE); stylus + multi-touch; lazy VTK init / safe teardown.
  **Cite:** CP §6.
- 5.3 **Dermatome coverage engine** — the centerpiece. State the aggregation, the **exact formulas** for
  `weighted_pain_burden`, `pain_area_share`, `local_involvement`, `mean_local_intensity`; the
  **segmental spread** and **overlap-flag** logic; the **thresholds** (`top_n=5`, meaningful `0.05`,
  overlap `rel_diff ≤ 0.30`); the result-dict structure. Present formulas as proper equations and give a
  small **worked example** with toy numbers. **Cite:** CP §8 (and note legacy §9 exists but isn't active).
- 5.4 **Decision-support analyzer** — rule-based design philosophy (explainable, auditable, *not* a
  diagnosis); input shape; output sections (findings / differentials / red flags / next steps); show
  representative rules by region (cervical→sacral) and the red-flag rules (cauda equina, zoster,
  Valsalva). **Cite:** CP §11, §16.
- 5.5 **Data model & persistence** — the `session.json` schema; `paint_v2` vs legacy `marks`; the
  `dermatome_coverage` key (+ legacy fallback); the bilingual `session_summary.txt`; the session folder
  convention; privacy (local-only). **Cite:** CP §10.
- 5.6 **UX, tablet & internationalization** — guided flow; gesture guide; auto-rotate; dominant-axis
  lock in clinician view; bilingual EN/HE + RTL; tablet keyboard; **packaging** to an offline EXE.
  **Cite:** CP §3, §4, §13.
**Length:** 10–14 pages total (this chapter dominates). **Pitfall:** put equations and the worked
example in 5.3 — examiners reward a concrete numeric demonstration. Use figures liberally.

## 6. Results / demonstration

**Goal:** show it works, end to end. (This is a *systems* project, so "results" = demonstrated
capability, not a clinical trial — say so.)
**Write:**
- 6.1 **Example session walkthrough** — the four screenshots in sequence (welcome → paint front → paint
  back → clinician analysis), narrated.
- 6.2 **Sample analytics output** — a real/representative coverage table (ranked dermatomes with burden/
  area/local/intensity, segmental spread, overlap flag) and what it means
  (e.g. the L5–S1 interpretation).
- 6.3 **Sample decision-support report** — paste an example analyzer output and annotate findings/red
  flags.
- 6.4 **Capability summary** — table mapping each requirement (§3) to "met / partial / future".
**Cite:** CP §8, §11, §15, §18; screenshots in CP §14.
**Length:** 4–6 pages. **Pitfall:** label it "demonstration / capability evaluation," not "clinical
results"; generate a clean, plausible demo session for the figures.

## 7. Discussion

**Goal:** interpret honestly.
**Write:**
- 7.1 **Meeting the goals** — which objectives (§1.2) were achieved and how.
- 7.2 **Strengths & novelty** — per-vertex 3D → quantitative per-nerve metrics with ranked burden and an
  overlap flag; explainable decision support; real clinical partner; finished & deployable; privacy.
- 7.3 **Limitations** — not validated; rules are textbook patterns not proof; dermatome boundaries are
  approximate (hence the overlap flag); self-report bias; female-topology verification; performance on
  older tablets; the touch-as-mouse quirk on some devices.
- 7.4 **Engineering reflections** — the hardest parts (robust painting on a live VTK pipeline on a
  tablet; VTK lifecycle safety; clean separation of rendering/interaction/analysis).
**Cite:** CP §15, §16; §12 for ownership.
**Length:** 3–5 pages. **Pitfall:** be candid about limitations — examiners trust honest discussion more
than hype.

## 8. Future work

**Goal:** a credible roadmap.
**Write:** visual dermatome **heatmap**; **quantitative longitudinal** comparison metrics; **ML** pattern
recognition built on the rule-based labeled foundation; a path toward **clinical validation** and
**regulatory** classification (decision support / CE).
**Cite:** CP §15, §16.
**Length:** 1–2 pages. **Pitfall:** tie each item to something already in place (e.g. ML uses the
existing rules + saved structured sessions).

## 9. Conclusion

**Goal:** close the loop.
**Write:** restate problem → what was built → why it matters → the honest framing. 1–2 paragraphs.
**Cite:** CP §1, §2, §16. **Length:** ~½–1 page.

## 10. References
**Goal:** real, verifiable sources. Categories to populate (find & verify actual citations — do **not**
fabricate): pain assessment / VAS; pain-drawing reliability; dermatome maps (e.g. classic anatomical
references); cauda equina & red-flag guidelines; disc-herniation epidemiology; VTK and PyQt
documentation. Use your faculty's citation style. **Pitfall:** every `[REF]` placeholder from §2/§5.4
must become a real citation.

## Appendices
**Goal:** the exhaustive detail that would clutter the body.
- A. **`session.json` schema** (full, from CP §10).
- B. **Coverage metric definitions & thresholds** (CP §8) — formal equations + the `DermatomeOptions`
  defaults table.
- C. **Questionnaire** — all sections, save-keys, and option values (CP §5).
- D. **Dermatome ID table** (CP §7).
- E. **Screen list & navigation** (CP §3).
- F. **Analyzer rule catalog** (expand CP §11).
- G. **Build & run instructions** (CP §13).
**Pitfall:** appendices are where "every detail" lives — keep the main body readable by pushing tables here.

---

## Figure & table checklist (prepare these assets)
- [ ] Architecture diagram (layers + ownership) — §4
- [ ] Dermatome pipeline diagram (paint → engine → panel/JSON) — §4/§5.3
- [ ] Screenshot set: welcome / paint-front / paint-back / clinician-analysis — §6.1
- [ ] Coverage metrics table (definitions + a worked example) — §5.3/§6.2
- [ ] Sample decision-support report (annotated) — §6.3
- [ ] Requirement → status table — §6.4
- [ ] Dermatome ID table & questionnaire table (appendices)

## Section length cheat-sheet (≈30–45 pp total)
Abstract ¼p · Intro 2–3 · Background 4–6 · Requirements 2–3 · Architecture 3–4 ·
**Methods 10–14** · Results 4–6 · Discussion 3–5 · Future 1–2 · Conclusion ½–1 · Refs/Appendices as needed.
