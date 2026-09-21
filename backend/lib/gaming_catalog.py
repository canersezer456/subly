"""Manually curated Gaming catalog.

Fiyatlar Türkiye'de yaygın satıcılardan derlenmiş yaklaşık gerçek fiyatlardır. Zamanla
elle güncellenir. `updated_at` alanı katalog güncellemesinin tarihini gösterir.

İleride resmi API/affiliate entegrasyonu eklendiğinde `offers` bu modül dışından
enjekte edilebilecek şekilde tasarlandı — modeller ve şema aynı kalır.
"""

from datetime import datetime

CATALOG_UPDATED_AT = "2026-02-15"

SELLERS: list[dict] = [
    {
        "id": "gamesatis",
        "name": "GameSatış",
        "domain": "gamesatis.com",
        "reliability": "verified",
        "delivery": "Anında",
        "return_policy": "14 gün cayma hakkı; kullanılmamış kodlarda iade",
        "payment_methods": ["Kredi kartı", "Havale", "BKM Express"],
        "note": "En eski Türk oyun kodu marketlerinden biri; müşteri hizmetleri 7/24.",
    },
    {
        "id": "bynogame",
        "name": "ByNoGame",
        "domain": "bynogame.com",
        "reliability": "verified",
        "delivery": "Anında",
        "return_policy": "14 gün cayma hakkı; kod kullanılırsa iade yok",
        "payment_methods": ["Kredi kartı", "Havale", "Papara"],
        "note": "Elektronik pin, hesap ve boost hizmetleri; güvenli teslimat sistemi.",
    },
    {
        "id": "oyunfor",
        "name": "Oyunfor",
        "domain": "oyunfor.com",
        "reliability": "trusted",
        "delivery": "1-5 dk",
        "return_policy": "14 gün cayma hakkı; teslim edilmiş dijital ürünlerde iade koşullu",
        "payment_methods": ["Kredi kartı", "Havale"],
        "note": "20+ yıllık dijital oyun pazarı, geniş envanter.",
    },
    {
        "id": "hesap-com-tr",
        "name": "Hesap.com.tr",
        "domain": "hesap.com.tr",
        "reliability": "trusted",
        "delivery": "1-5 dk",
        "return_policy": "14 gün cayma hakkı; kullanılmamış ürünlerde iade",
        "payment_methods": ["Kredi kartı", "Havale"],
        "note": "Oyun içi para ve hesap satışında yaygın.",
    },
    {
        "id": "trendyol",
        "name": "Trendyol",
        "domain": "trendyol.com",
        "reliability": "trusted",
        "delivery": "5-15 dk",
        "return_policy": "Trendyol iade politikası; dijital ürünlerde satıcı bağımlı",
        "payment_methods": ["Kredi kartı", "Trendyol Cüzdanım"],
        "note": "Üçüncü taraf satıcı; satıcı puanına dikkat.",
    },
    {
        "id": "hepsiburada",
        "name": "Hepsiburada",
        "domain": "hepsiburada.com",
        "reliability": "trusted",
        "delivery": "5-15 dk",
        "return_policy": "14 gün iade; dijital ürünlerde satıcı politikası geçerli",
        "payment_methods": ["Kredi kartı", "Hepsipay"],
        "note": "Marketplace; satıcının onaylı rozetini kontrol et.",
    },
    {
        "id": "turkcell-pasaj",
        "name": "Turkcell Pasaj",
        "domain": "pasaj.com.tr",
        "reliability": "verified",
        "delivery": "Anında",
        "return_policy": "Turkcell Pasaj güvencesi; kullanılmamış kodlarda iade",
        "payment_methods": ["Kredi kartı", "Turkcell fatura"],
        "note": "Operatör güvencesi; sık kampanya.",
    },
]

SELLERS_BY_ID = {s["id"]: s for s in SELLERS}


def _seller(seller_id: str) -> dict:
    return SELLERS_BY_ID[seller_id]


