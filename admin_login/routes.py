from flask import Blueprint, render_template, url_for, redirect, flash
from models import User, FarmProfile, Recommendation
from flask_login import login_required, current_user

admin_bp = Blueprint('admin_login', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    try:
        users = User.query.order_by(User.id.desc()).all()
        return render_template('admin_login/users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'danger')
        return redirect(url_for('home'))


@admin_bp.route('/farms')
@login_required
def farms():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    try:
        farms = FarmProfile.query.order_by(FarmProfile.created_at.desc()).all()
        return render_template('admin_login/farms.html', farms=farms)
    except Exception as e:
        flash(f'Error loading farms: {str(e)}', 'danger')
        return redirect(url_for('home'))


@admin_bp.route('/recommendations')
@login_required
def recommendations():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    try:
        recs = Recommendation.query.order_by(Recommendation.created_at.desc()).limit(200).all()
        return render_template('admin_login/recommendations.html', recs=recs)
    except Exception as e:
        flash(f'Error loading recommendations: {str(e)}', 'danger')
        return redirect(url_for('home'))
