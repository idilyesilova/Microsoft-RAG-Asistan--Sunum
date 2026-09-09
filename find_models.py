from foundry_local_sdk import FoundryLocalManager, Configuration

def list_all_models():
    print("Sistem başlatılıyor...")
    config = Configuration(app_name="SecureOps_Copilot")
    manager = FoundryLocalManager(config)
    
    print("\nKatalogdaki mevcut tüm modeller:")
    # Katalogdaki tüm modelleri çekiyoruz
    models = manager.catalog.list_models()
    
    for model in models:
        try:
            # Model nesnesinin ID'sini ekrana yazdırıyoruz
            print(f"- {model.id}")
        except AttributeError:
            # Eğer nesne değil direkt metinse kendini yazdır
            print(f"- {model}")

if __name__ == "__main__":
    list_all_models()