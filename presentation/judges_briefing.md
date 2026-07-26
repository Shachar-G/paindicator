# PAINDICATOR — Judges' Briefing

> **Everything a judge needs to understand, believe, and reward this project.**
> A reference document for the team and for the panel. Read top-to-bottom in ~6 minutes.

---

## 0. One-liner & elevator pitch

**PAINDICATOR turns "where does it hurt?" into structured, quantitative, trackable clinical data.**

A patient paints the *location* and *intensity* of their pain directly onto an interactive **3D body
model**. Because every point on that model is pre-mapped to a **dermatome** (the skin zone served by a
single spinal nerve root), the painting is instantly converted into per-nerve-segment metrics that
help a clinician **localize** the source of the pain and **track** it across visits. It is built for
**touch tablets** in a real clinic, ships as an **offline Windows app**, and was developed **with a
clinical partner** — Loewenstein Rehabilitation Medical Center.

*30-second version:* "Today, pain is documented as a hand drawing on paper or a vague verbal note —
subjective, unstructured, and impossible to measure over time. PAINDICATOR replaces that with an
interactive 3D body the patient paints on. Every painted point maps to a spinal nerve segment, so we
automatically produce quantitative, anatomical pain analytics and a transparent decision-support
report for the clinician. It's finished, it runs on a tablet, and we built it with a rehabilitation
hospital."

---

## 1. The problem

Pain is one of the most common reasons people see a doctor, yet it is one of the **worst-documented**
clinical signals:

- **Subjective & unstructured** — recorded as free text ("lower back, radiating down the leg") or a
  felt-tip drawing on a paper body chart.
- **Not quantifiable** — you cannot compute coverage, intensity distribution, or "how much of nerve
  root L5 is involved" from a paper drawing.
- **Not trackable** — comparing this month's drawing to last month's is eyeballing, not measurement.
  Pain management is fundamentally about change over time, and the current tools throw that away.
- **Loses anatomical precision** — a 2D sketch doesn't tell the clinician *which spinal level* the
  pattern points to, which is exactly the question that drives imaging and referral decisions.

The clinician's core task — **localizing pain to a nerve/spinal level** — is done from memory and a
paper picture. That is the gap PAINDICATOR closes.

---

## 2. The solution

A two-sided clinical tool:

1. **Patient side** — a guided, touch-first flow: enter ID → choose model (male/female) → answer a
   structured pain questionnaire → **paint pain onto a 3D body** at three intensity levels → save.
2. **Clinician side** — browse patients & sessions → replay the painted model → read **automated
   dermatome analytics** → read a **rule-based pain-pattern report** → toggle the dermatome map,
   click any region to name it, and **overlay multiple sessions** to see change over time.

The bridge between the two sides is the **dermatome engine**: painting is **per-vertex**, and every
vertex carries a dermatome ID, so the patient's subjective marks become **quantitative anatomical
data** with no extra work from anyone.

```
patient paints (per-vertex levels 0–3)
        │
        ▼
RendererScene.compute_dermatome_coverage_result()
        │
        ▼
dermatome_coverage.compute_dermatome_coverage()   ← pure math, no VTK / no UI
        │
        ▼
structured result: overall stats + ranked dermatomes
        ├──► clinician panel (live analytics)
        └──► session JSON (saved + comparable over time)
```

---

## 3. Who it's for, the team & the partner

- **Users:** patients (self-report on a tablet) and clinicians (review station) in **pain clinics,
  neurology, orthopedics, spine, and physical-medicine & rehabilitation (PM&R)**.
- **Team:** **Amit Bezalel** and **Shachar Guttman**, Biomedical Engineering students, **Tel Aviv
  University**.
- **Supervisor:** **Prof. Mickey Scheinowitz** (TAU).
- **Clinical partner:** **Loewenstein Rehabilitation Medical Center**, part of **Clalit Health
  Services** — a leading Israeli rehabilitation hospital. This is the credibility anchor: the tool was
  shaped around a real clinical documentation problem, not invented in a vacuum.

> This is a **final BME capstone project** with a genuine hospital collaborator — academic rigor +
> clinical relevance in one.

---

## 4. How it works (the two flows)

**Patient flow:** `role selection → patient ID → gender → questionnaire → 3D model (paint) → save`

