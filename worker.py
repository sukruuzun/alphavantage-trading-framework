#!/usr/bin/env python3
"""
🔄 Alpha Vantage Trading Framework - Background Worker
Arka planda sürekli çalışarak veri güncelleme sistemi
"""

import time
import os
import logging
from datetime import datetime

# Flask app ve modellerini import et
from web_app import app, db, User, Watchlist, CachedData, CorrelationCache, Asset, DailyBriefing
from alphavantage_provider import AlphaVantageProvider
from universal_trading_framework import UniversalTradingBot, AssetType

# Import configurations
from constants import CORRELATION_CONFIG, API_CONFIG

# Additional imports for correlation calculation
import pandas as pd
from sqlalchemy import text

# Loglama kurulumu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_asset_type(symbol, available_assets):
    """Sembol için doğru asset type'ı bul"""
    for asset_type, symbols in available_assets.items():
        if symbol in symbols:
            if asset_type == 'forex':
                return AssetType.FOREX
            elif asset_type == 'stocks':
                return AssetType.STOCKS
            elif asset_type == 'crypto':
                return AssetType.CRYPTO
    return AssetType.STOCKS  # Default

def get_active_symbols_from_db():
    """Veritabanından aktif olan tüm varlık sembollerini çeker"""
    with app.app_context():
        try:
            # Asset tablosundan aktif varlıkları çek (populate_assets.py ile tutarlı naming)
            forex_assets = [a.symbol for a in Asset.query.filter_by(asset_type='forex', is_active=True).all()]
            stock_assets = [a.symbol for a in Asset.query.filter_by(asset_type='stock', is_active=True).all()]  # FIX: 'stock' not 'stocks'
            crypto_assets = [a.symbol for a in Asset.query.filter_by(asset_type='crypto', is_active=True).all()]
            
            logger.info(f"📊 Database'den çekilen varlıklar:")
            logger.info(f"   Forex: {len(forex_assets)} varlık")
            logger.info(f"   Stocks: {len(stock_assets)} varlık")  
            logger.info(f"   Crypto: {len(crypto_assets)} varlık")
            
            # Eğer database boşsa, fallback constants kullan
            total_assets = len(forex_assets) + len(stock_assets) + len(crypto_assets)
            
            if total_assets == 0:
                logger.warning("⚠️ Database'de varlık bulunamadı, fallback constants kullanılıyor")
                # Fallback to constants if database is empty
                from constants import AVAILABLE_ASSETS
                return AVAILABLE_ASSETS
            
            return {
                'forex': forex_assets,
                'stocks': stock_assets,  # Keep 'stocks' key for compatibility with other parts
                'crypto': crypto_assets
            }
        except Exception as e:
            logger.error(f"❌ Database varlık okuma hatası: {e}")
            logger.warning("⚠️ Fallback constants kullanılıyor")
            # Fallback to constants on error
            from constants import AVAILABLE_ASSETS
            return AVAILABLE_ASSETS

