#!/usr/bin/env python3
"""
🏛️ Alpha Vantage Tam Entegrasyon Provider
Haberler, Sentiment Analizi ve Piyasa Verileri

🚀 Özellikler:
- Forex, Stocks, Crypto, Commodities
- News & Sentiment Analysis 
- Economic Indicators
- Technical Indicators
- Real-time & Historical Data
"""

import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from alpha_vantage.techindicators import TechIndicators
from universal_trading_framework import DataProvider, AssetType, Signal
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

# Import for dynamic correlations  
from constants import CORRELATION_CONFIG, API_CONFIG

# Lazy import için app context
from functools import wraps

class AlphaVantageProvider(DataProvider):
    """
    🏛️ Alpha Vantage Tam Entegrasyon Provider
    
    📊 Veri Kaynakları:
    1. Forex Exchange Rates
    2. Stock Market Data  
    3. Cryptocurrency Prices
    4. News & Sentiment Analysis
    5. Economic Indicators
    6. Technical Indicators
    
    🧠 Akıllı Özellikler:
    - Sentiment-enhanced signals
    - News impact analysis
    - Economic calendar integration
    - Multi-timeframe analysis
    """
    
    def __init__(self, api_key: str = None, use_cache: bool = True, is_premium: bool = False):
        self.logger = logging.getLogger(__name__)
        
        # API Key
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_KEY')
        if not self.api_key:
            raise ValueError("⚠️ Alpha Vantage API anahtarı gerekli! https://www.alphavantage.co/support/#api-key")
        
        # Plan tipini belirle
        self.is_premium = is_premium
        
        # Alpha Vantage clients
        self.fx = ForeignExchange(key=self.api_key, output_format='pandas')
        self.ts = TimeSeries(key=self.api_key, output_format='pandas')
        self.crypto = CryptoCurrencies(key=self.api_key, output_format='pandas') 
        self.ti = TechIndicators(key=self.api_key, output_format='pandas')
        
        # Cache sistemi - Plan tipine göre ayarla
        self.use_cache = use_cache
        self.cache = {}
        self.max_cache_size = 1000  # Maximum cache entries to prevent memory leaks
        
        if self.is_premium:
            self.cache_duration = 60  # Premium: 1 dakika cache (daha sık güncelleme)
            self.call_interval = 1    # Premium: 1 saniye ara (75 calls/min)
            plan_info = "Premium Pro (Unlimited calls, 75/min)"
        else:
            self.cache_duration = 300  # Free: 5 dakika cache (rate limit koruması)
            self.call_interval = 12   # Free: 12 saniye ara (5 calls/min için güvenli)
            plan_info = "Free Plan (25 calls/day, 5/min)"
        
        # Rate limiting
        self.last_call_time = 0
        
        # Database-driven sembol mapping (artık statik değil)
        
        # Gerçek spread'ler
        self.spreads = {
            # Forex spreads (pip)
            "EURUSD": 0.8, "GBPUSD": 1.2, "USDJPY": 0.9, "AUDUSD": 1.5,
            "USDCAD": 1.8, "EURJPY": 2.1, "GBPJPY": 2.5, "USDCHF": 1.9, "NZDUSD": 2.2,
            
            # Stock spreads (points)
            "AAPL": 0.01, "GOOGL": 0.50, "MSFT": 0.01, "AMZN": 0.05, "TSLA": 0.02,
            "NVDA": 0.05, "META": 0.02,
            
            # Crypto spreads (USD)
            "BTCUSD": 10.0, "ETHUSD": 2.0, "ADAUSD": 0.001, "DOTUSD": 0.01,
        }
        
        # Korelasyon matrisi artık dinamik - Database'den okunuyor
        
        # Başlatma logları - DISABLED for Railway worker timeout prevention
        # self.logger.info(f"🏛️ Alpha Vantage Provider başlatıldı")
        # self.logger.info(f"📊 Dynamic asset loading from database")
        # self.logger.info(f"⚡ Plan: {plan_info}")
        # self.logger.info(f"🕐 Cache: {self.cache_duration}s, Rate limit: {self.call_interval}s")
        
    def _get_asset_info(self, symbol: str) -> Optional[Dict]:
        """Database'den asset bilgilerini dinamik olarak çek"""
        try:
            # Lazy import to avoid circular imports
            from web_app import app, Asset
            
            with app.app_context():
                asset = Asset.query.filter_by(symbol=symbol, is_active=True).first()
                
                if not asset:
                    return None
                
                # Asset type'a göre mapping bilgileri oluştur
                if asset.asset_type == 'forex':
                    # Forex sembolleri için from/to para birimlerini parse et
                    if len(symbol) == 6:  # EURUSD format
                        from_curr, to_curr = symbol[:3], symbol[3:]
                        return {
                            'from': from_curr,
                            'to': to_curr, 
                            'type': 'forex',
                            'name': asset.name,
                            'exchange': asset.exchange
                        }
                elif asset.asset_type in ['stock', 'stocks']:  # Support both formats for compatibility
                    return {
                        'symbol': symbol,
                        'name': asset.name,
                        'type': 'stock',
                        'exchange': asset.exchange
                    }
                elif asset.asset_type == 'crypto':
                    # Crypto sembolleri için base currency parse et
                    if symbol.endswith('USD'):
                        base_currency = symbol.replace('USD', '')
                        return {
                            'symbol': base_currency,
                            'market': 'USD',
                            'type': 'crypto',
                            'name': asset.name,
                            'exchange': asset.exchange
                        }
                
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Database asset info error for {symbol}: {e}")
            return None
        
    def _rate_limit(self):
        """Dynamic Rate limiting - Plan tipine göre"""
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        
        if time_since_last < self.call_interval:
            sleep_time = self.call_interval - time_since_last
            if sleep_time > 0.1:  # Sadece 100ms'den fazla beklemeler için log
                plan_type = "Premium" if self.is_premium else "Free"
                self.logger.debug(f"⏱️ {plan_type} rate limit - {sleep_time:.1f}s bekleniyor...")
            
            # Maximum sleep time protection (avoid infinite waits)
            sleep_time = min(sleep_time, 30.0)  # Max 30 seconds wait
            time.sleep(sleep_time)
            
        self.last_call_time = time.time()
        
    def _get_cache_key(self, data_type: str, symbols: str = 'global') -> str:
        """Cache anahtarı - Collision-resistant format"""
        timestamp_bucket = int(time.time() / self.cache_duration)
        # Add API key hash to prevent cross-account cache pollution
        api_hash = hash(self.api_key) % 10000 if self.api_key else 0
        return f"{data_type}_{symbols}_{timestamp_bucket}_{api_hash}"
        
    def _is_cache_valid(self, key: str) -> bool:
        """Cache geçerli mi"""
        return key in self.cache and time.time() - self.cache[key]['timestamp'] < self.cache_duration
    
    def _cleanup_cache(self):
        """Cache cleanup to prevent memory leaks"""
        if len(self.cache) > self.max_cache_size:
            current_time = time.time()
            # Remove expired entries first
            expired_keys = [k for k, v in self.cache.items() 
                          if current_time - v['timestamp'] > self.cache_duration]
            for key in expired_keys:
                del self.cache[key]
            
            # If still too many entries, remove oldest ones
            if len(self.cache) > self.max_cache_size:
                sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
                excess_count = len(self.cache) - self.max_cache_size + 100  # Keep some buffer
                for key, _ in sorted_items[:excess_count]:
                    del self.cache[key]
                self.logger.debug(f"🧹 Cache cleanup: Removed {excess_count} old entries")
        
    def get_current_price(self, symbol: str) -> float:
        """Güncel fiyat al - Premium real-time (Database-driven)"""
        cache_key = self._get_cache_key('price', symbol)
        
        if self.use_cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        # Database'den asset bilgilerini al
        symbol_info = self._get_asset_info(symbol)
        if not symbol_info:
            raise ValueError(f"❌ {symbol} desteklenmiyor veya database'de bulunamadı")
            
        self._rate_limit()
        
        try:
            if symbol_info['type'] == 'forex':
                data, _ = self.fx.get_currency_exchange_rate(
                    from_currency=symbol_info['from'],
                    to_currency=symbol_info['to']
                )
                price = float(data['5. Exchange Rate'].iloc[0])
                
            elif symbol_info['type'] == 'stock':
                # 🚀 PREMIUM REAL-TIME: Use intraday 1min for latest price
                if self.is_premium:
                    # Premium: Real-time intraday data (1-minute interval)
                    data, _ = self.ts.get_intraday(
                        symbol=symbol_info['symbol'], 
                        interval='1min', 
                        outputsize='compact'  # Only last 100 data points
                    )
                    # Get the most recent price (first entry)
                    latest_timestamp = data.index[0]
                    price = float(data['4. close'].iloc[0])
                else:
                    # Free: Delayed quote endpoint (15-20 min delay)
                    data, _ = self.ts.get_quote_endpoint(symbol=symbol_info['symbol'])
                    price = float(data['05. price'].iloc[0])
                
            elif symbol_info['type'] == 'crypto':
                # 🚀 PREMIUM REAL-TIME: Use intraday 1min for crypto
                if self.is_premium:
                    # Premium: Real-time crypto intraday data (1-minute interval)
                    data, _ = self.crypto.get_digital_currency_intraday(
                        symbol=symbol_info['symbol'], 
                        market=symbol_info['market'],
                        interval='1min'
                    )
                    # Get the most recent price (first entry)
                    price = float(data['4b. close (USD)'].iloc[0])
                else:
                    # Free: Exchange rate (may have delay)
                    data, _ = self.crypto.get_digital_currency_exchange_rate(
                        from_currency=symbol_info['symbol'],
                        to_currency=symbol_info['market']
                    )
                    price = float(data['5. Exchange Rate'].iloc[0])
                
            else:
                raise ValueError(f"Bilinmeyen tip: {symbol_info['type']}")
                
            # Cache'e kaydet
            if self.use_cache:
                self._cleanup_cache()  # Prevent memory leaks
                self.cache[cache_key] = {
                    'data': price,
                    'timestamp': time.time()
                }
                
            data_type = "real-time" if self.is_premium else "delayed"
            self.logger.debug(f"💰 {symbol}: {price} ({data_type})")
            return price
            
        except requests.exceptions.Timeout:
            self.logger.error(f"❌ {symbol} fiyat hatası: API timeout")
            raise ValueError(f"API timeout for {symbol}")
        except requests.exceptions.ConnectionError:
            self.logger.error(f"❌ {symbol} fiyat hatası: Network connection error")
            raise ValueError(f"Network error for {symbol}")
        except KeyError as e:
            self.logger.error(f"❌ {symbol} fiyat hatası: API response format error - {e}")
            raise ValueError(f"Invalid API response format for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ {symbol} fiyat hatası: {e}")
            raise
                
    def get_news_sentiment(self, symbols: List[str] = None, limit: int = 50) -> Dict:
        """
        📰 Haberler ve Sentiment Analizi - Premium real-time
        
        Returns:
        {
            'overall_sentiment': float,  # -1 (negatif) ile +1 (pozitif) arası
            'news_count': int,
            'sentiment_breakdown': Dict,
            'top_news': List[Dict]
        }
        """
        # ✅ CRITICAL FIX: Include symbols in cache key!
        symbols_str = ','.join(sorted(symbols)) if symbols else 'global'
        cache_key = self._get_cache_key('news', symbols_str)
        
        if self.use_cache and self._is_cache_valid(cache_key):
            self.logger.debug(f"📋 Cache hit: sentiment for {symbols_str}")
            return self.cache[cache_key]['data']
            
        self._rate_limit()
        
        try:
            # Alpha Vantage News & Sentiment API (Official Documentation)
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.api_key,
                'limit': min(limit, 1000)  # API max limit is 1000
            }
            
            if symbols:
                # DÜZELTME: Alpha Vantage docs'a göre 'tickers' parametresi doğru
                params['tickers'] = ','.join(symbols)
                # Premium plan için ek parametreler
                if self.is_premium:
                    params['sort'] = 'LATEST'  # Premium: Sort by latest
                    params['time_from'] = (datetime.now() - timedelta(days=7)).strftime('%Y%m%dT%H%M')
                self.logger.debug(f"📰 Fetching sentiment for: {symbols}")
            else:
                self.logger.debug("📰 Fetching global sentiment")
                
            response = requests.get(url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()  # HTTP hatalarını yakala (4xx, 5xx)
            data = response.json()
            
            # Alpha Vantage API error handling (based on official documentation)
            if "Error Message" in data:
                error_msg = data["Error Message"]
                self.logger.error(f"❌ Alpha Vantage API Error: {error_msg}")
                if "Invalid API call" in error_msg:
                    raise ValueError(f"Invalid API call for {symbols_str}: {error_msg}")
                elif "API call frequency" in error_msg:
                    raise ValueError(f"Rate limit exceeded: {error_msg}")
                else:
                    raise ValueError(f"API Error: {error_msg}")
            
            if "Information" in data:
                info_msg = data["Information"]
                self.logger.warning(f"⚠️ Alpha Vantage API Info: {info_msg}")
                if "call frequency" in info_msg.lower():
                    raise ValueError(f"Rate limit: {info_msg}")
                return self._empty_sentiment()
            
            if 'feed' not in data:
                self.logger.warning(f"⚠️ '{symbols_str}' için haber bulunamadı (API boş feed döndürdü).")
                self.logger.debug(f"🚨 RAW API Response keys: {list(data.keys())}")
                # Check if it's a valid response but with no news
                if 'items' in data and len(data['items']) == 0:
                    return self._empty_sentiment()
                return self._empty_sentiment()
                
            news_feed = data['feed']
            
            # Sentiment analizi
            sentiments = []
            sentiment_counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            top_news = []
            
            for news in news_feed[:limit]:
                try:
                    # Overall sentiment
                    overall_sentiment = news.get('overall_sentiment_score', 0)
                    sentiments.append(float(overall_sentiment))
                    
                    # Sentiment label
                    sentiment_label = news.get('overall_sentiment_label', 'neutral').lower()
                    if sentiment_label in sentiment_counts:
                        sentiment_counts[sentiment_label] += 1
                    else:
                        sentiment_counts['neutral'] += 1
                        
                    # Top news
                    if len(top_news) < 10:
                        top_news.append({
                            'title': news.get('title', '')[:100],
                            'summary': news.get('summary', '')[:200],
                            'sentiment_score': float(overall_sentiment),
                            'sentiment_label': sentiment_label,
                            'time_published': news.get('time_published', ''),
                            'relevance_score': news.get('relevance_score', 0)
                        })
                        
                except (ValueError, KeyError):
                    continue
                    
            # Genel sentiment hesapla
            if sentiments:
                overall_sentiment = np.mean(sentiments)
            else:
                overall_sentiment = 0.0
                
            result = {
                'overall_sentiment': overall_sentiment,
                'news_count': len(news_feed),
                'sentiment_breakdown': sentiment_counts,
                'top_news': top_news,
                'last_updated': datetime.now().isoformat()
            }
            
            # Cache'e kaydet
            if self.use_cache:
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
                
            # self.logger.info(f"📰 {len(news_feed)} haber analiz edildi - Sentiment: {overall_sentiment:.3f}")  # Disabled for Railway
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ağ Hatası (Haber): {e}")
            return self._empty_sentiment()
        except Exception as e:
            self.logger.warning(f"❌ '{symbols_str}' için haber verisi işlenemedi. Hata: {e}")
            # EN ÖNEMLİ KISIM: Hatalı yanıtın ham metnini logla
            if 'response' in locals():
                self.logger.error(f"🚨 RAW API Response Text: {response.text}")
            return self._empty_sentiment()
                        
    def _empty_sentiment(self) -> Dict:
        """Boş sentiment verisi"""
        return {
            'overall_sentiment': 0.0,
            'news_count': 0,
            'sentiment_breakdown': {'bullish': 0, 'bearish': 0, 'neutral': 0},
            'top_news': [],
            'last_updated': datetime.now().isoformat()
        }
        
    def get_correlation_signal(self, primary_symbol: str, tech_signal: Signal) -> Signal:
        """
        DİNAMİK Korelasyon + Sentiment bazlı sinyal
        
        ✅ YENİ: Korelasyon matrisi gerçek piyasa verisiyle hesaplanıyor
        ✅ Veritabanından dinamik korelasyon okuma
        ✅ 90 günlük tarihsel veriye dayalı korelasyonlar
        """
        try:
            # Lazy import to avoid circular imports
            from web_app import app, CorrelationCache
            
            correlation_score = 0
            correlation_count = 0
            
            # 1. Veritabanından dinamik korelasyonları çek
            with app.app_context():
                # primary_symbol'ün hem symbol_1 hem de symbol_2 olabileceği durumları sorgula
                correlations = CorrelationCache.query.filter(
                    (CorrelationCache.symbol_1 == primary_symbol) | 
                    (CorrelationCache.symbol_2 == primary_symbol)
                ).filter(
                    func.abs(CorrelationCache.correlation_value) >= CORRELATION_CONFIG['correlation_threshold']
                ).all()

            if not correlations:
                self.logger.debug(f"🔍 {primary_symbol} için anlamlı korelasyon verisi bulunamadı (threshold: {CORRELATION_CONFIG['correlation_threshold']})")
                # Korelasyon verisi yoksa sadece sentiment kullan
                return self._sentiment_only_signal(primary_symbol)

            # 2. Korelasyon skorunu hesapla
            for corr_pair in correlations:
                # Diğer sembolü ve korelasyon değerini al
                other_symbol = corr_pair.symbol_2 if corr_pair.symbol_1 == primary_symbol else corr_pair.symbol_1
                corr_value = corr_pair.correlation_value
                
                # Diğer sembolün trend'ini al
                other_trend = self._get_cached_price_trend(other_symbol)
                correlation_score += corr_value * other_trend
                correlation_count += 1
                
                self.logger.debug(f"📊 {primary_symbol} ↔ {other_symbol}: {corr_value:.3f} (trend: {other_trend:.2f})")
                    
            # 3. Sentiment analizi (sadece stocks için)
            sentiment_score = 0
            primary_asset_info = self._get_asset_info(primary_symbol)
            if primary_asset_info and primary_asset_info.get('type') == 'stock':
                try:
                    sentiment_data = self.get_news_sentiment([primary_symbol], limit=15)
                    sentiment_score = sentiment_data['overall_sentiment']
                    self.logger.debug(f"📰 {primary_symbol} sentiment: {sentiment_score:.3f}")
                except:
                    sentiment_score = 0
                    
            # 4. Final karar (dinamik korelasyon + sentiment)
            if correlation_count > 0:
                avg_correlation = correlation_score / correlation_count
                # Korelasyona %70, sentiment'a %30 ağırlık ver
                combined_score = (avg_correlation * 0.7) + (sentiment_score * 0.3)
                
                if combined_score > 0.25:
                    return Signal.BUY
                elif combined_score < -0.25:
                    return Signal.SELL
                else:
                    return Signal.HOLD
            else:
                # Korelasyon yoksa sadece sentiment
                return self._sentiment_only_signal(primary_symbol)
                
        except Exception as e:
            self.logger.warning(f"⚠️ {primary_symbol} dinamik korelasyon hatası: {e}")
            return Signal.HOLD
    
    def _sentiment_only_signal(self, primary_symbol: str) -> Signal:
        """Sadece sentiment bazlı sinyal (korelasyon yoksa)"""
        try:
            primary_asset_info = self._get_asset_info(primary_symbol)
            if primary_asset_info and primary_asset_info.get('type') == 'stock':
                sentiment_data = self.get_news_sentiment([primary_symbol], limit=10)
                sentiment_score = sentiment_data['overall_sentiment']
                
                if sentiment_score > 0.3:
                    return Signal.BUY
                elif sentiment_score < -0.3:
                    return Signal.SELL
                else:
                    return Signal.HOLD
            else:
                return Signal.HOLD  # Non-stock assets without correlation
        except:
            return Signal.HOLD
            
    def _get_cached_price_trend(self, symbol: str) -> float:
        """
        Gerçek fiyat trendi (-1: düşüş, 0: yatay, +1: yükseliş) - Premium
        
        ⚠️ NOT: Bu fonksiyon kısmi simülasyon içerir:
        - Saatlik fiyat karşılaştırması: Gerçek cache verisinden
        - Geçmiş veri yoksa: Market sentiment'e dayalı tahmin (simülasyon)
        
        Gerçek trading için tam historical data analizi önerilir.
        """
        try:
            # Cache'den fiyat al veya gerçek fiyatı çek
            cache_key = self._get_cache_key('price', symbol)
            
            if self.use_cache and self._is_cache_valid(cache_key):
                current_price = self.cache[cache_key]['data']
            else:
                # Gerçek fiyatı al
                current_price = self.get_current_price(symbol)
                
            # Historical trend için saatlik fiyat karşılaştırması
            current_hour = int(time.time() / 3600)
            previous_hour = current_hour - 1
            
            # Önceki saat cache key'i düzgün format
            previous_hour_key = f"{symbol}_price_{previous_hour}"
            
            if previous_hour_key in self.cache:
                previous_price = self.cache[previous_hour_key]['data']
                change_pct = (current_price - previous_price) / previous_price
                
                if change_pct > 0.005:  # %0.5'ten fazla yükseliş
                    return 1.0
                elif change_pct < -0.005:  # %0.5'ten fazla düşüş
                    return -1.0
                else:
                    return 0.0
            else:
                # Geçmiş veri yoksa - saatlik cache'e mevcut fiyatı kaydet
                self.cache[f"{symbol}_price_{current_hour}"] = {
                    'data': current_price,
                    'timestamp': time.time()
                }
                
                # Market sentiment'e göre tahmin
                asset_info = self._get_asset_info(symbol)
                symbol_type = asset_info.get('type', 'unknown') if asset_info else 'unknown'
                
                if symbol_type == 'forex':
                    # USD pairs için basit market sentiment
                    if 'USD' in symbol and symbol.endswith('USD'):
                        return 0.1  # USD strength trend
                    elif symbol.startswith('USD'):
                        return -0.1  # USD weakness in inverse pairs
                    else:
                        return 0.0
                elif symbol_type == 'stock':
                    return 0.2  # Tech stocks genel pozitif trend
                elif symbol_type == 'crypto':
                    return 0.1  # Crypto genel pozitif trend ama volatile
                else:
                    return 0.0
                    
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} trend hesaplama hatası: {e}")
            return 0.0
            
    def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Historik veri al - Premium real-time"""
        cache_key = self._get_cache_key(f'hist_{timeframe}_{limit}', symbol)
        
        if self.use_cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        # Database'den asset bilgilerini al
        symbol_info = self._get_asset_info(symbol)
        if not symbol_info:
            raise ValueError(f"❌ {symbol} desteklenmiyor veya database'de bulunamadı")
            
        self._rate_limit()
        
        try:
            if symbol_info['type'] == 'forex':
                # Forex için intraday data (Volume yok)
                data, _ = self.fx.get_currency_exchange_intraday(
                    from_symbol=symbol_info['from'],
                    to_symbol=symbol_info['to'],
                    interval='1min',
                    outputsize='compact'
                )
                # Forex standardizasyonu: Volume ekle
                data = self._standardize_forex_data(data)
                
            elif symbol_info['type'] == 'stock':
                # Stock için intraday data (Volume var)
                data, _ = self.ts.get_intraday(
                    symbol=symbol_info['symbol'],
                    interval='1min',
                    outputsize='compact'
                )
                # Stock standardizasyonu
                data = self._standardize_stock_data(data)
                
            elif symbol_info['type'] == 'crypto':
                # Crypto için günlük data (Alpha Vantage intraday crypto yok)
                data, _ = self.crypto.get_digital_currency_daily(
                    symbol=symbol_info['symbol'],
                    market=symbol_info['market']
                )
                # Crypto standardizasyonu
                data = self._standardize_crypto_data(data)
                
            # Son N kayıt
            if not data.empty:
                data = data.head(limit)
                    
                # Cache'e kaydet
                if self.use_cache:
                    self.cache[cache_key] = {
                        'data': data.copy(),
                        'timestamp': time.time()
                    }
                    
                self.logger.debug(f"📈 {symbol} historik veri: {len(data)} kayıt")
                return data
            else:
                raise ValueError("Veri bulunamadı")
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} historik veri hatası: {e}")
            # Premium plan - no fallback, real data only
            raise
            
    def _standardize_forex_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Forex data standardizasyonu (Volume ekle)"""
        # Alpha Vantage forex format: '1. open', '2. high', '3. low', '4. close'
        standardized = pd.DataFrame({
            'Open': data['1. open'].astype(float),
            'High': data['2. high'].astype(float), 
            'Low': data['3. low'].astype(float),
            'Close': data['4. close'].astype(float),
            'Volume': 1000.0  # Forex için sabit volume (TA-Lib uyumluluğu için)
        }, index=data.index)
        
        return standardized.sort_index()
        
    def _standardize_stock_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Stock data standardizasyonu"""
        # Alpha Vantage stock format: '1. open', '2. high', '3. low', '4. close', '5. volume'
        standardized = pd.DataFrame({
            'Open': data['1. open'].astype(float),
            'High': data['2. high'].astype(float),
            'Low': data['3. low'].astype(float), 
            'Close': data['4. close'].astype(float),
            'Volume': data['5. volume'].astype(float)
        }, index=data.index)
        
        return standardized.sort_index()
        
    def _standardize_crypto_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Crypto data standardizasyonu"""
        # Alpha Vantage crypto günlük format - USD close price kullan
        close_col = None
        for col in data.columns:
            if 'close' in col.lower() and 'usd' in col.lower():
                close_col = col
                break
                
        if close_col is None:
            # İlk close kolunu kullan
            close_cols = [col for col in data.columns if 'close' in col.lower()]
            close_col = close_cols[0] if close_cols else data.columns[0]
            
        close_prices = data[close_col].astype(float)
        
        # OHLC simülasyonu (günlük data için)
        standardized = pd.DataFrame({
            'Open': close_prices,
            'High': close_prices * 1.02,  # %2 daily range simülasyonu
            'Low': close_prices * 0.98,
            'Close': close_prices,
            'Volume': 10000.0  # Crypto için sabit volume
        }, index=data.index)
        
        return standardized.sort_index()
        
    def get_spread(self, symbol: str) -> float:
        """Spread değeri"""
        return self.spreads.get(symbol, 2.0)
        
    def get_market_depth(self, symbol: str) -> Dict:
        """Market derinliği (simülasyon)"""
        current_price = self.get_current_price(symbol)
        spread = self.get_spread(symbol)
        
        bid = current_price - spread/2
        ask = current_price + spread/2
        
        return {
            'bids': [[bid, 100.0]],
            'asks': [[ask, 100.0]]
        }
        
    def get_available_symbols(self) -> List[str]:
        """Desteklenen semboller (Database-driven)"""
        try:
            from web_app import app, Asset
            with app.app_context():
                active_assets = Asset.query.filter_by(is_active=True).all()
                return [asset.symbol for asset in active_assets]
        except Exception as e:
            self.logger.error(f"❌ Error fetching available symbols: {e}")
            return []
        
    def get_provider_status(self) -> Dict:
        """Provider durumu - Dynamic plan info"""
        plan_name = "Premium Pro" if self.is_premium else "Free Plan"
        daily_limit = "Unlimited" if self.is_premium else "25 calls/day"
        
        return {
            'provider': f'Alpha Vantage {plan_name}',
            'status': 'active',
            'plan': plan_name,
            'is_premium': self.is_premium,
            'api_key': self.api_key[:8] + '...' if self.api_key else 'None',
            'cache_size': len(self.cache),
            'cache_duration': f'{self.cache_duration}s',
            'supported_symbols': len(self.get_available_symbols()),
            'rate_limit': f'{self.call_interval}s interval',
            'daily_limit': daily_limit,
            'features': [
                'Real-time prices',
                'Historical data', 
                f'News & Sentiment {"(Premium)" if self.is_premium else "(Limited)"}',
                'Technical indicators',
                'Correlation analysis',
                f'API calls: {"Unlimited" if self.is_premium else "25/day"}'
            ]
        } 