The 3D screen offers: **View** (rotate/zoom/pan), **Mark** (paint, with a 3-level palette —
🟡 mild / 🟠 moderate / 🔴 severe), **Erase**, **Undo**, **Reset View**, **Clear**, **Notes**, and a
**?** gesture guide. Input works by **stylus**, **finger**, or **mouse**, with two-finger pinch-zoom,
pan, and rotation, plus a navigation D-pad and auto-rotate.

**Clinician flow:** `clinician name → patient list → session list → session review + analytics`

The review screen shows the painted model (read-only), a **dermatome coverage panel**, a toggle to
swap to the **dermatome-region view**, **click-to-identify** a dermatome by name, a **multi-session
overlay** for longitudinal comparison, and the full session summary (demographics, questionnaire,
notes, analytics) — rendered **bilingually (English/Hebrew)**.

**Saved per session:** `session.json` (full data incl. per-vertex paint + dermatome metrics) +
`session_summary.txt` (human-readable, bilingual) + `front.png` / `back.png` screenshots, stored
**locally** under `data/sessions/{patient_id}/session_{timestamp}/`.

---

## 5. The dermatome engine (core innovation)

**What is a dermatome?** The patch of skin whose sensation is carried by a single spinal nerve root.
The body is covered by ~30 of them, labelled by spinal level: **C1–C8** (neck/arm), **T1–T12**
(trunk), **L1–L5** (front of leg), **S1–S5** (back of leg / saddle). When a nerve root is irritated
or compressed (e.g., a herniated disc), pain shows up in *that dermatome* — so the **pattern of pain
points to the spinal level**. This is everyday clinical reasoning; PAINDICATOR makes it computable.

**How we map it:** the 3D model (male and female) was authored so that **every vertex stores a
dermatome ID** in a compact binary `.u8` file (one byte per vertex). Painting is per-vertex, so a
lookup `derm_map[vertex_id]` instantly classifies each painted point. Topology of the painting model
and the `.u8` map share the same vertex order, so the mapping is exact.

**The metrics** (`codes/dermatome_coverage.py` — a pure-math, VTK-free, fully testable engine).
Each is plain arithmetic, so it is **transparent and auditable**:

| Metric | What it measures | Why a clinician cares |
|---|---|---|
| **Weighted pain burden** | this dermatome's share of the body's *total* pain "mass" (intensity-weighted) | **Primary ranking** — "of all this patient's pain, how much lives here?" Finds the dominant level. |
| **Pain area share** | this dermatome's share of all painted surface | Distinguishes large-area mild pain (e.g., fibromyalgia) from small-area intense pain (acute radiculopathy). |
| **Local involvement** | fraction of *this dermatome's own* surface that's painted | Is the whole nerve zone lit up or just a corner? Hints at full vs partial root involvement. |
| **Mean local intensity** | average pain level (1–3) where painted | Separates "burning, sharp 3/3" (radicular) from "dull 1/3" (myofascial). |
| **Segmental spread** | cranial-to-caudal span across involved levels | Narrow (1–2 levels) → single-level compression; wide (6+) → consider stenosis / central / multifocal. |
| **Overlap flag** | two *adjacent* levels with near-equal burden | Flags **radiculopathy ambiguity at a boundary** (e.g., L4 vs L5) — a real scenario paper maps miss. |

Dermatomes are **ranked** by burden, so the clinician immediately sees the dominant levels rather
than a flat list.

**The payoff:** "lower back, goes down the leg" becomes —
> *"L5–S1 distribution, 78% burden in L5, narrow 2-level spread, sharp 3/3 intensity → consistent
> with L5–S1 disc herniation."*

That sentence is what changes a clinic visit, and PAINDICATOR generates it from a patient's drawing.

---

## 6. Decision support (explainable, not a black box)

`codes/pain_analyzer.py` (~230 lines) turns the dermatome result **plus** the questionnaire into a
structured clinical report with four parts: **Clinical findings**, **Patterns to consider**
(differentials), **Red flags**, and **Recommended next steps**. It is **rule-based** — every line is
a readable, auditable clinical rule, which is a *feature* in medicine where black-box outputs are a
liability. A sample of the encoded knowledge:

