from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, FarmProfile, Recommendation
from services.climate import fetch_nasa_power_daily, summarize_climate_for_agriculture
from services.market import fetch_market_prices_stub
from services.recommender import recommend_crops
import datetime
import random
import logging

farm_bp = Blueprint('farm', __name__, url_prefix='/farm')


@farm_bp.route('/profile/new', methods=['GET', 'POST'])
@login_required
def create_profile():
    if request.method == 'POST':
        location_name = request.form.get('location_name', '').strip()
        soil_type = request.form.get('soil_type', '').strip()
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')

        try:
            latitude = float(lat) if lat is not None else None
            longitude = float(lon) if lon is not None else None
        except ValueError:
            latitude = None
            longitude = None

        if not soil_type or latitude is None or longitude is None:
            flash('Please select a point on the map and a soil type.', 'warning')
            return redirect(url_for('farm.create_profile'))

        profile = FarmProfile(
            user_id=current_user.id,
            location_name=location_name or None,
            latitude=latitude,
            longitude=longitude,
            soil_type=soil_type,
        )
        db.session.add(profile)
        db.session.commit()
        flash('Farm profile created.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('farm/profile_form.html')


@farm_bp.route('/profiles')
@login_required
def list_profiles():
    profiles = FarmProfile.query.filter_by(user_id=current_user.id).order_by(FarmProfile.created_at.desc()).all()
    return render_template('farm/profile_list.html', profiles=profiles)


@farm_bp.route('/profile/<int:profile_id>/recommend', methods=['POST'])
@login_required
def generate_recommendations(profile_id: int):
    profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=180)
    
    # Clear existing recommendations
    Recommendation.query.filter_by(farm_id=profile.id).delete()
    
    try:
        climate_json = fetch_nasa_power_daily(profile.latitude, profile.longitude, start, end)
        climate_summary = summarize_climate_for_agriculture(climate_json)
        flash('Climate data loaded successfully', 'info')
    except Exception as e:
        flash(f'Climate data unavailable: {str(e)}', 'warning')
        climate_summary = None

    try:
        market = fetch_market_prices_stub(['Wheat','Maize','Rice','Millet','Soybean','Chickpea','Lentil','Mustard','Cotton'])
        flash('Market data loaded successfully', 'info')
    except Exception as e:
        flash(f'Market data unavailable: {str(e)}', 'warning')
        market = {}

    recs = recommend_crops(profile.soil_type, climate_summary, market)

    # Enhanced ecological impacts
    ecological_impacts = {
        'Wheat': 'Improves soil structure, nitrogen fixation, good for crop rotation',
        'Maize': 'High biomass production, good for soil organic matter, carbon sequestration',
        'Rice': 'Water management benefits, supports wetland ecosystem, high yield potential',
        'Millet': 'Drought resistant, low water requirement, excellent for arid regions',
        'Soybean': 'Nitrogen fixation, improves soil fertility, high protein content',
        'Chickpea': 'Nitrogen fixation, drought tolerant, improves soil health',
        'Lentil': 'Nitrogen fixation, soil improvement, short growing season',
        'Mustard': 'Oil crop, good for crop rotation, pest management benefits',
        'Cotton': 'Fiber crop, requires careful pest management, high value crop'
    }

    # Store top 5 recommendations with enhanced data
    for r in recs[:5]:
        market_info = r.get('market_info', {})
        latest_price = market_info.get('latest_price', 0)
        demand_index = market_info.get('demand_index', 0.5)
        
        # Calculate profitability estimate
        base_yield = 2.5  # tons per hectare (average)
        cost_per_hectare = latest_price * 0.4  # 40% of market price as cost
        revenue_per_hectare = latest_price * base_yield
        profit_estimate = revenue_per_hectare - cost_per_hectare
        
        rec = Recommendation(
            farm_id=profile.id,
            crop_name=r['crop_name'],
            market_demand_score=demand_index,
            profitability_estimate=profit_estimate,
            cost_estimate=cost_per_hectare,
            ecological_impact=ecological_impacts.get(r['crop_name'], 'Improves soil health and biodiversity'),
            rationale=r['rationale'],
            data={
                'climate': climate_summary,
                'market': market_info,
                'soil_type': profile.soil_type,
                'coordinates': {'lat': profile.latitude, 'lng': profile.longitude},
                'ai_score': r['score']
            },
        )
        db.session.add(rec)
    
    db.session.commit()
    flash(f'Generated {len(recs[:5])} AI-powered recommendations with market insights!', 'success')
    return redirect(url_for('farm.view_profile', profile_id=profile.id))


@farm_bp.route('/profile/<int:profile_id>')
@login_required
def view_profile(profile_id: int):
    profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    recs = Recommendation.query.filter_by(farm_id=profile.id).order_by(Recommendation.created_at.desc()).all()
    # Serialize recommendations for JSON usage in template scripts
    recs_json = [
        {
            'id': r.id,
            'crop_name': r.crop_name,
            'market_demand_score': r.market_demand_score,
            'profitability_estimate': r.profitability_estimate,
            'cost_estimate': r.cost_estimate,
            'ecological_impact': r.ecological_impact,
            'rationale': r.rationale,
            'data': r.data or {}
        }
        for r in recs
    ]
    return render_template('farm/profile_detail.html', profile=profile, recs=recs, recs_json=recs_json)


