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
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META',
        'ORCL', 'CRM', 'ADBE', 'NFLX', 'UBER'
    ],
    'crypto': [
        'BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'BNBUSD'
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