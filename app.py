import os
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# Supabase 클라이언트 설정 (환경 변수 또는 기본값)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase 연결 실패: {e}")

def calculate_bmi(height_cm, weight_kg):
    """
    키(cm)와 몸무게(kg)를 입력받아 BMI를 계산합니다.
    대한비만학회(KSSO) 진단 기준 적용
    """
    height_m = height_cm / 100.0
    if height_m <= 0:
        raise ValueError("키는 0보다 커야 합니다.")
    
    bmi = weight_kg / (height_m ** 2)
    bmi = round(bmi, 2)
    
    if bmi < 18.5:
        category = "저체중 (Underweight)"
        category_code = "underweight"
        color = "#3b82f6"
        percentage = min(max((bmi / 18.5) * 25, 5), 25)
        advice = "균형 잡힌 식단과 적절한 영양 섭취가 필요합니다."
    elif 18.5 <= bmi < 23.0:
        category = "정상 (Normal)"
        category_code = "normal"
        color = "#10b981"
        percentage = 25 + ((bmi - 18.5) / (23.0 - 18.5)) * 25
        advice = "현재 건강한 체중을 유지하고 계십니다! 규칙적인 운동과 올바른 식습관을 계속 유지해보세요."
    elif 23.0 <= bmi < 25.0:
        category = "과체중 / 비만전단계 (Overweight)"
        category_code = "overweight"
        color = "#f59e0b"
        percentage = 50 + ((bmi - 23.0) / (25.0 - 23.0)) * 25
        advice = "체중 관리가 필요한 단계입니다. 식단 조절과 유산소 운동을 권장합니다."
    elif 25.0 <= bmi < 30.0:
        category = "1단계 비만 (Obesity Class I)"
        category_code = "obesity1"
        color = "#ef4444"
        percentage = 75 + ((bmi - 25.0) / (30.0 - 25.0)) * 15
        advice = "적절한 체중 감량이 필요합니다. 규칙적인 운동과 식단 관리를 추천합니다."
    else:
        category = "2단계 고도비만 (Obesity Class II)"
        category_code = "obesity2"
        color = "#8b5cf6"
        percentage = min(90 + ((bmi - 30.0) / 10.0) * 10, 100)
        advice = "전문의와의 상담을 통한 체계적인 건강 및 체중 관리를 권장합니다."
        
    return {
        "bmi": bmi,
        "category": category,
        "category_code": category_code,
        "color": color,
        "percentage": round(percentage, 1),
        "advice": advice,
        "height": height_cm,
        "weight": weight_kg
    }

def save_to_supabase(result):
    """Supabase bmi_records 테이블에 측정 기록 저장"""
    if supabase:
        try:
            supabase.table("bmi_records").insert({
                "height": result["height"],
                "weight": result["weight"],
                "bmi": result["bmi"],
                "category": result["category"]
            }).execute()
        except Exception as e:
            print(f"Supabase 데이터 저장 오류: {e}")

def get_supabase_history():
    """Supabase에서 최근 측정 기록 5건 조회"""
    if supabase:
        try:
            res = supabase.table("bmi_records").select("*").order("created_at", desc=True).limit(5).execute()
            return res.data or []
        except Exception as e:
            print(f"Supabase 데이터 조회 오류: {e}")
    return []

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    
    if request.method == "POST":
        try:
            height = float(request.form.get("height", 0))
            weight = float(request.form.get("weight", 0))
            
            if height <= 0 or weight <= 0:
                error = "키와 몸무게는 0보다 큰 양수이어야 합니다."
            elif height > 300 or weight > 500:
                error = "올바른 범위의 키와 몸무게를 입력해주세요."
            else:
                result = calculate_bmi(height, weight)
                # Supabase DB에 저장
                save_to_supabase(result)
        except (ValueError, TypeError):
            error = "올바른 숫자 형식으로 입력해주세요."
            
    history = get_supabase_history()
    return render_template("index.html", result=result, error=error, history=history, supabase_connected=bool(supabase))

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json() or {}
    try:
        height = float(data.get("height", 0))
        weight = float(data.get("weight", 0))
        
        if height <= 0 or weight <= 0:
            return jsonify({"success": False, "error": "키와 몸무게는 0보다 큰 양수이어야 합니다."}), 400
        if height > 300 or weight > 500:
            return jsonify({"success": False, "error": "올바른 범위의 키와 몸무게를 입력해주세요."}), 400
            
        result = calculate_bmi(height, weight)
        save_to_supabase(result)
        return jsonify({"success": True, "data": result})
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "올바른 숫자 형식으로 입력해주세요."}), 400

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
