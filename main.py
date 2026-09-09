# main.py
import foundry_local_sdk

def main():
    print("Harika! Foundry Local SDK başarıyla içeri aktarıldı.")
    print("Kütüphane içerisindeki erişilebilir modüller şunlar:")
    print(dir(foundry_local_sdk))

if __name__ == "__main__":
    main()