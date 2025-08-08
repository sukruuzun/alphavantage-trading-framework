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

# Framework imports moved to lazy loading sections for Railway optimization

# Import centralized constants
from constants import AVAILABLE_ASSETS

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

# 📊 Available Assets Configuration moved to constants.py (DRY principle)

# 📄 Database Models
class User(UserMixin, db.Model):
    """Kullanıcı modeli - Merkezi veri servisi (API key gerekmez)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
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

class CachedData(db.Model):
    """Background worker'ın güncelediği cache verisi"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    signal = db.Column(db.String(20), nullable=False, default='hold')
    sentiment = db.Column(db.Float, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'price': self.price,
            'signal': self.signal,
            'sentiment': self.sentiment,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'error': self.error_message
        }

class CorrelationCache(db.Model):
    """Dinamik olarak hesaplanan korelasyon katsayılarını saklar"""
    id = db.Column(db.Integer, primary_key=True)
    symbol_1 = db.Column(db.String(20), nullable=False, index=True)
    symbol_2 = db.Column(db.String(20), nullable=False, index=True)
    correlation_value = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İki sembol çiftinin benzersiz olmasını sağlar
    __table_args__ = (db.UniqueConstraint('symbol_1', 'symbol_2', name='_symbol_pair_uc'),)

    def __repr__(self):
        return f'<CorrelationCache {self.symbol_1}-{self.symbol_2}: {self.correlation_value:.3f}>'

