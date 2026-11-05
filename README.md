# 검토 보드 (review-board)

제안서·보고서 PDF를 장표별로 보면서 여러 사람이 메모를 남기는 웹페이지입니다.
검토자는 **링크 + 프로젝트 비밀번호**만 있으면 되고, Claude나 별도 로그인이 필요 없습니다.

- 화면: GitHub Pages (`https://coolday79.github.io/review-board/?p=프로젝트ID`)
- 장표: `projects/<ID>/` 에 **프로젝트 비밀번호로 암호화(AES-256-GCM)** 된 PDF로 저장. 공개 저장소여도 비밀번호 없이는 열리지 않습니다.
- 메모: Firebase Firestore(실시간 공유). `config.js`가 비어 있으면 데모 모드(각자 브라우저에만 저장).

## 프로젝트 만들기 / 라운드 추가

```bash
pip install cryptography
python tools/rb.py new   --id kicox27 --name "프로젝트 이름" --password 비밀번호
python tools/rb.py round --id kicox27 --password 비밀번호 --pdf 제안서_v3.pdf --label "v3" --note "변경 내용"
git add projects && git commit -m "kicox27 R2" && git push
```

`rb.py rekey`로 비밀번호를 바꿀 수 있고, 메모는 그대로 유지됩니다.

## Firebase 설정 (처음 한 번)

1. https://console.firebase.google.com → **프로젝트 추가** (이름 예: `review-board`, 애널리틱스는 꺼도 됨)
2. **빌드 → Firestore Database → 데이터베이스 만들기** → 위치 `asia-northeast3 (서울)` → **프로덕션 모드**
3. Firestore **규칙** 탭에 `firestore.rules` 내용을 붙여 넣고 **게시**
4. **빌드 → Authentication → 시작하기 → 로그인 방법: 익명(Anonymous) 사용 설정**
5. Authentication **설정 → 승인된 도메인**에 `coolday79.github.io` 추가
6. 프로젝트 개요 옆 ⚙ **프로젝트 설정 → 내 앱 → 웹(</>)** 앱 등록 → 나오는 `firebaseConfig` 값을 `config.js`의 `firebase:`에 넣기

## 검토자 사용법

- 썸네일을 누르면 크게 보이고, **장표를 클릭하면 그 위치에 핀**을 찍어 메모합니다.
- 메모마다 **대기·반영·보류** 상태, 답글. 내 메모만 수정·삭제.
- 이전 라운드와 **수정 전/후 비교**.
- **[피드백 모아 복사]** → Claude에 붙여 넣으면 수정 요청이 정리되어 전달됩니다.