# Her oyun için: slug, isim, para birimi, kategori, aksent rengi, ikon URL,
# kısa açıklama, popüler bayrağı, ve ürün listesi (name, amount, unit, offers).
# `offers`: (seller_id, price_try, original_price_try, delivery, campaign, url_path)
GAMES: list[dict] = [
    {
        "slug": "league-of-legends",
        "name": "League of Legends",
        "currency": "RP",
        "category": "MOBA",
        "accent": "#0AC8B9",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/League_of_Legends_2019_vector.svg/512px-League_of_Legends_2019_vector.svg.png",
        "tagline": "Riot Points ile şampiyon, ton ve battle pass",
        "popular": True,
        "products": [
            {"name": "590 RP", "amount": 590, "unit": "RP", "tag": None, "offers": [
                ("gamesatis", 129.00, 135.00, "Anında", None, "/pin/league-of-legends-rp"),
                ("bynogame", 129.90, None, "Anında", None, "/kategori/league-of-legends"),
                ("oyunfor", 132.00, None, "1-5 dk", None, "/league-of-legends"),
                ("turkcell-pasaj", 135.00, None, "Anında", None, "/oyun/league-of-legends"),
            ]},
            {"name": "1275 RP", "amount": 1275, "unit": "RP", "tag": "popular", "offers": [
                ("bynogame", 279.00, 299.00, "Anında", "Şubat kampanyası", "/kategori/league-of-legends"),
                ("gamesatis", 279.90, None, "Anında", None, "/pin/league-of-legends-rp"),
                ("oyunfor", 285.00, None, "1-5 dk", None, "/league-of-legends"),
                ("hesap-com-tr", 289.00, None, "1-5 dk", None, "/lol-rp"),
            ]},
            {"name": "2105 RP", "amount": 2105, "unit": "RP", "tag": "best_value", "offers": [
                ("gamesatis", 465.00, 495.00, "Anında", "Şubat kampanyası", "/pin/league-of-legends-rp"),
                ("bynogame", 469.00, None, "Anında", None, "/kategori/league-of-legends"),
                ("oyunfor", 475.00, None, "1-5 dk", None, "/league-of-legends"),
                ("turkcell-pasaj", 489.00, None, "Anında", "Yıldız kampanyası", "/oyun/league-of-legends"),
                ("hepsiburada", 499.00, None, "5-15 dk", None, "/x/lol-rp"),
            ]},
            {"name": "3250 RP", "amount": 3250, "unit": "RP", "tag": None, "offers": [
                ("gamesatis", 719.00, None, "Anında", None, "/pin/league-of-legends-rp"),
                ("bynogame", 725.00, None, "Anında", None, "/kategori/league-of-legends"),
                ("oyunfor", 735.00, None, "1-5 dk", None, "/league-of-legends"),
            ]},
        ],
    },
    {
        "slug": "valorant",
        "name": "Valorant",
        "currency": "VP",
        "category": "FPS",
        "accent": "#FF4655",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/512px-Valorant_logo_-_pink_color_version.svg.png",
        "tagline": "Valorant Points ile silah kaplama, ajan, battle pass",
        "popular": True,
        "products": [
            {"name": "475 VP", "amount": 475, "unit": "VP", "tag": None, "offers": [
                ("bynogame", 105.00, None, "Anında", None, "/kategori/valorant"),
                ("gamesatis", 109.00, None, "Anında", None, "/pin/valorant-vp"),
                ("oyunfor", 112.00, None, "1-5 dk", None, "/valorant"),
            ]},
            {"name": "1000 VP", "amount": 1000, "unit": "VP", "tag": "popular", "offers": [
                ("gamesatis", 219.00, 235.00, "Anında", "Şubat kampanyası", "/pin/valorant-vp"),
                ("bynogame", 219.90, None, "Anında", None, "/kategori/valorant"),
                ("hesap-com-tr", 225.00, None, "1-5 dk", None, "/valorant-vp"),
                ("turkcell-pasaj", 229.00, None, "Anında", None, "/oyun/valorant"),
            ]},
            {"name": "2050 VP", "amount": 2050, "unit": "VP", "tag": "best_value", "offers": [
                ("bynogame", 445.00, 475.00, "Anında", "Şubat kampanyası", "/kategori/valorant"),
                ("gamesatis", 449.00, None, "Anında", None, "/pin/valorant-vp"),
                ("oyunfor", 459.00, None, "1-5 dk", None, "/valorant"),
                ("hepsiburada", 475.00, None, "5-15 dk", None, "/x/valorant-vp"),
            ]},
            {"name": "3650 VP", "amount": 3650, "unit": "VP", "tag": None, "offers": [
                ("gamesatis", 795.00, None, "Anında", None, "/pin/valorant-vp"),
                ("bynogame", 799.00, None, "Anında", None, "/kategori/valorant"),
                ("oyunfor", 815.00, None, "1-5 dk", None, "/valorant"),
            ]},
        ],
    },
    {
        "slug": "pubg-mobile",
        "name": "PUBG Mobile",
        "currency": "UC",
        "category": "Battle Royale",
        "accent": "#F2A900",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/PUBG_Mobile_Logo_2023.png/512px-PUBG_Mobile_Logo_2023.png",
        "tagline": "Unknown Cash ile Royale Pass ve kostüm sandığı",
        "popular": True,
        "products": [
            {"name": "60 UC", "amount": 60, "unit": "UC", "tag": None, "offers": [
                ("bynogame", 35.00, None, "Anında", None, "/kategori/pubg-mobile"),
                ("gamesatis", 37.00, None, "Anında", None, "/pin/pubg-mobile-uc"),
                ("oyunfor", 39.00, None, "1-5 dk", None, "/pubg-mobile"),
            ]},
            {"name": "325 UC", "amount": 325, "unit": "UC", "tag": "popular", "offers": [
                ("gamesatis", 155.00, 169.00, "Anında", "Şubat kampanyası", "/pin/pubg-mobile-uc"),
                ("bynogame", 156.00, None, "Anında", None, "/kategori/pubg-mobile"),
                ("oyunfor", 162.00, None, "1-5 dk", None, "/pubg-mobile"),
                ("turkcell-pasaj", 165.00, None, "Anında", None, "/oyun/pubg-mobile"),
            ]},
            {"name": "660 UC", "amount": 660, "unit": "UC", "tag": "best_value", "offers": [
                ("bynogame", 305.00, 329.00, "Anında", "Şubat kampanyası", "/kategori/pubg-mobile"),
                ("gamesatis", 309.00, None, "Anında", None, "/pin/pubg-mobile-uc"),
                ("hesap-com-tr", 315.00, None, "1-5 dk", None, "/pubg-uc"),
            ]},
            {"name": "1800 UC", "amount": 1800, "unit": "UC", "tag": None, "offers": [
                ("gamesatis", 815.00, None, "Anında", None, "/pin/pubg-mobile-uc"),
                ("bynogame", 819.00, None, "Anında", None, "/kategori/pubg-mobile"),
                ("oyunfor", 829.00, None, "1-5 dk", None, "/pubg-mobile"),
            ]},
        ],
    },
    {
        "slug": "mobile-legends",
        "name": "Mobile Legends: Bang Bang",
        "currency": "Elmas",
        "category": "MOBA",
        "accent": "#5B8CFF",
        "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/b/bd/Mobile_Legends_Bang_Bang_Logo.png/512px-Mobile_Legends_Bang_Bang_Logo.png",
        "tagline": "Elmas ile kahraman ve kostüm",
        "popular": False,
        "products": [
            {"name": "86 Elmas", "amount": 86, "unit": "Elmas", "tag": None, "offers": [
                ("bynogame", 55.00, None, "Anında", None, "/kategori/mobile-legends"),
                ("oyunfor", 58.00, None, "1-5 dk", None, "/mobile-legends"),
                ("gamesatis", 59.00, None, "Anında", None, "/pin/mobile-legends"),
            ]},
            {"name": "172 Elmas", "amount": 172, "unit": "Elmas", "tag": "popular", "offers": [
                ("gamesatis", 105.00, 115.00, "Anında", None, "/pin/mobile-legends"),
                ("bynogame", 109.00, None, "Anında", None, "/kategori/mobile-legends"),
                ("oyunfor", 112.00, None, "1-5 dk", None, "/mobile-legends"),
            ]},
            {"name": "706 Elmas", "amount": 706, "unit": "Elmas", "tag": "best_value", "offers": [
                ("bynogame", 425.00, 449.00, "Anında", "Şubat kampanyası", "/kategori/mobile-legends"),
                ("gamesatis", 435.00, None, "Anında", None, "/pin/mobile-legends"),
                ("oyunfor", 449.00, None, "1-5 dk", None, "/mobile-legends"),
            ]},
        ],
    },
    {
        "slug": "roblox",
        "name": "Roblox",
        "currency": "Robux",
        "category": "Sandbox",
        "accent": "#00A2FF",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Roblox_Logo_2022.svg/512px-Roblox_Logo_2022.svg.png",
        "tagline": "Robux ile Roblox içi item ve pass",
        "popular": True,
        "products": [
            {"name": "400 Robux", "amount": 400, "unit": "Robux", "tag": None, "offers": [
                ("bynogame", 179.00, 189.00, "Anında", None, "/kategori/roblox"),
                ("gamesatis", 185.00, None, "Anında", None, "/pin/roblox-robux"),
                ("oyunfor", 189.00, None, "1-5 dk", None, "/roblox"),
                ("turkcell-pasaj", 195.00, None, "Anında", None, "/oyun/roblox"),
            ]},
            {"name": "800 Robux", "amount": 800, "unit": "Robux", "tag": "popular", "offers": [
                ("gamesatis", 355.00, 379.00, "Anında", "Şubat kampanyası", "/pin/roblox-robux"),
                ("bynogame", 359.00, None, "Anında", None, "/kategori/roblox"),
                ("oyunfor", 369.00, None, "1-5 dk", None, "/roblox"),
                ("hepsiburada", 385.00, None, "5-15 dk", None, "/x/roblox"),
            ]},
            {"name": "1700 Robux", "amount": 1700, "unit": "Robux", "tag": "best_value", "offers": [
                ("bynogame", 745.00, 799.00, "Anında", "Şubat kampanyası", "/kategori/roblox"),
                ("gamesatis", 755.00, None, "Anında", None, "/pin/roblox-robux"),
                ("oyunfor", 769.00, None, "1-5 dk", None, "/roblox"),
                ("hesap-com-tr", 785.00, None, "1-5 dk", None, "/roblox-robux"),
            ]},
        ],
    },
    {
        "slug": "fortnite",
        "name": "Fortnite",
        "currency": "V-Bucks",
        "category": "Battle Royale",
        "accent": "#9D4DFF",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Fortnite_F_lettermark_logo.png/240px-Fortnite_F_lettermark_logo.png",
        "tagline": "V-Bucks ile skin ve battle pass",
        "popular": True,
        "products": [
            {"name": "1000 V-Bucks", "amount": 1000, "unit": "V-Bucks", "tag": "popular", "offers": [
                ("gamesatis", 289.00, 309.00, "Anında", "Şubat kampanyası", "/pin/fortnite-v-bucks"),
                ("bynogame", 295.00, None, "Anında", None, "/kategori/fortnite"),
                ("oyunfor", 305.00, None, "1-5 dk", None, "/fortnite"),
                ("turkcell-pasaj", 315.00, None, "Anında", None, "/oyun/fortnite"),
            ]},
            {"name": "2800 V-Bucks", "amount": 2800, "unit": "V-Bucks", "tag": "best_value", "offers": [
                ("bynogame", 745.00, 799.00, "Anında", "Şubat kampanyası", "/kategori/fortnite"),
                ("gamesatis", 755.00, None, "Anında", None, "/pin/fortnite-v-bucks"),
                ("oyunfor", 775.00, None, "1-5 dk", None, "/fortnite"),
            ]},
            {"name": "5000 V-Bucks", "amount": 5000, "unit": "V-Bucks", "tag": None, "offers": [
                ("gamesatis", 1325.00, None, "Anında", None, "/pin/fortnite-v-bucks"),
                ("bynogame", 1335.00, None, "Anında", None, "/kategori/fortnite"),
            ]},
        ],
    },
    {
        "slug": "steam",
        "name": "Steam Cüzdan",
        "currency": "TL Kod",
        "category": "Platform",
        "accent": "#66C0F4",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/512px-Steam_icon_logo.svg.png",
        "tagline": "Steam Cüzdan kodu ile oyun / DLC / mikro-ödeme",
        "popular": True,
        "products": [
            {"name": "50 ₺ Steam Cüzdan", "amount": 50, "unit": "TL", "tag": None, "offers": [
                ("bynogame", 55.00, None, "Anında", None, "/kategori/steam-cuzdan-kodu"),
                ("gamesatis", 57.00, None, "Anında", None, "/pin/steam-cuzdan-kodu"),
                ("oyunfor", 58.00, None, "1-5 dk", None, "/steam-cuzdan-kodu"),
            ]},
            {"name": "100 ₺ Steam Cüzdan", "amount": 100, "unit": "TL", "tag": "popular", "offers": [
                ("bynogame", 109.00, None, "Anında", None, "/kategori/steam-cuzdan-kodu"),
                ("gamesatis", 112.00, None, "Anında", None, "/pin/steam-cuzdan-kodu"),
                ("oyunfor", 115.00, None, "1-5 dk", None, "/steam-cuzdan-kodu"),
                ("turkcell-pasaj", 119.00, None, "Anında", None, "/oyun/steam"),
            ]},
            {"name": "250 ₺ Steam Cüzdan", "amount": 250, "unit": "TL", "tag": "best_value", "offers": [
                ("bynogame", 272.00, None, "Anında", "Şubat kampanyası", "/kategori/steam-cuzdan-kodu"),
                ("gamesatis", 275.00, None, "Anında", None, "/pin/steam-cuzdan-kodu"),
                ("oyunfor", 285.00, None, "1-5 dk", None, "/steam-cuzdan-kodu"),
                ("hepsiburada", 295.00, None, "5-15 dk", None, "/x/steam-cuzdan"),
            ]},
            {"name": "500 ₺ Steam Cüzdan", "amount": 500, "unit": "TL", "tag": None, "offers": [
                ("bynogame", 545.00, None, "Anında", None, "/kategori/steam-cuzdan-kodu"),
                ("gamesatis", 549.00, None, "Anında", None, "/pin/steam-cuzdan-kodu"),
            ]},
        ],
    },
    {
        "slug": "playstation",
        "name": "PlayStation Store",
        "currency": "PSN",
        "category": "Konsol",
        "accent": "#006FCD",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/PlayStation_logo.svg/512px-PlayStation_logo.svg.png",
        "tagline": "PSN Cüzdan kodu ve PlayStation Plus üyelikleri",
        "popular": True,
        "products": [
            {"name": "200 TL PSN Cüzdan", "amount": 200, "unit": "TL", "tag": "popular", "offers": [
                ("bynogame", 219.00, None, "Anında", None, "/kategori/playstation-store"),
                ("gamesatis", 225.00, None, "Anında", None, "/pin/psn-cuzdan-kodu"),
                ("oyunfor", 229.00, None, "1-5 dk", None, "/playstation"),
                ("turkcell-pasaj", 235.00, None, "Anında", None, "/oyun/psn"),
            ]},
            {"name": "500 TL PSN Cüzdan", "amount": 500, "unit": "TL", "tag": "best_value", "offers": [
                ("bynogame", 545.00, 579.00, "Anında", "Şubat kampanyası", "/kategori/playstation-store"),
                ("gamesatis", 555.00, None, "Anında", None, "/pin/psn-cuzdan-kodu"),
                ("oyunfor", 569.00, None, "1-5 dk", None, "/playstation"),
                ("hepsiburada", 585.00, None, "5-15 dk", None, "/x/psn"),
            ]},
            {"name": "PS Plus Essential 3 Ay", "amount": 3, "unit": "Ay", "tag": None, "offers": [
                ("bynogame", 385.00, None, "Anında", None, "/kategori/ps-plus"),
                ("oyunfor", 395.00, None, "1-5 dk", None, "/ps-plus"),
                ("gamesatis", 399.00, None, "Anında", None, "/pin/ps-plus"),
            ]},
        ],
    },
    {
        "slug": "xbox",
        "name": "Xbox / Game Pass",
        "currency": "Xbox Kod",
        "category": "Konsol",
        "accent": "#0E7A0D",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Xbox_one_logo.svg/512px-Xbox_one_logo.svg.png",
        "tagline": "Xbox Gift Card ve Game Pass Ultimate üyelikleri",
        "popular": True,
        "products": [
            {"name": "200 TL Xbox Gift Card", "amount": 200, "unit": "TL", "tag": "popular", "offers": [
                ("bynogame", 219.00, None, "Anında", None, "/kategori/xbox-live"),
                ("gamesatis", 225.00, None, "Anında", None, "/pin/xbox-live-tl"),
                ("oyunfor", 229.00, None, "1-5 dk", None, "/xbox"),
            ]},
            {"name": "Game Pass Ultimate 1 Ay", "amount": 1, "unit": "Ay", "tag": "best_value", "offers": [
                ("bynogame", 165.00, 189.00, "Anında", "Şubat kampanyası", "/kategori/game-pass"),
                ("gamesatis", 175.00, None, "Anında", None, "/pin/game-pass"),
                ("oyunfor", 179.00, None, "1-5 dk", None, "/game-pass-ultimate"),
                ("hepsiburada", 189.00, None, "5-15 dk", None, "/x/game-pass"),
            ]},
            {"name": "Game Pass Ultimate 3 Ay", "amount": 3, "unit": "Ay", "tag": None, "offers": [
                ("bynogame", 485.00, None, "Anında", None, "/kategori/game-pass"),
                ("gamesatis", 495.00, None, "Anında", None, "/pin/game-pass"),
                ("oyunfor", 515.00, None, "1-5 dk", None, "/game-pass-ultimate"),
            ]},
        ],
    },
    {
        "slug": "nintendo",
        "name": "Nintendo eShop",
        "currency": "TL Kod",
        "category": "Konsol",
        "accent": "#E60012",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Nintendo_red_logo.svg/512px-Nintendo_red_logo.svg.png",
        "tagline": "Nintendo eShop cüzdan kodları",
        "popular": False,
        "products": [
            {"name": "Nintendo eShop 150 ₺", "amount": 150, "unit": "TL", "tag": None, "offers": [
                ("bynogame", 165.00, None, "Anında", None, "/kategori/nintendo-eshop"),
                ("gamesatis", 169.00, None, "Anında", None, "/pin/nintendo-eshop"),
                ("oyunfor", 175.00, None, "1-5 dk", None, "/nintendo-eshop"),
            ]},
            {"name": "Nintendo eShop 500 ₺", "amount": 500, "unit": "TL", "tag": "best_value", "offers": [
                ("bynogame", 545.00, None, "Anında", None, "/kategori/nintendo-eshop"),
                ("gamesatis", 555.00, None, "Anında", None, "/pin/nintendo-eshop"),
                ("oyunfor", 569.00, None, "1-5 dk", None, "/nintendo-eshop"),
            ]},
        ],
    },
    {
        "slug": "ea-fc",
        "name": "EA FC 25",
        "currency": "FC Points",
        "category": "Spor",
        "accent": "#005EB8",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/EA_Sports_FC_logo.svg/512px-EA_Sports_FC_logo.svg.png",
        "tagline": "FC Points ile Ultimate Team paketleri",
        "popular": True,
        "products": [
            {"name": "1050 FC Points", "amount": 1050, "unit": "FC Points", "tag": "popular", "offers": [
                ("bynogame", 245.00, 269.00, "Anında", "Şubat kampanyası", "/kategori/ea-fc-25"),
                ("gamesatis", 255.00, None, "Anında", None, "/pin/ea-fc-25"),
                ("oyunfor", 265.00, None, "1-5 dk", None, "/ea-fc-25"),
            ]},
            {"name": "2200 FC Points", "amount": 2200, "unit": "FC Points", "tag": "best_value", "offers": [
                ("bynogame", 495.00, 545.00, "Anında", "Şubat kampanyası", "/kategori/ea-fc-25"),
                ("gamesatis", 509.00, None, "Anında", None, "/pin/ea-fc-25"),
                ("oyunfor", 525.00, None, "1-5 dk", None, "/ea-fc-25"),
                ("hepsiburada", 549.00, None, "5-15 dk", None, "/x/ea-fc"),
            ]},
        ],
    },
    {
        "slug": "genshin-impact",
        "name": "Genshin Impact",
        "currency": "Genesis Crystal",
        "category": "RPG",
        "accent": "#4B7BEC",
        "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a0/Genshin_Impact_logo.png/512px-Genshin_Impact_logo.png",
        "tagline": "Genesis Crystal / Blessing of Welkin Moon",
        "popular": True,
        "products": [
            {"name": "60 + 3 Genesis Crystals", "amount": 60, "unit": "Crystal", "tag": None, "offers": [
                ("bynogame", 39.00, None, "Anında", None, "/kategori/genshin-impact"),
                ("gamesatis", 42.00, None, "Anında", None, "/pin/genshin-impact"),
                ("oyunfor", 45.00, None, "1-5 dk", None, "/genshin-impact"),
            ]},
            {"name": "Blessing of Welkin Moon", "amount": 1, "unit": "Ay", "tag": "best_value", "offers": [
                ("bynogame", 155.00, 179.00, "Anında", "Şubat kampanyası", "/kategori/genshin-impact"),
                ("gamesatis", 165.00, None, "Anında", None, "/pin/genshin-impact"),
                ("oyunfor", 175.00, None, "1-5 dk", None, "/genshin-impact"),
            ]},
            {"name": "1090 + 165 Crystals", "amount": 1090, "unit": "Crystal", "tag": "popular", "offers": [
                ("bynogame", 549.00, None, "Anında", None, "/kategori/genshin-impact"),
                ("gamesatis", 559.00, None, "Anında", None, "/pin/genshin-impact"),
                ("oyunfor", 569.00, None, "1-5 dk", None, "/genshin-impact"),
            ]},
        ],
    },
    {
        "slug": "cod-mobile",
        "name": "Call of Duty Mobile",
        "currency": "CP",
        "category": "FPS",
        "accent": "#FF9500",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Call_of_Duty_Mobile_logo.png/512px-Call_of_Duty_Mobile_logo.png",
        "tagline": "COD Points ile battle pass ve skinler",
        "popular": False,
        "products": [
            {"name": "80 CP", "amount": 80, "unit": "CP", "tag": None, "offers": [
                ("bynogame", 39.00, None, "Anında", None, "/kategori/cod-mobile"),
                ("gamesatis", 42.00, None, "Anında", None, "/pin/cod-mobile"),
                ("oyunfor", 45.00, None, "1-5 dk", None, "/cod-mobile"),
            ]},
            {"name": "400 CP", "amount": 400, "unit": "CP", "tag": "popular", "offers": [
                ("bynogame", 179.00, None, "Anında", None, "/kategori/cod-mobile"),
                ("gamesatis", 185.00, None, "Anında", None, "/pin/cod-mobile"),
                ("oyunfor", 189.00, None, "1-5 dk", None, "/cod-mobile"),
            ]},
            {"name": "1100 CP", "amount": 1100, "unit": "CP", "tag": "best_value", "offers": [
                ("bynogame", 449.00, 479.00, "Anında", "Şubat kampanyası", "/kategori/cod-mobile"),
                ("gamesatis", 459.00, None, "Anında", None, "/pin/cod-mobile"),
                ("oyunfor", 475.00, None, "1-5 dk", None, "/cod-mobile"),
            ]},
        ],
    },
    {
        "slug": "clash-of-clans",
        "name": "Clash of Clans",
        "currency": "Elmas",
        "category": "Strateji",
        "accent": "#FFC72C",
        "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/1/13/Clash_of_Clans_official_logo.png/512px-Clash_of_Clans_official_logo.png",
        "tagline": "Elmas paketleri ile hızlı yapılanma",
        "popular": False,
        "products": [
            {"name": "500 Elmas", "amount": 500, "unit": "Elmas", "tag": "popular", "offers": [
                ("bynogame", 165.00, None, "Anında", None, "/kategori/clash-of-clans"),
                ("gamesatis", 172.00, None, "Anında", None, "/pin/clash-of-clans"),
                ("oyunfor", 179.00, None, "1-5 dk", None, "/clash-of-clans"),
            ]},
            {"name": "1200 Elmas", "amount": 1200, "unit": "Elmas", "tag": "best_value", "offers": [
                ("bynogame", 379.00, 409.00, "Anında", None, "/kategori/clash-of-clans"),
                ("gamesatis", 389.00, None, "Anında", None, "/pin/clash-of-clans"),
                ("oyunfor", 399.00, None, "1-5 dk", None, "/clash-of-clans"),
            ]},
        ],
    },
    {
        "slug": "clash-royale",
        "name": "Clash Royale",
        "currency": "Elmas",
        "category": "Strateji",
        "accent": "#7C3AED",
        "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/2/2a/Clash_Royale_official_logo.png/512px-Clash_Royale_official_logo.png",
        "tagline": "Elmas ile sandık ve pass",
        "popular": False,
        "products": [
            {"name": "500 Elmas", "amount": 500, "unit": "Elmas", "tag": "popular", "offers": [
                ("bynogame", 165.00, None, "Anında", None, "/kategori/clash-royale"),
                ("gamesatis", 172.00, None, "Anında", None, "/pin/clash-royale"),
                ("oyunfor", 179.00, None, "1-5 dk", None, "/clash-royale"),
            ]},
            {"name": "1200 Elmas", "amount": 1200, "unit": "Elmas", "tag": "best_value", "offers": [
                ("bynogame", 379.00, 409.00, "Anında", None, "/kategori/clash-royale"),
                ("gamesatis", 389.00, None, "Anında", None, "/pin/clash-royale"),
                ("oyunfor", 399.00, None, "1-5 dk", None, "/clash-royale"),
            ]},
        ],
    },
    {
        "slug": "brawl-stars",
        "name": "Brawl Stars",
        "currency": "Elmas",
        "category": "Multiplayer",
        "accent": "#FFDA44",
        "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/Brawl_Stars_official_logo.png/512px-Brawl_Stars_official_logo.png",
        "tagline": "Brawl Pass ve elmas paketleri",
        "popular": True,
        "products": [
            {"name": "170 Elmas", "amount": 170, "unit": "Elmas", "tag": "popular", "offers": [
                ("bynogame", 145.00, None, "Anında", None, "/kategori/brawl-stars"),
                ("gamesatis", 149.00, None, "Anında", None, "/pin/brawl-stars"),
                ("oyunfor", 155.00, None, "1-5 dk", None, "/brawl-stars"),
            ]},
            {"name": "360 Elmas", "amount": 360, "unit": "Elmas", "tag": "best_value", "offers": [
                ("bynogame", 289.00, 319.00, "Anında", "Şubat kampanyası", "/kategori/brawl-stars"),
                ("gamesatis", 299.00, None, "Anında", None, "/pin/brawl-stars"),
                ("oyunfor", 309.00, None, "1-5 dk", None, "/brawl-stars"),
            ]},
        ],
    },
    {
        "slug": "minecraft",
        "name": "Minecraft",
        "currency": "Minecoins",
        "category": "Sandbox",
        "accent": "#5CA034",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Minecraft_2024.svg/512px-Minecraft_2024.svg.png",
        "tagline": "Minecoins ve Minecraft Java / Bedrock kod",
        "popular": False,
        "products": [
            {"name": "1720 Minecoins", "amount": 1720, "unit": "Minecoin", "tag": "popular", "offers": [
                ("bynogame", 245.00, None, "Anında", None, "/kategori/minecraft"),
                ("gamesatis", 255.00, None, "Anında", None, "/pin/minecraft"),
                ("oyunfor", 265.00, None, "1-5 dk", None, "/minecraft"),
            ]},
            {"name": "3500 Minecoins", "amount": 3500, "unit": "Minecoin", "tag": "best_value", "offers": [
                ("bynogame", 465.00, 499.00, "Anında", None, "/kategori/minecraft"),
                ("gamesatis", 475.00, None, "Anında", None, "/pin/minecraft"),
                ("oyunfor", 489.00, None, "1-5 dk", None, "/minecraft"),
            ]},
        ],
    },
]


