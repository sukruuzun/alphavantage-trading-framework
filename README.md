# 🏛️ Alpha Vantage Trading Framework

🤖 **AI Trading Advisor** - Premium Alpha Vantage API ile çalışan kapsamlı trading framework'ü

## 🚀 Yeni Özellikler

### 🎯 **AI Trading Advisor - Günlük Piyasa Brifingi**
- **Kapsamlı Piyasa Analizi**: 6 farklı analiz metodunu birleştirir
- **Akıllı Karar Verme**: Mantıklı öneri sistemi (NÖTR ≠ GÜÇLÜ sinyal)
- **Multi-Asset Coverage**: Forex, Stocks, Crypto (12+ enstrüman)
- **Gerçek-time Sentiment**: Alpha Vantage News & Sentiment API
- **Risk Değerlendirmesi**: Her öneri için risk/güven seviyesi

## 📊 Desteklenen Varlıklar

### 💱 **Forex Pairs**
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD
- EURJPY, GBPJPY, USDCHF, NZDUSD

### 📈 **US Stocks**
- AAPL, GOOGL, MSFT, AMZN, TSLA
- NVDA, META (Facebook)

### ₿ **Cryptocurrencies**
- BTCUSD, ETHUSD, ADAUSD, DOTUSD

## 🛠️ Kurulum

### Gereksinimler
```bash
pip install -r requirements.txt
```

### Alpha Vantage API Key
1. [Alpha Vantage](https://www.alphavantage.co/support/#api-key) hesabı oluşturun
2. API key alın
3. Environment variable olarak ayarlayın:
```bash
export ALPHA_VANTAGE_KEY="your_api_key_here"
```

## 🎯 Demo Özellikleri

### 1. 📰 Güncel Haberler & Sentiment Analizi
- Canlı piyasa haberleri
- Sentiment skorları (-1 ile +1 arası)
- Haber kategorileri ve trendler

### 2. 🧠 Haber Bazlı Akıllı Sinyal Üretimi
- Her hisse için ayrı sentiment analizi
- Teknik analiz + haber korelasyonu
- Sinyal gücü değerlendirmesi

### 3. 📊 Multi-Asset Piyasa Analizi
- Forex, Stocks, Crypto eş zamanlı analiz
- Teknik indikatörler (EMA, MACD, RSI, Bollinger)
- Gerçek-time fiyat verileri

### 4. 🔥 Hot Stocks - Sentiment Taraması
- Popüler hisselerin sentiment karşılaştırması
- Her hisse için AYRI API çağrısı (kritik düzeltme!)
- Kategorik sentiment sınıflandırması

### 5. 💱 Forex + Haber Korelasyonu
- Major forex çiftleri analizi
- Haber etkisi korelasyonu
- Cross-currency analiz

### 6. ⚡ Hızlı Sentiment Skoru
- Anlık sentiment değerlendirmesi
- Emoji tabanlı sonuç gösterimi
- Aksiyon önerileri

### 7. 🎯 **AI Trading Advisor (YENİ!)**
- **Kapsamlı günlük piyasa brifingi**
- **Tüm analizleri birleştiren akıllı karar sistemi**
- **Mantıklı öneri mekanizması**
- **Risk-aware portfolio önerileri**

## 🧠 AI Trading Advisor Detayları

### Analiz Süreci (5 Aşama):

1. **Global Market Sentiment** - Genel piyasa ruh hali
2. **Multi-Asset Performance** - Varlık sınıfları karşılaştırması
3. **Hot Stocks Sentiment** - Bireysel hisse analizleri
4. **Akıllı Fırsat Değerlendirmesi** - NÖTR ≠ GÜÇLÜ mantığı
5. **Günlük Öneriler & Aksiyon Planı** - Spesifik, actionable öneriler

### Düzeltilen Kritik Mantık Hataları:
- ✅ **"NÖTR = EN İYİ"** çelişkisi düzeltildi
- ✅ **"NÖTR = GÜÇLÜ SİNYAL"** mantık hatası giderildi
- ✅ **Belirsiz öneriler** → Spesifik sembol + fiyat + gerekçe
- ✅ **BEKLE** sinyali - Sinyal yoksa bekle diyebilir

## 🔧 Teknik Özellikler

### Premium API Optimizasyonu
- **Rate Limiting**: Free (12s) / Premium (1s)
- **Cache System**: Akıllı önbellekleme
- **Error Handling**: Veri yoksa None (HOLD değil)
- **Signal Filtering**: None değerleri filtreli işlem

### Sentiment Cache Bug Fix
- ✅ Her hisse için **ayrı cache key**
- ✅ Her sembol **farklı sentiment** verisi
- ✅ **Gerçek karşılaştırma** imkanı

### Risk Management
- Stop-Loss/Take-Profit hesaplama
- ATR bazlı volatilite analizi
- Position sizing önerileri
- Correlation analysis

## 🚀 Kullanım

```bash
python3 alphavantage_demo.py
```

### Menü Seçenekleri:
- **1-6**: Bireysel analiz araçları
- **7**: 🎯 **AI Trading Advisor** (Kapsamlı günlük analiz)
- **8**: Çıkış

## ⚠️ Önemli Notlar

### Yasal Uyarı
- Bu framework sadece **bilgilendirme amaçlıdır**
- Yatırım tavsiyesi değildir
- Yatırım kararlarınızı kendi riskinize göre alın
- Stop-loss kullanmayı unutmayın
- Portföy diversifikasyonu önemlidir

### Premium Özellikler
- **Free Plan**: 25 call/day, 5 call/min
- **Premium Plan**: Unlimited calls, 75 call/min
- **News & Sentiment**: Premium için unlimited

## 📈 Örnekler

### AI Trading Advisor Çıktısı:
```
🎯 GÜNÜN FIRSATLARı:
  1. AAPL - STRONG BUY consideration
     💡 Sebep: Çok yüksek pozitif sentiment: +0.222
     💰 Güncel Fiyat: $209.05
     ⚖️ Risk: YÜKSEK | Güven: YÜKSEK
```

### Multi-Asset Analysis:
```
💱 FOREX:
  🟡 EURUSD  |  1.14350 | HOLD
  🟢 GBPUSD  |  1.32500 | BUY
  📊 💱 FOREX Durumu: 🟡 KARIŞIK-POZİTİF (Buy: 1/3)
```

## 🔄 Güncellemeler

### v2.0 (Latest)
- ✅ AI Trading Advisor eklendi
- ✅ Sentiment cache bug düzeltildi
- ✅ Mantık hataları giderildi
- ✅ Premium API optimizasyonu
- ✅ Akıllı error handling

### v1.5
- ✅ Multi-asset support
- ✅ Correlation analysis
- ✅ Hot stocks scanner

### v1.0
- ✅ Basic Alpha Vantage integration
- ✅ News & sentiment analysis

## 🤝 Katkıda Bulunma

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License - Detaylar için LICENSE dosyasına bakın.

---

**🎯 Framework artık production-ready! Real-time trading decisions için güvenle kullanabilirsiniz.** d