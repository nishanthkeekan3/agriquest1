from typing import List, Dict, Optional


SUITABILITY_BY_SOIL = {
    'Loam': ['Wheat', 'Maize', 'Soybean', 'Chickpea', 'Vegetables'],
    'Clay': ['Rice', 'Mustard', 'Wheat'],
    'Sandy': ['Millet', 'Groundnut', 'Cotton'],
    'Silty': ['Rice', 'Wheat', 'Lentil'],
    'Peaty': ['Carrot', 'Onion', 'Cabbage'],
    'Chalky': ['Barley', 'Beet', 'Oats'],
}


def recommend_crops(soil_type: str, climate_summary: Optional[Dict], market: Optional[Dict]) -> List[Dict]:
    """
    Simple rule-based recommender combining soil suitability, climate, and market.
    Returns list of {crop_name, score, rationale, market_info}.
    """
    candidates = SUITABILITY_BY_SOIL.get(soil_type, [])
    results = []
    for crop in candidates:
        score = 0.5
        rationale_parts = [f"Suitable for {soil_type} soil"]
        if climate_summary:
            avg_temp = climate_summary.get('avg_temp_c')
            if avg_temp is not None:
                # crude temperature preference
                if crop in ['Wheat', 'Lentil', 'Chickpea'] and 10 <= avg_temp <= 25:
                    score += 0.2
                    rationale_parts.append('Average temperature favors cool-season crops')
                if crop in ['Maize', 'Rice', 'Cotton', 'Soybean'] and 20 <= avg_temp <= 35:
                    score += 0.2
                    rationale_parts.append('Average temperature favors warm-season crops')
            precip = climate_summary.get('avg_precip_mm')
            if precip is not None:
                if crop in ['Rice'] and precip >= 3:
                    score += 0.15
                    rationale_parts.append('Higher precipitation supports rice')
                if crop in ['Millet', 'Mustard', 'Chickpea'] and precip <= 2:
                    score += 0.1
                    rationale_parts.append('Lower precipitation suits drought-tolerant crops')
        market_info = (market or {}).get(crop)
        if market_info:
            demand = market_info.get('demand_index', 0.5)
            score += 0.2 * min(max(demand, 0), 1)
            rationale_parts.append('Market demand trend is favorable')
        results.append({
            'crop_name': crop,
            'score': round(min(score, 1.0), 2),
            'rationale': '; '.join(rationale_parts),
            'market_info': market_info or {},
        })
    # sort by score desc
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