class Asset(db.Model):
    """Filtrelenmiş yüksek kaliteli varlık listesi"""
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    exchange = db.Column(db.String(50), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # 'forex', 'stock', 'crypto'
    ipo_date = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Asset {self.symbol}: {self.name} ({self.exchange})>'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# 📝 Forms
class RegistrationForm(FlaskForm):
    """Kayıt formu - Merkezi veri servisi (API key gerekmez)"""
    username = StringField('Kullanıcı Adı', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
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
        
        # Create new user (API key gerekmez - merkezi veri servisi)
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
            
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
    
    # Group by asset type (match database asset_type values)
    user_watchlist = {
        'forex': [item.symbol for item in watchlist_items if item.asset_type == 'forex'],
        'stocks': [item.symbol for item in watchlist_items if item.asset_type in ['stock', 'stocks']],  # Support both
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
            item = Watchlist(user_id=current_user.id, asset_type='stock', symbol=symbol)  # Use 'stock' to match Asset table
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
    form.stock_symbols.data = [item.symbol for item in current_watchlist if item.asset_type in ['stock', 'stocks']]  # Support both
    form.crypto_symbols.data = [item.symbol for item in current_watchlist if item.asset_type == 'crypto']
    
    return render_template('watchlist.html', form=form)

@app.route('/api/live-data')
@login_required
def live_data():
    """Canlı veri API endpoint'i - DATABASE CACHE'DEN OKUMA"""
    try:
        # Get user's watchlist
        watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()
        
        results = {
            'forex': [],
            'stocks': [],
            'crypto': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Database cache'den veri oku (SÜPER HIZLI!)
        for item in watchlist_items:
            symbol = item.symbol
            asset_type = item.asset_type
            
            # Database'den cached data al
            cached_data = CachedData.query.filter_by(symbol=symbol).first()
            
            if cached_data:
                result_item = {
                    'symbol': symbol,
                    'price': cached_data.price,
                    'signal': cached_data.signal,
                    'sentiment': cached_data.sentiment,
                    'last_updated': cached_data.last_updated.strftime('%H:%M:%S') if cached_data.last_updated else 'N/A',
                    'error': cached_data.error_message
                }
                # Map 'stock' to 'stocks' for frontend compatibility
                frontend_asset_type = 'stocks' if asset_type == 'stock' else asset_type
                results[frontend_asset_type].append(result_item)
            else:
                # Database'de yoksa placeholder
                result_item = {
                    'symbol': symbol,
                    'price': 0,
                    'signal': 'loading',
                    'sentiment': None,
                    'last_updated': 'Worker güncelliyor...',
                    'error': None
                }
                # Map 'stock' to 'stocks' for frontend compatibility
                frontend_asset_type = 'stocks' if asset_type == 'stock' else asset_type
                results[frontend_asset_type].append(result_item)
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f"Live data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-movers')
@login_required
def get_market_movers():
    """📈 Market Movers - Top Gainers & Losers (Premium Feature)"""
    try:
        from alpha_intelligence_provider import AlphaIntelligenceProvider
        
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)'}), 500
        
        provider = AlphaIntelligenceProvider(api_key=system_api_key, is_premium=True)
        market_data = provider.get_top_gainers_losers()
        
        return jsonify(market_data)
        
    except Exception as e:
        logging.error(f"Market movers error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insider/<symbol>')
@login_required
def get_insider_activity(symbol):
    """🏛️ Insider Trading Activity (Premium Feature)"""
    try:
        from alpha_intelligence_provider import AlphaIntelligenceProvider
        
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)'}), 500
        
        provider = AlphaIntelligenceProvider(api_key=system_api_key, is_premium=True)
        insider_data = provider.get_insider_transactions(symbol.upper())
        
        return jsonify(insider_data)
        
    except Exception as e:
        logging.error(f"Insider activity error for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/earnings-calendar')
@login_required
def get_earnings_calendar():
    """📅 Earnings Calendar (Premium Feature)"""
    try:
        from alpha_intelligence_provider import AlphaIntelligenceProvider
        
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)'}), 500
        
        horizon = request.args.get('horizon', '3month')  # 3month, 6month, 12month
        
        provider = AlphaIntelligenceProvider(api_key=system_api_key, is_premium=True)
        earnings_data = provider.get_earnings_calendar(horizon)
        
        return jsonify(earnings_data)
        
    except Exception as e:
        logging.error(f"Earnings calendar error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-api-key')
@login_required
def test_api_key():
    """🔑 API Key Test & Validation"""
    try:
        from alphavantage_provider import AlphaVantageProvider
        import requests
        
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)'}), 500
        
        # Test basic API call
        test_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={system_api_key}"
        
        response = requests.get(test_url, timeout=10)
        data = response.json()
        
        # Analyze response
        if "Error Message" in data:
            return jsonify({
                'api_key_status': 'invalid',
                'error': data["Error Message"],
                'api_key_preview': f"{system_api_key[:8]}...",
                'suggestion': 'API key geçersiz veya yanlış format'
            }), 400
        
        if "Information" in data:
            if "call frequency" in data["Information"].lower():
                return jsonify({
                    'api_key_status': 'rate_limited',
                    'error': data["Information"],
                    'api_key_preview': f"{system_api_key[:8]}...",
                    'suggestion': 'Free plan rate limit aşıldı - Premium plan gerekli'
                }), 429
        
        if "Global Quote" in data:
            quote_data = data["Global Quote"]
            return jsonify({
                'api_key_status': 'valid',
                'plan_type': 'premium' if response.elapsed.total_seconds() < 2 else 'free',
                'api_key_preview': f"{system_api_key[:8]}...",
                'test_symbol': 'AAPL',
                'test_price': quote_data.get('05. price', 'N/A'),
                'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2),
                'suggestion': 'API key çalışıyor!'
            })
        
        return jsonify({
            'api_key_status': 'unknown_response',
            'raw_response': data,
            'api_key_preview': f"{system_api_key[:8]}...",
            'suggestion': 'Beklenmeyen API yanıtı'
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'api_key_status': 'timeout',
            'error': 'API timeout - network problemi olabilir',
            'suggestion': 'İnternet bağlantısını kontrol edin'
        }), 408
        
    except Exception as e:
        logging.error(f"API key test error: {e}")
        return jsonify({
            'api_key_status': 'error',
            'error': str(e),
            'suggestion': 'Beklenmeyen hata oluştu'
        }), 500

@app.route('/api/daily-briefing')
@login_required
def get_daily_briefing():
    """🎯 Günlük Piyasa Brifingi API Endpoint"""
    try:
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı'}), 500
            
        # AlphaVantage provider ile briefing oluştur
        from alphavantage_provider import AlphaVantageProvider
        from universal_trading_framework import UniversalTradingBot, AssetType
        from datetime import datetime
        import time
        
        provider = AlphaVantageProvider(system_api_key, is_premium=True)
        framework = UniversalTradingBot(provider, AssetType.STOCKS)
        
        # Briefing verilerini topla
        briefing_data = {
            'timestamp': datetime.now().isoformat(),
            'global_sentiment': None,
            'top_opportunities': [],
            'market_summary': {},
            'recommendations': [],
            'risk_analysis': {}
        }
        
        # 1. Global Sentiment
        try:
            sentiment_data = provider.get_news_sentiment(limit=50)
            briefing_data['global_sentiment'] = {
                'overall_score': sentiment_data.get('overall_sentiment', 0),
                'news_count': sentiment_data.get('news_count', 0),
                'status': 'Pozitif' if sentiment_data.get('overall_sentiment', 0) > 0.1 else 
                         'Negatif' if sentiment_data.get('overall_sentiment', 0) < -0.1 else 'Nötr'
            }
        except Exception as e:
            logging.warning(f"Global sentiment hatası: {e}")
            briefing_data['global_sentiment'] = {'status': 'Veri yok', 'overall_score': 0}
        
        # 2. TÜM SİSTEM TARAMASI - Tüm asset'leri analiz et
        try:
            from constants import AVAILABLE_ASSETS
            import random
            
            # Tüm sistemdeki enstrümanları topla
            all_symbols = []
            all_symbols.extend(AVAILABLE_ASSETS['stocks'])  # ~60 hisse
            all_symbols.extend(AVAILABLE_ASSETS['forex'])   # 9 forex
            all_symbols.extend(AVAILABLE_ASSETS['crypto'])  # 4 crypto
            
            # Performans için randomize et ve ilk 15-20'sini analiz et
            random.shuffle(all_symbols)
            symbols_to_analyze = all_symbols[:20]  # İlk 20 sembol (hız için)
            
            logging.info(f"📊 Günlük briefing: {len(symbols_to_analyze)} sembol analiz ediliyor...")
            
            analyzed_count = 0
            for symbol in symbols_to_analyze:
                try:
                    analysis = framework.analyze_symbol(symbol)
                    analyzed_count += 1
                    
                    # BUY/SELL sinyali varsa fırsat listesine ekle
                    if analysis.get('final_signal') in ['buy', 'sell']:
                        # Asset tipini belirle
                        asset_type = 'Stock'
                        if symbol in AVAILABLE_ASSETS['forex']:
                            asset_type = 'Forex'
                        elif symbol in AVAILABLE_ASSETS['crypto']:
                            asset_type = 'Crypto'
                            
                        briefing_data['top_opportunities'].append({
                            'symbol': symbol,
                            'signal': analysis.get('final_signal', 'hold').upper(),
                            'price': analysis.get('current_price', 0),
                            'asset_type': asset_type,
                            'confidence': 'Yüksek' if analysis.get('final_signal') != 'hold' else 'Düşük'
                        })
                        
                        # En fazla 10 fırsat göster (UI için)
                        if len(briefing_data['top_opportunities']) >= 10:
                            break
                            
                except Exception as e:
                    logging.warning(f"Sembol analiz hatası {symbol}: {e}")
                    continue
            
            logging.info(f"✅ Günlük briefing tamamlandı: {analyzed_count} sembol, {len(briefing_data['top_opportunities'])} fırsat bulundu")
                    
        except Exception as e:
            logging.warning(f"Sistem tarama hatası: {e}")
        
        # 3. Market Summary
        briefing_data['market_summary'] = {
            'total_symbols_in_system': len(AVAILABLE_ASSETS['stocks']) + len(AVAILABLE_ASSETS['forex']) + len(AVAILABLE_ASSETS['crypto']),
            'analyzed_symbols': analyzed_count if 'analyzed_count' in locals() else 0,
            'opportunities_found': len(briefing_data['top_opportunities']),
            'buy_signals': len([op for op in briefing_data['top_opportunities'] if op['signal'] == 'BUY']),
            'sell_signals': len([op for op in briefing_data['top_opportunities'] if op['signal'] == 'SELL']),
            'market_mood': briefing_data['global_sentiment']['status'],
            'asset_breakdown': {
                'stocks': len([op for op in briefing_data['top_opportunities'] if op.get('asset_type') == 'Stock']),
                'forex': len([op for op in briefing_data['top_opportunities'] if op.get('asset_type') == 'Forex']),
                'crypto': len([op for op in briefing_data['top_opportunities'] if op.get('asset_type') == 'Crypto'])
            }
        }
        
        # 4. Akıllı Öneriler - Sistem taraması sonuçlarına göre
        sentiment_score = briefing_data['global_sentiment']['overall_score']
        buy_count = briefing_data['market_summary']['buy_signals']
        sell_count = briefing_data['market_summary']['sell_signals']
        total_opportunities = briefing_data['market_summary']['opportunities_found']
        analyzed = briefing_data['market_summary']['analyzed_symbols']
        
        # Ana strateji önerisi
        if sentiment_score > 0.1 and buy_count > sell_count:
            briefing_data['recommendations'].append("🟢 Pozitif piyasa sentiment - Alım fırsatlarını değerlendirin")
        elif sentiment_score < -0.1 and sell_count > buy_count:
            briefing_data['recommendations'].append("🔴 Negatif piyasa sentiment - Risk yönetimi yapın")
        else:
            briefing_data['recommendations'].append("🟡 Karışık sinyaller - Temkinli yaklaşın")
        
        # Fırsat yoğunluğu analizi
        if total_opportunities == 0:
            briefing_data['recommendations'].append("⏸️ Sistem taramasında net sinyal yok - Bekleyici pozisyon alın")
        elif total_opportunities <= 2:
            briefing_data['recommendations'].append("📊 Az sayıda fırsat - Seçici davranın")
        elif total_opportunities >= 5:
            briefing_data['recommendations'].append("🎯 Çok sayıda fırsat - Portföy çeşitliliği yapın")
        
        # Asset sınıfı önerileri
        asset_breakdown = briefing_data['market_summary']['asset_breakdown']
        if asset_breakdown['stocks'] > asset_breakdown['forex'] + asset_breakdown['crypto']:
            briefing_data['recommendations'].append("📈 Hisse senetlerinde daha fazla aktivite")
        elif asset_breakdown['forex'] > 0:
            briefing_data['recommendations'].append("💱 Forex piyasasında hareket var")
        elif asset_breakdown['crypto'] > 0:
            briefing_data['recommendations'].append("₿ Kripto piyasasında fırsatlar mevcut")
        
        # Sistem kapsamı bilgisi
        briefing_data['recommendations'].append(f"🔍 {analyzed} sembol analiz edildi (Sistem: {briefing_data['market_summary']['total_symbols_in_system']} enstrüman)")
        
        return jsonify(briefing_data)
        
    except Exception as e:
        logging.error(f"Daily briefing error: {e}")
        return jsonify({
            'error': 'Günlük briefing oluşturulamadı',
            'details': str(e)
        }), 500

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
        
        # Merkezi sistem API key kullan (fallback to ALPHA_VANTAGE_KEY)
        system_api_key = os.environ.get('SYSTEM_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not system_api_key:
            return jsonify({'error': 'API anahtarı bulunamadı (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)'}), 500
        
        # DÜZELTME: API key validation ve proper error handling
        try:
            provider = AlphaVantageProvider(api_key=system_api_key, is_premium=True)
            news_data = provider.get_news_sentiment([symbol], limit=10)
            
            # API response validation
            if 'error' in news_data:
                logging.error(f"Alpha Vantage API Error for {symbol}: {news_data['error']}")
                return jsonify({
                    'symbol': symbol,
                    'error': f'API hatası: {news_data["error"]}',
                    'overall_sentiment': 0,
                    'news_count': 0,
                    'top_news': []
                }), 400
            
            return jsonify({
                'symbol': symbol,
                'overall_sentiment': news_data.get('overall_sentiment', 0),
                'news_count': news_data.get('news_count', 0),
                'top_news': news_data.get('top_news', [])[:5],
                'last_updated': news_data.get('last_updated', 'N/A')
            })
            
        except ValueError as api_error:
            logging.error(f"API Value Error for {symbol}: {api_error}")
            return jsonify({
                'symbol': symbol,
                'error': f'API çağrı hatası: {str(api_error)}',
                'overall_sentiment': 0,
                'news_count': 0,
                'top_news': []
            }), 400
        
    except Exception as e:
        logging.error(f"Unexpected error in get_symbol_news for {symbol}: {e}")
        return jsonify({'error': f'Beklenmeyen hata: {str(e)}'}), 500

# Initialize database
def init_db():
    """Database'i başlat"""
    with app.app_context():
        db.create_all()
        print("✅ Database initialized!")

# Initialize DB for both development and production - ENABLED for Asset table creation
with app.app_context():
    db.create_all()
    print("✅ Database tables created/migrated!")
# Note: Asset table added for smart asset filtering

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("🚀 Starting Alpha Vantage Trading Dashboard...")
    print(f"🌐 Access: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(debug=debug, host='0.0.0.0', port=port) 