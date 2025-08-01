#!/usr/bin/env python3
"""
🎯 Alpha Vantage Smart Asset Filter
Listing_status.csv'den kaliteli varlıkları filtreler ve database'e kaydeder.

📊 Filtreleme Kriterleri:
- Status: Active (delisted olanlar dahil değil)
- AssetType: Stock (ETF'ler dahil değil)  
- Exchange: NYSE, NASDAQ (büyük borsalar)
- Son 5 yılda IPO (güncel şirketler)
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from web_app import app, db, User, Watchlist, CachedData, CorrelationCache

# Yeni Asset modeli için import
from sqlalchemy import Column, Integer, String, DateTime, Boolean

class Asset(db.Model):
    """Filtrelenmiş yüksek kaliteli varlık listesi"""
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    exchange = Column(String(50), nullable=False)
    asset_type = Column(String(20), nullable=False)  # 'forex', 'stock', 'crypto'
    ipo_date = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Asset {self.symbol}: {self.name} ({self.exchange})>'

def load_and_filter_assets():
    """listing_status.csv'den kaliteli varlıkları filtreler"""
    print("📊 listing_status.csv yükleniyor...")
    
    # CSV dosyasını oku
    df = pd.read_csv('listing_status.csv')
    print(f"🔢 Toplam varlık sayısı: {len(df):,}")
    
    # Filtreleme adımları
    print("\n🔍 Filtreleme aşamaları:")
    
    # Adım 1: Sadece aktif varlıklar
    active_df = df[df['status'] == 'Active']
    print(f"1️⃣ Aktif varlıklar: {len(active_df):,} ({len(active_df)/len(df)*100:.1f}%)")
    
    # Adım 2: Sadece hisse senetleri (ETF'ler dahil değil)
    stocks_df = active_df[active_df['assetType'] == 'Stock']
    print(f"2️⃣ Sadece hisseler: {len(stocks_df):,} ({len(stocks_df)/len(active_df)*100:.1f}%)")
    
    # Adım 3: Büyük borsalar (NYSE, NASDAQ)
    major_exchanges = ['NYSE', 'NASDAQ']
    major_df = stocks_df[stocks_df['exchange'].isin(major_exchanges)]
    print(f"3️⃣ Büyük borsalar: {len(major_df):,} ({len(major_df)/len(stocks_df)*100:.1f}%)")
    
    # Adım 4: Son 10 yılda IPO (eski şirketleri de dahil et, daha geniş havuz için)
    cutoff_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    
    # IPO tarihini datetime'a çevir, hatalı olanları None yap
    def parse_date(date_str):
        try:
            if pd.isna(date_str) or date_str == 'null':
                return None
            return pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except:
            return None
    
    major_df = major_df.copy()
    major_df['parsed_ipo'] = major_df['ipoDate'].apply(parse_date)
    
    # Son 10 yılda IPO olanlar VEYA IPO tarihi bilinmeyenler (eski köklü şirketler)
    recent_df = major_df[
        (major_df['parsed_ipo'].isna()) |  # Eski şirketler (tarih bilinmiyor)
        (major_df['parsed_ipo'] >= cutoff_date)  # Son 10 yıl
    ]
    print(f"4️⃣ Son 10 yıl + eski şirketler: {len(recent_df):,} ({len(recent_df)/len(major_df)*100:.1f}%)")
    
    # Adım 5: Sembol uzunluğu <= 5 (karmaşık türevleri filtrele)
    clean_df = recent_df[recent_df['symbol'].str.len() <= 5]
    print(f"5️⃣ Temiz semboller (≤5 karakter): {len(clean_df):,} ({len(clean_df)/len(recent_df)*100:.1f}%)")
    
    # Adım 6: Bilinen problemli sembolleri çıkar
    exclude_patterns = ['-', '.', ' ', 'WS', 'RT', 'WT', 'U']  # Warrants, Rights, Units
    for pattern in exclude_patterns:
        before_count = len(clean_df)
        clean_df = clean_df[~clean_df['symbol'].str.contains(pattern, na=False)]
        after_count = len(clean_df)
        if before_count != after_count:
            print(f"   📝 '{pattern}' içerenler çıkarıldı: -{before_count-after_count:,}")
    
    print(f"\n✅ FINAL FİLTRELENMİŞ LİSTE: {len(clean_df):,} kaliteli hisse senedi")
    
    return clean_df

