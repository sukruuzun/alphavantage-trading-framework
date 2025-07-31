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
from web_app import app, db, User, Watchlist, CachedData
from alphavantage_provider import AlphaVantageProvider
from universal_trading_framework import UniversalTradingBot, AssetType

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

            # Available assets tanımla (web_app.py'den kopyala)
            AVAILABLE_ASSETS = {
                'forex': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURGBP'],
                'stocks': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'SPY', 'QQQ'],
                'crypto': ['BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'LTCUSD', 'XRPUSD', 'SOLUSD']
            }

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
    
    # Database tablolarını oluştur (gerekirse)
    with app.app_context():
        db.create_all()
        logger.info("✅ Database tables ready!")
    
    while True:
        try:
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