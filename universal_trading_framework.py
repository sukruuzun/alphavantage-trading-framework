# universal_trading_framework.py

import pandas as pd
import numpy as np
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import ta
from typing import Dict, List, Optional, Tuple
from enum import Enum

class AssetType(Enum):
    CRYPTO = "crypto"
    FOREX = "forex" 
    STOCKS = "stocks"
    COMMODITIES = "commodities"
    INDICES = "indices"

class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class DataProvider(ABC):
    """Soyut veri sağlayıcı sınıfı - farklı varlık türleri için implement edilecek"""
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Geçmiş verilerini alır"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Güncel fiyatı alır"""
        pass
    
    @abstractmethod
    def get_market_depth(self, symbol: str) -> Dict:
        """Market derinliği bilgisi alır"""
        pass

class TechnicalAnalyzer:
    """Teknik analiz motoru - orijinal koddan esinlenildi"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Temel teknik indikatörleri hesaplar"""
        try:
            # Hareketli ortalamalar
            df['EMA_5'] = ta.trend.EMAIndicator(close=df['Close'], window=5).ema_indicator()
            df['EMA_13'] = ta.trend.EMAIndicator(close=df['Close'], window=13).ema_indicator()
            df['EMA_50'] = ta.trend.EMAIndicator(close=df['Close'], window=50).ema_indicator()
            df['EMA_200'] = ta.trend.EMAIndicator(close=df['Close'], window=200).ema_indicator()
            
            # MACD
            df['MACD'] = ta.trend.MACD(close=df['Close']).macd()
            df['MACD_Signal'] = ta.trend.MACD(close=df['Close']).macd_signal()
            
            # RSI
            df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
            
            # Bollinger Bantları
            bb = ta.volatility.BollingerBands(close=df['Close'])
            df['BB_Upper'] = bb.bollinger_hband()
            df['BB_Lower'] = bb.bollinger_lband()
            df['BB_Middle'] = bb.bollinger_mavg()
            
            # ATR (Average True Range) - YENİ EKLEME
            df['ATR'] = ta.volatility.AverageTrueRange(
                high=df['High'], 
                low=df['Low'], 
                close=df['Close'], 
                window=14
            ).average_true_range()
            
            # Volume indikatörleri
            if 'Volume' in df.columns:
                df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            
            self.logger.debug("Teknik indikatörler hesaplandı")
            return df
            
        except Exception as e:
            self.logger.error(f"İndikatör hesaplama hatası: {e}")
            return df
    
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """Teknik analiz sinyali üretir - İyileştirilmiş threshold'lar"""
        if len(df) < 50:  # 200'den 50'ye düşürdük - daha az veri ile çalışır
            return Signal.HOLD
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = []
        
        # EMA trend sinyali - Daha esnek kontrol
        try:
            if pd.notna(latest['EMA_5']) and pd.notna(latest['EMA_13']) and pd.notna(latest['EMA_50']):
                if latest['EMA_5'] > latest['EMA_13'] > latest['EMA_50']:
                    signals.append(1)  # Yükseliş trendi
                elif latest['EMA_5'] < latest['EMA_13'] < latest['EMA_50']:
                    signals.append(-1)  # Düşüş trendi
                elif latest['EMA_5'] > latest['EMA_13']:  # Kısa vadeli pozitif
                    signals.append(0.5)  # Zayıf yükseliş
                elif latest['EMA_5'] < latest['EMA_13']:  # Kısa vadeli negatif  
                    signals.append(-0.5)  # Zayıf düşüş
                else:
                    signals.append(0)
            else:
                signals.append(0)  # NaN değerler varsa nötr
        except (KeyError, IndexError):
            signals.append(0)  # Hata durumunda nötr
        
        # MACD sinyali - Güvenli kontrol
        try:
            if (pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']) and 
                pd.notna(prev['MACD']) and pd.notna(prev['MACD_Signal'])):
                if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
                    signals.append(1)  # MACD golden cross
                elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
                    signals.append(-1)  # MACD death cross
                elif latest['MACD'] > latest['MACD_Signal']:
                    signals.append(0.3)  # MACD pozitif ama cross yok
                elif latest['MACD'] < latest['MACD_Signal']:
                    signals.append(-0.3)  # MACD negatif ama cross yok
                else:
                    signals.append(0)
            else:
                signals.append(0)  # NaN değerler varsa nötr
        except (KeyError, IndexError):
            signals.append(0)  # Hata durumunda nötr
        
        # RSI sinyali - Güvenli ve daha hassas
        try:
            if pd.notna(latest['RSI']):
                if latest['RSI'] < 30:
                    signals.append(1)  # Aşırı satım - güçlü alım
                elif latest['RSI'] > 70:
                    signals.append(-1)  # Aşırı alım - güçlü satım
                elif latest['RSI'] < 40:
                    signals.append(0.5)  # Zayıf alım bölgesi
                elif latest['RSI'] > 60:
                    signals.append(-0.5)  # Zayıf satım bölgesi
                else:
                    signals.append(0)  # Nötr bölge
            else:
                signals.append(0)
        except (KeyError, IndexError):
            signals.append(0)
        
        # Bollinger Bantları sinyali - Güvenli kontrol
        try:
            if (pd.notna(latest['Close']) and pd.notna(latest['BB_Lower']) and 
                pd.notna(latest['BB_Upper']) and pd.notna(latest['BB_Middle'])):
                if latest['Close'] < latest['BB_Lower']:
                    signals.append(1)  # Alt banda yakın - alım fırsatı
                elif latest['Close'] > latest['BB_Upper']:
                    signals.append(-1)  # Üst banda yakın - satım fırsatı
                elif latest['Close'] < latest['BB_Middle']:
                    signals.append(0.2)  # Orta bandin altında - zayıf alım
                elif latest['Close'] > latest['BB_Middle']:
                    signals.append(-0.2)  # Orta bandin üstünde - zayıf satım
                else:
                    signals.append(0)
            else:
                signals.append(0)
        except (KeyError, IndexError):
            signals.append(0)
        
        # Sinyal birleştirme - Çok daha hassas threshold'lar
        total_signal = sum(signals)
        
        # Çok hassas sinyal üretimi - gerçek trading için optimize edildi
        if total_signal >= 0.3:  # 0.8'den 0.3'e düşürdük - çok daha kolay BUY
            return Signal.BUY
        elif total_signal <= -0.3:  # -0.8'den -0.3'e düşürdük - çok daha kolay SELL
            return Signal.SELL
        else:
            return Signal.HOLD