def save_to_database(filtered_df):
    """Filtrelenmiş varlıkları database'e kaydet"""
    print(f"\n💾 {len(filtered_df):,} varlık database'e kaydediliyor...")
    
    with app.app_context():
        # Önceki varlıkları temizle
        Asset.query.delete()
        
        # Manuel olarak kaliteli forex ve crypto'ları ekle (Alpha Vantage desteklediğini bildiğimiz)
        manual_assets = [
            # Forex (Major pairs)
            {'symbol': 'EURUSD', 'name': 'Euro/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'GBPUSD', 'name': 'British Pound/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'USDJPY', 'name': 'US Dollar/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'AUDUSD', 'name': 'Australian Dollar/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'USDCAD', 'name': 'US Dollar/Canadian Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'EURJPY', 'name': 'Euro/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'GBPJPY', 'name': 'British Pound/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'USDCHF', 'name': 'US Dollar/Swiss Franc', 'exchange': 'FOREX', 'asset_type': 'forex'},
            {'symbol': 'NZDUSD', 'name': 'New Zealand Dollar/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
            
            # Crypto (Major coins)
            {'symbol': 'BTCUSD', 'name': 'Bitcoin/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
            {'symbol': 'ETHUSD', 'name': 'Ethereum/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
            {'symbol': 'ADAUSD', 'name': 'Cardano/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
            {'symbol': 'DOTUSD', 'name': 'Polkadot/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
        ]
        
        # Manuel varlıkları ekle
        for asset_data in manual_assets:
            asset = Asset(
                symbol=asset_data['symbol'],
                name=asset_data['name'],
                exchange=asset_data['exchange'],
                asset_type=asset_data['asset_type'],
                ipo_date=None,
                is_active=True
            )
            db.session.add(asset)
        
        # Filtrelenmiş hisse senetlerini ekle (top 200 sadece - performans için)
        top_stocks = filtered_df.head(200)  # Top 200 kaliteli hisse
        
        added_count = 0
        for _, row in top_stocks.iterrows():
            asset = Asset(
                symbol=row['symbol'],
                name=row['name'],
                exchange=row['exchange'],
                asset_type='stock',
                ipo_date=row.get('ipoDate'),
                is_active=True
            )
            db.session.add(asset)
            added_count += 1
        
        db.session.commit()
        
        total_assets = Asset.query.count()
        print(f"✅ Database'e kaydedildi:")
        print(f"   📊 Forex: {len([a for a in manual_assets if a['asset_type']=='forex'])}")
        print(f"   💰 Crypto: {len([a for a in manual_assets if a['asset_type']=='crypto'])}")
        print(f"   📈 Stocks: {added_count}")
        print(f"   🔢 TOPLAM: {total_assets}")

def update_constants():
    """constants.py'yi database tabanlı hale getir"""
    print("\n🔄 constants.py güncelleniyor...")
    
    constants_content = '''"""
🎯 Alpha Vantage Trading Framework - Constants  
Uygulama genelinde kullanılacak sabitleri ve konfigürasyonları saklar.

⚡ AVAILABLE_ASSETS artık database'den dinamik olarak okunuyor!
"""

# Korelasyon hesaplama konfigürasyonu
CORRELATION_CONFIG = {
    'update_interval_hours': 24,  # Günde bir korelasyon güncelleme
    'historical_days': 90,        # 90 günlük veri ile korelasyon hesapla
    'min_data_points': 50,        # Minimum veri noktası
    'timeframe': '15m',           # 15 dakikalık periyot
    'correlation_threshold': 0.3  # Minimum anlamlı korelasyon
}

def get_available_assets():
    """Database'den aktif varlıkları dinamik olarak al"""
    from web_app import app, Asset
    
    with app.app_context():
        # Asset type'a göre grupla
        forex_assets = Asset.query.filter_by(asset_type='forex', is_active=True).all()
        stock_assets = Asset.query.filter_by(asset_type='stock', is_active=True).all()  
        crypto_assets = Asset.query.filter_by(asset_type='crypto', is_active=True).all()
        
        return {
            'forex': [asset.symbol for asset in forex_assets],
            'stocks': [asset.symbol for asset in stock_assets],
            'crypto': [asset.symbol for asset in crypto_assets]
        }

# Backward compatibility için
AVAILABLE_ASSETS = get_available_assets()
'''
    
    with open('constants.py', 'w', encoding='utf-8') as f:
        f.write(constants_content)
    
    print("✅ constants.py dinamik asset loading'e güncellendi!")

def main():
    """Ana filtreleme ve güncelleme süreci"""
    print("🚀 Alpha Vantage Smart Asset Filter başlatıldı")
    print("=" * 60)
    
    # Database'i hazırla
    with app.app_context():
        db.create_all()
        print("✅ Database tablolar hazır!")
    
    # 1. CSV'den kaliteli varlıkları filtrele
    filtered_assets = load_and_filter_assets()
    
    # 2. Database'e kaydet
    save_to_database(filtered_assets)
    
    # 3. Constants.py'yi güncelle
    update_constants()
    
    print("\n🎉 Smart Asset Filter tamamlandı!")
    print("🔄 Worker restart edildiğinde yeni varlık listesi kullanılacak.")

if __name__ == '__main__':
    main() 