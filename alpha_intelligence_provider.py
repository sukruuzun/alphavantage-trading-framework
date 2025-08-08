#!/usr/bin/env python3
"""
🧠 Alpha Intelligence™ Provider
Advanced market intelligence features using Alpha Vantage Premium APIs

📊 Features:
- Top Gainers & Losers
- Insider Transactions  
- Earnings Call Transcripts
- Analytics (Fixed & Sliding Window)
- Earnings Calendar & IPO Calendar
"""

import requests
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from constants import API_CONFIG

class AlphaIntelligenceProvider:
    """
    🧠 Alpha Intelligence™ Premium Features
    
    Based on Alpha Vantage documentation:
    https://www.alphavantage.co/documentation/
    """
    
    def __init__(self, api_key: str, is_premium: bool = True):
        self.api_key = api_key
        self.is_premium = is_premium
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.alphavantage.co/query"
        self.last_call_time = 0
        
        if not self.is_premium:
            self.logger.warning("⚠️ Alpha Intelligence features require Premium subscription")
    
    def _rate_limit(self):
        """Premium rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        min_interval = 1.2 if self.is_premium else 12  # Premium: 75/min, Free: 5/min
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def get_top_gainers_losers(self) -> Dict:
        """
        📈 Top Gainers & Losers
        Real-time market movers
        """
        if not self.is_premium:
            return {'error': 'Premium subscription required'}
        
        self._rate_limit()
        
        try:
            params = {
                'function': 'TOP_GAINERS_LOSERS',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data["Error Message"])
            
            return {
                'top_gainers': data.get('top_gainers', [])[:10],
                'top_losers': data.get('top_losers', [])[:10],
                'most_actively_traded': data.get('most_actively_traded', [])[:10],
                'last_updated': data.get('last_updated', datetime.now().isoformat())
            }
            
        except Exception as e:
            self.logger.error(f"❌ Top gainers/losers error: {e}")
            return {'error': str(e)}
    
    def get_insider_transactions(self, symbol: str) -> Dict:
        """
        🏛️ Insider Transactions
        Corporate insider trading activity
        """
        if not self.is_premium:
            return {'error': 'Premium subscription required'}
        
        self._rate_limit()
        
        try:
            params = {
                'function': 'INSIDER_TRANSACTIONS',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data["Error Message"])
            
            transactions = data.get('data', [])
            
            # Analyze insider activity
            recent_transactions = [t for t in transactions if 
                                 datetime.strptime(t.get('transaction_date', '1900-01-01'), '%Y-%m-%d') 
                                 > datetime.now() - timedelta(days=90)]
            
            buy_volume = sum([float(t.get('acquisition_or_disposition', '0')) 
                            for t in recent_transactions if t.get('transaction_type') == 'P'])
            sell_volume = sum([float(t.get('acquisition_or_disposition', '0')) 
                             for t in recent_transactions if t.get('transaction_type') == 'S'])
            
            insider_sentiment = 'bullish' if buy_volume > sell_volume else 'bearish' if sell_volume > buy_volume else 'neutral'
            
            return {
                'symbol': symbol,
                'recent_transactions': recent_transactions[:20],
                'insider_sentiment': insider_sentiment,
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'total_transactions': len(recent_transactions)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Insider transactions error for {symbol}: {e}")
            return {'error': str(e)}
    
    def get_earnings_calendar(self, horizon: str = '3month') -> Dict:
        """
        📅 Earnings Calendar
        Upcoming earnings announcements
        """
        self._rate_limit()
        
        try:
            params = {
                'function': 'EARNINGS_CALENDAR',
                'horizon': horizon,  # 3month, 6month, 12month
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            
            # Earnings calendar returns CSV format
            if response.headers.get('content-type', '').startswith('text/csv'):
                import io
                df = pd.read_csv(io.StringIO(response.text))
                
                # Convert to JSON format
                earnings_data = df.to_dict('records')
                
                # Filter upcoming earnings (next 30 days)
                upcoming = []
                for earning in earnings_data:
                    try:
                        report_date = pd.to_datetime(earning.get('reportDate'))
                        if report_date >= datetime.now() and report_date <= datetime.now() + timedelta(days=30):
                            upcoming.append(earning)
                    except:
                        continue
                
                return {
                    'upcoming_earnings': upcoming[:50],
                    'total_count': len(earnings_data),
                    'horizon': horizon
                }
            else:
                data = response.json()
                if "Error Message" in data:
                    raise ValueError(data["Error Message"])
                return data
                
        except Exception as e:
            self.logger.error(f"❌ Earnings calendar error: {e}")
            return {'error': str(e)}
    
    def get_ipo_calendar(self) -> Dict:
        """
        🚀 IPO Calendar
        Upcoming Initial Public Offerings
        """
        self._rate_limit()
        
        try:
            params = {
                'function': 'IPO_CALENDAR',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            
            # IPO calendar returns CSV format
            if response.headers.get('content-type', '').startswith('text/csv'):
                import io
                df = pd.read_csv(io.StringIO(response.text))
                
                ipo_data = df.to_dict('records')
                
                # Filter upcoming IPOs
                upcoming_ipos = []
                for ipo in ipo_data:
                    try:
                        ipo_date = pd.to_datetime(ipo.get('ipoDate'))
                        if ipo_date >= datetime.now():
                            upcoming_ipos.append(ipo)
                    except:
                        continue
                
                return {
                    'upcoming_ipos': upcoming_ipos[:20],
                    'total_count': len(ipo_data)
                }
            else:
                data = response.json()
                if "Error Message" in data:
                    raise ValueError(data["Error Message"])
                return data
                
        except Exception as e:
            self.logger.error(f"❌ IPO calendar error: {e}")
            return {'error': str(e)}
    
    def get_analytics_fixed_window(self, symbols: List[str], range_period: str = '1month') -> Dict:
        """
        📊 Analytics (Fixed Window)
        Statistical analysis over fixed time periods
        """
        if not self.is_premium:
            return {'error': 'Premium subscription required'}
        
        self._rate_limit()
        
        try:
            params = {
                'function': 'ANALYTICS_FIXED_WINDOW',
                'SYMBOLS': ','.join(symbols),
                'RANGE': range_period,  # 1day, 7day, 1month, 3month, etc.
                'OHLC': 'close',
                'CALCULATIONS': 'MEAN,STDDEV,MIN,MAX',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data["Error Message"])
            
            return {
                'symbols': symbols,
                'range_period': range_period,
                'analytics': data.get('payload', {}),
                'calculation_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Analytics fixed window error: {e}")
            return {'error': str(e)}

# Integration with main web app
def integrate_alpha_intelligence():
    """
    🔗 Web app integration function
    """
    return {
        'market_movers_endpoint': '/api/market-movers',
        'insider_activity_endpoint': '/api/insider/<symbol>',
        'earnings_calendar_endpoint': '/api/earnings-calendar',
        'ipo_calendar_endpoint': '/api/ipo-calendar',
        'analytics_endpoint': '/api/analytics/<symbols>'
    } 