def _stable_id(*parts: str) -> str:
    return "-".join(parts)


def build_catalog() -> dict:
    """Return the full catalog as dicts keyed for fast lookup."""
    games: list[dict] = []
    products_by_id: dict[str, dict] = {}
    offers_by_product: dict[str, list[dict]] = {}
    all_offers: list[dict] = []
    updated_at_iso = datetime.fromisoformat(f"{CATALOG_UPDATED_AT}T00:00:00").isoformat()

    for game in GAMES:
        game_product_count = 0
        game_best_price: float | None = None
        for product_spec in game["products"]:
            product_id = _stable_id("prod", game["slug"], product_spec["name"].lower().replace(" ", "-").replace("₺", "tl"))
            offers: list[dict] = []
            for seller_id, price, original, delivery, campaign, url_path in product_spec["offers"]:
                seller = _seller(seller_id)
                offer_id = _stable_id("off", product_id, seller_id)
                url = f"https://{seller['domain']}{url_path}"
                offers.append({
                    "id": offer_id,
                    "product_id": product_id,
                    "seller_id": seller_id,
                    "seller_name": seller["name"],
                    "seller_reliability": seller["reliability"],
                    "seller_domain": seller["domain"],
                    "price_try": float(price),
                    "original_price_try": float(original) if original is not None else None,
                    "delivery": delivery,
                    "stock": "in_stock",
                    "verified": True,
                    "campaign": campaign,
                    "url": url,
                    "updated_at": updated_at_iso,
                })
            # Sort offers by (reliability rank, price)
            reliability_rank = {"verified": 0, "trusted": 1, "caution": 2}
            offers.sort(key=lambda o: (reliability_rank.get(o["seller_reliability"], 3), o["price_try"]))
            best_price = min((o["price_try"] for o in offers), default=None)
            if best_price is not None and (game_best_price is None or best_price < game_best_price):
                game_best_price = best_price
            product = {
                "id": product_id,
                "game_slug": game["slug"],
                "game_name": game["name"],
                "game_currency": game["currency"],
                "name": product_spec["name"],
                "amount": float(product_spec["amount"]),
                "unit": product_spec["unit"],
                "description": "",
                "tag": product_spec.get("tag"),
                "icon": game["icon"],
                "best_price_try": best_price,
                "offer_count": len(offers),
            }
            products_by_id[product_id] = product
            offers_by_product[product_id] = offers
            all_offers.extend(offers)
            game_product_count += 1

        games.append({
            "slug": game["slug"],
            "name": game["name"],
            "currency": game["currency"],
            "category": game["category"],
            "accent_color": game["accent"],
            "icon_url": game["icon"],
            "tagline": game["tagline"],
            "popular": bool(game.get("popular")),
            "product_count": game_product_count,
            "best_price_try": game_best_price,
            "_product_ids": [p["id"] for p in list(products_by_id.values()) if p["game_slug"] == game["slug"]],
        })

    return {
        "updated_at": updated_at_iso,
        "games": games,
        "products_by_id": products_by_id,
        "offers_by_product": offers_by_product,
        "all_offers": all_offers,
        "sellers": SELLERS,
    }


