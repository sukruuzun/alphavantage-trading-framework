#!/usr/bin/env python3
"""
🏛️ ALPHA VANTAGE DEMO - Haberler + Sentiment Analizi
Profesyonel seviyede piyasa analizi ve haber bazlı trading

📰 Özellikler:
- Gerçek zamanlı haberler
- Sentiment analizi  
- Piyasa duygusu skorları
- Haber bazlı sinyal üretimi
- Multi-asset analizi
"""

import os
import time
import logging
from datetime import datetime
from alphavantage_provider import AlphaVantageProvider
from universal_trading_framework import UniversalTradingBot, AssetType

def setup_logging():
    """Logging setup"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def show_menu():
    """Ana menü"""
    print("\n" + "="*75)
    print("🏛️ ALPHA VANTAGE TRADING FRAMEWORK - HABERLEr + SENTIMENT")
    print("="*75)
    print("📰 GERÇEK HABERLEr: Alpha Vantage News & Sentiment API")
    print("🧠 AKILLI SİNYALLEr: Haber + Korelasyon + Teknik Analiz")
    print("💹 ÇOKLU VARLIK: Forex + Stocks + Crypto")
    print()
    print("📋 DEMO SEÇENEKLERİ:")
    print("1. 📰 Güncel Haberler & Sentiment Analizi")
    print("2. 🧠 Haber Bazlı Akıllı Sinyal Üretimi")
    print("3. 📊 Multi-Asset Piyasa Analizi")
    print("4. 🔥 Hot Stocks - Sentiment Taraması")
    print("5. 💱 Forex + Haber Korelasyonu")
    print("6. ⚡ Hızlı Sentiment Skoru")
    print("7. 🎯 Günlük Piyasa Brifingi ve Fırsat Tarayıcısı (YENİ!)")
    print("8. ❌ Çıkış")
    print("="*75)

def current_news_sentiment():
    """Haberler ve sentiment analizi"""
    print("\n📰 GÜNCEL HABERLEr & SENTIMENT ANALİZİ")
    print("="*60)
    
    try:
        provider = AlphaVantageProvider()
        
        print("🔄 Alpha Vantage'dan son haberler alınıyor...")
        sentiment_data = provider.get_news_sentiment(limit=30)
        
        print(f"\n📊 GENEL PİYASA DUYGUSU")
        print("-" * 40)
        
        overall = sentiment_data['overall_sentiment']
        sentiment_emoji = "🟢" if overall > 0.1 else "🔴" if overall < -0.1 else "🟡"
        sentiment_text = "POZİTİF" if overall > 0.1 else "NEGATİF" if overall < -0.1 else "NÖTR"
        
        print(f"{sentiment_emoji} Genel Sentiment: {overall:.3f} ({sentiment_text})")
        print(f"📰 Analiz edilen haber: {sentiment_data['news_count']}")
        
        # Sentiment breakdown
        breakdown = sentiment_data['sentiment_breakdown']
        total = sum(breakdown.values())
        if total > 0:
            print(f"\n📈 SENTIMENT DAĞILIMI:")
            print(f"   🟢 Bullish: {breakdown['bullish']} ({breakdown['bullish']/total*100:.1f}%)")
            print(f"   🔴 Bearish: {breakdown['bearish']} ({breakdown['bearish']/total*100:.1f}%)")
            print(f"   🟡 Neutral: {breakdown['neutral']} ({breakdown['neutral']/total*100:.1f}%)")
        
        # Top haberler
        print(f"\n🔥 EN ÖNEMLİ HABERLEr:")
        print("-" * 60)
        
        for i, news in enumerate(sentiment_data['top_news'][:5], 1):
            sentiment_emoji = "🟢" if news['sentiment_score'] > 0.1 else "🔴" if news['sentiment_score'] < -0.1 else "🟡"
            
            print(f"\n{i}. {sentiment_emoji} {news['title']}")
            print(f"   📊 Sentiment: {news['sentiment_score']:.3f} ({news['sentiment_label']})")
            print(f"   🎯 İlgililik: {news['relevance_score']:.3f}")
            print(f"   ⏰ Zaman: {news['time_published']}")
            if len(news['summary']) > 10:
                print(f"   📝 Özet: {news['summary'][:100]}...")
        
        print(f"\n💡 Son güncelleme: {sentiment_data['last_updated'][:19]}")
        
    except Exception as e:
        print(f"❌ Haber analizi hatası: {e}")

def smart_signal_generation():
    """Haber bazlı akıllı sinyal üretimi"""
    print("\n🧠 HABER BAZLI AKILLI SİNYAL ÜRETİMİ")
    print("="*60)
    
    try:
        # Auto-detect premium plan
        import os
        api_key = os.getenv('ALPHA_VANTAGE_KEY')
        provider = AlphaVantageProvider(is_premium=True)  # Assume premium for now
        
        # Test sembolleri - Stocks (haber etkisi en yüksek)
        test_stocks = ["AAPL", "GOOGL", "TSLA", "NVDA", "META"]
        
        print("🔄 Hisse senetleri için haber + teknik analiz yapılıyor...")
        print()
        
        results = []
        
        for symbol in test_stocks:
            try:
                framework = UniversalTradingBot(provider, AssetType.STOCKS)
                analysis = framework.analyze_symbol(symbol)
                
                # ERROR CHECK - Veri eksikliği kontrolü
                if 'error' in analysis:
                    error_type = analysis.get('error_type', 'UNKNOWN')
                    if error_type == 'DATA_UNAVAILABLE':
                        print(f"⚠️ {symbol:5} | VERİ EKSİK - Analiz yapılamadı")
                        available = analysis.get('available_signals', {})
                        missing = [k for k, v in available.items() if v is None]
                        if missing:
                            print(f"     Eksik: {', '.join(missing)}")
                    else:
                        print(f"❌ {symbol:5} | HATA: {analysis['error'][:50]}...")
                    continue
                
                # Özel sentiment analizi
                sentiment_data = provider.get_news_sentiment([symbol], limit=10)
                
                final_signal = analysis.get('final_signal', 'hold')
                correlation_signal = analysis.get('correlation_signal', 'hold')
                price = analysis.get('current_price', 0)
                sentiment_score = sentiment_data['overall_sentiment']
                news_count = sentiment_data['news_count']
                
                # Sinyal gücü hesaplama
                signal_strength = 1
                if final_signal == correlation_signal and final_signal != 'hold':
                    signal_strength += 1
                if abs(sentiment_score) > 0.2:  # Güçlü sentiment
                    signal_strength += 1
                if news_count >= 5:  # Yeterli haber var
                    signal_strength += 1
                
                results.append({
                    'symbol': symbol,
                    'price': price,
                    'final_signal': final_signal,
                    'sentiment_score': sentiment_score,
                    'news_count': news_count,
                    'signal_strength': signal_strength
                })
                
                # Emoji'ler
                signal_emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(final_signal, "⚪")
                sentiment_emoji = "📈" if sentiment_score > 0.1 else "📉" if sentiment_score < -0.1 else "➡️"
                strength_stars = "⭐" * signal_strength
                
                print(f"{signal_emoji} {symbol:5} | ${price:>8.2f} | "
                      f"Sinyal: {final_signal.upper():>4} | "
                      f"Sentiment: {sentiment_emoji}{sentiment_score:>+.3f} | "
                      f"Haberler: {news_count:>2} | {strength_stars}")
                
                time.sleep(1)  # Reduced rate limiting
                
            except Exception as e:
                print(f"❌ {symbol:5} | Analiz hatası: {str(e)[:30]}...")
                
        # En güçlü sinyalleri sırala
        if results:
            results.sort(key=lambda x: x['signal_strength'], reverse=True)
            
            print(f"\n🎯 EN GÜÇLÜ SİNYALLER:")
            print("-" * 50)
            
            for i, result in enumerate(results[:3], 1):
                if result['signal_strength'] >= 3:
                    emoji = "🟢" if result['final_signal'] == 'buy' else "🔴" if result['final_signal'] == 'sell' else "🟡"
                    print(f"{i}. {emoji} {result['symbol']} - {result['final_signal'].upper()} "
                          f"(Güç: {result['signal_strength']}/4, Sentiment: {result['sentiment_score']:+.3f})")
        else:
            print("\n⚠️ Hiçbir sembol için analiz tamamlanamadı - Veri eksikliği")
        
    except Exception as e:
        print(f"❌ Akıllı sinyal hatası: {e}")

def multi_asset_analysis():
    """Çoklu varlık analizi"""
    print("\n📊 MULTI-ASSET PİYASA ANALİZİ")
    print("="*60)
    
    try:
        provider = AlphaVantageProvider(is_premium=True)  # Auto-detect or assume premium
        
        asset_groups = [
            {
                "name": "💱 MAJOR FOREX",
                "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
                "type": AssetType.FOREX
            },
            {
                "name": "📈 TECH STOCKS",
                "symbols": ["AAPL", "GOOGL", "NVDA"],
                "type": AssetType.STOCKS
            },
            {
                "name": "₿ CRYPTO",
                "symbols": ["BTCUSD", "ETHUSD"],
                "type": AssetType.CRYPTO
            }
        ]
        
        print(f"⏰ Analiz zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔄 Alpha Vantage'dan gerçek veriler alınıyor...\n")
        
        for group in asset_groups:
            print(f"{group['name']}")
            print("-" * 50)
            
            framework = UniversalTradingBot(provider, group['type'])
            
            for symbol in group['symbols']:
                try:
                    start_time = time.time()
                    analysis = framework.analyze_symbol(symbol)
                    analysis_time = time.time() - start_time
                    
                    # ERROR CHECK - Veri eksikliği kontrolü
                    if 'error' in analysis:
                        error_type = analysis.get('error_type', 'UNKNOWN')
                        if error_type == 'DATA_UNAVAILABLE':
                            print(f"⚠️ {symbol:7} | VERİ EKSİK - Teknik analiz yapılamadı | {analysis_time*1000:.0f}ms")
                            available = analysis.get('available_signals', {})
                            unavailable = [k.replace('_signal', '') for k, v in available.items() if v is None]
                            if unavailable:
                                print(f"     Eksik veriler: {', '.join(unavailable)}")
                        else:
                            print(f"❌ {symbol:7} | HATA: {analysis['error'][:30]}... | {analysis_time*1000:.0f}ms")
                        continue
                    
                    price = analysis.get('current_price', 0)
                    final_signal = analysis.get('final_signal', 'hold')
                    correlation_signal = analysis.get('correlation_signal', 'hold')
                    
                    # Hisse senetleri için sentiment ekle
                    sentiment_info = ""
                    if group['type'] == AssetType.STOCKS:
                        try:
                            sentiment_data = provider.get_news_sentiment([symbol], limit=5)
                            sentiment_score = sentiment_data['overall_sentiment']
                            sentiment_emoji = "📈" if sentiment_score > 0.1 else "📉" if sentiment_score < -0.1 else "➡️"
                            sentiment_info = f" | Sentiment: {sentiment_emoji}{sentiment_score:+.3f}"
                        except:
                            sentiment_info = " | Sentiment: ➡️0.000"
                    
                    signal_emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(final_signal, "⚪")
                    corr_emoji = {"buy": "⬆️", "sell": "⬇️", "hold": "➡️"}.get(correlation_signal, "➡️")
                    
                    # Fiyat formatı
                    if symbol in ["USDJPY"]:
                        price_str = f"{price:>8.3f}"
                    elif symbol.endswith("USD") and symbol.startswith(("BTC", "ETH")):
                        price_str = f"${price:>8,.0f}"
                    elif group['type'] == AssetType.STOCKS:
                        price_str = f"${price:>8.2f}"
                    else:
                        price_str = f"{price:>8.5f}"
                    
                    print(f"{signal_emoji} {symbol:7} | {price_str} | "
                          f"Final: {final_signal.upper():>4} | "
                          f"Korel: {corr_emoji}{correlation_signal.upper():>4}"
                          f"{sentiment_info} | {analysis_time*1000:.0f}ms")
                    
                    time.sleep(0.5)  # Reduced rate limiting
                    
                except Exception as e:
                    print(f"❌ {symbol:7} | Analiz hatası: {str(e)[:35]}...")
            
            print()
            
    except Exception as e:
        print(f"❌ Multi-asset analiz hatası: {e}")

def hot_stocks_sentiment():
    """Popüler hisse senetleri sentiment taraması - Her hisse için ayrı API çağrısı"""
    print("\n🔥 HOT STOCKS - SENTIMENT TARAMASI")
    print("="*60)
    
    try:
        # Premium plan kullan (daha hızlı rate limit)
        provider = AlphaVantageProvider(is_premium=True)
        
        # Popüler tech + meme stocks (sıralı)
        hot_stocks = ["AAPL", "TSLA", "NVDA", "META", "GOOGL", "MSFT", "AMZN"]
        
        print("🔄 Popüler hisse senetlerinin sentiment skoru hesaplanıyor...")
        print("📋 NOT: Her hisse için AYRI sentiment verisi çekiliyor (gerçek karşılaştırma)")
        print()
        
        sentiment_results = []
        
        for i, stock in enumerate(hot_stocks, 1):
            try:
                print(f"   {i}/{len(hot_stocks)} - {stock} işleniyor...", end=" ", flush=True)
                
                # ✅ HER HİSSE İÇİN AYRI API ÇAĞRISI (kritik!)
                sentiment_data = provider.get_news_sentiment([stock], limit=15)
                price = provider.get_current_price(stock)
                
                sentiment_score = sentiment_data['overall_sentiment']
                news_count = sentiment_data['news_count']
                
                # Error check - Veri yoksa skip
                if news_count == 0:
                    print("❌ Haber bulunamadı")
                    continue
                
                # Sentiment kategorisi
                if sentiment_score > 0.2:
                    category = "🔥 ÇOK POZİTİF"
                elif sentiment_score > 0.05:
                    category = "📈 POZİTİF"
                elif sentiment_score < -0.2:
                    category = "❄️ ÇOK NEGATİF"
                elif sentiment_score < -0.05:
                    category = "📉 NEGATİF"
                else:
                    category = "😐 NÖTR"
                
                sentiment_results.append({
                    'stock': stock,
                    'price': price,
                    'sentiment_score': sentiment_score,
                    'news_count': news_count,
                    'category': category
                })
                
                print(f"✅ {category}")
                print(f"{category[:2]} {stock:5} | ${price:>8.2f} | "
                      f"Sentiment: {sentiment_score:>+.3f} | "
                      f"Haberler: {news_count:>2} | {category[3:]}")
                
                # Premium rate limiting (1s)
                time.sleep(1.2)
                
            except Exception as e:
                print(f"❌ API Hatası: {str(e)[:25]}...")
        
        # Analiz sonuçları - Sadece veri varsa
        if sentiment_results:
            sentiment_results.sort(key=lambda x: x['sentiment_score'], reverse=True)
            
            print(f"\n📊 SENTIMENT ANALİZ SONUÇLARI ({len(sentiment_results)} hisse)")
            print("="*50)
            
            print(f"🏆 EN POZİTİF SENTIMENT:")
            pos_count = 0
            for result in sentiment_results:
                if result['sentiment_score'] > 0 and pos_count < 2:
                    print(f"   🟢 {result['stock']} - {result['sentiment_score']:+.3f} ({result['news_count']} haber)")
                    pos_count += 1
            
            if pos_count == 0:
                print("   ⚪ Pozitif sentiment bulunamadı")
            
            print(f"\n⚠️ EN NEGATİF SENTIMENT:")
            neg_results = [r for r in sentiment_results if r['sentiment_score'] < 0]
            if neg_results:
                for result in neg_results[-2:]:
                    print(f"   🔴 {result['stock']} - {result['sentiment_score']:+.3f} ({result['news_count']} haber)")
            else:
                print("   ⚪ Negatif sentiment bulunamadı")
                
            # Özet istatistik
            avg_sentiment = sum(r['sentiment_score'] for r in sentiment_results) / len(sentiment_results)
            total_news = sum(r['news_count'] for r in sentiment_results)
            print(f"\n📈 ÖZET: Ortalama Sentiment: {avg_sentiment:+.3f} | Toplam Haber: {total_news}")
            
        else:
            print("\n⚠️ Hiçbir hisse için sentiment verisi alınamadı!")
        
    except Exception as e:
        print(f"❌ Hot stocks sentiment hatası: {e}")

def forex_news_correlation():
    """Forex + haber korelasyonu"""
    print("\n💱 FOREX + HABER KORELASYONU")
    print("="*60)
    
    try:
        provider = AlphaVantageProvider()
        
        forex_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        
        print("🔄 Forex çiftleri + global sentiment analizi...")
        print()
        
        # Global sentiment al
        global_sentiment = provider.get_news_sentiment(limit=50)
        
        print(f"🌍 GLOBAL PİYASA DUYGUSU: {global_sentiment['overall_sentiment']:+.3f}")
        print(f"📰 Analiz edilen haber sayısı: {global_sentiment['news_count']}")
        print()
        
        print("💱 FOREX ÇİFTLERİ ANALİZİ:")
        print("-" * 50)
        
        for pair in forex_pairs:
            try:
                framework = UniversalTradingBot(provider, AssetType.FOREX)
                analysis = framework.analyze_symbol(pair)
                
                price = analysis.get('current_price', 0)
                final_signal = analysis.get('final_signal', 'hold')
                correlation_signal = analysis.get('correlation_signal', 'hold')
                
                # Global sentiment ile uyum kontrolü
                global_score = global_sentiment['overall_sentiment']
                sentiment_alignment = ""
                
                if final_signal == 'buy' and global_score > 0.1:
                    sentiment_alignment = "✅ UYUMLU"
                elif final_signal == 'sell' and global_score < -0.1:
                    sentiment_alignment = "✅ UYUMLU"
                elif final_signal != 'hold':
                    sentiment_alignment = "⚠️ UYUMSUZ"
                else:
                    sentiment_alignment = "➡️ NÖTR"
                
                signal_emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(final_signal, "⚪")
                
                print(f"{signal_emoji} {pair:7} | {price:>8.5f} | "
                      f"Sinyal: {final_signal.upper():>4} | "
                      f"Global Sentiment: {sentiment_alignment}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ {pair:7} | Forex analiz hatası: {str(e)[:30]}...")
        
        # Global sentiment breakdown
        breakdown = global_sentiment['sentiment_breakdown']
        total = sum(breakdown.values())
        
        if total > 0:
            print(f"\n📊 GLOBAL SENTIMENT DAĞILIMI:")
            print(f"   🟢 Bullish: {breakdown['bullish']/total*100:.1f}%")
            print(f"   🔴 Bearish: {breakdown['bearish']/total*100:.1f}%")
            print(f"   🟡 Neutral: {breakdown['neutral']/total*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Forex + haber korelasyonu hatası: {e}")

def quick_sentiment_score():
    """Hızlı sentiment skoru"""
    print("\n⚡ HIZLI SENTIMENT SKORU")
    print("="*60)
    
    try:
        provider = AlphaVantageProvider()
        
        print("🔄 Genel piyasa sentiment'i hesaplanıyor...")
        
        sentiment_data = provider.get_news_sentiment(limit=100)
        
        score = sentiment_data['overall_sentiment']
        news_count = sentiment_data['news_count']
        
        # Sentiment emoji ve açıklama
        if score > 0.3:
            emoji = "🚀"
            description = "ÇOK POZİTİF - Güçlü yükseliş beklentisi"
            recommendation = "Risk alma zamanı"
        elif score > 0.1:
            emoji = "📈"
            description = "POZİTİF - Orta düzey yükseliş beklentisi"
            recommendation = "Dikkatli yatırım yapılabilir"
        elif score > -0.1:
            emoji = "😐"
            description = "NÖTR - Kararsızlık hakim"
            recommendation = "Bekle ve gör"
        elif score > -0.3:
            emoji = "📉"
            description = "NEGATİF - Düşüş beklentisi"
            recommendation = "Pozisyonları azalt"
        else:
            emoji = "🔻"
            description = "ÇOK NEGATİF - Güçlü düşüş beklentisi"
            recommendation = "Risk yönetimi kritik"
        
        print(f"\n{emoji} PİYASA SENTIMENT SKORU: {score:+.3f}")
        print(f"📊 Durum: {description}")
        print(f"💡 Öneri: {recommendation}")
        print(f"📰 Analiz edilen haber: {news_count}")
        print(f"⏰ Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")
        
        # Son 3 önemli haber
        if sentiment_data['top_news']:
            print(f"\n📰 SON ÖNEMLİ HABERLEr:")
            for i, news in enumerate(sentiment_data['top_news'][:3], 1):
                sentiment_emoji = "🟢" if news['sentiment_score'] > 0.1 else "🔴" if news['sentiment_score'] < -0.1 else "🟡"
                print(f"   {i}. {sentiment_emoji} {news['title'][:60]}...")
                print(f"      Sentiment: {news['sentiment_score']:+.3f}")
        
    except Exception as e:
        print(f"❌ Hızlı sentiment hatası: {e}")

def daily_market_briefing():
    """🎯 Günlük Piyasa Brifingi ve Fırsat Tarayıcısı - AI Trading Advisor"""
    print("\n🎯 GÜNLÜK PİYASA BRİFİNGİ VE FIRSAT TARAYICISI")
    print("="*80)
    print("🤖 AI Trading Advisor - Tüm piyasaları analiz ederek en iyi fırsatları belirler")
    print("📊 6 farklı analiz metodunu birleştirir ve kapsamlı rapor sunar")
    print("⏰ Analiz süresi: ~2-3 dakika (Premium API)")
    print()
    
    from datetime import datetime
    import time
    
    try:
        provider = AlphaVantageProvider(is_premium=True)
        analysis_start = time.time()
        
        # Analiz sonuçları storage
        briefing_results = {
            'global_sentiment': None,
            'multi_asset': {},
            'hot_stocks': [],
            'forex_analysis': {},
            'smart_signals': [],
            'opportunities': [],
            'risk_analysis': {},
            'recommendations': []
        }
        
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Günlük Piyasa Brifingi Başlıyor...")
        print("=" * 80)
        
        # 1️⃣ Global Market Sentiment (Foundation)
        print("\n1️⃣ GLOBAL PİYASA SENTİMENTİ")
        print("-" * 50)
        try:
            global_sentiment = provider.get_news_sentiment(limit=100)
            briefing_results['global_sentiment'] = global_sentiment
            
            sentiment_score = global_sentiment['overall_sentiment']
            news_count = global_sentiment['news_count']
            
            if sentiment_score > 0.15:
                sentiment_status = "🟢 POZİTİF"
                market_mood = "Risk alma zamanı"
            elif sentiment_score > 0.05:
                sentiment_status = "🟡 NÖTR-POZİTİF" 
                market_mood = "Temkinli iyimserlik"
            elif sentiment_score < -0.15:
                sentiment_status = "🔴 NEGATİF"
                market_mood = "Risk kaçınma modu"
            elif sentiment_score < -0.05:
                sentiment_status = "🟡 NÖTR-NEGATİF"
                market_mood = "Belirsizlik hakim"
            else:
                sentiment_status = "⚪ NÖTR"
                market_mood = "Kararsız piyasa"
                
            print(f"📊 Global Sentiment: {sentiment_status} ({sentiment_score:+.3f})")
            print(f"📰 Toplam Haber: {news_count}")
            print(f"🎯 Piyasa Ruh Hali: {market_mood}")
            
        except Exception as e:
            print(f"❌ Global sentiment alınamadı: {e}")
            
        time.sleep(1.5)
        
        # 2️⃣ Multi-Asset Performance Analysis
        print("\n2️⃣ MULTI-ASSET PERFORMANS ANALİZİ")
        print("-" * 50)
        
        asset_groups = [
            {
                "name": "💱 FOREX",
                "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
                "type": AssetType.FOREX
            },
            {
                "name": "📈 STOCKS",
                "symbols": ["AAPL", "GOOGL", "NVDA"],
                "type": AssetType.STOCKS
            },
            {
                "name": "₿ CRYPTO",
                "symbols": ["BTCUSD", "ETHUSD"],
                "type": AssetType.CRYPTO
            }
        ]
        
        asset_scores = {}
        
        for group in asset_groups:
            print(f"\n{group['name']}:")
            framework = UniversalTradingBot(provider, group['type'])
            
            buy_signals = 0
            sell_signals = 0
            hold_signals = 0
            total_analyzed = 0
            
            for symbol in group['symbols']:
                try:
                    analysis = framework.analyze_symbol(symbol)
                    
                    if 'error' not in analysis:
                        final_signal = analysis.get('final_signal', 'hold')
                        price = analysis.get('current_price', 0)
                        
                        if final_signal == 'buy':
                            buy_signals += 1
                            signal_emoji = "🟢"
                        elif final_signal == 'sell':
                            sell_signals += 1
                            signal_emoji = "🔴"
                        else:
                            hold_signals += 1
                            signal_emoji = "🟡"
                            
                        total_analyzed += 1
                        
                        # Fiyat formatı
                        if symbol == "USDJPY":
                            price_str = f"{price:>8.3f}"
                        elif symbol.endswith("USD") and symbol.startswith(("BTC", "ETH")):
                            price_str = f"${price:>8,.0f}"
                        elif group['type'] == AssetType.STOCKS:
                            price_str = f"${price:>8.2f}"
                        else:
                            price_str = f"{price:>8.5f}"
                            
                        print(f"  {signal_emoji} {symbol:7} | {price_str} | {final_signal.upper()}")
                        
                        briefing_results['multi_asset'][symbol] = {
                            'signal': final_signal,
                            'price': price
                        }
                        
                    time.sleep(0.8)
                    
                except Exception as e:
                    print(f"  ❌ {symbol:7} | Analiz hatası")
            
            # Asset group skoru
            if total_analyzed > 0:
                buy_ratio = buy_signals / total_analyzed
                sell_ratio = sell_signals / total_analyzed
                
                if buy_ratio >= 0.6:
                    group_status = "🟢 GÜÇLÜ ALIŞ"
                    group_score = 5
                elif buy_ratio >= 0.4:
                    group_status = "🟡 KARIŞIK-POZİTİF"
                    group_score = 3
                elif sell_ratio >= 0.6:
                    group_status = "🔴 GÜÇLÜ SATIŞ"
                    group_score = 1
                elif sell_ratio >= 0.4:
                    group_status = "🟡 KARIŞIK-NEGATİF"
                    group_score = 2
                else:
                    group_status = "⚪ NÖTR"
                    group_score = 3
                    
                asset_scores[group['name']] = {
                    'status': group_status,
                    'score': group_score,
                    'buy_ratio': buy_ratio,
                    'sell_ratio': sell_ratio
                }
                
                print(f"  📊 {group['name']} Durumu: {group_status} (Buy: {buy_signals}/{total_analyzed})")
        
        # 3️⃣ Hot Stocks Sentiment Analysis
        print(f"\n3️⃣ HOT STOCKS SENTIMENT ANALİZİ")
        print("-" * 50)
        
        hot_stocks = ["AAPL", "TSLA", "NVDA", "META", "GOOGL", "MSFT", "AMZN"]
        stock_sentiments = []
        
        for stock in hot_stocks[:5]:  # İlk 5'i analiz et (zaman sınırı)
            try:
                sentiment_data = provider.get_news_sentiment([stock], limit=15)
                price = provider.get_current_price(stock)
                
                sentiment_score = sentiment_data['overall_sentiment']
                news_count = sentiment_data['news_count']
                
                if news_count > 0:
                    stock_sentiments.append({
                        'stock': stock,
                        'sentiment': sentiment_score,
                        'news_count': news_count,
                        'price': price
                    })
                    
                    if sentiment_score > 0.2:
                        sentiment_status = "🔥 ÇOK POZİTİF"
                    elif sentiment_score > 0.05:
                        sentiment_status = "📈 POZİTİF"
                    elif sentiment_score < -0.2:
                        sentiment_status = "❄️ ÇOK NEGATİF"
                    elif sentiment_score < -0.05:
                        sentiment_status = "📉 NEGATİF"
                    else:
                        sentiment_status = "😐 NÖTR"
                        
                    print(f"  {sentiment_status[:2]} {stock:5} | ${price:>8.2f} | {sentiment_score:+.3f} ({news_count} haber)")
                    
                time.sleep(1.2)
                
            except Exception as e:
                print(f"  ❌ {stock:5} | Sentiment alınamadı")
        
        briefing_results['hot_stocks'] = stock_sentiments
        
        # 4️⃣ AKILLI FIRSAT DEĞERLENDİRMESİ
        print(f"\n4️⃣ AKILLI FIRSAT DEĞERLENDİRMESİ")
        print("-" * 50)
        
        opportunities = []
        
        # Asset class skorlarına göre MANTIKLI analiz
        sorted_assets = sorted(asset_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # ✅ CRITICAL FIX: NÖTR durumları için özel mantık
        if sorted_assets:
            best_asset = sorted_assets[0]
            worst_asset = sorted_assets[-1]
            
            # Gerçekten güçlü bir sinyal var mı kontrol et
            has_strong_signal = any(asset[1]['score'] >= 4 for asset in sorted_assets)
            all_neutral = all(asset[1]['score'] == 3 for asset in sorted_assets)
            
            if all_neutral:
                print("⚪ TÜM VARLIK SINIFLARI NÖTR DURUMDA")
                print("📊 Forex, Stocks ve Crypto'da net yönlü sinyal tespit edilemedi")
                print("🎯 Sistem Önerisi: TEMKİNLİ GÖZLEM MOD")
                
                # NÖTR durumda "en iyi" diye bir şey yok
                print("❌ 'En İyi Performans' kategorisi oluşturulamadı - Yeterli sinyal yok")
                
            elif has_strong_signal:
                print(f"🏆 EN İYİ PERFORMANS: {best_asset[0]} - {best_asset[1]['status']}")
                print(f"⚠️ EN ZAYIF PERFORMANS: {worst_asset[0]} - {worst_asset[1]['status']}")
                
                opportunities.append({
                    'type': 'asset_class',
                    'symbol': best_asset[0],
                    'recommendation': f"Focus on {best_asset[0]}",
                    'reason': f"Güçlü sinyaller: {best_asset[1]['status']}",
                    'risk': 'ORTA',
                    'confidence': 'YÜKSEK'
                })
            else:
                # Zayıf sinyaller durumu
                print(f"🟡 EN GÖRECELI İYİ: {best_asset[0]} - {best_asset[1]['status']}")
                print(f"⚠️ Ancak güçlü bir sinyal değil - Temkinli yaklaşım önerilir")
                
                opportunities.append({
                    'type': 'weak_signal',
                    'symbol': best_asset[0],
                    'recommendation': f"Temkinli gözlem: {best_asset[0]}",
                    'reason': f"Göreceli olarak daha iyi ama zayıf: {best_asset[1]['status']}",
                    'risk': 'DÜŞÜK',
                    'confidence': 'DÜŞÜK'
                })
        
        # En pozitif stock sentiment - ama MANTIKLI şekilde
        if stock_sentiments:
            top_sentiment_stock = max(stock_sentiments, key=lambda x: x['sentiment'])
            
            # Sadece gerçekten yüksek sentiment'larda öneri yap
            if top_sentiment_stock['sentiment'] > 0.20:
                print(f"💎 ÖNE ÇIKAN HİSSE: {top_sentiment_stock['stock']} ({top_sentiment_stock['sentiment']:+.3f})")
                print(f"📊 Bu, çok güçlü pozitif sentiment - Takip edilmeli")
                
                opportunities.append({
                    'type': 'individual_stock',
                    'symbol': top_sentiment_stock['stock'],
                    'recommendation': f"{top_sentiment_stock['stock']} - STRONG BUY consideration",
                    'reason': f"Çok yüksek pozitif sentiment: {top_sentiment_stock['sentiment']:+.3f}",
                    'risk': 'YÜKSEK',
                    'confidence': 'YÜKSEK',
                    'price': top_sentiment_stock['price']
                })
            elif top_sentiment_stock['sentiment'] > 0.15:
                print(f"📈 İLGİNÇ HİSSE: {top_sentiment_stock['stock']} ({top_sentiment_stock['sentiment']:+.3f})")
                print(f"📊 Orta-güçlü pozitif sentiment - Gözlem listesine alınabilir")
                
                opportunities.append({
                    'type': 'watchlist_stock',
                    'symbol': top_sentiment_stock['stock'],
                    'recommendation': f"{top_sentiment_stock['stock']} - Gözlem listesine ekle",
                    'reason': f"Orta-güçlü pozitif sentiment: {top_sentiment_stock['sentiment']:+.3f}",
                    'risk': 'ORTA',
                    'confidence': 'ORTA',
                    'price': top_sentiment_stock['price']
                })
            else:
                print(f"📊 En yüksek hisse sentiment: {top_sentiment_stock['stock']} ({top_sentiment_stock['sentiment']:+.3f})")
                print(f"⚪ Ancak yeterince güçlü değil - Genel piyasa belirsizliği hakim")
        
        # Global sentiment'e göre genel strateji - MANTIKLI
        strategy_recommendation = ""
        if global_sentiment:
            sentiment_score = global_sentiment['overall_sentiment']
            if sentiment_score > 0.15:
                print(f"🎯 GENEL STRATEJİ: Risk alma zamanı - Güçlü pozitif ruh hali")
                strategy_recommendation = "RISK-ON"
            elif sentiment_score > 0.05:
                print(f"🟡 GENEL STRATEJİ: Temkinli iyimserlik - Seçici olun")
                strategy_recommendation = "CAUTIOUS-POSITIVE"  
            elif sentiment_score < -0.15:
                print(f"🛡️ GENEL STRATEJİ: Risk kaçınma - Defensive pozisyon")
                strategy_recommendation = "RISK-OFF"
            elif sentiment_score < -0.05:
                print(f"⚠️ GENEL STRATEJİ: Belirsizlik modu - Pozisyon almaktan kaçının")
                strategy_recommendation = "CAUTIOUS-NEGATIVE"
            else:
                print(f"⚖️ GENEL STRATEJİ: Tam belirsizlik - BEKLE ve GÖZLE")
                strategy_recommendation = "WAIT_AND_WATCH"
        
        # 5️⃣ AKILLI ÖNERİLER - Mantıklı karar verme
        print(f"\n5️⃣ GÜNLÜK ÖNERİLER ve AKSIYON PLANI")
        print("-" * 50)
        
        analysis_time = time.time() - analysis_start
        
        print(f"⏱️ Toplam Analiz Süresi: {analysis_time:.1f} saniye")
        print(f"📊 Analiz Edilen Enstrüman: {len(briefing_results['multi_asset']) + len(briefing_results['hot_stocks'])}")
        print()
        
        # ✅ MANTIKLI ÖNERİ MANTĞI
        if not opportunities:
            # Hiç fırsat yok durumu
            print("🎯 GÜNÜN STRATEJİSİ: TEMKİNLİ GÖZLEM")
            print()
            print("📊 DURUM RAPORU:")
            print("  • Tüm varlık sınıflarında net yönlü sinyal tespit edilemedi")
            print("  • Piyasalar kararsız ve yönsüz seyir izliyor")
            print("  • En iyi strateji: Pozisyon almaktan kaçınmak")
            print()
            print("⚠️ ÖNERİ: Bugün net bir alım-satım fırsatı bulunmadığından,")
            print("         piyasayı gözlemlemek ve beklemek en mantıklı yaklaşım.")
            
        elif strategy_recommendation == "WAIT_AND_WATCH":
            # Belirsizlik durumu
            print("🎯 GÜNÜN STRATEJİSİ: BEKLE ve GÖZLE")
            print()
            print("📊 DURUM RAPORU:")
            print("  • Global sentiment belirsiz (nötr bölge)")
            print("  • Teknik sinyaller henüz net değil")
            print("  • Risk alma için çok erken")
            print()
            
            if opportunities:
                print("👀 GÖZLEM LİSTESİ:")
                for i, opp in enumerate(opportunities[:2], 1):
                    print(f"  {i}. {opp['recommendation']}")
                    print(f"     💡 Sebep: {opp['reason']}")
                    if 'price' in opp:
                        print(f"     💰 Fiyat: ${opp['price']:.2f}")
                    print(f"     ⚖️ Risk: {opp['risk']} | Güven: {opp['confidence']}")
                    print()
        else:
            # Normal öneri durumu
            print("🎯 GÜNÜN FIRSATLARı:")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"  {i}. {opp['recommendation']}")
                print(f"     💡 Sebep: {opp['reason']}")
                if 'price' in opp:
                    print(f"     💰 Güncel Fiyat: ${opp['price']:.2f}")
                print(f"     ⚖️ Risk: {opp['risk']} | Güven: {opp['confidence']}")
                print()
        
        # Son uyarılar
        print("⚠️ UNUTMAYIN:")
        print("  • Bu analiz sadece bilgilendirme amaçlıdır")
        print("  • Yatırım kararlarınızı kendi riskinize göre alın") 
        print("  • Stop-loss kullanmayı unutmayın")
        print("  • Portföy diversifikasyonu önemlidir")
        
        print(f"\n📈 Bir sonraki analiz: {datetime.now().strftime('%Y-%m-%d')} akşam güncelleme")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Günlük briefing hatası: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Ana program"""
    setup_logging()
    
    # API key kontrolü
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    if not api_key or api_key == 'demo':
        print("\n❌ Alpha Vantage API anahtarı bulunamadı!")
        print("💡 Lütfen API anahtarınızı ayarlayın:")
        print("   export ALPHA_VANTAGE_KEY='your_key_here'")
        print("   https://www.alphavantage.co/support/#api-key")
        return
    
    print(f"\n✅ Alpha Vantage API Key: {api_key[:8]}...")
    
    while True:
        show_menu()
        
        try:
            choice = input("\nSeçiminizi yapın (1-8): ").strip()
            
            if choice == '1':
                current_news_sentiment()
            elif choice == '2':
                smart_signal_generation()
            elif choice == '3':
                multi_asset_analysis() 
            elif choice == '4':
                hot_stocks_sentiment()
            elif choice == '5':
                forex_news_correlation()
            elif choice == '6':
                quick_sentiment_score()
            elif choice == '7':
                daily_market_briefing()
            elif choice == '8':
                print("\n👋 Alpha Vantage Trading Framework'den çıkılıyor...")
                break
            else:
                print("❌ Geçersiz seçim! (1-7 arası)")
                
        except KeyboardInterrupt:
            print("\n👋 Program sonlandırıldı!")
            break
        except Exception as e:
            print(f"\n❌ Beklenmeyen hata: {e}")

if __name__ == "__main__":
    main() 