# PAINDICATOR — 10-Minute Competition Deck (Slide-by-Slide)

**Goal:** win "best project." **Length:** 10:00. **12 slides.** Balanced across academic, clinical,
technical, innovation, and product. A ~2-minute demo slot (Slide 4) is **optional** — swap in the
screenshots if you don't go live.

**Delivery tips**
- Two presenters: alternate roughly every 2 slides so both voices are heard (good for a team award).
- Memorize the **first 20 seconds** and the **last 20 seconds** verbatim. Improvise the middle.
- Lead with the *problem and a human story*, not the tech. Earn the right to show the engineering.
- Say the numbers out loud: "31 dermatomes," "~5,600 lines," "built with Loewenstein."
- Leave the disclaimer slide up during Q&A — it signals maturity.

**Running clock**

| # | Start | Slide | Job |
|---|-------|-------|-----|
| 1 | 0:00 | Title & team | Credibility |
| 2 | 0:40 | The problem | Hook |
| 3 | 1:30 | The insight | The idea |
| 4 | 2:20 | Demo / walkthrough | Product (optional live) |
| 5 | 4:20 | From paint to data | Innovation |
| 6 | 5:10 | Quantitative analytics | Clinical value |
| 7 | 6:10 | Decision support | Clinical + technical |
| 8 | 7:10 | Under the hood | Engineering |
| 9 | 8:00 | Impact & partner | Real-world |
| 10 | 8:45 | Roadmap | Vision |
| 11 | 9:20 | Why we win | Recap |
| 12 | 9:50 | Thank you / disclaimer | Close |

---

## Slide 1 — Title & team  · 0:00–0:40
**On screen:** PAINDICATOR logo, tagline *"Map Your Pain"*, team names, supervisor, TAU +
Loewenstein/Clalit affiliation.
**Talking points**
- "We're Amit and Shachar, Biomedical Engineering at Tel Aviv University."
- "PAINDICATOR is a clinical decision-support system for digital pain mapping — built with
  Loewenstein Rehabilitation Medical Center."
- One sentence: "It turns *'where does it hurt?'* into structured, measurable clinical data."
**Notes:** Warm, confident, 40 seconds max. Don't read the slide — say the one sentence and move on.

## Slide 2 — The problem  · 0:40–1:30
**On screen:** a paper body-chart pain drawing (or stock image) with a big "?" — subjective, 2D.
**Talking points**
- Pain is a top reason people see a doctor — and one of the worst-documented signals.
- Today it's a felt-tip drawing on paper or vague free text: **subjective, unstructured,
  not measurable, impossible to compare over time.**
- The clinician's real job is to **localize pain to a spinal nerve level** — done from a flat
  sketch and memory.
**Notes:** This is the emotional + clinical hook. Slow down. Make them feel the gap.

## Slide 3 — The insight  · 1:30–2:20
**On screen:** the 3D model with a few painted zones (use `welcome.png` or `painting-front.png`).
**Talking points**
- "What if the patient painted their pain onto a 3D body instead?"
- The key idea: **every point on our model is mapped to a dermatome** — the skin zone of one spinal
  nerve root.
- So painting isn't just a picture — it's **anatomical data**, automatically.
**Notes:** This is the "aha." Land the word **dermatome** clearly; you'll define it again on Slide 5.

## Slide 4 — Demo / walkthrough  · 2:20–4:20  *(optional live; screenshots fallback)*
**If LIVE (see demo script below):** paint 2–3 zones at different intensities, rotate to the back,
switch to clinician view, show the analytics panel. **~2 minutes, rehearsed, with a fallback.**
**If SCREENSHOTS:** step through `welcome.png` → `painting-front.png` → `painting-back.png` →
`clinician-analysis.png`.
**Talking points**
- "Patient picks a model, answers a short pain questionnaire, then paints — three intensity levels,
  by stylus or finger."
- "Rotate, paint the back, undo, erase — it's a tablet-first clinical tool."
- "The clinician opens the same session and sees the analysis."
**Notes:** Highest-impact slide. If live, **have the screenshots one keypress away** in case VTK or
the tablet misbehaves. Never debug on stage — cut to screenshots and keep talking.

## Slide 5 — From paint to data  · 4:20–5:10
**On screen:** the pipeline diagram (paint → coverage engine → ranked dermatomes → panel + JSON).
**Talking points**
- "A dermatome is the skin served by one spinal nerve root — C1 to S5, about 30 of them."
- "Every vertex carries a dermatome ID in a compact 1-byte-per-vertex map; painting is per-vertex,
  so each mark is classified instantly."
- "A pure-math engine — no graphics — turns that into ranked, per-nerve metrics."
**Notes:** Emphasize "pure math, testable, transparent." Sets up the credibility of Slide 6.

## Slide 6 — Quantitative analytics  · 5:10–6:10
**On screen:** `clinician-analysis.png` + the 6-metric table (burden, area share, local involvement,
mean intensity, segmental spread, overlap flag).
**Talking points**
- Walk one row: "**Weighted pain burden** = of all this patient's pain, how much is in this nerve
  level — that's how we rank the dominant levels."