_CATALOG_CACHE: dict | None = None


def catalog() -> dict:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        _CATALOG_CACHE = build_catalog()
    return _CATALOG_CACHE


# ---- Affiliate configuration --------------------------------------------

# Approximate per-seller affiliate commission rates. Real values come from each
# seller's partner program; adjust these when live agreements are signed. The
# `param` is appended to product URLs so referred traffic is attributed to Subly.
AFFILIATE: dict[str, dict] = {
    "gamesatis": {"param": "ref=subly-app", "rate": 0.04},
    "bynogame": {"param": "aff=subly", "rate": 0.05},
    "oyunfor": {"param": "utm_source=subly&utm_medium=affiliate", "rate": 0.035},
    "hesap-com-tr": {"param": "ref=subly", "rate": 0.03},
    "trendyol": {"param": "utm_source=subly", "rate": 0.02},
    "hepsiburada": {"param": "utm_source=subly", "rate": 0.02},
    "turkcell-pasaj": {"param": "ref=subly", "rate": 0.025},
}


def commission_rate(seller_id: str) -> float:
    return float(AFFILIATE.get(seller_id, {}).get("rate", 0.0))


def apply_affiliate(url: str, seller_id: str) -> str:
    param = AFFILIATE.get(seller_id, {}).get("param")
    if not param:
        return url
    sep = "&" if "?" in url else "?"
    if param in url:
        return url
    return f"{url}{sep}{param}"


