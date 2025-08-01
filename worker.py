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
from web_app import app, db, User, Watchlist, CachedData, CorrelationCache
from alphavantage_provider import AlphaVantageProvider
from universal_trading_framework import UniversalTradingBot, AssetType

# Import centralized constants
from constants import AVAILABLE_ASSETS, CORRELATION_CONFIG

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

def calculate_and_store_correlations(provider):
    """Tüm varlıklar için korelasyon matrisini hesaplar ve veritabanına kaydeder"""
    logger.info("📈 Dinamik korelasyon hesaplaması başlıyor...")
    
    # Tüm sembolleri topla
    all_symbols = (AVAILABLE_ASSETS['forex'] + 
                   AVAILABLE_ASSETS['stocks'] + 
                   AVAILABLE_ASSETS['crypto'])
    
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

            # Merkezi sistem API key kullan
            system_api_key = os.getenv('SYSTEM_ALPHA_VANTAGE_KEY')
            if not system_api_key:
                logger.error("❌ SYSTEM_ALPHA_VANTAGE_KEY environment variable bulunamadı!")
                return
                
            provider = AlphaVantageProvider(api_key=system_api_key, is_premium=True)
            logger.info(f"🔑 Sistem API key kullanılıyor: {system_api_key[:8]}...")

            # Tüm benzersiz sembolleri topla
            all_watchlist_items = Watchlist.query.all()
            unique_symbols = {item.symbol for item in all_watchlist_items}
            
            logger.info(f"🔄 {len(unique_symbols)} benzersiz varlık için veri çekilecek...")

            # Available assets artık constants.py'den import ediliyor (DRY principle)

            successful_updates = 0
            
            for symbol in unique_symbols:
                try:
                    logger.info(f"🔄 {symbol} verisi güncelleniyor...")
                    
                    # Current price al
                    price = provider.get_current_price(symbol)
                    
                    # Asset type belirle
                    asset_type = get_asset_type(symbol, AVAILABLE_ASSETS)
                    
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

                    # Database cache'e kaydet
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
                    
                    # Database'e commit
                    db.session.commit()
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} için veri çekilemedi: {e}")
                    # Hata durumunda database'e error kaydet
                    try:
                        cached_data = CachedData.query.filter_by(symbol=symbol).first()
                        if cached_data:
                            cached_data.error_message = str(e)
                            cached_data.last_updated = datetime.now()
                            db.session.commit()
                    except Exception as db_error:
                        logger.error(f"❌ Database error for {symbol}: {db_error}")
                        db.session.rollback()

            logger.info(f"✅ Veri güncelleme tamamlandı: {successful_updates}/{len(unique_symbols)} başarılı")
            
        except Exception as e:
            logger.error(f"❌ Genel güncelleme hatası: {e}")

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
                system_api_key = os.getenv('SYSTEM_ALPHA_VANTAGE_KEY')
                
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
                    logger.error("❌ SYSTEM_ALPHA_VANTAGE_KEY bulunamadı - korelasyon güncellenemiyor")
            
            # Normal veri güncelleme (her 5 dakika)
            update_data_for_all_users()
            logger.info("🕒 Sonraki güncelleme için 5 dakika bekleniyor...")
            time.sleep(300)  # 5 dakika
            
        except KeyboardInterrupt:
            logger.info("👋 Background Worker durduruluyor...")
            break
        except Exception as e:
            logger.error(f"❌ Worker döngüsü hatası: {e}")
            logger.info("🔄 30 saniye sonra yeniden denenecek...")
            time.sleep(30)

if __name__ == '__main__':
    main() 