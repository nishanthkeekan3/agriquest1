import datetime
from typing import List, Dict, Optional


def fetch_market_prices_stub(crop_names: List[str], region: Optional[str] = None) -> Dict:
    """Enhanced market data simulation with realistic trends and insights."""
    import random
    
    # Base prices in INR per quintal (more realistic for Indian market)
    base_prices = {
        'Wheat': 2200,
        'Maize': 1800,
        'Rice': 2500,
        'Millet': 1500,
        'Soybean': 4000,
        'Chickpea': 5000,
        'Lentil': 5200,
        'Mustard': 4500,
        'Cotton': 6000,
    }
    
    # Market volatility factors
    volatility = {
        'Wheat': 0.05,
        'Maize': 0.08,
        'Rice': 0.06,
        'Millet': 0.10,
        'Soybean': 0.12,
        'Chickpea': 0.15,
        'Lentil': 0.18,
        'Mustard': 0.14,
        'Cotton': 0.20,
    }
    
    data = {}
    today = datetime.date.today()
    
    for crop in crop_names:
        base_price = base_prices.get(crop, 2000)
        vol = volatility.get(crop, 0.10)
        
        # Generate realistic price series with seasonal trends
        series = []
        for i in range(31):
            date = today - datetime.timedelta(days=30 - i)
            
            # Seasonal adjustment (example: higher prices in harvest season)
            seasonal_factor = 1.0
            if date.month in [10, 11, 12]:  # Harvest season
                seasonal_factor = 1.1
            elif date.month in [6, 7, 8]:  # Monsoon season
                seasonal_factor = 0.95
            
            # Random walk with trend
            trend = 0.001 * i  # Slight upward trend
            random_factor = random.uniform(-vol, vol)
            price = base_price * seasonal_factor * (1 + trend + random_factor)
            
            series.append({
                'date': date.isoformat(),
                'price': round(price, 2)
            })
        
        # Calculate demand index based on price trend and volatility
        price_change = (series[-1]['price'] - series[0]['price']) / series[0]['price']
        demand_index = max(0.1, min(0.9, 0.5 + price_change * 2))
        
        # Market insights
        market_insights = {
            'trend': 'upward' if price_change > 0.02 else 'downward' if price_change < -0.02 else 'stable',
            'volatility': 'high' if vol > 0.15 else 'medium' if vol > 0.08 else 'low',
            'seasonality': 'harvest' if today.month in [10, 11, 12] else 'monsoon' if today.month in [6, 7, 8] else 'normal'
        }
        
        data[crop] = {
            'latest_price': series[-1]['price'],
            'trend_series': series,
            'demand_index': demand_index,
            'price_change_pct': round(price_change * 100, 2),
            'market_insights': market_insights,
            'support_level': round(series[-1]['price'] * 0.9, 2),
            'resistance_level': round(series[-1]['price'] * 1.1, 2)
        }
    
    return data


