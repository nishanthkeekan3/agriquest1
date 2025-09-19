import datetime
import requests


def fetch_nasa_power_daily(lat: float, lon: float, start: datetime.date, end: datetime.date) -> dict:
    """
    Fetch daily climate variables from NASA POWER API for a point and date range.
    Returns JSON data or raises for HTTP errors.
    """
    params = {
        'latitude': lat,
        'longitude': lon,
        'start': start.strftime('%Y%m%d'),
        'end': end.strftime('%Y%m%d'),
        'community': 'AG',
        'parameters': 'T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RELHUM,ALLSKY_SFC_SW_DWN',
        'format': 'JSON'
    }
    url = 'https://power.larc.nasa.gov/api/temporal/daily/point'
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def summarize_climate_for_agriculture(power_json: dict) -> dict:
    """
    Produce simple aggregates useful for recommendations.
    """
    if not power_json or 'properties' not in power_json:
        return {}
    params = power_json['properties']['parameter']
    def avg(series):
        vals = list(series.values())
        return sum(vals) / len(vals) if vals else None
    return {
        'avg_temp_c': avg(params.get('T2M', {})),
        'avg_min_temp_c': avg(params.get('T2M_MIN', {})),
        'avg_max_temp_c': avg(params.get('T2M_MAX', {})),
        'avg_precip_mm': avg(params.get('PRECTOTCORR', {})),
        'avg_rel_humidity': avg(params.get('RELHUM', {})),
        'avg_solar_mj_m2': avg(params.get('ALLSKY_SFC_SW_DWN', {})),
    }







