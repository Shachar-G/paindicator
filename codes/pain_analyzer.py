# codes/pain_analyzer.py
# NOTE: All comments are in English only.
# AI-based clinical decision support — pain pattern analyzer.
# Returns a formatted text report based on dermatome distribution and questionnaire data.


def analyze_pain(patient_data):
    dermatomes = patient_data.get("dermatomes", [])
    severity_map = patient_data.get("severity_map", {})
    vas_peak = patient_data.get("pain peak", 0)
    vas_average = patient_data.get("pain average", 0)
    vas_anamnesis = patient_data.get("pain anamnesis", 0)
    pain_character = patient_data.get("pain character", [])
    aggravating = patient_data.get("aggravating factors", "").lower()
    alleviating = patient_data.get("alleviating factors", "").lower()
    associated = patient_data.get("associated symptoms", "").lower()
    frequency = patient_data.get("frequency", [])
    radiation = patient_data.get("radiation", "").lower()
    life_impact = patient_data.get("life impact", [])

    findings = []
    differentials = []
    red_flags = []
    recommendations = []

    # -- CERVICAL --
    if "C5" in dermatomes and "C6" in dermatomes:
        differentials.append("C5-C6 disc herniation")
        findings.append("Outer shoulder and thumb/index finger involvement suggests C5-C6 root compression")
    elif "C6" in dermatomes and "C7" in dermatomes:
        differentials.append("C6-C7 disc herniation (most common cervical level)")
        findings.append("Middle finger and index finger distribution consistent with C6-C7 involvement")
    elif "C7" in dermatomes:
        differentials.append("C7 radiculopathy")
        findings.append("Middle finger and tricep region — C7 most common cervical disc level")
    elif "C8" in dermatomes:
        differentials.append("C8 radiculopathy")
        findings.append("Little finger and inner forearm distribution — C8 involvement")
    if "C8" in dermatomes and "T1" in dermatomes:
        differentials.append("Thoracic outlet syndrome")
        findings.append("C8+T1 combination suggests thoracic outlet involvement")
    cervical_count = len([d for d in dermatomes if d.startswith("C")])
    if cervical_count >= 3:
        differentials.append("Cervical spondylosis")
    if cervical_count >= 4:
        red_flags.append("Multiple bilateral cervical levels — consider cervical myelopathy")

    # -- THORACIC --
    thoracic = [d for d in dermatomes if d.startswith("T")]
    if len(thoracic) == 1:
        differentials.append("Intercostal neuralgia")
        findings.append(f"Single thoracic band ({thoracic[0]}) — classic intercostal neuralgia pattern")
    if any(d in dermatomes for d in ["T2", "T3", "T4", "T5", "T6"]):
        findings.append("Mid-thoracic band involvement — verify unilateral vs bilateral")
    if "T10" in dermatomes:
        findings.append("T10 level — umbilicus zone, consider abdominal referred pain")
    if any(d in dermatomes for d in ["T11", "T12"]):
        findings.append("Lower thoracic — possible lower abdominal or groin referral")
    if vas_peak >= 7 and len(thoracic) == 1:
        differentials.append("Herpes zoster (pre-rash phase)")
        red_flags.append("Severe unilateral thoracic band — consider zoster even without visible rash")
    if any(d in dermatomes for d in ["T2", "T3", "T4", "T5", "T6"]) and vas_peak >= 7:
        red_flags.append("Left-sided mid-thoracic severe pain — consider cardiac referral")
    if len(thoracic) >= 3:
        differentials.append("Thoracic disc disease")
        if len(thoracic) >= 5:
            red_flags.append("Multiple thoracic levels bilateral — consider thoracic myelopathy")

    # -- LUMBAR --
    if "L4" in dermatomes and "L5" in dermatomes:
        differentials.append("L4-L5 disc herniation")
        findings.append("L4-L5 pattern — most common lumbar disc level")
    elif "L3" in dermatomes and "L4" in dermatomes:
        differentials.append("L3-L4 disc herniation")
        findings.append("Anterior thigh and inner shin distribution — L3-L4 level")
    if all(d in dermatomes for d in ["L2", "L3", "L4"]):
        differentials.append("Femoral nerve involvement")
        findings.append("L2-L3-L4 combination suggests femoral nerve distribution")
    lumbar_count = len([d for d in dermatomes if d.startswith("L")])
    if lumbar_count >= 3 and all(d in dermatomes for d in ["L1", "L2", "L3"]):
        differentials.append("Lumbar spinal stenosis")
    if lumbar_count >= 4:
        red_flags.append("Multiple bilateral lumbar levels — consider lumbar stenosis or central pathology")

    # -- SACRAL --
    if "L5" in dermatomes and "S1" in dermatomes:
        differentials.append("L5-S1 disc herniation (most common overall)")
        findings.append("L5-S1 classic sciatica — outer shin to little toe and heel")
    if all(d in dermatomes for d in ["S3", "S4", "S5"]):
        red_flags.append("S3-S4-S5 involvement — URGENT: possible cauda equina syndrome")
        recommendations.append("Urgent surgical referral — do not delay")
    elif all(d in dermatomes for d in ["S3", "S4"]):
        red_flags.append("S3-S4 perineal involvement — assess bladder/bowel function")
    if "S1" in dermatomes and "S2" in dermatomes and "L5" not in dermatomes:
        differentials.append("S1-S2 radiculopathy")
        findings.append("Posterior thigh and outer foot without L5 — S1-S2 distribution")
    sacral_bilateral = len([d for d in dermatomes if d.startswith("S")]) >= 3
    if sacral_bilateral:
        red_flags.append("Bilateral sacral involvement — rule out cauda equina")

    # -- CROSS-REGION --
    has_cervical = any(d.startswith("C") for d in dermatomes)
    has_thoracic = any(d.startswith("T") for d in dermatomes)
    has_lumbar = any(d.startswith("L") for d in dermatomes)
    has_sacral = any(d.startswith("S") for d in dermatomes)

    if has_lumbar and has_sacral:
        findings.append("Combined lumbar-sacral pattern — consistent with sciatica")
    if has_cervical and has_thoracic:
        findings.append("Cervical with thoracic spread — consider referred pain component")
    if has_cervical and has_lumbar:
        red_flags.append("Non-contiguous cervical and lumbar — consider central pathology or multifocal disease")
    if len(dermatomes) >= 7:
        differentials.append("Central sensitization or fibromyalgia")
        findings.append("Widespread multi-level distribution — consider central pain mechanism")

    # -- PAIN CHARACTER --
    if "Burning" in pain_character and "Tingling" in pain_character:
        findings.append("Burning + tingling strongly suggests neuropathic pain component")
        recommendations.append("Consider neuropathic pain assessment (DN4 score)")
    if "Neuropathic" in pain_character:
        findings.append("Patient self-reports neuropathic quality")
        recommendations.append("Consider neuropathic pain scale (NRS/DN4)")
    if "Shooting" in pain_character or "Sharp" in pain_character:
        findings.append("Shooting/sharp quality consistent with radiculopathy")
    if "Burning" in pain_character and len(thoracic) == 1:
        differentials.append("Neuropathic pain / zoster")
    if "Pulsating" in pain_character:
        findings.append("Pulsating character — consider vascular component")
    if "Pressing" in pain_character and vas_average >= 5:
        findings.append("Pressing quality with moderate-high average VAS — consider myofascial component")

    # -- VAS MODIFIERS --
    if vas_peak >= 8:
        findings.append(f"High peak VAS ({vas_peak}/10) — suggests acute nerve compression or episodic radiculopathy")
    if vas_average >= 6:
        recommendations.append("Chronic high average pain (VAS {}/10) — consider neuropathic pain management protocol".format(vas_average))
    if vas_peak - vas_average >= 4:
        findings.append(f"Large VAS gap (average {vas_average}, peak {vas_peak}) — suggests positional or episodic compression")
    if vas_anamnesis >= 7:
        findings.append(f"High pain at examination (VAS {vas_anamnesis}/10) — patient in significant acute distress")

    # -- FREQUENCY --
    if "Constant" in frequency:
        findings.append("Constant pain — more consistent with structural nerve compression")
    if "Intermittent" in frequency:
        findings.append("Intermittent pattern — consider dynamic stenosis or inflammatory cause")
    if "Related to a specific event" in frequency:
        findings.append("Event-related onset — consider traumatic or post-event radiculopathy")
    if "Sudden onset" in frequency:
        findings.append("Sudden onset reported — consider acute disc herniation")
        if vas_peak >= 7:
            red_flags.append("Sudden onset + high VAS — rule out acute disc prolapse")

    # -- AGGRAVATING / ALLEVIATING --
    if "sitting" in aggravating:
        findings.append("Worse with sitting — supports lumbar disc herniation")
    if "standing" in aggravating or "walking" in aggravating:
        differentials.append("Neurogenic claudication / spinal stenosis")
        findings.append("Worse standing/walking — consider neurogenic claudication")
    if "cough" in aggravating or "sneez" in aggravating or "strain" in aggravating:
        findings.append("Valsalva maneuver aggravates — high specificity for disc herniation")
        recommendations.append("Valsalva sign positive — consider MRI spine")
    if "lying" in alleviating or "rest" in alleviating:
        findings.append("Relief with lying/rest — supports mechanical cause")
    if "walk" in alleviating:
        findings.append("Relief with walking — consider vascular claudication vs neurogenic")

    # -- RADIATION --
    if radiation:
        findings.append(f"Reported radiation: '{patient_data.get('radiation', '')}' — correlate with dermatomal pattern")
        if "leg" in radiation or "arm" in radiation or "foot" in radiation or "hand" in radiation:
            findings.append("Limb radiation pattern consistent with radiculopathy")

    # -- ASSOCIATED SYMPTOMS --
    if "bladder" in associated or "bowel" in associated or "incontinence" in associated:
        red_flags.append("Bladder/bowel symptoms — URGENT: rule out cauda equina syndrome immediately")
        recommendations.append("Urgent MRI and emergency surgical consultation")
    if "weakness" in associated or "weak" in associated:
        findings.append("Motor weakness reported — neurological examination essential")
        recommendations.append("Urgent neurological examination for motor deficit")
    if "numb" in associated:
        findings.append("Numbness reported — sensory examination required")
    if "fever" in associated:
        red_flags.append("Fever with spine pain — rule out discitis or epidural abscess")

    # -- LIFE IMPACT --
    if "Sleep" in life_impact and "Mood" in life_impact:
        findings.append("Sleep and mood affected — consider pain psychology referral")
    if len(life_impact) >= 5:
        findings.append(f"Significant life impact across {len(life_impact)} domains — consider multidisciplinary pain management")
    if "Walking" in life_impact or "Physical activity" in life_impact:
        findings.append("Mobility affected — functional assessment recommended")

    # -- BUILD REPORT --
    if not dermatomes:
        return "No dermatomes marked on the model.\nPlease have the patient mark their pain areas first."

    # Rank intensity labels robustly. The caller may use either the descriptive
    # scale ("Low/Moderate/High intensity") or a classic one ("Mild/Moderate/Severe");
    # unknown labels fall back to 0 so this never raises.
    def _severity_rank(label):
        order = {
            "low intensity": 1, "mild": 1,
            "moderate intensity": 2, "moderate": 2,
            "high intensity": 3, "severe": 3,
        }
        return order.get(str(label).strip().lower(), 0)

    primary = max(
        severity_map,
        key=lambda d: _severity_rank(severity_map.get(d))
    ) if severity_map else dermatomes[0]

    report = []
    report.append("PAIN PATTERN ANALYSIS")
    report.append("─" * 44)
    report.append("Clinical decision support — demonstration only.")
    report.append("Descriptive summary of recorded data; not a diagnosis.")
    report.append("─" * 44)

    report.append(f"\nDermatomes affected:  {', '.join(dermatomes)}")
    report.append(f"Primary zone:         {primary} ({severity_map.get(primary, 'N/A')})")
    report.append(f"VAS — exam: {vas_anamnesis}/10  |  average: {vas_average}/10  |  peak: {vas_peak}/10")

    if findings:
        report.append("\nCLINICAL FINDINGS:")
        for f in findings:
            report.append(f"  • {f}")

    if differentials:
        report.append("\nPATTERNS TO CONSIDER (clinical correlation required):")
        for i, d in enumerate(differentials, 1):
            report.append(f"  {i}. {d}")

    if red_flags:
        report.append("\n!! RED FLAGS:")
        for r in red_flags:
            report.append(f"  !! {r}")

    if recommendations:
        report.append("\nRECOMMENDED NEXT STEPS:")
        for r in recommendations:
            report.append(f"  -> {r}")
    else:
        report.append("\nRECOMMENDED NEXT STEPS:")
        report.append("  -> Clinical correlation and physical examination")
        report.append("  -> Consider imaging if symptoms persist > 6 weeks")

    report.append("\n" + "─" * 44)
    report.append("!! CLINICAL DECISION SUPPORT — NOT A DIAGNOSIS")
    report.append("The patterns above are not clinically validated and are")
    report.append("provided for clinician correlation only.")
    report.append("Not a substitute for clinical judgment.")

    return "\n".join(report)