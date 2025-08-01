#!/usr/bin/env python3
"""
🚀 Asset Table Populator
75 kaliteli varlığı Asset tablosuna yükler
"""

import os
from web_app import app, db, Asset

def populate_assets():
    """4-tier sistem ile Asset tablosunu doldur"""
    print("🚀 Asset table populating başlatıldı...")
    
    # 4-Tier Quality Asset System
    assets_data = [
        # Forex (9 varlık)
        {'symbol': 'EURUSD', 'name': 'Euro/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'GBPUSD', 'name': 'British Pound/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'USDJPY', 'name': 'US Dollar/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'AUDUSD', 'name': 'Australian Dollar/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'USDCAD', 'name': 'US Dollar/Canadian Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'EURJPY', 'name': 'Euro/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'GBPJPY', 'name': 'British Pound/Japanese Yen', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'USDCHF', 'name': 'US Dollar/Swiss Franc', 'exchange': 'FOREX', 'asset_type': 'forex'},
        {'symbol': 'NZDUSD', 'name': 'New Zealand Dollar/US Dollar', 'exchange': 'FOREX', 'asset_type': 'forex'},
        
        # Crypto (4 varlık)
        {'symbol': 'BTCUSD', 'name': 'Bitcoin/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
        {'symbol': 'ETHUSD', 'name': 'Ethereum/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
        {'symbol': 'ADAUSD', 'name': 'Cardano/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
        {'symbol': 'DOTUSD', 'name': 'Polkadot/US Dollar', 'exchange': 'CRYPTO', 'asset_type': 'crypto'},
        
        # Tier 1: Major Tech (14 varlık)
        {'symbol': 'AAPL', 'name': 'Apple Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'META', 'name': 'Meta Platforms Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'ADBE', 'name': 'Adobe Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'NFLX', 'name': 'Netflix Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'CRM', 'name': 'Salesforce Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'INTC', 'name': 'Intel Corporation', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'CSCO', 'name': 'Cisco Systems Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        
        # Tier 2: Blue Chip Stocks (24 varlık)
        # Financials
        {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'BAC', 'name': 'Bank of America Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'WFC', 'name': 'Wells Fargo & Company', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'GS', 'name': 'Goldman Sachs Group Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'MS', 'name': 'Morgan Stanley', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'C', 'name': 'Citigroup Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'USB', 'name': 'U.S. Bancorp', 'exchange': 'NYSE', 'asset_type': 'stock'},
        
        # Healthcare  
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'PFE', 'name': 'Pfizer Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'ABBV', 'name': 'AbbVie Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'MRK', 'name': 'Merck & Co Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'UNH', 'name': 'UnitedHealth Group Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'CVS', 'name': 'CVS Health Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        
        # Consumer
        {'symbol': 'KO', 'name': 'Coca-Cola Company', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'PEP', 'name': 'PepsiCo Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'WMT', 'name': 'Walmart Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'HD', 'name': 'Home Depot Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'MCD', 'name': 'McDonald\'s Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'DIS', 'name': 'Walt Disney Company', 'exchange': 'NYSE', 'asset_type': 'stock'},
        
        # Energy
        {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'CVX', 'name': 'Chevron Corporation', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'COP', 'name': 'ConocoPhillips', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'SLB', 'name': 'Schlumberger Limited', 'exchange': 'NYSE', 'asset_type': 'stock'},
        
        # Fintech
        {'symbol': 'V', 'name': 'Visa Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'MA', 'name': 'Mastercard Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'SQ', 'name': 'Block Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        
        # Tier 3: Popular Growth Stocks (14 varlık) 
        {'symbol': 'ABNB', 'name': 'Airbnb Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'UBER', 'name': 'Uber Technologies Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'LYFT', 'name': 'Lyft Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'SNAP', 'name': 'Snap Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'TWTR', 'name': 'Twitter Inc', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'ZM', 'name': 'Zoom Video Communications Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'ROKU', 'name': 'Roku Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'SNOW', 'name': 'Snowflake Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'PLTR', 'name': 'Palantir Technologies Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'COIN', 'name': 'Coinbase Global Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'RBLX', 'name': 'Roblox Corporation Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'CRWD', 'name': 'CrowdStrike Holdings Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'NET', 'name': 'Cloudflare Inc Class A', 'exchange': 'NYSE', 'asset_type': 'stock'},
        {'symbol': 'DDOG', 'name': 'Datadog Inc Class A', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        
        # Tier 4: ETFs (7 varlık)
        {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'exchange': 'NYSE ARCA', 'asset_type': 'stock'},
        {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust Series 1', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
        {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF', 'exchange': 'NYSE ARCA', 'asset_type': 'stock'},
        {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'exchange': 'NYSE ARCA', 'asset_type': 'stock'},
        {'symbol': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'exchange': 'NYSE ARCA', 'asset_type': 'stock'},
        {'symbol': 'ARKK', 'name': 'ARK Innovation ETF', 'exchange': 'NYSE ARCA', 'asset_type': 'stock'},
        {'symbol': 'TQQQ', 'name': 'ProShares UltraPro QQQ', 'exchange': 'NASDAQ', 'asset_type': 'stock'},
    ]
    
    with app.app_context():
        # Önceki asset'leri temizle
        Asset.query.delete()
        db.session.commit()
        
        # Yeni asset'leri ekle
        for asset_data in assets_data:
            asset = Asset(
                symbol=asset_data['symbol'],
                name=asset_data['name'],
                exchange=asset_data['exchange'],
                asset_type=asset_data['asset_type'],
                is_active=True
            )
            db.session.add(asset)
        
        db.session.commit()
        
        # Sonuçları göster
        forex_count = Asset.query.filter_by(asset_type='forex').count()
        stock_count = Asset.query.filter_by(asset_type='stock').count()
        crypto_count = Asset.query.filter_by(asset_type='crypto').count()
        total_count = Asset.query.count()
        
        print(f"✅ Asset table populated successfully!")
        print(f"   📊 Forex: {forex_count}")
        print(f"   📈 Stocks: {stock_count}")  
        print(f"   💰 Crypto: {crypto_count}")
        print(f"   🔢 TOTAL: {total_count}")

if __name__ == '__main__':
    print("🚀 4-Tier Asset System Populator")
    print("=" * 50)
    populate_assets()
    print("🎉 Complete!") 