class MarketDepthAnalyzer:
    """Market derinliği analizi - orijinal OrderBookAnalyzer'den esinlenildi"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_depth(self, depth_data: Dict, threshold: float = 5.0) -> Signal:
        """Market derinliği analizini yapar"""
        try:
            if not depth_data or 'bids' not in depth_data or 'asks' not in depth_data:
                return Signal.HOLD
            
            bids = depth_data['bids']
            asks = depth_data['asks']
            
            if not bids or not asks:
                return Signal.HOLD
            
            # Toplam bid ve ask hacimlerini hesapla
            total_bids = sum([float(bid[1]) for bid in bids[:20]])  # İlk 20 seviye
            total_asks = sum([float(ask[1]) for ask in asks[:20]])
            
            if total_asks == 0:
                return Signal.HOLD
            
            # Yüzde farkı hesapla
            difference = total_bids - total_asks
            percentage_diff = (difference / total_asks) * 100
            
            self.logger.debug(f"Market derinliği analizi: %{percentage_diff:.2f}")
            
            if percentage_diff > threshold:
                return Signal.BUY
            elif percentage_diff < -threshold:
                return Signal.SELL
            else:
                return Signal.HOLD
                
        except Exception as e:
            self.logger.error(f"Market derinliği analiz hatası: {e}")
            return Signal.HOLD

class PredictionEngine:
    """Tahmin motoru - basit trend analizi (ML modeli olmadan)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def predict_price(self, df: pd.DataFrame, periods: int = 1) -> Tuple[float, Signal]:
        """Basit trend analizi ile fiyat tahmini"""
        if len(df) < 10:
            current_price = df['Close'].iloc[-1]
            return current_price, Signal.HOLD
        
        # Son 10 periyottan trend çıkar
        recent_prices = df['Close'].tail(10).values
        
        # Linear regression benzeri basit trend hesabı
        x = np.arange(len(recent_prices))
        slope = np.polyfit(x, recent_prices, 1)[0]
        
        current_price = df['Close'].iloc[-1]
        predicted_price = current_price + (slope * periods)
        
        # Sinyal üret
        price_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        if price_change_pct > 0.5:
            signal = Signal.BUY
        elif price_change_pct < -0.5:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        
        self.logger.debug(f"Fiyat tahmini: {predicted_price:.4f}, Değişim: %{price_change_pct:.2f}")
        
        return predicted_price, signal