def calculate_and_store_correlations(provider):
    """Tüm varlıklar için korelasyon matrisini hesaplar ve veritabanına kaydeder"""
    logger.info("📈 Dinamik korelasyon hesaplaması başlıyor...")
    
    # Tüm sembolleri database'den al
    available_assets = get_active_symbols_from_db()
    all_symbols = (available_assets['forex'] + 
                   available_assets['stocks'] + 
                   available_assets['crypto'])
    
    price_data = {}
    
    logger.info(f"📊 Tarihsel veri çekiliyor ({len(all_symbols)} varlık)...")
    
    for symbol in all_symbols:
        try:
            # 90 günlük veri al (daha stabil korelasyon için)
            days_back = CORRELATION_CONFIG['historical_days']
            # 15dk periyotlarla günlük data: 96 periyot/gün * 90 gün = 8640 periyot
            data_points = 96 * days_back
            
            df = provider.get_historical_data(symbol, 
                                            CORRELATION_CONFIG['timeframe'], 
                                            data_points)
            
            if not df.empty and len(df) >= CORRELATION_CONFIG['min_data_points']:
                # Close fiyatları al
                price_data[symbol] = df['Close'].ffill(limit=10).dropna()
                logger.info(f"✅ {symbol}: {len(price_data[symbol])} veri noktası")
            else:
                logger.warning(f"⚠️ {symbol}: Yetersiz veri ({len(df) if not df.empty else 0} nokta)")
            
            # Rate limiting
            time.sleep(1.5)
            
        except Exception as e:
            logger.warning(f"❌ {symbol} korelasyon verisi alınamadı: {e}")

    if len(price_data) < 10:
        logger.error("❌ Korelasyon için yeterli veri toplanamadı.")
        return False

    try:
        # Yüzdesel değişime göre korelasyon hesapla (daha stabil)
        full_df = pd.DataFrame(price_data).pct_change(fill_method=None).dropna()
        correlation_matrix = full_df.corr()
        
        logger.info("✅ Korelasyon matrisi hesaplandı. Veritabanına kaydediliyor...")
        
        # Flask app context içinde database işlemleri
        with app.app_context():
            # Veritabenına kaydet
            valid_correlations = 0
            
            # Önceki verileri temizle
            CorrelationCache.query.delete()
            
            # Yeni verileri ekle
            for symbol_1 in correlation_matrix.columns:
                for symbol_2 in correlation_matrix.columns:
                    if symbol_1 >= symbol_2:  # Tekrarlı çiftleri önle
                        continue
                    
                    corr_value = correlation_matrix.loc[symbol_1, symbol_2]
                    
                    # NaN olmayan ve anlamlı korelasyonları kaydet
                    if pd.notna(corr_value) and abs(corr_value) >= CORRELATION_CONFIG['correlation_threshold']:
                        new_corr = CorrelationCache(
                            symbol_1=symbol_1,
                            symbol_2=symbol_2,
                            correlation_value=float(corr_value)
                        )
                        db.session.add(new_corr)
                        valid_correlations += 1
            
            db.session.commit()
            logger.info(f"✅ {valid_correlations} anlamlı korelasyon veritabanına kaydedildi")
            
            # Örnek korelasyonları logla
            sample_corrs = CorrelationCache.query.order_by(CorrelationCache.correlation_value.desc()).limit(5).all()
            for corr in sample_corrs:
                logger.info(f"📊 En yüksek korelasyon: {corr.symbol_1} ↔ {corr.symbol_2}: {corr.correlation_value:.3f}")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Korelasyon hesaplama/kaydetme hatası: {e}")
        with app.app_context():
            db.session.rollback()
        return False