- **Localizing patterns:** C5–C6 / C6–C7 / C7 / C8 cervical roots; thoracic outlet (C8+T1);
  L3–L4 / L4–L5 lumbar discs; femoral nerve (L2–L3–L4); **L5–S1 sciatica** (most common overall).
- **Red flags (urgent):** **S3–S4–S5 → possible cauda equina syndrome → urgent surgical referral**;
  **bladder/bowel symptoms → rule out cauda equina immediately**; **fever + spine pain → discitis /
  epidural abscess**; multi-level cervical/thoracic → **myelopathy**; severe unilateral thoracic band
  → **herpes zoster pre-rash**; left mid-thoracic severe → consider **cardiac** referral.
- **Symptom phenotyping (from the questionnaire):** burning + tingling → **neuropathic** (suggest DN4);
  worse with **cough/sneeze/strain → Valsalva-positive**, high specificity for disc (suggest MRI);
  worse standing/walking → **neurogenic claudication / stenosis**; sudden onset + high VAS → acute
  disc prolapse; ≥7 dermatomes → **central sensitization / fibromyalgia**.

**Safety / framing:** the report states up front and at the bottom that it is **clinical decision
support — descriptive only, not a diagnosis**, and not a substitute for clinical judgment, physical
examination, or imaging. This is exactly the right posture for a medical tool and signals maturity.

---

## 7. Engineering highlights

A real, robust application — **~5,600 lines of Python**, not a script.

| Layer | File | Responsibility |
|---|---|---|
| Entry point | `codes/app.py` | `QApplication`, `SessionManager`, `MainWindow` |
| Navigation | `codes/ui_main.py` | `QStackedWidget` + fade transitions |
| State (single source of truth) | `codes/session_manager.py` | all session data |
| 3D pipeline | `codes/renderer_scene.py` | owns every VTK object; toolbar-facing API |
| Interaction | `codes/vtk_interactor_custom.py` | paint / erase / camera (per-vertex Paint V2) |
| Analysis (pure math) | `codes/dermatome_coverage.py` | dermatome metrics, VTK-free |
| Mapping | `codes/dermatome_mapper.py` | loads the `.u8` dermatome map |
| Decision support | `codes/pain_analyzer.py` | rule-based pattern report |

Notable engineering:
- **Per-vertex painting with normal gating** — a radius brush paints only vertices facing the camera
  (dot(normal, view) test), so you **can't paint through the body** to the far side; screen-space
  interpolation fills gaps in fast strokes.
- **True per-stroke undo** — each stroke captures `{vertex_id: old_level}` for exact, granular undo.
- **Fragile-but-tamed VTK lifecycle** — lazy init on first show, clean teardown on hide (no
  `Finalize()`/`TerminateApp()`), so the native renderer never crashes the app.
- **Tablet-first** — stylus pressure painting, two-finger pinch/pan/twist, on-screen gesture guide,
  auto-popup virtual keyboard.
- **Bilingual EN/HE with full RTL** layout and live language switching.
- **Offline & deployable** — packaged with PyInstaller into a **standalone Windows EXE** (no Python
  needed on the clinic tablet); models and assets bundled.

**Scope at a glance:** 2 anatomical models (male/female), **31 dermatomes**, ~200k vertices/model,
12 UI screens, bilingual UI, full save/load + screenshot pipeline.

---

## 8. What makes it competition-worthy

- **Genuine novelty** — automatic, quantitative pain-to-dermatome mapping with a per-nerve burden
  ranking and an adjacent-level overlap flag. Existing EMR "body charts" are 2D click-regions; this
  is per-vertex 3D mapped to nerve roots with computed metrics.
- **Real clinical partner** — co-developed with Loewenstein (Clalit). Not a hypothetical.
- **Finished & deployable** — runs today on a tablet as an offline EXE; full patient + clinician
  flows, persistence, analytics, and a decision-support report all work.
- **Explainable by design** — rule-based reasoning a clinician can read and override; the right
  ethic for clinical software and easy to defend to a panel.
- **Privacy-by-design** — sessions stored locally; runs fully offline; no cloud dependency.
- **IP / product potential** — the dermatome mapping + metric set + analyzer is a protectable,
  extensible system with a clear market (pain clinics, neuro, ortho, spine, PM&R).
