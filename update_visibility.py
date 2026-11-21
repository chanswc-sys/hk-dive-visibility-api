import json
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests

HKT = timezone(timedelta(hours=8))
NOW_HKT = datetime.now(HKT)

# 1. 香港天文台 (HKO) 官方公開實時 API
HKO_RHRREAD_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
HKO_WIND_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_10min_wind_uc.csv"
HKO_TIDE_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/tide/ALL_uc.csv"

# 2. 漁農自然護理署 (AFCD) 養魚區實時水質及紅潮端點
# 註：漁護署養魚區實時水質系統網頁為 https://www.afcd.gov.hk/tc_chi/fisheries/fish_aqu/fish_aqu_env/fish_aqu_env.html
# 若您在瀏覽器 F12 Network 取得其底層 JSON 數據介面，可填入 AFCD_FCZ_REALTIME_API_URL 環境變數或下方預設值
AFCD_FCZ_REALTIME_API_URL = os.getenv("AFCD_FCZ_API_URL", "")
AFCD_RED_TIDE_RSS_URL = "https://www.afcd.gov.hk/tc_chi/fisheries/hkredtide/rss/redtide_tc.xml"

# 3. 45個潛點水文屬性對照表（新增 fcz_buoy 對應最近的漁護署養魚區水質浮標）
SITE_HYDRO_PROFILES = {
    "HKRC2025-01": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["N", "NE", "E"], "mud_sensitive": False, "base_score": 82},
    "HKRC2025-02": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["E", "SE"], "mud_sensitive": False, "base_score": 80},
    "HKRC2025-03": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 78},
    "HKRC2025-04": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 65},
    "HKRC2025-05": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NW", "N"], "mud_sensitive": True, "base_score": 60},
    "HKRC2025-06": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 62},
    "HKRC2025-07": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE"], "mud_sensitive": True, "base_score": 68},
    "HKRC2025-08": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE"], "mud_sensitive": True, "base_score": 62},
    "HKRC2025-09": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["NW", "N", "NE"], "mud_sensitive": False, "base_score": 74},
    "HKRC2025-10": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["NW", "W"], "mud_sensitive": False, "base_score": 72},
    "HKRC2025-11": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["SE", "S"], "mud_sensitive": False, "base_score": 75},
    "HKRC2025-12": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["NE", "E", "SE"], "mud_sensitive": False, "base_score": 74},
    "HKRC2025-13": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 68},
    "HKRC2025-14": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 80},
    "HKRC2025-15": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N", "NE"], "mud_sensitive": False, "base_score": 74},
    "HKRC2025-16": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N"], "mud_sensitive": False, "base_score": 76},
    "HKRC2025-17": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N"], "mud_sensitive": True, "base_score": 72},
    "HKRC2025-18": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N", "NE"], "mud_sensitive": False, "base_score": 74},
    "HKRC2025-19": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 82},
    "HKRC2025-20": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["SE", "S"], "mud_sensitive": False, "base_score": 80},
    "HKRC2025-21": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 80},
    "HKRC2025-22": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["S", "SW"], "mud_sensitive": False, "base_score": 76},
    "HKRC2025-23": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["W", "NW"], "mud_sensitive": True, "base_score": 68},
    "HKRC2025-24": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 65},
    "HKRC2025-25": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["N", "NE", "E"], "mud_sensitive": False, "base_score": 78},
    "HKRC2025-26": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE"], "mud_sensitive": False, "base_score": 75},
    "HKRC2025-27": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["W", "NW"], "mud_sensitive": False, "base_score": 76},
    "HKRC2025-28": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["S", "SW"], "mud_sensitive": False, "base_score": 75},
    "HKRC2025-29": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 68},
    "HKRC2025-30": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["W", "SW"], "mud_sensitive": False, "base_score": 76},
    "HKRC2025-31": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["N", "NE", "E"], "mud_sensitive": False, "base_score": 82},
    "HKRC2025-32": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 80},
    "HKRC2025-33": {"region": "西貢", "wind_stn": "橫瀾島", "fcz_buoy": "糧船灣", "exposed": ["N", "NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 88},
    "HKRC2025-34": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 64},
    "HKRC2025-35": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N", "NE"], "mud_sensitive": False, "base_score": 72},
    "HKRC2025-36": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 70},
    "SUP-01":      {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["N", "NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 85},
    "SUP-02":      {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["N", "NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 84},
    "SUP-03":      {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 83},
    "SUP-04":      {"region": "西貢", "wind_stn": "橫瀾島", "fcz_buoy": "東龍洲", "exposed": ["NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 76},
    "SUP-05":      {"region": "南區", "wind_stn": "橫瀾島", "fcz_buoy": "東龍洲", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 78},
    "SUP-06":      {"region": "離島", "wind_stn": "橫瀾島", "fcz_buoy": "蒲台", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 86},
    "SUP-07":      {"region": "離島", "wind_stn": "長洲", "fcz_buoy": "索罟灣", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": True, "base_score": 60},
    "SUP-08":      {"region": "離島", "wind_stn": "長洲", "fcz_buoy": "索罟灣", "exposed": ["SE", "S", "SW", "W"], "mud_sensitive": True, "base_score": 52},
    "SUP-09":      {"region": "九龍城", "wind_stn": "啟德", "fcz_buoy": "東龍洲", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 58},
}

WIND_DIR_MAP = {
    "北": "N", "東北": "NE", "東": "E", "東南": "SE",
    "南": "S", "西南": "SW", "西": "W", "西北": "NW"
}

def fetch_hko_data():
    """抓取天文台實時雨量、風向風速及潮汐趨勢"""
    rainfall_dict, wind_dict, tide_trend = {}, {}, "未知"
    try:
        r = requests.get(HKO_RHRREAD_URL, timeout=15).json()
        for item in r.get("rainfall", {}).get("data", []):
            rainfall_dict[item.get("place", "")] = item.get("max", 0)
    except Exception as e:
        print(f"HKO Rainfall API error: {e}")

    try:
        df_wind = pd.read_csv(HKO_WIND_CSV_URL)
        for _, row in df_wind.iterrows():
            stn = str(row.iloc[1]).strip()
            w_dir_tc = str(row.iloc[2]).strip()
            w_spd = pd.to_numeric(row.iloc[3], errors="coerce")
            wind_dict[stn] = {
                "dir_tc": w_dir_tc,
                "dir_code": WIND_DIR_MAP.get(w_dir_tc, ""),
                "speed_kmh": 0 if pd.isna(w_spd) else float(w_spd)
            }
    except Exception as e:
        print(f"HKO Wind CSV error: {e}")

    try:
        df_tide = pd.read_csv(HKO_TIDE_CSV_URL)
        tmw = df_tide[df_tide.iloc[:, 0].astype(str).str.contains("大廟灣")].tail(2)
        if len(tmw) == 2:
            tide_trend = "漲潮" if float(tmw.iloc[1, 3]) >= float(tmw.iloc[0, 3]) else "退潮"
    except Exception as e:
        print(f"HKO Tide CSV error: {e}")

    return rainfall_dict, wind_dict, tide_trend

def fetch_afcd_buoy_and_redtide():
    """
    抓取漁護署養魚區實時水質浮標 (濁度 NTU 與 葉綠素 ug/L) 及 紅潮警示
    回傳格式: { "養魚區名稱": {"turbidity_ntu": float|None, "chlorophyll_ugl": float|None, "red_tide_alert": bool, "status": str} }
    """
    buoy_data = {}
    red_tide_text = ""

    # 1. 抓取漁護署紅潮資訊 RSS (偵測最新是否有紅潮報告提及相關水域)
    try:
        resp_rt = requests.get(AFCD_RED_TIDE_RSS_URL, timeout=12)
        if resp_rt.status_code == 200:
            resp_rt.encoding = "utf-8"
            red_tide_text = resp_rt.text
    except Exception as e:
        print(f"AFCD Red Tide RSS warning: {e}")

    # 2. 若已設定漁護署實時浮標 JSON 端點，自動解析濁度與葉綠素
    if AFCD_FCZ_REALTIME_API_URL:
        try:
            r_fcz = requests.get(AFCD_FCZ_REALTIME_API_URL, timeout=15).json()
            # 支援常見清單格式 [{"zone": "糧船灣", "turbidity": 2.4, "chlorophyll": 3.1}, ...]
            items = r_fcz if isinstance(r_fcz, list) else r_fcz.get("data", [])
            for item in items:
                zone_name = str(item.get("zone") or item.get("fcz_name") or item.get("name", "")).strip()
                turb = pd.to_numeric(item.get("turbidity") or item.get("turbidity_ntu"), errors="coerce")
                chl = pd.to_numeric(item.get("chlorophyll") or item.get("chlorophyll_a"), errors="coerce")
                buoy_data[zone_name] = {
                    "turbidity_ntu": None if pd.isna(turb) else round(float(turb), 2),
                    "chlorophyll_ugl": None if pd.isna(chl) else round(float(chl), 2),
                    "status": "實時浮標連線正常"
                }
        except Exception as e:
            print(f"AFCD FCZ Buoy API warning: {e}")

    # 3. 為所有對應浮標站補齊結構與紅潮檢核
    default_zones = ["吉澳", "往灣", "塔門", "較寮灣", "鹽田仔", "滘西", "糧船灣", "東龍洲", "蒲台", "索罟灣"]
    for z in default_zones:
        if z not in buoy_data:
            buoy_data[z] = {
                "turbidity_ntu": None,
                "chlorophyll_ugl": None,
                "status": "未連接實時浮標JSON（僅啟用紅潮與氣象水文推算）"
            }
        # 檢查最新紅潮 RSS 標題/內容是否提及該水域
        buoy_data[z]["red_tide_alert"] = (z in red_tide_text)

    return buoy_data

def calculate_visibility(site_id, rainfall_dict, wind_dict, tide_trend, buoy_data):
    """融合氣象(HKO) + 水質浮標(AFCD濁度/葉綠素/紅潮) 計算實時能見度"""
    prof = SITE_HYDRO_PROFILES.get(site_id, {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": [], "mud_sensitive": False, "base_score": 70})
    score = prof["base_score"]
    factors = []

    # 1. 季節基準
    month = NOW_HKT.month
    if 5 <= month <= 9:
        score -= 10
        factors.append("夏季西南流/雨季基準(-10)")
    elif month in [10, 11, 12, 1, 2]:
        score += 5
        factors.append("秋冬水清期(+5)")

    # 2. 降雨徑流
    rain_mm = rainfall_dict.get(prof["region"], 0)
    if rain_mm >= 20:
        score -= 35
        factors.append(f"{prof['region']}暴雨{rain_mm}mm(-35)")
    elif rain_mm >= 5:
        score -= 20
        factors.append(f"{prof['region']}有雨{rain_mm}mm(-20)")
    elif rain_mm > 0:
        score -= 8
        factors.append(f"{prof['region']}微雨{rain_mm}mm(-8)")

    # 3. 風速與當風面湧浪
    w_info = wind_dict.get(prof["wind_stn"], {"dir_tc": "無風", "dir_code": "", "speed_kmh": 0})
    w_spd = w_info["speed_kmh"]
    is_exposed = w_info["dir_code"] in prof["exposed"]

    if w_spd >= 30:
        penalty = 28 if is_exposed else 15
        score -= penalty
        factors.append(f"{prof['wind_stn']}{w_info['dir_tc']}風{int(w_spd)}km/h(-{penalty})")
    elif w_spd >= 18:
        penalty = 16 if is_exposed else 6
        score -= penalty
        factors.append(f"{prof['wind_stn']}{w_info['dir_tc']}風{int(w_spd)}km/h(-{penalty})")

    # 4. 沙泥底揚塵
    if prof["mud_sensitive"] and (rain_mm > 0 or w_spd >= 20):
        score -= 8
        factors.append("沙泥底易揚塵(-8)")

    # 5. 潮汐修正
    if tide_trend == "漲潮":
        score += 4
        factors.append("漲潮清流(+4)")
    elif tide_trend == "退潮":
        score -= 4
        factors.append("退潮濁流(-4)")

    # 6. 漁護署養魚區實時水質浮標 (濁度 NTU、葉綠素 ug/L 及紅潮)
    fcz_name = prof["fcz_buoy"]
    b_info = buoy_data.get(fcz_name, {})
    turb = b_info.get("turbidity_ntu")
    chl = b_info.get("chlorophyll_ugl")
    rt_alert = b_info.get("red_tide_alert", False)

    if turb is not None:
        if turb >= 10.0:
            score -= 30
            factors.append(f"{fcz_name}浮標極高濁度{turb}NTU(-30)")
        elif turb >= 5.0:
            score -= 15
            factors.append(f"{fcz_name}浮標偏濁{turb}NTU(-15)")
        elif turb <= 2.0:
            score += 6
            factors.append(f"{fcz_name}浮標水質極清{turb}NTU(+6)")

    if chl is not None:
        if chl >= 15.0:
            score -= 28
            factors.append(f"{fcz_name}浮標高葉綠素/藻華{chl}ug/L(-28)")
        elif chl >= 8.0:
            score -= 14
            factors.append(f"{fcz_name}浮標葉綠素偏高{chl}ug/L(-14)")

    if rt_alert:
        score -= 25
        factors.append(f"漁護署紅潮報告提及{fcz_name}水域(-25)")

    score = max(10, min(98, score))

    if score >= 75:
        grade, est_meters = "優", "6–10+ 米"
    elif score >= 52:
        grade, est_meters = "良", "3–6 米"
    else:
        grade, est_meters = "差", "< 3 米"

    turb_str = f"{turb} NTU" if turb is not None else "待接入"
    chl_str = f"{chl} ug/L" if chl is not None else "待接入"

    return {
        "預估能見度等級": grade,
        "預估能見度範圍": est_meters,
        "能見度指數_0至100": score,
        "鄰近養魚區浮標站": f"{fcz_name}養魚區",
        "浮標濁度_NTU": turb,
        "浮標葉綠素_ugL": chl,
        "紅潮預警": "是（水色異常）" if rt_alert else "無",
        "當前氣象水文摘要": f"雨量:{rain_mm}mm | {prof['wind_stn']}:{w_info['dir_tc']}({int(w_spd)}km/h) | 潮汐:{tide_trend} | {fcz_name}濁度:{turb_str} / 葉綠素:{chl_str}",
        "影響因子明細": "；".join(factors) if factors else "海況平穩"
    }

def main():
    input_csv = "HK_Coral_Communities_2025_ArcGIS-v2.csv"
    df = pd.read_csv(input_csv)

    rainfall_dict, wind_dict, tide_trend = fetch_hko_data()
    buoy_data = fetch_afcd_buoy_and_redtide()
    update_time_str = NOW_HKT.strftime("%Y-%m-%d %H:%M:%S HKT")

    vis_results = []
    for _, row in df.iterrows():
        res = calculate_visibility(row["編號"], rainfall_dict, wind_dict, tide_trend, buoy_data)
        res["更新時間"] = update_time_str
        vis_results.append(res)

    df_vis = pd.DataFrame(vis_results)
    df_out = pd.concat([df, df_vis], axis=1)

    df_out.to_csv("visibility_latest.csv", index=False, encoding="utf-8-sig")

    features = []
    for _, row in df_out.iterrows():
        props = row.where(pd.notnull(row), None).to_dict()
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["Longitude"], row["Latitude"]]
            },
            "properties": props
        })

    api_payload = {
        "type": "FeatureCollection",
        "metadata": {
            "title": "香港45個珊瑚潛點實時預估能見度 API（氣象＋漁護署水質浮標版）",
            "updated_at": update_time_str,
            "data_source": "香港天文台 (HKO) 實時氣象潮汐 + 漁護署 (AFCD) 養魚區水質浮標與紅潮網絡 + 2025珊瑚礁普查",
            "tide_trend_east": tide_trend,
            "total_sites": len(features)
        },
        "features": features
    }

    with open("visibility_api.json", "w", encoding="utf-8") as f:
        json.dump(api_payload, f, ensure_ascii=False, indent=2)

    print(f"[{update_time_str}] 已完成 {len(features)} 個潛點的氣象＋水質浮標能見度運算！")

if __name__ == "__main__":
    main()
