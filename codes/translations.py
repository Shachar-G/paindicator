"""
Translation strings for PAINDICATOR.
Fill in the "he" values with Hebrew translations.
Leave "en" values unchanged.
"""

STRINGS = {
    # --- General ---
    "app_title": {
        "en": "PAINDICATOR",
        "he": "PAINDICATOR",
    },
    "continue_btn": {
        "en": "Continue",
        "he": "המשך",
    },

    # --- Role Selection Screen ---
    "role_welcome_title": {
        "en": "Welcome to PAINDICATOR",
        "he": "Welcome to PAINDICATOR",
    },
    "role_welcome_subtitle": {
        "en": "Please select your role to begin",
        "he": "בחר תפקיד כדי להתחיל",
    },
    "role_clinician": {
        "en": "Clinician",
        "he": "רופא",
    },
    "role_patient": {
        "en": "Patient",
        "he": "מטופל",
    },

    # --- Clinician Name Screen ---
    "clinician_name_title": {
        "en": "Enter Clinician Name",
        "he": "הכנס את שם הרופא",
    },
    "clinician_name_placeholder": {
        "en": "e.g., Dr. Levi Cohen",
        "he": "למשל, דר' לוי כהן",
    },

    # --- Patient ID Screen ---
    "patient_id_title": {
        "en": "Enter Patient ID",
        "he": "הכנס מספר מטופל",
    },
    "patient_id_placeholder": {
        "en": "e.g., PAT-12345",
        "he": "למשל, 12345",
    },

    # --- Gender Selection Screen ---
    "gender_title": {
        "en": "Select Patient Model",
        "he": "בחר מודל",
    },
    "gender_male": {
        "en": "Male",
        "he": "גבר",
    },
    "gender_female": {
        "en": "Female",
        "he": "אישה",
    },

    # --- Questionnaire Screen: Patient Info ---
    "q_section_patient_info": {
        "en": "Patient Information",
        "he": "פרטי המטופל",
    },
    "q_patient_age": {
        "en": "Age",
        "he": "גיל",
    },

    # --- Questionnaire Screen: Section Titles ---
    "q_section_pain_intensity": {
        "en": "Pain Intensity (VAS)",
        "he": "עוצמת הכאב (VAS)",
    },
    "q_section_pain_frequency": {
        "en": "Pain Frequency",
        "he": "תדירות הכאב",
    },
    "q_section_pain_characteristics": {
        "en": "Pain Characteristics",
        "he": "מאפייני הכאב",
    },
    "q_section_factors": {
        "en": "Factors",
        "he": "גורמים והשפעות",
    },
    "q_section_impact": {
        "en": "Impact on Daily Life",
        "he": "השפעה על תחומי החיים",
    },
    "q_section_exam_date": {
        "en": "Examination Date",
        "he": "מועד הבדיקה",
    },

    # --- Questionnaire Screen: Pain Intensity ---
    "q_pain_during_anamnesis": {
        "en": "Pain intensity during anamnesis",
        "he": "עוצמת הכאב בעת לקיחת האנמנזה",
    },
    "q_pain_average": {
        "en": "Average pain level recently",
        "he": "כאב ממוצע בתקופה האחרונה",
    },
    "q_pain_acute": {
        "en": "Pain intensity during acute episodes",
        "he": "עוצמת הכאב בעת התקף חריף",
    },

    # --- Questionnaire Screen: Pain Frequency ---
    "q_freq_specific_event": {
        "en": "Related to a specific event",
        "he": "קשור לאירוע",
    },
    "q_freq_sudden_onset": {
        "en": "Sudden onset",
        "he": "מתפרץ",
    },
    "q_freq_other": {
        "en": "Other",
        "he": "אחר",
    },
    "q_freq_constant": {
        "en": "Constant",
        "he": "קבוע",
    },
    "q_freq_intermittent": {
        "en": "Intermittent",
        "he": "לסירוגין",
    },
    "q_freq_comment": {
        "en": "Comment on frequency",
        "he": "הערה לגבי תדירות הכאב",
    },

    # --- Questionnaire Screen: Pain Characteristics ---
    "q_char_radiation": {
        "en": "Radiation",
        "he": "לאן הכאב מקרין?",
    },
    "q_char_when_began": {
        "en": "When did the pain begin?",
        "he": "מתי התחיל הכאב?",
    },
    "q_char_varies_day": {
        "en": "Does the pain vary during the day?",
        "he": "האם יש שינוי בעוצמת הכאב במהלך היממה?",
    },
    "q_char_pressing": {
        "en": "Pressing",
        "he": "לוחץ",
    },
    "q_char_burning": {
        "en": "Burning",
        "he": "שורף",
    },
    "q_char_stabbing": {
        "en": "Stabbing",
        "he": "דוקר",
    },
    "q_char_hot": {
        "en": "Hot",
        "he": "בוער",
    },
    "q_char_tingling": {
        "en": "Tingling",
        "he": "עקצוץ",
    },
    "q_char_sharp": {
        "en": "Sharp",
        "he": "חד",
    },
    "q_char_dull": {
        "en": "Dull",
        "he": "עמום",
    },
    "q_char_pulsating": {
        "en": "Pulsating",
        "he": "פועם",
    },
    "q_char_neuropathic": {
        "en": "Neuropathic",
        "he": "נוירופטי",
    },
    "q_char_other": {
        "en": "Other",
        "he": "אחר",
    },
    "q_char_comment": {
        "en": "Comment on pain character",
        "he": "הערה לגבי אופי הכאב",
    },

    # --- Questionnaire Screen: Factors ---
    "q_factor_alleviating": {
        "en": "Alleviating factors",
        "he": "גורמים מקלים",
    },
    "q_factor_aggravating": {
        "en": "Aggravating factors",
        "he": "גורמים מחמירים",
    },
    "q_factor_associated": {
        "en": "Associated symptoms",
        "he": "סימפטומים נלווים לכאב",
    },

    # --- Questionnaire Screen: Impact on Daily Life ---
    "q_impact_sleep": {
        "en": "Sleep",
        "he": "שינה",
    },
    "q_impact_appetite": {
        "en": "Appetite",
        "he": "תיאבון",
    },
    "q_impact_rest": {
        "en": "Rest",
        "he": "מנוחה",
    },
    "q_impact_physical": {
        "en": "Physical activity",
        "he": "פעילות",
    },
    "q_impact_walking": {
        "en": "Walking",
        "he": "הליכה",
    },
    "q_impact_educational": {
        "en": "Educational framework",
        "he": "מסגרת חינוכית",
    },
    "q_impact_mood": {
        "en": "Mood",
        "he": "מצב רוח",
    },
    "q_impact_concentration": {
        "en": "Concentration",
        "he": "ריכוז",
    },
    "q_impact_family": {
        "en": "Family relationships",
        "he": "יחסים במשפחה",
    },
    "q_impact_social": {
        "en": "Social life",
        "he": "חיי חברה",
    },
    "q_impact_comments": {
        "en": "Additional comments",
        "he": "הערות נוספות",
    },

    # --- VTK Toolbar ---
    "toolbar_view": {
        "en": "View",
        "he": "תצוגה",
    },
    "toolbar_mark": {
        "en": "Mark",
        "he": "סמן",
    },
    "toolbar_erase": {
        "en": "Erase",
        "he": " מחק ",
    },
    "toolbar_undo": {
        "en": "Undo",
        "he": "חזור",
    },
    "toolbar_reset_camera": {
        "en": "Reset View",
        "he": "אפס תצוגה ",
    },
    "toolbar_clear": {
        "en": "Clear",
        "he": "מחק הכל",
    },
    "toolbar_save": {
        "en": "Save",
        "he": "שמור",
    },
    "toolbar_notes": {
        "en": "Notes",
        "he": "הערות",
    },
    "toolbar_brush": {
        "en": "Brush",
        "he": "מברשת",
    },
    "toolbar_mild": {
        "en": "Mild",
        "he": "קל",
    },
    "toolbar_moderate": {
        "en": "Moderate",
        "he": "בינוני",
    },
    "toolbar_severe": {
        "en": "Severe",
        "he": "חמור",
    },

    # --- Comment Popup ---
    "comment_title": {
        "en": "Comments",
        "he": "הערות",
    },
    "comment_label": {
        "en": "Enter comment:",
        "he": "הכנס הערה",
    },
    "comment_placeholder": {
        "en": "Enter comment here...",
        "he": "הכנס הערה כאן...",
    },
    "comment_save_btn": {
        "en": "Save",
        "he": "שמור",
    },
    "comment_close_btn": {
        "en": "Close",
        "he": "סגור",
    },

    # --- Questionnaire: pain character section label ---
    "q_char_character_section": {
        "en": "Pain character:",
        "he": "מהו אופי הכאב?",
    },

    # --- Shared words ---
    "sessions_word": {
        "en": "sessions",
        "he": "מפגשים",
    },

    # --- Clinician Patients Screen ---
    "clinician_patients_title": {
        "en": "Patients List",
        "he": "רשימת מטופלים",
    },
    "clinician_patients_subtitle": {
        "en": "Search by Patient ID and select a folder",
        "he": "חפש לפי מספר מטופל ובחר תיקייה",
    },
    "clinician_search_placeholder": {
        "en": "Search Patient ID…",
        "he": "חפש מספר מטופל...",
    },
    "clinician_no_patients": {
        "en": "(No matching patients found)",
        "he": "(לא נמצאו מטופלים תואמים)",
    },
    "clinician_back_btn": {
        "en": "Back",
        "he": "חזרה",
    },

    # --- Clinician Session Selection Screen ---
    "clinician_session_edit": {
        "en": "Edit",
        "he": "ערוך",
    },
    "clinician_session_title": {
        "en": "Select Session",
        "he": "בחירת מפגש",
    },
    "clinician_back_to_patients": {
        "en": "Back to Patients",
        "he": "חזרה לרשימת המטופלים",
    },
    "clinician_session_label": {
        "en": "Session #",
        "he": "מפגש ",
    },
    "clinician_clinician_label": {
        "en": "Clinician",
        "he": "רופא",
    },

    # --- Clinician View Session Screen ---
    "clinician_view_back": {
        "en": " Back",
        "he": " חזרה",
    },
    "clinician_view_dermatome_map": {
        "en": "Dermatome Map",
        "he": "מפת דרמטומים",
    },
    "clinician_view_compare": {
        "en": " Compare",
        "he": " השווה",
    },
    "clinician_view_compare_session": {
        "en": " Compare Session",
        "he": " השווה מפגש ",
    },
    "clinician_view_remove_compare": {
        "en": " Remove Compare",
        "he": " הסר השוואה",
    },
    "clinician_view_reset_view": {
        "en": " Reset View",
        "he": " אפס תצוגה ",
    },
    "clinician_view_analyze": {
        "en": " Analyze",
        "he": " נתח",
    },
    "clinician_view_dermatome_analysis": {
        "en": "Dermatome Analysis",
        "he": "ניתוח דרמטומלי",
    },
    "clinician_view_questionnaire": {
        "en": "Questionnaire",
        "he": "שאלון",
    },
    "clinician_view_comments": {
        "en": "Comments",
        "he": "הערות",
    },
    "clinician_view_no_questionnaire": {
        "en": "(No questionnaire data)",
        "he": "(אין נתוני שאלון)",
    },
    "clinician_view_no_comments": {
        "en": "(No comments)",
        "he": "(אין הערות)",
    },
    "clinician_view_derm_male_only": {
        "en": "Dermatome analysis available for male patients only.",
        "he": "ניתוח דרמטומלי זמין למטופלים גברים בלבד.",
    },
    "clinician_view_derm_load_fail": {
        "en": "Dermatome mapper could not be loaded.",
        "he": "לא ניתן לטעון את מפת הדרמטומים.",
    },
    "clinician_view_no_pain_areas": {
        "en": "No pain areas marked.",
        "he": "לא סומנו אזורי כאב.",
    },
    "clinician_view_derm_fail": {
        "en": "Dermatome analysis failed.",
        "he": "ניתוח דרמטומלי נכשל.",
    },
    "clinician_view_patient_label": {
        "en": "Patient",
        "he": "מטופל",
    },
    "clinician_compare_dialog_title": {
        "en": "Select Session to Compare",
        "he": "בחר מפגש להשוואה",
    },
    "clinician_compare_dialog_info": {
        "en": "Select a previous session to overlay on the current model:",
        "he": "בחר מפגש קודם להצגה על המודל הנוכחי:",
    },
    "clinician_analyze_dialog_title": {
        "en": "Pain Pattern Analysis",
        "he": "ניתוח תבנית כאב",
    },
    "clinician_analyze_save_btn": {
        "en": "Save Report",
        "he": "שמור דוח",
    },
    "clinician_analyze_saved": {
        "en": "Saved ✓",
        "he": "נשמר ✓",
    },
    "clinician_analyze_save_failed": {
        "en": "Save failed",
        "he": "שמירה נכשלה",
    },
    "clinician_analyze_no_folder": {
        "en": "No session folder",
        "he": "אין תיקיית מפגש",
    },
    "clinician_analyze_close_btn": {
        "en": "Close",
        "he": "סגור",
    },

    # --- Session Summary File Labels ---
    "summary_patient_id": {
        "en": "Patient ID",
        "he": "מזהה מטופל",
    },
    "summary_gender": {
        "en": "Gender",
        "he": "מגדר",
    },
    "summary_clinician_name": {
        "en": "Clinician Name",
        "he": "שם הרופא",
    },
    "summary_questionnaire": {
        "en": "Questionnaire",
        "he": "שאלון",
    },
    "summary_no_questionnaire": {
        "en": "(No questionnaire data)",
        "he": "(אין נתוני שאלון)",
    },
    "summary_comments": {
        "en": "Comments",
        "he": "הערות",
    },
    "summary_no_comments": {
        "en": "(No comments)",
        "he": "(אין הערות)",
    },
    "summary_painted_points": {
        "en": "Painted Points",
        "he": "נקודות מסומנות",
    },
    "summary_painted_triangles": {
        "en": "Painted Triangles",
        "he": "משולשים מסומנים",
    },
    "summary_dermatome_analysis": {
        "en": "Dermatome Analysis",
        "he": "ניתוח דרמטומלי",
    },
    "summary_analysis_report": {
        "en": "Analysis Report",
        "he": "דוח ניתוח",
    },
    "summary_analysis_english_only": {
        "en": "(Analysis available in English only)",
        "he": "(ניתוח זמין באנגלית בלבד)",
    },
}


# ---------------------------------------------------------------------------
# Language Manager — plain Python, no QObject needed
# ---------------------------------------------------------------------------

class LanguageManager:
    """Singleton that tracks the active language and notifies listeners."""

    def __init__(self):
        self._lang = "en"
        self._callbacks = []

    def connect(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def disconnect(self, callback):
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    def get_language(self) -> str:
        return self._lang

    def set_language(self, lang: str):
        if lang != self._lang:
            self._lang = lang
            for cb in list(self._callbacks):
                try:
                    cb(lang)
                except Exception as e:
                    print(f"[LanguageManager] callback error: {e}")

    def toggle(self):
        self.set_language("he" if self._lang == "en" else "en")


lang_manager = LanguageManager()


def t(key: str) -> str:
    """Translate a string key to the current language, falling back to English."""
    entry = STRINGS.get(key, {})
    lang = lang_manager.get_language()
    value = entry.get(lang, "")
    return value if value else entry.get("en", key)