- **Engineering depth** — tightly-coupled UI+VTK system handled with a clean
  ownership architecture and a VTK-free, testable math core.

---

## 9. Roadmap (where it goes next)

- **Visual dermatome heatmap** — color the model by computed burden for an at-a-glance picture.
- **Quantitative longitudinal metrics** — turn the existing multi-session overlay into numeric
  change-over-time (burden deltas per level, treatment-response curves).
- **ML pattern recognition** — the rule-based analyzer is the labeled foundation; a trained model
  could learn patterns from accumulated sessions (with the rules as a safety net / explainer).
- **Regulatory path** — position as decision-support; explore CE / medical-device classification.

---

## 10. Judge Q&A prep (anticipate & answer crisply)

**Q: Is this validated / has it been clinically tested?**
A: It's a finished prototype built *with* Loewenstein around their real documentation workflow. The
analytics are transparent arithmetic and the decision rules are clearly labelled "not validated,
clinician-correlation only." Formal clinical validation is the explicit next step — and the
architecture (a pure, testable math core + saved structured sessions) is built to support a study.

**Q: How accurate is the dermatome map?**
A: The map is authored per-vertex on the anatomical model and shares topology with the painting
model, so the lookup is exact by construction. Dermatome boundaries are inherently approximate in
medicine (they vary between people and references) — which is exactly why we surface an **overlap
flag** for adjacent levels rather than pretending boundaries are crisp.

**Q: How is this different from drawing on a paper body chart or an EMR body diagram?**
A: Paper/2D charts capture a picture; we capture **per-vertex 3D data mapped to spinal nerve roots**,
then **compute** burden, coverage, intensity, spread and overlap, rank the levels, generate a
report, and make sessions **numerically comparable over time**. The drawing is the input; the
quantitative clinical signal is the output.

**Q: Isn't AI in medicine risky / a black box?**
A: That's why ours is **rule-based and explainable** — every suggestion traces to a readable rule a
clinician can audit and override, and the report is framed as decision support, **not a diagnosis**.

**Q: Privacy?**
A: Sessions are stored **locally** and the app runs **fully offline** — suitable for an isolated
clinic tablet; no cloud, no transmission.

**Q: Why not the web?**
A: Clinics need reliable offline operation on tablets and high-performance 3D interaction; a native
PyQt6 + VTK app gives smooth stylus/touch painting and ships as a single offline executable.

**Q: What was the hardest engineering part?**
A: Robust per-vertex painting on a live VTK pipeline on a touch tablet — normal gating to avoid
painting through the body, gap-free fast strokes, per-stroke undo, and a VTK lifecycle that never
crashes — while keeping a clean separation between rendering, interaction, and the analytics core.

---

## 11. Fact sheet (quick reference for slide-building)

- **Name / tagline:** PAINDICATOR — *Map Your Pain.* A clinical decision-support system for digital
  pain mapping and dermatome analysis.
- **Team:** Amit Bezalel & Shachar Guttman — BME, Tel Aviv University.
- **Supervisor:** Prof. Mickey Scheinowitz. **Partner:** Loewenstein Rehabilitation Medical Center
  (Clalit Health Services).
- **Stack:** Python 3.11 · PyQt6 6.10.0 · VTK 9.5.2 · NumPy 2.3.5 · Pillow 12.0.0 ·
  PyInstaller 6.17.0 (standalone Windows EXE).
- **Scope:** ~5,600 LOC · 12 screens · 2 models (male/female) · 31 dermatomes · bilingual EN/HE (RTL).
- **Per-session output:** `session.json` + bilingual `session_summary.txt` + `front.png` / `back.png`
  (stored locally).
- **Dermatome metrics:** weighted pain burden · pain area share · local involvement · mean local
  intensity · segmental spread · overlap flag.
- **Disclaimer (use verbatim on a slide):** *"PAINDICATOR is a research/decision-support tool. Its
  analysis is a descriptive summary of recorded data and is not a diagnosis or a substitute for
  clinical judgment, physical examination, or imaging."*
- **Assets:** `docs/logo.png`, `docs/screenshots/welcome.png`, `docs/screenshots/painting-front.png`,
  `docs/screenshots/painting-back.png`, `docs/screenshots/clinician-analysis.png`.
