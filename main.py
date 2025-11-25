from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys

def setup_chrome_driver(headless=False):
    """Setup Chrome WebDriver - bisa headless atau tampil window"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument('--headless=new')
    
    # Opsi untuk menghindari deteksi bot
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Opsi standar
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--mute-audio')
    
    # User agent normal
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Auto-install ChromeDriver dengan webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Hapus tanda webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def skip_ad_if_exists(driver):
    """Coba skip iklan jika tombol skip tersedia"""
    try:
        # Berbagai selector untuk tombol skip iklan
        skip_selectors = [
            "button.ytp-ad-skip-button",
            "button.ytp-skip-ad-button",
            ".ytp-ad-skip-button-modern",
            "button[class*='skip']",
            ".videoAdUiSkipButton",
            "button.skip-button",
            ".ytp-ad-skip-button-container button"
        ]
        
        for selector in skip_selectors:
            try:
                skip_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                skip_button.click()
                print("⏭️  Iklan berhasil di-skip!")
                time.sleep(1)
                return True
            except:
                continue
        
        return False
    except Exception as e:
        return False

def wait_for_ad_to_finish(driver, max_wait=30):
    """Tunggu iklan selesai jika tidak bisa di-skip"""
    print("⏳ Menunggu iklan selesai...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Cek apakah masih ada iklan
            ad_playing = driver.find_elements(By.CSS_SELECTOR, 
                ".video-ads.ytp-ad-module, .ytp-ad-player-overlay, .ytp-ad-text")
            
            if not ad_playing:
                print("✅ Iklan selesai!")
                return True
            
            # Coba skip lagi
            if skip_ad_if_exists(driver):
                return True
            
            # Tunggu sebentar
            time.sleep(2)
            
        except Exception as e:
            pass
    
    print("⚠️  Timeout menunggu iklan selesai")
    return False

def handle_youtube_ads(driver):
    """Handle iklan YouTube dengan menonton/skip"""
    try:
        # Tunggu video player muncul
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "video"))
        )
        
        print("🎬 Video player terdeteksi")
        time.sleep(3)  # Tunggu iklan muncul
        
        # Cek apakah ada iklan
        ad_elements = driver.find_elements(By.CSS_SELECTOR, 
            ".video-ads.ytp-ad-module, .ytp-ad-player-overlay, .ad-showing")
        
        if ad_elements:
            print("📺 Iklan terdeteksi!")
            
            # Tunggu beberapa detik untuk tombol skip muncul
            time.sleep(5)
            
            # Coba skip iklan
            if not skip_ad_if_exists(driver):
                # Jika tidak bisa skip, tunggu iklan selesai
                wait_for_ad_to_finish(driver)
        else:
            print("✅ Tidak ada iklan, video langsung diputar")
        
        return True
        
    except TimeoutException:
        print("⚠️  Video player tidak ditemukan")
        return False
    except Exception as e:
        print(f"❌ Error handling ads: {str(e)}")
        return False

def play_video(driver, video_url):
    """Buka dan putar video"""
    try:
        print(f"🌐 Membuka URL: {video_url}")
        driver.get(video_url)
        
        # Handle iklan
        if handle_youtube_ads(driver):
            print("▶️  Video sedang diputar...")
            
            # Play video jika terpause
            try:
                video = driver.find_element(By.CSS_SELECTOR, "video")
                driver.execute_script("arguments[0].play();", video)
            except:
                pass
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def monitor_ads_continuously(driver, duration_minutes=10):
    """Monitor dan handle iklan yang muncul selama video berjalan"""
    print(f"👀 Monitoring iklan selama {duration_minutes} menit...")
    
    end_time = time.time() + (duration_minutes * 60)
    check_count = 0
    
    while time.time() < end_time:
        try:
            check_count += 1
            
            # Cek apakah ada iklan yang muncul
            ad_elements = driver.find_elements(By.CSS_SELECTOR, 
                ".video-ads.ytp-ad-module, .ytp-ad-player-overlay, .ad-showing")
            
            if ad_elements:
                print(f"\n📺 Iklan baru terdeteksi! (Check #{check_count})")
                time.sleep(5)  # Tunggu tombol skip
                
                if not skip_ad_if_exists(driver):
                    wait_for_ad_to_finish(driver)
            
            # Cek apakah video masih berjalan
            try:
                video = driver.find_element(By.CSS_SELECTOR, "video")
                is_paused = driver.execute_script("return arguments[0].paused;", video)
                current_time = driver.execute_script("return arguments[0].currentTime;", video)
                duration = driver.execute_script("return arguments[0].duration;", video)
                
                if is_paused:
                    print("⏸️  Video terpause, mencoba play...")
                    driver.execute_script("arguments[0].play();", video)
                
                # Tampilkan progress setiap 30 detik
                if check_count % 6 == 0:
                    progress = (current_time / duration * 100) if duration > 0 else 0
                    print(f"📊 Progress video: {progress:.1f}% ({int(current_time)}s / {int(duration)}s)")
                    
            except Exception as e:
                pass
            
            # Tunggu sebelum cek lagi
            time.sleep(5)
            
        except Exception as e:
            print(f"⚠️  Error saat monitoring: {str(e)}")
            time.sleep(5)
    
    print("\n✅ Monitoring selesai!")

def main():
    print("=" * 60)
    print("🎥 CHROME VIDEO WATCHER - AUTO SKIP IKLAN")
    print("=" * 60)
    
    # Input URL video
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        video_url = input("\n🔗 Masukkan URL video: ").strip()
    
    if not video_url:
        print("❌ URL tidak boleh kosong!")
        return
    
    # Tanya mode headless atau tidak
    mode = input("\n🖥️  Tampilkan Chrome window? (y/n, default=y): ").strip().lower()
    headless = mode == 'n'
    
    # Tanya durasi monitoring
    duration_input = input("\n⏱️  Durasi monitoring (menit, default=10): ").strip()
    duration = int(duration_input) if duration_input.isdigit() else 10
    
    print("\n🚀 Memulai Chrome WebDriver...")
    print("📥 Downloading ChromeDriver jika belum tersedia...\n")
    
    driver = None
    
    try:
        # Setup driver
        driver = setup_chrome_driver(headless=headless)
        print("✅ Chrome berhasil dijalankan!\n")
        
        # Putar video
        if play_video(driver, video_url):
            # Monitor iklan secara kontinyu
            monitor_ads_continuously(driver, duration_minutes=duration)
        else:
            print("❌ Gagal memutar video")
        
        print("\n✅ Proses selesai!")
        print("🔒 Browser akan tetap terbuka selama 30 detik...")
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Program dihentikan oleh user (Ctrl+C)")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("🔒 Browser ditutup")

if __name__ == '__main__':
    main()