@farm_bp.route('/profile/<int:profile_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(profile_id: int):
    try:
        profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            location_name = request.form.get('location_name', '').strip()
            soil_type = request.form.get('soil_type', '').strip()
            lat = request.form.get('latitude')
            lon = request.form.get('longitude')

            try:
                latitude = float(lat) if lat is not None else None
                longitude = float(lon) if lon is not None else None
            except (ValueError, TypeError):
                latitude = None
                longitude = None

            if not soil_type or latitude is None or longitude is None:
                flash('Please select a point on the map and a soil type.', 'warning')
                return redirect(url_for('farm.edit_profile', profile_id=profile.id))

            profile.location_name = location_name or None
            profile.latitude = latitude
            profile.longitude = longitude
            profile.soil_type = soil_type
            
            db.session.commit()
            flash('Farm profile updated successfully!', 'success')
            return redirect(url_for('farm.view_profile', profile_id=profile.id))

        return render_template('farm/profile_edit.html', profile=profile)
    
    except Exception as e:
        flash(f'Error updating farm profile: {str(e)}', 'danger')
        return redirect(url_for('farm.list_profiles'))


@farm_bp.route('/profile/<int:profile_id>/delete', methods=['POST'])
@login_required
def delete_profile(profile_id: int):
    profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    db.session.delete(profile)
    db.session.commit()
    flash('Farm profile deleted.', 'success')
    return redirect(url_for('farm.list_profiles'))


@farm_bp.route('/ai-insights')
@login_required
def ai_insights():
    """AI Insights page with comprehensive crop recommendations"""
    try:
        logging.info(f"AI Insights requested by user {current_user.id}")
        
        # Get user's farm profiles
        profiles = FarmProfile.query.filter_by(user_id=current_user.id).all()
        logging.info(f"Found {len(profiles)} profiles for user {current_user.id}")
        
        if not profiles:
            flash('Please create a farm profile first to get AI insights.', 'info')
            return redirect(url_for('farm.create_profile'))
        
        # Get the most recent profile for analysis
        latest_profile = profiles[0]
        logging.info(f"Using profile {latest_profile.id} for AI analysis")
        
        # Generate AI insights using multiple AI tools consensus
        ai_insights = generate_ai_consensus_insights(latest_profile)
        logging.info(f"Generated AI insights successfully")
        
        return render_template('farm/ai_insights.html', 
                             profile=latest_profile, 
                             insights=ai_insights,
                             all_profiles=profiles)
    
    except Exception as e:
        logging.error(f"Error in AI insights: {str(e)}", exc_info=True)
        flash(f'Error generating AI insights: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@farm_bp.route('/market-data')
@login_required
def market_data():
    """Market Data page with interactive charts and analysis"""
    try:
        logging.info(f"Market data requested by user {current_user.id}")
        
        # Get market data for visualization
        market_data = fetch_market_prices_stub(['Wheat','Maize','Rice','Millet','Soybean','Chickpea','Lentil','Mustard','Cotton'])
        logging.info(f"Fetched market data for {len(market_data)} crops")
        
        # Get user's farm profiles for context
        profiles = FarmProfile.query.filter_by(user_id=current_user.id).all()
        logging.info(f"Found {len(profiles)} profiles for user {current_user.id}")
        
        return render_template('farm/market_data.html', 
                             market_data=market_data,
                             profiles=profiles)
    
    except Exception as e:
        logging.error(f"Error in market data: {str(e)}", exc_info=True)
        flash(f'Error loading market data: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@farm_bp.route('/api/ai-insights/<int:profile_id>')
@login_required
def get_ai_insights_api(profile_id):
    """API endpoint for AI insights"""
    try:
        profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
        insights = generate_ai_consensus_insights(profile)
        return jsonify(insights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@farm_bp.route('/api/market-data')
@login_required
def get_market_data_api():
    """API endpoint for market data"""
    try:
        market_data = fetch_market_prices_stub(['Wheat','Maize','Rice','Millet','Soybean','Chickpea','Lentil','Mustard','Cotton'])
        return jsonify(market_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@farm_bp.route('/profile/<int:profile_id>/market-analysis')
@login_required
def farm_market_analysis(profile_id: int):
    """Detailed market analysis for a specific farm"""
    try:
        logging.info(f"Farm market analysis requested for profile {profile_id} by user {current_user.id}")
        
        # Get the specific farm profile
        profile = FarmProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
        logging.info(f"Found profile {profile.id} for analysis")
        
        # Get comprehensive market data
        market_data = fetch_market_prices_stub(['Wheat','Maize','Rice','Millet','Soybean','Chickpea','Lentil','Mustard','Cotton'])
        
        # Get climate data for the farm location
        end = datetime.date.today()
        start = end - datetime.timedelta(days=180)
        
        try:
            climate_json = fetch_nasa_power_daily(profile.latitude, profile.longitude, start, end)
            climate_summary = summarize_climate_for_agriculture(climate_json)
            logging.info(f"Climate data loaded for profile {profile.id}")
        except Exception as e:
            logging.warning(f"Climate data unavailable for profile {profile.id}: {str(e)}")
            climate_summary = None
        
        # Generate farm-specific recommendations
        recommendations = recommend_crops(profile.soil_type, climate_summary, market_data)
        
        # Calculate farm-specific market insights
        farm_insights = calculate_farm_market_insights(profile, market_data, climate_summary)
        
        logging.info(f"Generated farm market analysis for profile {profile.id}")
        
        return render_template('farm/farm_market_analysis.html', 
                             profile=profile,
                             market_data=market_data,
                             climate_summary=climate_summary,
                             recommendations=recommendations,
                             farm_insights=farm_insights)
    
    except Exception as e:
        logging.error(f"Error in farm market analysis: {str(e)}", exc_info=True)
        flash(f'Error loading farm market analysis: {str(e)}', 'danger')
        return redirect(url_for('farm.list_profiles'))


def generate_ai_consensus_insights(profile):
    """Generate comprehensive AI insights with climate and price consensus"""
    try:
        # Get climate data
        end = datetime.date.today()
        start = end - datetime.timedelta(days=180)
        
        try:
            climate_json = fetch_nasa_power_daily(profile.latitude, profile.longitude, start, end)
            climate_summary = summarize_climate_for_agriculture(climate_json)
        except:
            climate_summary = None
        
        # Get market data
        try:
            market = fetch_market_prices_stub(['Wheat','Maize','Rice','Millet','Soybean','Chickpea','Lentil','Mustard','Cotton'])
        except:
            market = {}
        
        # AI Tool 1: Soil-based recommendations
        soil_recommendations = get_soil_based_recommendations(profile.soil_type)
        
        # AI Tool 2: Climate-based recommendations
        climate_recommendations = get_climate_based_recommendations(climate_summary)
        
        # AI Tool 3: Market-based recommendations
        market_recommendations = get_market_based_recommendations(market)
        
        # AI Tool 4: Weather condition analysis
        weather_analysis = get_weather_condition_analysis(climate_summary)
        
        # Enhanced consensus algorithm with detailed recommendations
        consensus_crops = calculate_enhanced_consensus_recommendations(
            soil_recommendations, climate_recommendations, market_recommendations, climate_summary, market
        )
        
        # Generate comprehensive crop recommendations with climate and price consensus
        comprehensive_recommendations = generate_comprehensive_crop_recommendations(
            profile, climate_summary, market, consensus_crops
        )
        
        return {
            'consensus_crops': consensus_crops,
            'comprehensive_recommendations': comprehensive_recommendations,
            'weather_analysis': weather_analysis,
            'soil_analysis': soil_recommendations,
            'climate_analysis': climate_recommendations,
            'market_analysis': market_recommendations,
            'farm_profile': {
                'location': f"{profile.latitude:.4f}, {profile.longitude:.4f}",
                'soil_type': profile.soil_type,
                'farm_name': profile.location_name or 'Unnamed Farm'
            }
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'consensus_crops': [],
            'comprehensive_recommendations': [],
            'weather_analysis': {},
            'soil_analysis': {},
            'climate_analysis': {},
            'market_analysis': {}
        }


def get_soil_based_recommendations(soil_type):
    """AI Tool 1: Soil-based crop recommendations"""
    soil_crop_mapping = {
        'Loam': {
            'excellent': ['Wheat', 'Maize', 'Soybean', 'Rice'],
            'good': ['Chickpea', 'Lentil', 'Mustard'],
            'moderate': ['Millet', 'Cotton']
        },
        'Clay': {
            'excellent': ['Rice', 'Wheat'],
            'good': ['Maize', 'Soybean'],
            'moderate': ['Chickpea', 'Lentil']
        },
        'Sandy': {
            'excellent': ['Millet', 'Cotton'],
            'good': ['Chickpea', 'Lentil'],
            'moderate': ['Wheat', 'Maize']
        },
        'Silty': {
            'excellent': ['Wheat', 'Rice', 'Maize'],
            'good': ['Soybean', 'Mustard'],
            'moderate': ['Chickpea', 'Lentil']
        },
        'Peaty': {
            'excellent': ['Rice', 'Mustard'],
            'good': ['Wheat', 'Maize'],
            'moderate': ['Soybean', 'Chickpea']
        },
        'Chalky': {
            'excellent': ['Wheat', 'Mustard'],
            'good': ['Maize', 'Chickpea'],
            'moderate': ['Soybean', 'Lentil']
        }
    }
    
    recommendations = soil_crop_mapping.get(soil_type, soil_crop_mapping['Loam'])
    return {
        'soil_type': soil_type,
        'recommendations': recommendations,
        'confidence': 0.85,
        'reasoning': f"Based on {soil_type} soil characteristics and nutrient availability"
    }


def get_climate_based_recommendations(climate_summary):
    """AI Tool 2: Climate-based recommendations"""
    if not climate_summary:
        return {
            'climate_data': 'unavailable',
            'recommendations': ['Wheat', 'Maize', 'Rice'],
            'confidence': 0.5,
            'reasoning': 'Using default recommendations due to unavailable climate data'
        }
    
    avg_temp = climate_summary.get('avg_temp', 25)
    avg_rainfall = climate_summary.get('avg_rainfall', 1000)
    
    recommendations = []
    reasoning_parts = []
    
    # Temperature-based recommendations
    if avg_temp > 30:
        recommendations.extend(['Cotton', 'Millet', 'Soybean'])
        reasoning_parts.append("high temperature tolerance")
    elif avg_temp < 15:
        recommendations.extend(['Wheat', 'Mustard', 'Chickpea'])
        reasoning_parts.append("cold temperature tolerance")
    else:
        recommendations.extend(['Rice', 'Maize', 'Lentil'])
        reasoning_parts.append("moderate temperature suitability")
    
    # Rainfall-based recommendations
    if avg_rainfall > 1500:
        recommendations.extend(['Rice', 'Soybean'])
        reasoning_parts.append("high rainfall requirement")
    elif avg_rainfall < 500:
        recommendations.extend(['Millet', 'Chickpea', 'Lentil'])
        reasoning_parts.append("drought tolerance")
    
    return {
        'climate_data': climate_summary,
        'recommendations': list(set(recommendations)),
        'confidence': 0.8,
        'reasoning': f"Based on temperature ({avg_temp}°C) and rainfall ({avg_rainfall}mm) - " + ", ".join(reasoning_parts)
    }


def get_market_based_recommendations(market):
    """AI Tool 3: Market-based recommendations"""
    if not market:
        return {
            'market_data': 'unavailable',
            'recommendations': ['Wheat', 'Rice', 'Maize'],
            'confidence': 0.5,
            'reasoning': 'Using default recommendations due to unavailable market data'
        }
    
    # Sort crops by profitability
    crop_profits = []
    for crop, data in market.items():
        price = data.get('latest_price', 0)
        demand = data.get('demand_index', 0.5)
        profit_score = price * demand
        crop_profits.append((crop, profit_score, price, demand))
    
    # Sort by profit score
    crop_profits.sort(key=lambda x: x[1], reverse=True)
    
    recommendations = [crop for crop, _, _, _ in crop_profits[:5]]
    
    return {
        'market_data': market,
        'recommendations': recommendations,
        'confidence': 0.75,
        'reasoning': f"Based on current market prices and demand trends - top profitable crops identified"
    }


def get_weather_condition_analysis(climate_summary):
    """AI Tool 4: Weather condition analysis"""
    if not climate_summary:
        return {
            'current_conditions': 'Data unavailable',
            'forecast': 'Unable to generate forecast',
            'recommendations': 'Use soil-based recommendations',
            'risk_level': 'medium'
        }
    
    avg_temp = climate_summary.get('avg_temp', 25)
    avg_rainfall = climate_summary.get('avg_rainfall', 1000)
    
    # Determine current conditions
    if avg_temp > 30:
        conditions = "Hot and dry"
        risk_level = "high"
        recommendations = "Focus on drought-resistant crops, ensure irrigation"
    elif avg_temp < 15:
        conditions = "Cool and wet"
        risk_level = "medium"
        recommendations = "Good for cool-season crops, watch for frost"
    else:
        conditions = "Moderate temperature"
        risk_level = "low"
        recommendations = "Ideal conditions for most crops"
    
    # Generate forecast
    forecast = f"Expected temperature around {avg_temp}°C with {avg_rainfall}mm rainfall"
    
    return {
        'current_conditions': conditions,
        'forecast': forecast,
        'recommendations': recommendations,
        'risk_level': risk_level,
        'temperature': avg_temp,
        'rainfall': avg_rainfall
    }


def calculate_consensus_recommendations(soil_recs, climate_recs, market_recs):
    """Calculate consensus from multiple AI tools"""
    all_crops = set()
    
    # Collect all recommended crops
    all_crops.update(soil_recs.get('recommendations', {}).get('excellent', []))
    all_crops.update(climate_recs.get('recommendations', []))
    all_crops.update(market_recs.get('recommendations', []))
    
    # Score each crop based on consensus
    crop_scores = {}
    for crop in all_crops:
        score = 0
        confidence = 0
        
        # Soil score
        soil_excellent = soil_recs.get('recommendations', {}).get('excellent', [])
        soil_good = soil_recs.get('recommendations', {}).get('good', [])
        if crop in soil_excellent:
            score += 3
            confidence += soil_recs.get('confidence', 0.5)
        elif crop in soil_good:
            score += 2
            confidence += soil_recs.get('confidence', 0.5) * 0.7
        
        # Climate score
        if crop in climate_recs.get('recommendations', []):
            score += 2
            confidence += climate_recs.get('confidence', 0.5)
        
        # Market score
        if crop in market_recs.get('recommendations', []):
            score += 2
            confidence += market_recs.get('confidence', 0.5)
        
        crop_scores[crop] = {
            'score': score,
            'confidence': confidence / 3 if confidence > 0 else 0.5,
            'soil_suitability': crop in soil_excellent or crop in soil_good,
            'climate_suitability': crop in climate_recs.get('recommendations', []),
            'market_suitability': crop in market_recs.get('recommendations', [])
        }
    
    # Sort by score and confidence
    sorted_crops = sorted(crop_scores.items(), 
                         key=lambda x: (x[1]['score'], x[1]['confidence']), 
                         reverse=True)
    
    return sorted_crops[:5]  # Top 5 recommendations


def calculate_farm_market_insights(profile, market_data, climate_summary):
    """Calculate farm-specific market insights"""
    try:
        insights = {
            'farm_location': f"{profile.latitude:.4f}, {profile.longitude:.4f}",
            'soil_type': profile.soil_type,
            'farm_name': profile.location_name or 'Unnamed Farm',
            'climate_zone': determine_climate_zone(climate_summary),
            'optimal_crops': [],
            'market_opportunities': [],
            'risk_factors': [],
            'profitability_analysis': {},
            'seasonal_recommendations': {}
        }
        
        # Analyze optimal crops for this farm
        soil_suitable_crops = get_soil_suitable_crops(profile.soil_type)
        climate_suitable_crops = get_climate_suitable_crops(climate_summary)
        
        # Find intersection of soil and climate suitable crops
        optimal_crops = list(set(soil_suitable_crops) & set(climate_suitable_crops))
        insights['optimal_crops'] = optimal_crops
        
        # Analyze market opportunities
        for crop in optimal_crops:
            if crop in market_data:
                crop_data = market_data[crop]
                opportunity_score = crop_data['demand_index'] * crop_data['latest_price'] / 1000
                insights['market_opportunities'].append({
                    'crop': crop,
                    'price': crop_data['latest_price'],
                    'demand': crop_data['demand_index'],
                    'trend': crop_data['price_change_pct'],
                    'opportunity_score': opportunity_score
                })
        
        # Sort by opportunity score
        insights['market_opportunities'].sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        # Calculate profitability analysis
        for crop in optimal_crops[:5]:  # Top 5 crops
            if crop in market_data:
                crop_data = market_data[crop]
                # Estimate costs and profits
                estimated_yield = 2.5  # tons per hectare
                estimated_cost = crop_data['latest_price'] * 0.4  # 40% of price as cost
                estimated_revenue = crop_data['latest_price'] * estimated_yield
                estimated_profit = estimated_revenue - estimated_cost
                
                insights['profitability_analysis'][crop] = {
                    'estimated_yield': estimated_yield,
                    'estimated_cost': estimated_cost,
                    'estimated_revenue': estimated_revenue,
                    'estimated_profit': estimated_profit,
                    'profit_margin': (estimated_profit / estimated_revenue) * 100 if estimated_revenue > 0 else 0
                }
        
        # Identify risk factors
        if climate_summary:
            avg_temp = climate_summary.get('avg_temp', 25)
            avg_rainfall = climate_summary.get('avg_rainfall', 1000)
            
            if avg_temp > 35:
                insights['risk_factors'].append('High temperature risk - consider heat-tolerant crops')
            if avg_temp < 10:
                insights['risk_factors'].append('Low temperature risk - consider cold-tolerant crops')
            if avg_rainfall < 500:
                insights['risk_factors'].append('Low rainfall risk - ensure irrigation capacity')
            if avg_rainfall > 2000:
                insights['risk_factors'].append('High rainfall risk - ensure drainage systems')
        
        # Seasonal recommendations
        current_month = datetime.date.today().month
        insights['seasonal_recommendations'] = get_seasonal_recommendations(current_month, optimal_crops)
        
        return insights
        
    except Exception as e:
        logging.error(f"Error calculating farm market insights: {str(e)}")
        return {
            'error': str(e),
            'farm_location': f"{profile.latitude:.4f}, {profile.longitude:.4f}",
            'soil_type': profile.soil_type,
            'farm_name': profile.location_name or 'Unnamed Farm'
        }


def determine_climate_zone(climate_summary):
    """Determine climate zone based on temperature and rainfall"""
    if not climate_summary:
        return "Unknown"
    
    avg_temp = climate_summary.get('avg_temp', 25)
    avg_rainfall = climate_summary.get('avg_rainfall', 1000)
    
    if avg_temp > 30 and avg_rainfall < 500:
        return "Hot and Dry"
    elif avg_temp > 25 and avg_rainfall > 1500:
        return "Hot and Humid"
    elif avg_temp < 15 and avg_rainfall < 500:
        return "Cold and Dry"
    elif avg_temp < 20 and avg_rainfall > 1000:
        return "Cool and Wet"
    else:
        return "Temperate"


def get_soil_suitable_crops(soil_type):
    """Get crops suitable for specific soil type"""
    soil_crop_mapping = {
        'Loam': ['Wheat', 'Maize', 'Soybean', 'Rice', 'Chickpea', 'Lentil', 'Mustard'],
        'Clay': ['Rice', 'Wheat', 'Maize', 'Soybean'],
        'Sandy': ['Millet', 'Cotton', 'Chickpea', 'Lentil'],
        'Silty': ['Wheat', 'Rice', 'Maize', 'Soybean', 'Mustard'],
        'Peaty': ['Rice', 'Mustard', 'Wheat', 'Maize'],
        'Chalky': ['Wheat', 'Mustard', 'Maize', 'Chickpea']
    }
    return soil_crop_mapping.get(soil_type, ['Wheat', 'Maize', 'Rice'])


def get_climate_suitable_crops(climate_summary):
    """Get crops suitable for specific climate"""
    if not climate_summary:
        return ['Wheat', 'Maize', 'Rice']
    
    avg_temp = climate_summary.get('avg_temp', 25)
    avg_rainfall = climate_summary.get('avg_rainfall', 1000)
    
    suitable_crops = []
    
    if avg_temp > 30:
        suitable_crops.extend(['Cotton', 'Millet', 'Soybean'])
    elif avg_temp < 15:
        suitable_crops.extend(['Wheat', 'Mustard', 'Chickpea'])
    else:
        suitable_crops.extend(['Rice', 'Maize', 'Lentil'])
    
    if avg_rainfall > 1500:
        suitable_crops.extend(['Rice', 'Soybean'])
    elif avg_rainfall < 500:
        suitable_crops.extend(['Millet', 'Chickpea', 'Lentil'])
    
    return list(set(suitable_crops))


def get_seasonal_recommendations(month, crops):
    """Get seasonal planting recommendations"""
    seasonal_mapping = {
        1: {'season': 'Winter', 'recommended': ['Wheat', 'Mustard', 'Chickpea']},
        2: {'season': 'Winter', 'recommended': ['Wheat', 'Mustard', 'Chickpea']},
        3: {'season': 'Spring', 'recommended': ['Maize', 'Rice', 'Soybean']},
        4: {'season': 'Spring', 'recommended': ['Maize', 'Rice', 'Soybean']},
        5: {'season': 'Spring', 'recommended': ['Maize', 'Rice', 'Soybean']},
        6: {'season': 'Monsoon', 'recommended': ['Rice', 'Maize', 'Millet']},
        7: {'season': 'Monsoon', 'recommended': ['Rice', 'Maize', 'Millet']},
        8: {'season': 'Monsoon', 'recommended': ['Rice', 'Maize', 'Millet']},
        9: {'season': 'Autumn', 'recommended': ['Wheat', 'Mustard', 'Lentil']},
        10: {'season': 'Autumn', 'recommended': ['Wheat', 'Mustard', 'Lentil']},
        11: {'season': 'Autumn', 'recommended': ['Wheat', 'Mustard', 'Lentil']},
        12: {'season': 'Winter', 'recommended': ['Wheat', 'Mustard', 'Chickpea']}
    }
    
    season_info = seasonal_mapping.get(month, {'season': 'Unknown', 'recommended': []})
    
    # Filter recommended crops to only include those suitable for this farm
    farm_suitable_seasonal = [crop for crop in season_info['recommended'] if crop in crops]
    
    return {
        'current_season': season_info['season'],
        'recommended_crops': farm_suitable_seasonal,
        'all_seasonal_crops': season_info['recommended']
    }


def calculate_enhanced_consensus_recommendations(soil_recs, climate_recs, market_recs, climate_summary, market):
    """Enhanced consensus algorithm with detailed scoring"""
    all_crops = set()
    
    # Collect all recommended crops
    all_crops.update(soil_recs.get('recommendations', {}).get('excellent', []))
    all_crops.update(climate_recs.get('recommendations', []))
    all_crops.update(market_recs.get('recommendations', []))
    
    # Score each crop based on enhanced consensus
    crop_scores = {}
    for crop in all_crops:
        score = 0
        confidence = 0
        details = {
            'soil_score': 0,
            'climate_score': 0,
            'market_score': 0,
            'price_trend': 'stable',
            'profitability': 'medium',
            'climate_suitability': 'moderate',
            'seasonal_timing': 'optimal'
        }
        
        # Soil score (40% weight)
        soil_excellent = soil_recs.get('recommendations', {}).get('excellent', [])
        soil_good = soil_recs.get('recommendations', {}).get('good', [])
        if crop in soil_excellent:
            score += 4
            confidence += soil_recs.get('confidence', 0.5)
            details['soil_score'] = 4
        elif crop in soil_good:
            score += 3
            confidence += soil_recs.get('confidence', 0.5) * 0.7
            details['soil_score'] = 3
        
        # Climate score (30% weight)
        if crop in climate_recs.get('recommendations', []):
            score += 3
            confidence += climate_recs.get('confidence', 0.5)
            details['climate_score'] = 3
            details['climate_suitability'] = 'excellent'
        
        # Market score (30% weight)
        if crop in market_recs.get('recommendations', []):
            score += 3
            confidence += market_recs.get('confidence', 0.5)
            details['market_score'] = 3
        
        # Enhanced market analysis
        if crop in market:
            crop_data = market[crop]
            price_change = crop_data.get('price_change_pct', 0)
            if price_change > 5:
                details['price_trend'] = 'rising'
                score += 1
            elif price_change < -5:
                details['price_trend'] = 'falling'
                score -= 1
            
            # Profitability analysis
            price = crop_data.get('latest_price', 0)
            demand = crop_data.get('demand_index', 0.5)
            if price > 3000 and demand > 0.7:
                details['profitability'] = 'high'
                score += 1
            elif price < 2000 or demand < 0.4:
                details['profitability'] = 'low'
                score -= 1
        
        # Seasonal timing bonus
        current_month = datetime.date.today().month
        seasonal_crops = get_seasonal_crops_for_month(current_month)
        if crop in seasonal_crops:
            details['seasonal_timing'] = 'optimal'
            score += 1
        
        crop_scores[crop] = {
            'score': score,
            'confidence': confidence / 3 if confidence > 0 else 0.5,
            'details': details,
            'soil_suitability': crop in soil_excellent or crop in soil_good,
            'climate_suitability': crop in climate_recs.get('recommendations', []),
            'market_suitability': crop in market_recs.get('recommendations', [])
        }
    
    # Sort by score and confidence
    sorted_crops = sorted(crop_scores.items(), 
                         key=lambda x: (x[1]['score'], x[1]['confidence']), 
                         reverse=True)
    
    return sorted_crops[:8]  # Top 8 recommendations


def generate_comprehensive_crop_recommendations(profile, climate_summary, market, consensus_crops):
    """Generate comprehensive crop recommendations with detailed analysis"""
    recommendations = []
    
    for crop_data in consensus_crops:
        crop_name = crop_data[0]
        crop_info = crop_data[1]
        
        # Get market data for this crop
        market_data = market.get(crop_name, {})
        
        # Generate detailed recommendation
        recommendation = {
            'crop_name': crop_name,
            'overall_score': crop_info['score'],
            'confidence': crop_info['confidence'],
            'details': crop_info['details'],
            
            # Climate-based recommendations
            'climate_recommendations': generate_climate_recommendations(crop_name, climate_summary),
            
            # Price-based recommendations
            'price_recommendations': generate_price_recommendations(crop_name, market_data),
            
            # Seasonal recommendations
            'seasonal_recommendations': generate_seasonal_recommendations(crop_name),
            
            # Profitability analysis
            'profitability_analysis': generate_profitability_analysis(crop_name, market_data),
            
            # Risk assessment
            'risk_assessment': generate_risk_assessment(crop_name, climate_summary, market_data),
            
            # Implementation timeline
            'implementation_timeline': generate_implementation_timeline(crop_name),
            
            # Success factors
            'success_factors': generate_success_factors(crop_name, profile.soil_type)
        }
        
        recommendations.append(recommendation)
    
    return recommendations


def generate_climate_recommendations(crop_name, climate_summary):
    """Generate climate-specific recommendations for a crop"""
    if not climate_summary:
        return ["Climate data unavailable - use general recommendations"]
    
    avg_temp = climate_summary.get('avg_temp', 25)
    avg_rainfall = climate_summary.get('avg_rainfall', 1000)
    
    recommendations = []
    
    # Temperature-based recommendations
    if crop_name in ['Cotton', 'Millet', 'Soybean']:
        if avg_temp > 30:
            recommendations.append("✓ Excellent for hot climate - optimal temperature range")
        elif avg_temp < 20:
            recommendations.append("⚠️ Consider heat management - may need greenhouse or shade")
    
    elif crop_name in ['Wheat', 'Mustard', 'Chickpea']:
        if avg_temp < 20:
            recommendations.append("✓ Perfect for cool climate - ideal growing conditions")
        elif avg_temp > 30:
            recommendations.append("⚠️ High temperature risk - plant early or use heat-resistant varieties")
    
    # Rainfall-based recommendations
    if crop_name in ['Rice', 'Soybean']:
        if avg_rainfall > 1200:
            recommendations.append("✓ High rainfall suitable - ensure proper drainage")
        elif avg_rainfall < 600:
            recommendations.append("⚠️ Low rainfall - ensure irrigation capacity")
    
    elif crop_name in ['Millet', 'Chickpea', 'Lentil']:
        if avg_rainfall < 800:
            recommendations.append("✓ Drought-tolerant crops - perfect for low rainfall")
        elif avg_rainfall > 1500:
            recommendations.append("⚠️ High rainfall risk - ensure drainage systems")
    
    return recommendations if recommendations else ["Climate conditions are suitable for this crop"]


def generate_price_recommendations(crop_name, market_data):
    """Generate price-based recommendations for a crop"""
    if not market_data:
        return ["Market data unavailable - monitor prices regularly"]
    
    price_change = market_data.get('price_change_pct', 0)
    current_price = market_data.get('latest_price', 0)
    demand_index = market_data.get('demand_index', 0.5)
    
    recommendations = []
    
    # Price trend analysis
    if price_change > 10:
        recommendations.append("📈 Strong upward price trend - excellent timing for planting")
    elif price_change > 5:
        recommendations.append("📈 Rising prices - good market opportunity")
    elif price_change < -10:
        recommendations.append("📉 Declining prices - consider waiting or diversifying")
    elif price_change < -5:
        recommendations.append("📉 Price decline - monitor market closely")
    else:
        recommendations.append("📊 Stable prices - reliable market conditions")
    
    # Demand analysis
    if demand_index > 0.8:
        recommendations.append("🔥 High market demand - prioritize this crop")
    elif demand_index > 0.6:
        recommendations.append("👍 Good market demand - solid choice")
    elif demand_index < 0.4:
        recommendations.append("⚠️ Low market demand - consider alternatives")
    
    # Price level analysis
    if current_price > 4000:
        recommendations.append("💰 High-value crop - focus on quality production")
    elif current_price > 2500:
        recommendations.append("💵 Moderate value - balance yield and quality")
    else:
        recommendations.append("💸 Lower value - focus on high yield and low costs")
    
    return recommendations


def generate_seasonal_recommendations(crop_name):
    """Generate seasonal planting recommendations"""
    current_month = datetime.date.today().month
    
    seasonal_mapping = {
        'Wheat': {
            'optimal_months': [10, 11, 12, 1, 2],
            'season': 'Winter',
            'planting_window': 'October-February',
            'harvest_window': 'March-May'
        },
        'Rice': {
            'optimal_months': [6, 7, 8, 9],
            'season': 'Monsoon',
            'planting_window': 'June-September',
            'harvest_window': 'October-December'
        },
        'Maize': {
            'optimal_months': [3, 4, 5, 6],
            'season': 'Spring-Summer',
            'planting_window': 'March-June',
            'harvest_window': 'July-September'
        },
        'Soybean': {
            'optimal_months': [6, 7, 8],
            'season': 'Monsoon',
            'planting_window': 'June-August',
            'harvest_window': 'September-November'
        },
        'Cotton': {
            'optimal_months': [4, 5, 6],
            'season': 'Summer',
            'planting_window': 'April-June',
            'harvest_window': 'October-December'
        },
        'Millet': {
            'optimal_months': [6, 7, 8],
            'season': 'Monsoon',
            'planting_window': 'June-August',
            'harvest_window': 'September-November'
        },
        'Chickpea': {
            'optimal_months': [10, 11, 12],
            'season': 'Winter',
            'planting_window': 'October-December',
            'harvest_window': 'March-May'
        },
        'Lentil': {
            'optimal_months': [10, 11, 12],
            'season': 'Winter',
            'planting_window': 'October-December',
            'harvest_window': 'March-April'
        },
        'Mustard': {
            'optimal_months': [10, 11, 12],
            'season': 'Winter',
            'planting_window': 'October-December',
            'harvest_window': 'February-April'
        }
    }
    
    crop_info = seasonal_mapping.get(crop_name, {
        'optimal_months': [3, 4, 5, 6, 7, 8],
        'season': 'General',
        'planting_window': 'March-August',
        'harvest_window': 'September-December'
    })
    
    recommendations = []
    
    if current_month in crop_info['optimal_months']:
        recommendations.append(f"🌱 Perfect timing! Current month ({current_month}) is optimal for {crop_name}")
    else:
        next_optimal = min([m for m in crop_info['optimal_months'] if m > current_month], 
                          default=crop_info['optimal_months'][0])
        recommendations.append(f"📅 Next optimal planting: Month {next_optimal}")
    
    recommendations.append(f"📆 Planting window: {crop_info['planting_window']}")
    recommendations.append(f"🌾 Harvest window: {crop_info['harvest_window']}")
    recommendations.append(f"🌤️ Best season: {crop_info['season']}")
    
    return recommendations


def generate_profitability_analysis(crop_name, market_data):
    """Generate profitability analysis for a crop"""
    if not market_data:
        return {
            'estimated_profit': 'N/A',
            'profit_margin': 'N/A',
            'recommendations': ['Market data unavailable']
        }
    
    current_price = market_data.get('latest_price', 0)
    demand_index = market_data.get('demand_index', 0.5)
    
    # Estimate costs and profits
    estimated_yield = 2.5  # tons per hectare (average)
    estimated_cost_per_hectare = current_price * 0.4  # 40% of price as cost
    estimated_revenue_per_hectare = current_price * estimated_yield
    estimated_profit_per_hectare = estimated_revenue_per_hectare - estimated_cost_per_hectare
    profit_margin = (estimated_profit_per_hectare / estimated_revenue_per_hectare) * 100 if estimated_revenue_per_hectare > 0 else 0
    
    recommendations = []
    
    if profit_margin > 50:
        recommendations.append("💰 Excellent profitability - high priority crop")
    elif profit_margin > 30:
        recommendations.append("💵 Good profitability - solid investment")
    elif profit_margin > 15:
        recommendations.append("💸 Moderate profitability - consider cost optimization")
    else:
        recommendations.append("⚠️ Low profitability - evaluate alternatives")
    
    if demand_index > 0.7:
        recommendations.append("📈 High demand supports premium pricing")
    
    return {
        'estimated_profit': estimated_profit_per_hectare,
        'profit_margin': profit_margin,
        'estimated_yield': estimated_yield,
        'estimated_cost': estimated_cost_per_hectare,
        'estimated_revenue': estimated_revenue_per_hectare,
        'recommendations': recommendations
    }


def generate_risk_assessment(crop_name, climate_summary, market_data):
    """Generate risk assessment for a crop"""
    risks = []
    mitigations = []
    
    # Climate risks
    if climate_summary:
        avg_temp = climate_summary.get('avg_temp', 25)
        avg_rainfall = climate_summary.get('avg_rainfall', 1000)
        
        if crop_name in ['Rice', 'Soybean'] and avg_rainfall < 600:
            risks.append("Drought risk - insufficient rainfall")
            mitigations.append("Ensure irrigation backup systems")
        
        if crop_name in ['Wheat', 'Mustard'] and avg_temp > 30:
            risks.append("Heat stress risk - high temperatures")
            mitigations.append("Plant early or use heat-resistant varieties")
    
    # Market risks
    if market_data:
        price_change = market_data.get('price_change_pct', 0)
        if price_change < -10:
            risks.append("Price volatility - declining market")
            mitigations.append("Consider price hedging or diversification")
        
        demand_index = market_data.get('demand_index', 0.5)
        if demand_index < 0.4:
            risks.append("Low market demand")
            mitigations.append("Focus on quality and niche markets")
    
    # General risks
    risks.append("Weather variability")
    mitigations.append("Implement crop insurance")
    
    risks.append("Pest and disease pressure")
    mitigations.append("Follow integrated pest management")
    
    return {
        'risk_level': 'High' if len(risks) > 3 else 'Medium' if len(risks) > 1 else 'Low',
        'risks': risks,
        'mitigations': mitigations
    }


def generate_implementation_timeline(crop_name):
    """Generate implementation timeline for a crop"""
    current_month = datetime.date.today().month
    
    timeline = {
        'immediate_actions': [],
        'short_term': [],
        'medium_term': [],
        'long_term': []
    }
    
    # Immediate actions (next 30 days)
    timeline['immediate_actions'] = [
        "Prepare soil and test pH levels",
        "Procure quality seeds/varieties",
        "Plan irrigation system if needed",
        "Check equipment and tools"
    ]
    
    # Short term (1-3 months)
    timeline['short_term'] = [
        "Complete soil preparation",
        "Plant seeds at optimal time",
        "Monitor initial growth",
        "Apply initial fertilizers"
    ]
    
    # Medium term (3-6 months)
    timeline['medium_term'] = [
        "Regular crop monitoring",
        "Pest and disease management",
        "Irrigation management",
        "Weed control"
    ]
    
    # Long term (6+ months)
    timeline['long_term'] = [
        "Harvest planning",
        "Post-harvest handling",
        "Market preparation",
        "Crop rotation planning"
    ]
    
    return timeline


def generate_success_factors(crop_name, soil_type):
    """Generate success factors for growing a crop"""
    factors = []
    
    # Soil-specific factors
    if soil_type == 'Loam':
        factors.append("✓ Loam soil provides excellent drainage and water retention")
    elif soil_type == 'Clay':
        factors.append("⚠️ Clay soil needs proper drainage - consider raised beds")
    elif soil_type == 'Sandy':
        factors.append("⚠️ Sandy soil needs frequent irrigation and organic matter")
    
    # Crop-specific factors
    crop_factors = {
        'Wheat': ["Proper seed rate (100-120 kg/hectare)", "Timely sowing in October-November", "Balanced NPK fertilization"],
        'Rice': ["Water management is critical", "Transplanting at proper age", "Pest management for stem borer"],
        'Maize': ["High seed rate (20-25 kg/hectare)", "Proper spacing (60x20 cm)", "Zinc application"],
        'Soybean': ["Inoculation with Rhizobium", "Proper spacing (45x10 cm)", "Timely harvesting to prevent shattering"],
        'Cotton': ["High seed rate (8-10 kg/hectare)", "Proper spacing (90x60 cm)", "Pest management for bollworm"],
        'Millet': ["Low seed rate (8-10 kg/hectare)", "Drought-resistant varieties", "Minimal irrigation"],
        'Chickpea': ["Proper spacing (30x10 cm)", "Timely sowing in October", "Disease-resistant varieties"],
        'Lentil': ["Low seed rate (30-40 kg/hectare)", "Proper spacing (30x10 cm)", "Timely harvesting"],
        'Mustard': ["Proper spacing (45x10 cm)", "Balanced fertilization", "Pest management for aphids"]
    }
    
    factors.extend(crop_factors.get(crop_name, ["Follow general agricultural practices"]))
    
    return factors


def get_seasonal_crops_for_month(month):
    """Get crops suitable for planting in a specific month"""
    seasonal_crops = {
        1: ['Wheat', 'Mustard', 'Chickpea'],
        2: ['Wheat', 'Mustard', 'Chickpea'],
        3: ['Maize', 'Rice', 'Soybean'],
        4: ['Maize', 'Rice', 'Cotton'],
        5: ['Maize', 'Rice', 'Cotton'],
        6: ['Rice', 'Maize', 'Millet', 'Soybean'],
        7: ['Rice', 'Maize', 'Millet', 'Soybean'],
        8: ['Rice', 'Maize', 'Millet', 'Soybean'],
        9: ['Wheat', 'Mustard', 'Lentil'],
        10: ['Wheat', 'Mustard', 'Lentil', 'Chickpea'],
        11: ['Wheat', 'Mustard', 'Lentil', 'Chickpea'],
        12: ['Wheat', 'Mustard', 'Chickpea']
    }
    return seasonal_crops.get(month, [])


