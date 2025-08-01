#!/usr/bin/env python3
"""
🎯 Alpha Vantage Smart Asset Filter - LOCAL TEST VERSION
Listing_status.csv'den kaliteli varlıkları filtreler (database'e kaydetmeden).
"""

import pandas as pd
from datetime import datetime, timedelta

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
    
    # Adım 4: Son 10 yılda IPO (eski şirketleri de dahil et)
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
    
    # Adım 6: Sadece gerçekten problemli sembolleri çıkar
    
    # Warrants, Rights, Units sembollerini çıkar (ama . karakterini çıkarma!)
    warrant_patterns = ['WS', 'RT', 'WT']  # Warrants, Rights  
    for pattern in warrant_patterns:
        before_count = len(clean_df)
        clean_df = clean_df[~clean_df['symbol'].str.endswith(pattern)]
        after_count = len(clean_df)
        if before_count != after_count:
            print(f"   📝 '{pattern}' ile bitenler çıkarıldı: -{before_count-after_count:,}")
    
    # Tire içerenleri çıkar (karmaşık SPAC'ler)
    before_count = len(clean_df)
    clean_df = clean_df[~clean_df['symbol'].str.contains('-', na=False)]
    after_count = len(clean_df)
    if before_count != after_count:
        print(f"   📝 Tire (-) içerenler çıkarıldı: -{before_count-after_count:,}")
    
    # Boşluk içerenleri çıkar
    before_count = len(clean_df)
    clean_df = clean_df[~clean_df['symbol'].str.contains(' ', na=False)]
    after_count = len(clean_df)
    if before_count != after_count:
        print(f"   📝 Boşluk içerenler çıkarıldı: -{before_count-after_count:,}")
    
    # NOT: Nokta (.) karakterini çıkarmıyoruz çünkü BRK.A, BRK.B gibi meşru hisseler var
    
    print(f"\n✅ FINAL FİLTRELENMİŞ LİSTE: {len(clean_df):,} kaliteli hisse senedi")
    
    return clean_df

def show_sample_results(filtered_df):
    """Filtrelenmiş sonuçları göster"""
    print(f"\n📋 İLK 50 KALİTELİ HİSSE:")
    print("=" * 80)
    
    top_50 = filtered_df.head(50)
    for i, (_, row) in enumerate(top_50.iterrows(), 1):
        print(f"{i:2d}. {row['symbol']:5s} | {row['name'][:50]:50s} | {row['exchange']}")
    
    print(f"\n📊 EXCHANGE DAĞILIMI:")
    exchange_counts = filtered_df['exchange'].value_counts()
    for exchange, count in exchange_counts.items():
        print(f"   {exchange}: {count:,} hisse")
    
    # Önerilen TOP 200 listesi
    top_200 = filtered_df.head(200)['symbol'].tolist()
    
    print(f"\n🎯 ÖNERİLEN CONSTANTS.PY GÜNCELLEMESİ:")
    print("=" * 60)
    
    manual_assets = {
        'forex': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURJPY', 'GBPJPY', 'USDCHF', 'NZDUSD'],
        'crypto': ['BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD'],
        'stocks': top_200
    }
    
    print(f"AVAILABLE_ASSETS = {manual_assets}")
    
    print(f"\n📈 TOPLAM VARLIK SAYILARI:")
    print(f"   Forex: {len(manual_assets['forex'])}")
    print(f"   Crypto: {len(manual_assets['crypto'])}")
    print(f"   Stocks: {len(manual_assets['stocks'])}")
    print(f"   TOPLAM: {len(manual_assets['forex']) + len(manual_assets['crypto']) + len(manual_assets['stocks'])}")

def main():
    """Ana filtreleme süreci"""
    print("🚀 Alpha Vantage Smart Asset Filter - LOCAL TEST")
    print("=" * 60)
    
    # CSV'den kaliteli varlıkları filtrele
    filtered_assets = load_and_filter_assets()
    
    # Sonuçları göster
    show_sample_results(filtered_assets)
    
    print("\n🎉 Local test tamamlandı!")
    print("📝 Bu sonuçları constants.py'ye manuel olarak ekleyebilirsin.")

if __name__ == '__main__':
    main() 