class RiskManager:
    """Risk yönetimi - orijinal TradeManager'den esinlenildi"""
    
    def __init__(self, risk_percentage: float = 0.02, max_positions: int = 5):
        self.risk_percentage = risk_percentage  # Portfolio'nun %2'si
        self.max_positions = max_positions
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, balance: float, entry_price: float, 
                              stop_loss: float) -> float:
        """Pozisyon büyüklüğünü hesaplar"""
        risk_amount = balance * self.risk_percentage
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff == 0:
            return 0
        
        position_size = risk_amount / price_diff
        return position_size
    
    def calculate_levels(self, entry_price: float, signal: Signal, 
                        atr: float = None) -> Tuple[float, float]:
        """Stop-loss ve take-profit seviyelerini hesaplar"""
        if atr is None:
            atr = entry_price * 0.02  # %2 varsayılan volatilite
        
        if signal == Signal.BUY:
            stop_loss = entry_price - (2 * atr)
            take_profit = entry_price + (3 * atr)
        elif signal == Signal.SELL:
            stop_loss = entry_price + (2 * atr)
            take_profit = entry_price - (3 * atr)
        else:
            return entry_price, entry_price
        
        return stop_loss, take_profit

class UniversalTradingBot:
    """Ana trading bot sınıfı - tüm bileşenleri birleştirir"""
    
    def __init__(self, data_provider: DataProvider, asset_type: AssetType):
        self.data_provider = data_provider
        self.asset_type = asset_type
        self.technical_analyzer = TechnicalAnalyzer()
        self.depth_analyzer = MarketDepthAnalyzer()
        self.prediction_engine = PredictionEngine()
        self.risk_manager = RiskManager()
        
        self.logger = logging.getLogger(__name__)
        # self.logger.info(f"UniversalTradingBot başlatıldı - Varlık türü: {asset_type.value}")  # Disabled for Railway
    
    def analyze_symbol(self, symbol: str, timeframe: str = '1m') -> Dict:
        """
        Ana analiz fonksiyonu - tüm sinyalleri birleştirir
        None döndürme durumları net şekilde raporlar
        """
        try:
            current_price = self.data_provider.get_current_price(symbol)
            
            # 1. Teknik analiz sinyalleri
            tech_signal_short = self._get_technical_signal(symbol, '1m')
            tech_signal_long = self._get_technical_signal(symbol, '15m')
            
            # 2. Basit trend tahmini
            prediction_signal = self._get_prediction_signal(symbol)
            
            # 3. Market derinliği analizi
            depth_signal = self._get_market_depth_signal(symbol)
            
            # 4. Korelasyon analizi (eğer provider destekliyorsa)
            correlation_signal = Signal.HOLD
            if hasattr(self.data_provider, 'get_correlation_signal'):
                try:
                    correlation_signal = self.data_provider.get_correlation_signal(symbol, tech_signal_long)
                except:
                    correlation_signal = Signal.HOLD
                    
            # 5. Final karar - artık None dönebilir
            final_signal = self._combine_signals(
                tech_signal_short, 
                tech_signal_long, 
                prediction_signal, 
                depth_signal,
                correlation_signal
            )
            
            # Veri eksikliği durumu kontrolü
            if final_signal is None:
                self.logger.error(f"❌ {symbol} - Kritik veri eksikliği, analiz tamamlanamadı")
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'error': 'Veri eksikliği - Analiz yapılamadı',
                    'error_type': 'DATA_UNAVAILABLE',
                    'available_signals': {
                        'technical_short': tech_signal_short.value if tech_signal_short else None,
                        'technical_long': tech_signal_long.value if tech_signal_long else None,
                        'prediction': prediction_signal.value if prediction_signal else None,
                        'depth': depth_signal.value if depth_signal else None,
                        'correlation': correlation_signal.value if correlation_signal else None
                    },
                    'timestamp': datetime.now().isoformat()
                }
            
            # Risk yönetimi
            atr = self._calculate_atr(symbol)
            stop_loss, take_profit = self._calculate_risk_levels(current_price, final_signal, atr)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'final_signal': final_signal.value,
                'technical_signal_short': tech_signal_short.value if tech_signal_short else 'unavailable',
                'technical_signal_long': tech_signal_long.value if tech_signal_long else 'unavailable',
                'prediction_signal': prediction_signal.value if prediction_signal else 'unavailable',
                'depth_signal': depth_signal.value if depth_signal else 'unavailable',
                'correlation_signal': correlation_signal.value if correlation_signal else 'unavailable',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'atr': atr,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Analiz hatası {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'error_type': 'ANALYSIS_ERROR',
                'timestamp': datetime.now().isoformat()
            }

    def _combine_signals(self, tech_short: Signal, tech_long: Signal, 
                        pred: Signal, depth: Signal, correlation: Signal = Signal.HOLD) -> Signal:
        """
        5 farklı sinyali birleştirerek final karar verir - None değerleri filtreler
        
        Önemli: None = Veri yok, HOLD = Kararsız piyasa (çok farklı!)
        """
        # None değerleri filtrele - sadece geçerli sinyalleri say
        all_signals = [tech_short, tech_long, pred, depth, correlation]
        valid_signals = [s for s in all_signals if s is not None]
        
        # Kritik kontrol: Uzun vadeli teknik trend yoksa analiz yapamayız
        if tech_long is None:
            self.logger.warning("❌ Uzun vadeli teknik veri yok - Analiz yapılamıyor")
            return None  # Veri yoksa None döndür
            
        # Uzun vadeli trend HOLD ise diğer sinyalleri de değerlendir (daha esnek)
        # Sadece uzun vadeli HOLD'a bakarak karar vermeyelim
            
        # Geçerli sinyal sayısı yetersizse
        if len(valid_signals) < 3:
            self.logger.warning(f"⚠️ Yetersiz veri: Sadece {len(valid_signals)}/5 sinyal mevcut")
            return Signal.HOLD  # Bu durumda bekle - veri eksikliği var
        
        # Oy sayma - sadece geçerli sinyallerden
        buy_count = valid_signals.count(Signal.BUY)
        sell_count = valid_signals.count(Signal.SELL)
        
        # Korelasyon ağırlıklandırması (varsa)
        correlation_weight = 0.5
        if correlation == Signal.BUY:
            buy_count += correlation_weight
        elif correlation == Signal.SELL:
            sell_count += correlation_weight
        
        # Final karar - Çok daha esnek threshold'lar
        total_valid = len(valid_signals)
        
        # Basit çoğunluk kuralı - uzun vadeli teknik analiz şartı kaldırıldı
        if buy_count >= sell_count and buy_count >= 1:  # En az 1 BUY sinyali yeterli
            return Signal.BUY
        elif sell_count > buy_count and sell_count >= 1:  # En az 1 SELL sinyali yeterli
            return Signal.SELL
        else:
            return Signal.HOLD
    
    def _get_technical_signal(self, symbol: str, timeframe: str) -> Signal:
        """Teknik analiz sinyali üretir"""
        try:
            limit = 500 if timeframe == '1m' else 200
            df = self.data_provider.get_historical_data(symbol, timeframe, limit)
            
            if df.empty:
                self.logger.warning(f"⚠️ {symbol} {timeframe} - Veri boş")
                return None  # HOLD değil None döndür
                
            df = self.technical_analyzer.calculate_indicators(df)
            return self.technical_analyzer.generate_signal(df)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} {timeframe} teknik analiz hatası: {e}")
            return None  # Hata durumunda None döndür
            
    def _get_prediction_signal(self, symbol: str) -> Signal:
        """Trend tahmini sinyali"""
        try:
            df = self.data_provider.get_historical_data(symbol, '1m', 100)
            if df.empty:
                self.logger.warning(f"⚠️ {symbol} - Tahmin için veri boş")
                return None
                
            predicted_price, pred_signal = self.prediction_engine.predict_price(df)
            return pred_signal
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} tahmin hatası: {e}")
            return None
            
    def _get_market_depth_signal(self, symbol: str) -> Signal:
        """Market derinliği sinyali"""
        try:
            depth_data = self.data_provider.get_market_depth(symbol)
            return self.depth_analyzer.analyze_depth(depth_data)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} derinlik analizi hatası: {e}")
            return None
            
    def _calculate_atr(self, symbol: str) -> float:
        """ATR hesaplar"""
        try:
            df = self.data_provider.get_historical_data(symbol, '1m', 100)
            if df.empty or len(df) < 14:
                return self.data_provider.get_current_price(symbol) * 0.02  # %2 fallback
                
            df = self.technical_analyzer.calculate_indicators(df)
            return df['ATR'].iloc[-1] if 'ATR' in df.columns else df['Close'].iloc[-1] * 0.02
            
        except Exception as e:
            self.logger.warning(f"{symbol} ATR hatası: {e}")
            return self.data_provider.get_current_price(symbol) * 0.02
            
    def _calculate_risk_levels(self, current_price: float, signal: Signal, atr: float) -> tuple:
        """Stop loss ve take profit seviyelerini hesaplar"""
        try:
            return self.risk_manager.calculate_levels(current_price, signal, atr)
        except:
            # Fallback hesaplama
            if signal == Signal.BUY:
                stop_loss = current_price - (atr * 2)
                take_profit = current_price + (atr * 3)
            elif signal == Signal.SELL:
                stop_loss = current_price + (atr * 2)
                take_profit = current_price - (atr * 3)
            else:
                stop_loss = take_profit = current_price
                
            return stop_loss, take_profit

    def _empty_analysis(self) -> Dict:
        """Boş analiz sonucu"""
        return {
            "symbol": "",
            "current_price": 0,
            "predicted_price": 0,
            "final_signal": Signal.HOLD.value,
            "technical_signal_short": Signal.HOLD.value,
            "technical_signal_long": Signal.HOLD.value,
            "prediction_signal": Signal.HOLD.value,
            "depth_signal": Signal.HOLD.value,
            "stop_loss": 0,
            "take_profit": 0,
            "atr": 0,
            "timestamp": datetime.now().isoformat()
        }

