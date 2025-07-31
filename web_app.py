#!/usr/bin/env python3
"""
🎯 Alpha Vantage Trading Framework - Web Dashboard
Kullanıcı kayıt/giriş sistemi ve kişiselleştirilmiş trading dashboard'u
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from datetime import datetime, timedelta
import json
import logging
import os

# Import our existing framework - LAZY LOADING for Railway
# from alphavantage_provider import AlphaVantageProvider
# from universal_trading_framework import UniversalTradingBot, AssetType

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
from config import config
app.config.from_object(config[config_name])

# Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Logging
logging.basicConfig(level=logging.INFO)

# 📊 Available Assets Configuration
AVAILABLE_ASSETS = {
    'forex': [
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
        'EURJPY', 'GBPJPY', 'USDCHF', 'NZDUSD'
    ],
    'stocks': [
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META',
        'ORCL', 'CRM', 'ADBE', 'NFLX', 'UBER'
    ],
    'crypto': [
        'BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'BNBUSD'
    ]
}

# 📄 Database Models
class User(UserMixin, db.Model):
    """Kullanıcı modeli"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    api_key = db.Column(db.String(255))  # Alpha Vantage API key
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlist = db.relationship('Watchlist', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Watchlist(db.Model):
    """Kullanıcı watchlist modeli"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # forex, stocks, crypto
    symbol = db.Column(db.String(20), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# 📝 Forms
class RegistrationForm(FlaskForm):
    """Kayıt formu"""
    username = StringField('Kullanıcı Adı', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    api_key = StringField('Alpha Vantage API Key', validators=[DataRequired()])
    submit = SubmitField('Kayıt Ol')

class LoginForm(FlaskForm):
    """Giriş formu"""
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

class WatchlistForm(FlaskForm):
    """Watchlist formu"""
    forex_symbols = SelectMultipleField('Forex Pairs', choices=[(s, s) for s in AVAILABLE_ASSETS['forex']])
    stock_symbols = SelectMultipleField('Stocks', choices=[(s, s) for s in AVAILABLE_ASSETS['stocks']])
    crypto_symbols = SelectMultipleField('Crypto', choices=[(s, s) for s in AVAILABLE_ASSETS['crypto']])
    submit = SubmitField('Watchlist Güncelle')

# 🏠 Routes
@app.route('/')
def index():
    """Ana sayfa"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Kullanıcı kayıt"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Bu kullanıcı adı zaten mevcut!', 'danger')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Bu email zaten kayıtlı!', 'danger')
            return render_template('register.html', form=form)
        
        # Test API key
        try:
            provider = AlphaVantageProvider(api_key=form.api_key.data)
            test_data = provider.get_current_price('AAPL')  # Test call
            
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                api_key=form.api_key.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'API anahtarı geçersiz: {str(e)}', 'danger')
            
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı giriş"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Kullanıcı çıkış"""
    logout_user()
    flash('Çıkış yapıldı!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Ana dashboard"""
    # Get user's watchlist
    watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    # Group by asset type
    user_watchlist = {
        'forex': [item.symbol for item in watchlist_items if item.asset_type == 'forex'],
        'stocks': [item.symbol for item in watchlist_items if item.asset_type == 'stocks'],
        'crypto': [item.symbol for item in watchlist_items if item.asset_type == 'crypto']
    }
    
    return render_template('dashboard.html', 
                         username=current_user.username,
                         user_watchlist=user_watchlist,
                         available_assets=AVAILABLE_ASSETS)

@app.route('/watchlist', methods=['GET', 'POST'])
@login_required
def manage_watchlist():
    """Watchlist yönetimi"""
    form = WatchlistForm()
    
    if form.validate_on_submit():
        # Clear existing watchlist
        Watchlist.query.filter_by(user_id=current_user.id).delete()
        
        # Add new selections
        for symbol in form.forex_symbols.data:
            item = Watchlist(user_id=current_user.id, asset_type='forex', symbol=symbol)
            db.session.add(item)
            
        for symbol in form.stock_symbols.data:
            item = Watchlist(user_id=current_user.id, asset_type='stocks', symbol=symbol)
            db.session.add(item)
            
        for symbol in form.crypto_symbols.data:
            item = Watchlist(user_id=current_user.id, asset_type='crypto', symbol=symbol)
            db.session.add(item)
        
        db.session.commit()
        flash('Watchlist güncellendi!', 'success')
        return redirect(url_for('dashboard'))
    
    # Pre-populate form with current selections
    current_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    form.forex_symbols.data = [item.symbol for item in current_watchlist if item.asset_type == 'forex']
    form.stock_symbols.data = [item.symbol for item in current_watchlist if item.asset_type == 'stocks']
    form.crypto_symbols.data = [item.symbol for item in current_watchlist if item.asset_type == 'crypto']
    
    return render_template('watchlist.html', form=form)

@app.route('/api/live-data')
@login_required
def live_data():
    """Canlı veri API endpoint'i"""
    try:
        # Lazy import to prevent Railway worker timeout
        from alphavantage_provider import AlphaVantageProvider
        from universal_trading_framework import UniversalTradingBot, AssetType
        
        provider = AlphaVantageProvider(api_key=current_user.api_key, is_premium=True)
        
        # Get user's watchlist
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()
        
        results = {
            'forex': [],
            'stocks': [],
            'crypto': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Fetch data for each watched symbol
        for item in watchlist_items[:15]:  # Limit to 15 items to avoid rate limits
            try:
                symbol = item.symbol
                asset_type = item.asset_type
                
                # Get current price
                price = provider.get_current_price(symbol)
                
                # Get sentiment if it's a stock
                sentiment_score = None
                if asset_type == 'stocks':
                    sentiment_data = provider.get_news_sentiment([symbol], limit=5)
                    sentiment_score = sentiment_data.get('overall_sentiment', 0)
                
                # Quick technical analysis
                framework = UniversalTradingBot(provider, 
                    AssetType.FOREX if asset_type == 'forex' 
                    else AssetType.STOCKS if asset_type == 'stocks' 
                    else AssetType.CRYPTO)
                
                analysis = framework.analyze_symbol(symbol)
                
                result_item = {
                    'symbol': symbol,
                    'price': price,
                    'signal': analysis.get('final_signal', 'hold') if 'error' not in analysis else 'error',
                    'sentiment': sentiment_score
                }
                
                results[asset_type].append(result_item)
                
            except Exception as e:
                logging.error(f"Error fetching data for {symbol}: {e}")
                continue
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f"Live data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/news/<symbol>')
@login_required
def get_symbol_news(symbol):
    """Belirli sembol için haberler (sadece US Stocks)"""
    try:
        # Check if symbol is a stock (Alpha Vantage News API only supports US stocks)
        stock_symbols = AVAILABLE_ASSETS['stocks']
        
        if symbol not in stock_symbols:
            return jsonify({
                'symbol': symbol,
                'overall_sentiment': 0,
                'news_count': 0,
                'top_news': [],
                'message': 'Haber servisi sadece US hisse senetleri için mevcuttur'
            })
        
        # Lazy import to prevent Railway worker timeout
        from alphavantage_provider import AlphaVantageProvider
        
        provider = AlphaVantageProvider(api_key=current_user.api_key, is_premium=True)
        news_data = provider.get_news_sentiment([symbol], limit=10)
        
        return jsonify({
            'symbol': symbol,
            'overall_sentiment': news_data.get('overall_sentiment', 0),
            'news_count': news_data.get('news_count', 0),
            'top_news': news_data.get('top_news', [])[:5]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database
def init_db():
    """Database'i başlat"""
    with app.app_context():
        db.create_all()
        print("✅ Database initialized!")

# Initialize DB for both development and production - DISABLED to prevent deadlock
# with app.app_context():
#     db.create_all()
#     print("✅ Database tables created!")
# Note: Tables are already created in Railway PostgreSQL

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("🚀 Starting Alpha Vantage Trading Dashboard...")
    print(f"🌐 Access: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(debug=debug, host='0.0.0.0', port=port) 