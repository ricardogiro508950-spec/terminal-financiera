# ==========================================
# LAS 8 VERSIONES CON CAPITAL DE PAPEL
# ==========================================
VERSIONES = {
    # --- CONTROL (La original del PDF) ---
    "V1 - PDF Original (Control)": {"capital": 5000.0, "tiempo_eval": 24, "filtros": "ninguno"},
    
    # --- V2 - MEJORADAS (VELAS + VOLUMEN) ---
    "V2 - Ultra-Conservadora": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "estricto"},
    "V2 - Estándar (Actual)": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "medio"},
    "V2 - Agresiva (Rápida)": {"capital": 5000.0, "tiempo_eval": 6, "filtros": "laxo"},

    # --- V3 - SCALPERS (GESTIÓN AGRESIVA) ---
    "V3 - Scalper Agresivo (3R)": {"capital": 5000.0, "tiempo_eval": 4, "filtros": "ninguno"},
    "V3 - Ultra-Rápido (Trailing)": {"capital": 5000.0, "tiempo_eval": 2, "filtros": "ninguno"},
    
    # --- NUEVA: ESTRATEGIA DE PRUEBAS ---
    "V8 - Ultra-Sensible (Modo Pruebas)": {"capital": 5000.0, "tiempo_eval": 1, "filtros": "pruebas"}
}