# Örnek veri sağlayıcı implementasyonu
class MockDataProvider(DataProvider):
    """Test için sahte veri sağlayıcı"""
    
    def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        # Sahte veri üret
        dates = pd.date_range(start='2024-01-01', periods=limit, freq='1min')
        np.random.seed(42)
        
        price = 50000  # Başlangıç fiyatı
        data = []
        
        for i, date in enumerate(dates):
            # Daha gerçekçi volatilite - %1-2 arası
            change = np.random.normal(0, 0.015)  # %1.5 volatilite (0.002'den 0.015'e)
            price *= (1 + change)
            
            # Daha gerçekçi high/low spread
            high_change = abs(np.random.normal(0, 0.008))  # %0.8 high spread
            low_change = abs(np.random.normal(0, 0.008))   # %0.8 low spread
            
            high = price * (1 + high_change)
            low = price * (1 - low_change)
            volume = np.random.randint(1000, 10000)  # Daha yüksek volume
            
            data.append({
                'Open': price,
                'High': high,
                'Low': low, 
                'Close': price,
                'Volume': volume,
                'Timestamp': date
            })
        
        return pd.DataFrame(data)
    
    def get_current_price(self, symbol: str) -> float:
        return 50000 + np.random.normal(0, 100)
    
    def get_market_depth(self, symbol: str) -> Dict:
        # Sahte market derinliği
        current_price = self.get_current_price(symbol)
        
        bids = []
        asks = []
        
        for i in range(20):
            bid_price = current_price - (i + 1) * 0.01
            ask_price = current_price + (i + 1) * 0.01
            volume = np.random.uniform(0.1, 5.0)
            
            bids.append([bid_price, volume])
            asks.append([ask_price, volume])
        
        return {"bids": bids, "asks": asks} 