# ---- Per-user price overrides -------------------------------------------


def apply_overrides(cat: dict, overrides: list[dict]) -> dict:
    """Return a shallow-cloned catalog view with per-offer overrides applied.

    `overrides` is a list of docs from the gaming_price_overrides collection.
    Each doc: {offer_id, price_try?, original_price_try?, delivery?, campaign?, url?, updated_at}
    Only provided fields are patched; missing fields fall back to the base catalog.
    """
    if not overrides:
        return cat
    override_by_id: dict[str, dict] = {o["offer_id"]: o for o in overrides}

    reliability_rank = {"verified": 0, "trusted": 1, "caution": 2}

    new_offers_by_product: dict[str, list[dict]] = {}
    new_products_by_id: dict[str, dict] = {}

    for product_id, base_offers in cat["offers_by_product"].items():
        patched: list[dict] = []
        for base in base_offers:
            ov = override_by_id.get(base["id"])
            if not ov:
                patched.append(base)
                continue
            merged = {**base}
            if ov.get("price_try") is not None:
                merged["price_try"] = float(ov["price_try"])
            if ov.get("original_price_try") is not None:
                merged["original_price_try"] = float(ov["original_price_try"])
            if ov.get("delivery"):
                merged["delivery"] = ov["delivery"]
            if "campaign" in ov and ov["campaign"] is not None:
                merged["campaign"] = ov["campaign"]
            if ov.get("url"):
                merged["url"] = ov["url"]
            if ov.get("updated_at"):
                merged["updated_at"] = ov["updated_at"]
            patched.append(merged)
        patched.sort(key=lambda o: (reliability_rank.get(o["seller_reliability"], 3), o["price_try"]))
        new_offers_by_product[product_id] = patched
        # Refresh product best_price
        base_product = cat["products_by_id"][product_id]
        best = min((o["price_try"] for o in patched), default=None)
        new_products_by_id[product_id] = {**base_product, "best_price_try": best, "offer_count": len(patched)}

    # Recompute game best_price
    new_games: list[dict] = []
    for game in cat["games"]:
        game_best: float | None = None
        for pid in game["_product_ids"]:
            p_best = new_products_by_id[pid]["best_price_try"]
            if p_best is not None and (game_best is None or p_best < game_best):
                game_best = p_best
        new_games.append({**game, "best_price_try": game_best})

    all_offers = [o for lst in new_offers_by_product.values() for o in lst]

    return {
        **cat,
        "games": new_games,
        "products_by_id": new_products_by_id,
        "offers_by_product": new_offers_by_product,
        "all_offers": all_offers,
    }
