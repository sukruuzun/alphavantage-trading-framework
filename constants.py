"""
🎯 Alpha Vantage Trading Framework - Constants
Uygulama genelinde kullanılacak sabitleri ve konfigürasyonları saklar.
"""

AVAILABLE_ASSETS = {
    'forex': [
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
        'EURJPY', 'GBPJPY', 'USDCHF', 'NZDUSD'
    ],
    'stocks': [
        # Tier 1: Major Tech (guaranteed Alpha Vantage support)
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META',
        'ORCL', 'ADBE', 'NFLX', 'CRM', 'INTC', 'AMD', 'CSCO',
        
        # Tier 2: Blue Chip Stocks (high liquidity)
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB',  # Financials
        'JNJ', 'PFE', 'ABBV', 'MRK', 'UNH', 'CVS',   # Healthcare  
        'KO', 'PEP', 'WMT', 'HD', 'MCD', 'DIS',      # Consumer
        'XOM', 'CVX', 'COP', 'SLB',                   # Energy
        'V', 'MA', 'PYPL', 'SQ',                      # Fintech
        
        # Tier 3: Popular Growth Stocks  
        'ABNB', 'UBER', 'LYFT', 'SNAP', 'TWTR', 'ZM', 'ROKU',
        'SNOW', 'PLTR', 'COIN', 'RBLX', 'CRWD', 'NET', 'DDOG',
        
        # Tier 4: ETFs (broad market exposure)
        'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'ARKK', 'TQQQ'
    ],
    'crypto': [
        'BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD'  # Tested and working
    ]
}

# Korelasyon hesaplama konfigürasyonu
CORRELATION_CONFIG = {
    'update_interval_hours': 24,  # Günde bir korelasyon güncelleme
    'historical_days': 90,        # 90 günlük veri ile korelasyon hesapla
    'min_data_points': 50,        # Minimum veri noktası
    'timeframe': '15m',           # 15 dakikalık periyot
    'correlation_threshold': 0.3  # Minimum anlamlı korelasyon
} 