def update_data_for_all_users():
    """Tüm kullanıcıların watchlist'leri için veri güncelle"""
    logger.info("🚀 Background Worker: Veri güncelleme döngüsü başladı...")
    
    with app.app_context():
        try:
            # Tüm kullanıcıları kontrol et (watchlist için gerekli)
            users = User.query.all()
            if not users:
                logger.warning("❌ Hiç kullanıcı bulunamadı. Bekleniyor...")
                return

            # Merkezi sistem API key kullan (fallback to ALPHA_VANTAGE_KEY)
            system_api_key = os.getenv('SYSTEM_ALPHA_VANTAGE_KEY') or os.getenv('ALPHA_VANTAGE_KEY')
            if not system_api_key:
                logger.error("❌ API anahtarı bulunamadı! (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)")
                return
                
            provider = AlphaVantageProvider(api_key=system_api_key, is_premium=True)
            logger.info(f"🔑 Sistem API key kullanılıyor: {system_api_key[:8]}...")

            # Veritabanından aktif varlıkları çek (database-driven dynamic assets)
            available_assets = get_active_symbols_from_db()
            
            # Tüm available sembol listesi (korelasyon için gerekli)
            all_available_symbols = set(available_assets['forex'] + 
                                       available_assets['stocks'] + 
                                       available_assets['crypto'])
            
            # Kullanıcı watchlist'lerinden sembolleri al
            all_watchlist_items = Watchlist.query.all()
            watchlist_symbols = {item.symbol for item in all_watchlist_items}
            
            # Kullanıcı watchlist'i + temel varlıklar (minimum coverage için)
            # Eğer watchlist boşsa, en azından major assets'ler analiz edilsin
            essential_symbols = {'AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'EURUSD', 'BTCUSD', 'ETHUSD'}
            
            # Final unique symbols: watchlist + essential + intersect with available
            unique_symbols = (watchlist_symbols | essential_symbols) & all_available_symbols
            
            logger.info(f"📊 Available symbols: {len(all_available_symbols)}")
            logger.info(f"📝 Watchlist symbols: {len(watchlist_symbols)}")  
            logger.info(f"🔄 Processing symbols: {len(unique_symbols)}")
            
            if len(unique_symbols) < 20:
                logger.warning(f"⚠️ Az sembol tespit edildi ({len(unique_symbols)}), tüm available symbols kullanılıyor")
                unique_symbols = all_available_symbols

            successful_updates = 0
            
            # OPTIMIZASYON: Bulk asset info loading (N+1 query problemi çözümü)
            asset_info_cache = {}
            with app.app_context():
                all_assets = Asset.query.filter(Asset.symbol.in_(unique_symbols), Asset.is_active == True).all()
                asset_info_cache = {asset.symbol: asset for asset in all_assets}
            
            for symbol in unique_symbols:
                try:
                    logger.info(f"🔄 {symbol} verisi güncelleniyor...")
                    
                    # AKILLI FİLTRELEME: Asset type kontrolü (Cache'den al)
                    asset_info = asset_info_cache.get(symbol)
                    
                    # Eğer varlık veritabanında yok veya desteklenmeyen türde ise, atla
                    if not asset_info:
                        logger.warning(f"⚠️ {symbol} veritabanında bulunamadı veya pasif. Analiz atlanıyor.")
                        continue
                    
                    # ETF'leri atla (News API desteklemiyor)
                    if asset_info.asset_type.lower() in ['etf', 'fund']:
                        logger.warning(f"⚠️ {symbol} bir ETF/Fund. News API desteklemiyor, analiz atlanıyor.")
                        continue
                    
                    # TWTR gibi delisted stocks için ek kontrol
                    if symbol in ['TWTR', 'FB']:  # Bilinen delisted/renamed stocks
                        logger.warning(f"⚠️ {symbol} delisted/renamed stock. Analiz atlanıyor.")
                        continue
                    
                    # Current price al
                    price = provider.get_current_price(symbol)
                    
                    # Asset type belirle (database-driven)
                    asset_type = get_asset_type(symbol, available_assets)
                    
                    # Framework ile analiz yap
                    framework = UniversalTradingBot(provider, asset_type)
                    analysis = framework.analyze_symbol(symbol)
                    
                    # Sentiment (sadece stocks için)
                    sentiment_score = None
                    if asset_type == AssetType.STOCKS:
                        try:
                            sentiment_data = provider.get_news_sentiment([symbol], limit=3)
                            sentiment_score = sentiment_data.get('overall_sentiment', 0)
                        except:
                            sentiment_score = 0

                    # Database cache'e kaydet (Batch operation için prepare)
                    cached_data = CachedData.query.filter_by(symbol=symbol).first()
                    if cached_data:
                        # Mevcut kayıt varsa güncelle
                        cached_data.price = price
                        cached_data.signal = analysis.get('final_signal', 'hold') if 'error' not in analysis else 'error' 
                        cached_data.sentiment = sentiment_score
                        cached_data.last_updated = datetime.now()
                        cached_data.error_message = None
                    else:
                        # Yeni kayıt oluştur
                        cached_data = CachedData(
                            symbol=symbol,
                            price=price,
                            signal=analysis.get('final_signal', 'hold') if 'error' not in analysis else 'error',
                            sentiment=sentiment_score,
                            last_updated=datetime.now(),
                            error_message=None
                        )
                        db.session.add(cached_data)
                    
                    logger.info(f"✅ {symbol}: ${price} | {analysis.get('final_signal', 'N/A')}")
                    successful_updates += 1
                    
                    # OPTIMIZASYON: Batch commit (configurable size)
                    if successful_updates % API_CONFIG['batch_commit_size'] == 0:
                        db.session.commit()
                        logger.debug(f"📊 Batch commit: {successful_updates} güncelleme")
                    
                    # Rate limiting (configurable)
                    time.sleep(API_CONFIG['rate_limit_sleep'])
                    
                except Exception as e:
                    error_message = str(e)
                    logger.error(f"❌ {symbol} için veri çekilemedi: {error_message}")
                    
                    # AKILLI AUTO-DEACTIVATION: "Invalid API call" hatası varsa varlığı pasif yap
                    if "Invalid API call" in error_message:
                        try:
                            with app.app_context():
                                asset_to_deactivate = Asset.query.filter_by(symbol=symbol).first()
                                if asset_to_deactivate:
                                    asset_to_deactivate.is_active = False
                                    db.session.commit()
                                    logger.info(f"🔧 {symbol} otomatik pasif yapıldı (Invalid API call nedeniyle)")
                        except Exception as deactivate_error:
                            logger.error(f"❌ {symbol} pasif yapılamadı: {deactivate_error}")
                    
                    # Hata durumunda database'e error kaydet
                    try:
                        cached_data = CachedData.query.filter_by(symbol=symbol).first()
                        if cached_data:
                            cached_data.error_message = error_message
                            cached_data.last_updated = datetime.now()
                            db.session.commit()
                    except Exception as db_error:
                        logger.error(f"❌ Database error for {symbol}: {db_error}")
                        db.session.rollback()

            # Final commit for remaining records
            if successful_updates > 0:
                db.session.commit()
                logger.debug("📊 Final commit completed")
            
            logger.info(f"✅ Veri güncelleme tamamlandı: {successful_updates}/{len(unique_symbols)} başarılı")
            
        except Exception as e:
            logger.error(f"❌ Genel güncelleme hatası: {e}")
            db.session.rollback()  # Rollback on error

def main():
    """Ana worker döngüsü"""
    logger.info("🚀 Alpha Vantage Background Worker başlatıldı")
    logger.info("📊 Her 5 dakikada veri güncellenecek")
    logger.info(f"📈 Her {CORRELATION_CONFIG['update_interval_hours']} saatte korelasyon güncellenecek")
    
    # Database tablolarını oluştur (gerekirse)
    with app.app_context():
        db.create_all()
        logger.info("✅ Database tables ready!")
    
    # Korelasyon hesaplama zamanlaması
    last_correlation_update = 0
    correlation_interval = CORRELATION_CONFIG['update_interval_hours'] * 3600  # Hours to seconds
    
    while True:
        try:
            # Korelasyon güncellemesi kontrolü (günde bir kez)
            if time.time() - last_correlation_update > correlation_interval:
                logger.info("🔄 Korelasyon güncelleme zamanı geldi...")
                system_api_key = os.getenv('SYSTEM_ALPHA_VANTAGE_KEY') or os.getenv('ALPHA_VANTAGE_KEY')
                
                if system_api_key:
                    provider = AlphaVantageProvider(api_key=system_api_key, is_premium=True)
                    correlation_success = calculate_and_store_correlations(provider)
                    
                    if correlation_success:
                        last_correlation_update = time.time()
                        logger.info("✅ Korelasyon güncelleme tamamlandı")
                    else:
                        logger.error("❌ Korelasyon güncelleme başarısız - 1 saat sonra yeniden denenecek")
                        last_correlation_update = time.time() - correlation_interval + 3600  # Retry in 1 hour
                else:
                    logger.error("❌ API anahtarı bulunamadı - korelasyon güncellenemiyor (SYSTEM_ALPHA_VANTAGE_KEY veya ALPHA_VANTAGE_KEY)")
            
            # Normal veri güncelleme (configurable interval)
            update_data_for_all_users()
            sleep_minutes = API_CONFIG['worker_sleep_interval'] // 60
            logger.info(f"🕒 Sonraki güncelleme için {sleep_minutes} dakika bekleniyor...")
            time.sleep(API_CONFIG['worker_sleep_interval'])
            
        except KeyboardInterrupt:
            logger.info("👋 Background Worker durduruluyor...")
            break
        except Exception as e:
            logger.error(f"❌ Worker döngüsü hatası: {e}")
            logger.info("🔄 30 saniye sonra yeniden denenecek...")
            time.sleep(30)

def generate_daily_briefing():
    """🎯 Günlük Piyasa Brifingi Oluştur ve Database'e Kaydet"""
    with app.app_context():
        try:
            from datetime import date
            import json
            import random
            
            current_date = date.today()
            current_hour = datetime.now().hour
            
            logger.info(f"📊 Günlük briefing oluşturuluyor: {current_date} {current_hour}:00")
            
            # API key al
            system_api_key = os.getenv('SYSTEM_ALPHA_VANTAGE_KEY') or os.getenv('ALPHA_VANTAGE_KEY')
            if not system_api_key:
                logger.error("❌ API anahtarı bulunamadı - Briefing atlanıyor")
                return
            
            # Provider ve framework oluştur
            provider = AlphaVantageProvider(system_api_key, is_premium=True)
            framework = UniversalTradingBot(provider, AssetType.STOCKS)
            
            # Mevcut briefing'i kontrol et
            existing_briefing = DailyBriefing.query.filter_by(
                briefing_date=current_date, 
                briefing_hour=current_hour
            ).first()
            
            if existing_briefing:
                logger.info(f"✅ Bu saatte briefing zaten mevcut: {current_hour}:00")
                return existing_briefing.to_dict()
            
            # 1. Global Sentiment
            briefing_data = {
                'global_sentiment_score': 0.0,
                'global_sentiment_status': 'Nötr',
                'news_count': 0,
                'total_analyzed': 0,
                'buy_signals_count': 0,
                'sell_signals_count': 0,
                'top_opportunities': [],
                'recommendations': [],
                'market_movers_data': {}
            }
            
            try:
                sentiment_data = provider.get_news_sentiment(limit=50)
                briefing_data['global_sentiment_score'] = sentiment_data.get('overall_sentiment', 0)
                briefing_data['news_count'] = sentiment_data.get('news_count', 0)
                
                score = briefing_data['global_sentiment_score']
                briefing_data['global_sentiment_status'] = (
                    'Pozitif' if score > 0.1 else 
                    'Negatif' if score < -0.1 else 'Nötr'
                )
                logger.info(f"📈 Global sentiment: {briefing_data['global_sentiment_status']} ({score:.3f})")
            except Exception as e:
                logger.warning(f"⚠️ Global sentiment hatası: {e}")
            
            # 2. Tüm Sistem Taraması (Sadece BUY/SELL sinyalleri)
            try:
                from constants import AVAILABLE_ASSETS
                
                # Tüm sembolleri topla
                all_symbols = []
                all_symbols.extend(AVAILABLE_ASSETS['stocks'])
                all_symbols.extend(AVAILABLE_ASSETS['forex'])
                all_symbols.extend(AVAILABLE_ASSETS['crypto'])
                
                # 30 rastgele sembol analiz et (briefing için daha kapsamlı)
                random.shuffle(all_symbols)
                symbols_to_analyze = all_symbols[:30]
                
                logger.info(f"🔍 {len(symbols_to_analyze)} sembol analiz ediliyor...")
                
                for symbol in symbols_to_analyze:
                    try:
                        analysis = framework.analyze_symbol(symbol)
                        briefing_data['total_analyzed'] += 1
                        
                        signal = analysis.get('final_signal', 'hold')
                        
                        # Sadece BUY/SELL sinyalleri kaydet (HOLD'ları atla)
                        if signal in ['buy', 'sell']:
                            # Asset tipini belirle
                            asset_type = 'Stock'
                            if symbol in AVAILABLE_ASSETS['forex']:
                                asset_type = 'Forex'
                            elif symbol in AVAILABLE_ASSETS['crypto']:
                                asset_type = 'Crypto'
                            
                            briefing_data['top_opportunities'].append({
                                'symbol': symbol,
                                'signal': signal.upper(),
                                'price': analysis.get('current_price', 0),
                                'asset_type': asset_type,
                                'confidence': 'Yüksek'
                            })
                            
                            if signal == 'buy':
                                briefing_data['buy_signals_count'] += 1
                            else:
                                briefing_data['sell_signals_count'] += 1
                            
                            # En fazla 15 fırsat kaydet
                            if len(briefing_data['top_opportunities']) >= 15:
                                break
                                
                    except Exception as e:
                        logger.warning(f"Analiz hatası {symbol}: {e}")
                        continue
                
                logger.info(f"✅ {briefing_data['total_analyzed']} sembol analiz edildi, {len(briefing_data['top_opportunities'])} fırsat bulundu")
                
            except Exception as e:
                logger.error(f"❌ Sistem tarama hatası: {e}")
            
            # 3. Market Movers (Alpha Intelligence)
            try:
                from alpha_intelligence_provider import AlphaIntelligenceProvider
                intelligence_provider = AlphaIntelligenceProvider(system_api_key, is_premium=True)
                market_movers = intelligence_provider.get_top_gainers_losers()
                briefing_data['market_movers_data'] = market_movers
                logger.info("📈 Market movers verisi alındı")
            except Exception as e:
                logger.warning(f"⚠️ Market movers hatası: {e}")
                briefing_data['market_movers_data'] = {}
            
            # 4. Akıllı Öneriler Oluştur
            recommendations = []
            sentiment_score = briefing_data['global_sentiment_score']
            buy_count = briefing_data['buy_signals_count']
            sell_count = briefing_data['sell_signals_count']
            total_opportunities = len(briefing_data['top_opportunities'])
            
            # Ana strateji
            if sentiment_score > 0.1 and buy_count > sell_count:
                recommendations.append("🟢 Pozitif piyasa sentiment - Alım fırsatlarını değerlendirin")
            elif sentiment_score < -0.1 and sell_count > buy_count:
                recommendations.append("🔴 Negatif piyasa sentiment - Risk yönetimi yapın")
            else:
                recommendations.append("🟡 Karışık sinyaller - Temkinli yaklaşın")
            
            # Fırsat analizi
            if total_opportunities == 0:
                recommendations.append("⏸️ Net sinyal yok - Bekleyici pozisyon alın")
            elif total_opportunities <= 3:
                recommendations.append("📊 Az sayıda fırsat - Seçici davranın")
            elif total_opportunities >= 8:
                recommendations.append("🎯 Çok sayıda fırsat - Portföy çeşitliliği yapın")
            
            # Asset dağılımı
            asset_counts = {}
            for opp in briefing_data['top_opportunities']:
                asset_type = opp.get('asset_type', 'Stock')
                asset_counts[asset_type] = asset_counts.get(asset_type, 0) + 1
            
            if asset_counts.get('Stock', 0) > asset_counts.get('Forex', 0) + asset_counts.get('Crypto', 0):
                recommendations.append("📈 Hisse senetlerinde daha fazla aktivite")
            elif asset_counts.get('Forex', 0) > 0:
                recommendations.append("💱 Forex piyasasında hareket var")
            elif asset_counts.get('Crypto', 0) > 0:
                recommendations.append("₿ Kripto piyasasında fırsatlar mevcut")
            
            recommendations.append(f"🔍 {briefing_data['total_analyzed']} sembol analiz edildi (Sistem: 73 enstrüman)")
            
            briefing_data['recommendations'] = recommendations
            
            # 5. Database'e Kaydet
            new_briefing = DailyBriefing(
                briefing_date=current_date,
                briefing_hour=current_hour,
                global_sentiment_score=briefing_data['global_sentiment_score'],
                global_sentiment_status=briefing_data['global_sentiment_status'],
                news_count=briefing_data['news_count'],
                total_analyzed=briefing_data['total_analyzed'],
                buy_signals_count=briefing_data['buy_signals_count'],
                sell_signals_count=briefing_data['sell_signals_count'],
                top_opportunities=json.dumps(briefing_data['top_opportunities']),
                recommendations=json.dumps(briefing_data['recommendations']),
                market_movers_data=json.dumps(briefing_data['market_movers_data'])
            )
            
            db.session.add(new_briefing)
            db.session.commit()
            
            logger.info(f"✅ Günlük briefing kaydedildi: {len(briefing_data['top_opportunities'])} fırsat, {len(briefing_data['recommendations'])} öneri")
            
            return new_briefing.to_dict()
            
        except Exception as e:
            logger.error(f"❌ Günlük briefing hatası: {e}")
            db.session.rollback()
            return None

def enhanced_worker_main():
    """🚀 Gelişmiş Worker - Saatlik briefing ile"""
    logger.info("🚀 Gelişmiş Background Worker başlatılıyor...")
    logger.info("📊 Özellikler: Veri güncelleme + Saatlik briefing")
    
    last_briefing_hour = -1  # İlk çalışmada briefing yap
    
    while True:
        try:
            current_hour = datetime.now().hour
            
            # Saatlik briefing kontrolü
            if current_hour != last_briefing_hour:
                logger.info(f"🎯 Saatlik briefing zamanı: {current_hour}:00")
                generate_daily_briefing()
                last_briefing_hour = current_hour
            
            # Normal veri güncelleme
            logger.info("🔄 Veri güncelleme başlıyor...")
            update_cached_data()
            
            # Bekleme
            sleep_minutes = API_CONFIG['worker_sleep_interval'] // 60
            logger.info(f"🕒 Sonraki güncelleme için {sleep_minutes} dakika bekleniyor...")
            time.sleep(API_CONFIG['worker_sleep_interval'])
            
        except KeyboardInterrupt:
            logger.info("👋 Gelişmiş Background Worker durduruluyor...")
            break
        except Exception as e:
            logger.error(f"❌ Gelişmiş worker döngüsü hatası: {e}")
            logger.info("🔄 30 saniye sonra yeniden denenecek...")
            time.sleep(30)

if __name__ == '__main__':
    # Gelişmiş worker'ı başlat
    enhanced_worker_main() 