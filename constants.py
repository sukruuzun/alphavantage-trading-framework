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
        'V', 'MA', 'PYPL',                          # Fintech
        
        # Tier 3: Popular Growth Stocks  
        'ABNB', 'UBER', 'LYFT', 'SNAP', 'ZM', 'ROKU',
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

# API ve Worker konfigürasyonu
API_CONFIG = {
    'timeout': 20,                # API request timeout (seconds)
    'max_retries': 3,            # Maximum retry attempts
    'rate_limit_sleep': 1.5,     # Sleep between rate limited requests
    'batch_commit_size': 10,     # Database batch commit size
    'max_cache_size': 1000,      # Maximum cache entries
    'worker_sleep_interval': 300  # Worker sleep interval (5 minutes)
}

# Signal thresholds
SIGNAL_CONFIG = {
    'buy_threshold': 2,           # Minimum signals for BUY
    'sell_threshold': 2,          # Minimum signals for SELL
    'correlation_weight': 0.5,    # Correlation signal weight
    'sentiment_threshold': 0.3    # Sentiment signal threshold
} 