- "**Overlap flag** catches two adjacent levels with near-equal burden — the radiculopathy ambiguity
  a paper chart completely misses."
- Punchline: *'lower back, down the leg'* → *"L5–S1 distribution, 78% burden in L5, sharp 3/3 → consistent with L5–S1 disc herniation."*
**Notes:** Say the punchline sentence slowly — it's the single most persuasive moment in the deck.

## Slide 7 — Decision support  · 6:10–7:10
**On screen:** a sample pain-pattern report (findings / patterns to consider / red flags / next steps).
**Talking points**
- "On top of the metrics, a rule-based analyzer correlates the pattern with the questionnaire."
- "It surfaces **red flags** — cauda equina, herpes zoster, bladder/bowel symptoms — and patterns
  like a positive Valsalva sign suggesting a disc."
- "It's **explainable** — every line is a readable rule a clinician can audit and override. And it
  says, clearly, **decision support, not a diagnosis.**"
**Notes:** Stress *explainable, not a black box* — judges love this in medical AI.

## Slide 8 — Under the hood  · 7:10–8:00
**On screen:** architecture table + small badges: VTK · per-vertex paint · normal gating · undo ·
tablet · bilingual · offline EXE.
**Talking points**
- "~5,600 lines of Python: PyQt6 for UI, VTK for 3D, a clean ownership split between rendering,
  interaction, and the analytics core."
- "Real engineering: a radius brush with **normal gating** so you can't paint through the body,
  gap-free fast strokes, true per-stroke undo, stylus + multi-touch."
- "Bilingual English/Hebrew with RTL, and it ships as a **standalone offline Windows app**."
**Notes:** This is the "we can really build" slide. Keep it brisk — breadth over depth.

## Slide 9 — Impact & partner  · 8:00–8:45
**On screen:** Loewenstein/Clalit + TAU logos; "who benefits" list; longitudinal overlay image.
**Talking points**
- "Built with Loewenstein Rehabilitation Medical Center around their real documentation problem."
- "Useful in pain clinics, neurology, orthopedics, spine, and rehab."
- "Sessions are saved and **comparable over time** — pain management is about change, and we finally
  measure it."
**Notes:** Tie the clinical partner to credibility. This separates you from a class project.

## Slide 10 — Roadmap  · 8:45–9:20
**On screen:** 4 bullets — visual heatmap · quantitative longitudinal metrics · ML pattern
recognition · regulatory path.
**Talking points**
- "Next: color the body by burden as a heatmap; turn multi-session comparison into numeric
  change-over-time."
- "The rule-based analyzer is also the **labeled foundation** for a future ML model — with the rules
  as the safety net."
**Notes:** Show vision without overpromising. 35 seconds.

## Slide 11 — Why we win  · 9:20–9:50
**On screen:** 5 crisp differentiators.
**Talking points (read as a list, fast & confident):**
- Genuine novelty: quantitative pain-to-nerve mapping with ranked burden + overlap flag.
- Real clinical partner (Loewenstein / Clalit).
- Finished & deployable today — offline tablet app.
- Explainable, privacy-by-design.
- Solid engineering: ~5,600 LOC, 2 models, 31 dermatomes.
**Notes:** Energy peak. This is your closing argument.

## Slide 12 — Thank you / disclaimer  · 9:50–10:00
**On screen:** logo, team + contact, and the disclaimer verbatim.
**Disclaimer:** *"PAINDICATOR is a research/decision-support tool. Its analysis is a descriptive
summary of recorded data and is not a diagnosis or a substitute for clinical judgment, physical
examination, or imaging."*
**Talking points:** "Thank you — we'd love your questions." Leave this slide up for Q&A.

---

## Live demo script (≈2 min) — for Slide 4

1. **Role / setup** — open on role selection (use Demo mode to skip ID entry if available).
2. **Choose a model** — pick male or female.
3. **Paint** — Mark mode; paint a **lower-back zone in red (severe)**, a **down-the-leg streak in
   orange**, and a **small mild yellow patch**. Narrate the three intensity levels.
4. **Interact** — rotate to the **back**, paint one posterior zone, then **Undo** once to show undo,
   and re-paint. (Shows it's robust.)
5. **Save** — hit Save; mention "JSON + summary + front/back screenshots, stored locally."
6. **Clinician view** — switch to clinician flow, open the session; show the **dermatome analytics
   panel**, toggle the **dermatome view**, and **click a region** to name it.
7. **Land it** — "From a drawing to ranked, per-nerve metrics in under a minute."

**Fallback rule:** if anything stalls for >5 seconds, say "let me show you the captured flow,"
press to the screenshots, and keep the narration going. Rehearse the demo **at least 5 times** on the
actual tablet you'll use.

## Pre-talk checklist
- [ ] Tablet charged; app launched once already (VTK warm); brightness up.
- [ ] Screenshots loaded as the fallback, one keypress from the demo.
- [ ] Decide live-demo vs screenshots **before** you walk in (Slide 4 works both ways).
- [ ] Logos for TAU + Loewenstein/Clalit on slides 1 and 9.
- [ ] Timer visible to the off-presenter; cut Slide 10 first if you're running long.
- [ ] One-line answers ready for the Q&A items in `judges_briefing.md` §10.
