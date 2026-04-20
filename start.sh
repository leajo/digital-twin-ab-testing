#!/bin/bash
# 디지털 트윈 A/B 테스트 서비스 실행 스크립트
# 사용법: 터미널에서 bash start.sh 입력

echo "========================================="
echo "🧪 디지털 트윈 A/B 테스트 서비스 시작"
echo "========================================="
echo ""

# 1. 백엔드 의존성 설치
echo "📦 백엔드 패키지 설치 중..."
cd backend
pip install -r requirements.txt -q 2>&1 | tail -3
echo "✅ 백엔드 패키지 설치 완료"
echo ""

# 2. 백엔드 서버 시작 (백그라운드)
echo "🚀 백엔드 서버 시작 중 (포트 8000)..."
uvicorn app.main:app --port 8000 &
BACKEND_PID=$!
sleep 3
echo "✅ 백엔드 서버 시작 완료 (PID: $BACKEND_PID)"
echo ""

# 3. 프론트엔드 의존성 설치
echo "📦 프론트엔드 패키지 설치 중..."
cd ../frontend
npm install --silent 2>&1 | tail -3
echo "✅ 프론트엔드 패키지 설치 완료"
echo ""

# 4. 프론트엔드 서버 시작
echo "🚀 프론트엔드 서버 시작 중 (포트 3000)..."
echo ""
echo "========================================="
echo "✅ 서비스가 시작되었습니다!"
echo ""
echo "👉 브라우저에서 http://localhost:3000 을 열어주세요"
echo ""
echo "종료하려면 Ctrl+C 를 누르세요"
echo "========================================="
echo ""

# 프론트엔드를 포그라운드로 실행 (Ctrl+C로 종료 가능)
npm run dev

# 종료 시 백엔드도 함께 종료
kill $BACKEND_PID 2>/dev/null
echo "서비스가 종료되었습니다."
