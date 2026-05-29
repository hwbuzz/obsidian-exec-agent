# Obsidian Execution Agent 현재 개발 요약

## 현재 구현 범위

현재 구현된 기능은 아래 3개로 볼 수 있다.

```text
1. Q&A Mode
2. Planning Mode
3. Planning 결과 저장 기능 (--write)
```

설계 문서 기준 7개 모드 중 완전히 구현된 것은 Q&A Mode와 Planning Mode다. Action Mode는 아직 독립 모드가 아니라, Planning 결과를 markdown 파일로 저장하는 수준까지 구현되어 있다.

## 현재 실행 구조

```text
사용자 CLI 입력
-> .env에서 Gemini API key 로딩
-> .agent_config.json에서 기본 vault 경로 로딩
-> vault markdown 파일 검색
-> 관련 노트 snippet/관련 본문 일부 구성
-> Gemini API 호출
-> Q&A 또는 계획 결과 출력
-> --write 옵션이 있으면 markdown 파일 저장
```

## 현재 기본 설정

기본 vault는 `sample_vault`로 설정되어 있다.

```text
sample_vault/
└─ 역량개발/
   ├─ 프로젝트/
   ├─ 교육/
   ├─ 회의록/
   └─ 에이전트/
```

Gemini 설정은 `.env`에서 읽는다.

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

기본 모델은 `gemini-2.5-flash`이며, 호출 실패 시 fallback 모델을 사용한다.

```text
Fallback Models:
- gemini-2.5-flash-lite
- gemini-flash-lite-latest
```

## 주요 명령

```powershell
python agent.py config --show
python agent.py ask "교육 수강 계획의 이번 주 할 일은 뭐야?"
python agent.py plan "이번 주 안에 프로젝트 테스트 결과 문서를 팀에 공유하고 싶어"
python agent.py plan "설정 검증 명령 추가 계획을 노트로 남기고 싶어" --write
```

## Sample Vault 기준 Mode별 테스트 예시

현재 구현된 기능은 아래 3개로 볼 수 있다.

```text
1. Q&A Mode
2. Planning Mode
3. Planning 결과 저장 기능 (--write)
```

기본 vault는 `sample_vault`로 설정되어 있다.

```text
sample_vault/
└─ 역량개발/
   ├─ 프로젝트/
   ├─ 교육/
   ├─ 회의록/
   └─ 에이전트/
```

## 1. Q&A Mode

### Q&A Mode에서 Gemini의 역할

Q&A Mode는 단순 파일 검색이 아니다.

```text
Python agent:
- vault markdown 파일 로딩
- 질문 키워드 추출
- 관련 노트 검색 및 점수화
- 상위 노트 snippet/excerpt 구성

Gemini:
- 검색된 vault 근거를 읽고 해석
- 질문에 맞는 답변 생성
- 관련 노트 정리
- 다음 액션 제안
```

### 예시 1

입력:

```powershell
python agent.py ask "교육 수강 계획의 이번 주 할 일은 뭐야?" --limit 3
```

흐름:

```text
sample_vault 검색
-> 역량개발/교육/교육_수강_계획.md 발견
-> 관련 본문 excerpt를 Gemini에 전달
-> Gemini가 이번 주 할 일을 요약
-> Gemini가 관련 노트와 다음 액션을 함께 생성
```

실제 결과:

```text
교육 수강 계획의 이번 주 할 일은 다음과 같습니다.

- 교육 자료 목차 확인
- 실습 환경 준비
- 첫 번째 예제 스크립트 실행
- 학습 기록 템플릿 만들기

관련 노트:
- 역량개발/교육/교육_수강_계획.md

다음 액션:
- 위의 할 일 목록을 참고하여 이번 주 학습을 진행하세요.
- 학습 기록 템플릿을 사용하여 배운 내용을 정리하세요.
```

### 예시 2

입력:

```powershell
python agent.py ask "설정 경험 개선을 위해 회의에서 결정한 것은 뭐야?" --limit 3
```

흐름:

```text
sample_vault 검색
-> 역량개발/회의록/프로젝트_회의록_2026-05-28.md 발견
-> customer_feedback.md도 관련 근거로 포함
-> 관련 excerpt를 Gemini에 전달
-> Gemini가 회의 결정 사항과 배경을 요약
-> Gemini가 관련 노트와 다음 액션을 생성
```

실제 결과:

```text
회의에서는 자동화 도구의 초기 설정 경험을 개선하기 위해 다음 사항을 결정했습니다.

- 초기 설정 명령을 별도로 제공
- 설정이 올바른지 확인하는 검증 명령 추가
- 오류 메시지는 원인, 해결 방법, 다음 명령 예시를 함께 보여주도록 개선

이는 고객 피드백에서 설정 과정이 길고 오류 발생 시 원인 파악이 어렵다는 점이 반복적으로 제기되었기 때문입니다.

관련 노트:
- 역량개발\회의록\프로젝트_회의록_2026-05-28.md
- customer_feedback.md

다음 액션:
- 설정 파일 예시 작성
- 검증 명령 초안 구현
- 오류 메시지 문구 개선
- README 상단에 빠른 시작 섹션 추가
```

## 2. Planning Mode

### Planning Mode에서 Gemini의 역할

Planning Mode에서 Gemini는 목표를 실제 실행 계획으로 재구성한다.

```text
Python agent:
- 목표 문장에서 마감 힌트 추출
- 목표 유형에 따른 기본 WBS 후보 생성
- 관련 vault 노트 검색
- Gemini prompt 구성

Gemini:
- 목표 해석
- WBS 재구성
- 이번 주 우선순위 제안
- 리스크 정리
- 오늘 시작할 작업 제안
- 관련 노트 정리
```

### 예시 1

입력:

```powershell
python agent.py plan "이번 주 안에 프로젝트 테스트 결과 문서를 팀에 공유하고 싶어" --limit 3
```

흐름:

```text
목표 분석
-> "이번 주" 마감 힌트 감지
-> sample_vault에서 프로젝트 일일보고/회의록/테스트계획 검색
-> Gemini가 WBS, 우선순위, 리스크, 오늘 시작할 작업 생성
```

실제 결과 요약:

```text
목표 해석:
이번 주 안에 프로젝트 테스트 결과 문서를 팀에 공유하는 목표입니다.

WBS:
1. 프로젝트 테스트 결과 취합 및 정리
2. 테스트 결과 문서 초안 작성
3. 팀 공유를 위한 문서 형식 확정
4. 최종 검토 및 수정
5. 팀에 문서 공유

이번 주 우선순위:
1. 테스트 결과 문서 초안 작성
2. 테스트 결과 취합 및 정리
3. 문서 형식 확정
4. 최종 검토
5. 팀 공유

리스크:
- 샘플 데이터 부족
- 기능별 테스트 결과를 한 곳에서 보기 어려움
- 문서화 시간 부족

오늘 시작할 작업:
현재까지 진행된 테스트 결과 데이터를 수집하고 성공/실패 여부를 명확히 표시합니다.

관련 노트:
- 역량개발\에이전트\obsidian_agent_테스트계획.md
- 역량개발\프로젝트\프로젝트_일일보고_2026-05-29.md
- 역량개발\회의록\팀_주간회의_2026-05-29.md
```

### 예시 2

입력:

```powershell
python agent.py plan "4주 동안 Python 자동화 교육을 운영하고 싶어" --limit 3
```

흐름:

```text
목표 분석
-> 교육/스터디 관련 노트 검색
-> 교육 수강 계획, 학습 템플릿, 스터디 계획을 근거로 Gemini 호출
-> Gemini가 4주 운영 계획 생성
```

실제 결과 요약:

```text
목표 해석:
4주 동안 Python 자동화 교육을 운영하려는 목표입니다.
실무형 Python 자동화와 테스트 기초에 초점을 맞춥니다.

WBS:
1. 교육 운영 계획 수립
   - 교육 목표 및 완료 기준 구체화
   - 4주차 커리큘럼 상세 설계
   - 운영 방식 및 일정 확정

2. 교육 준비 및 환경 구축
   - 교육 자료 초안 작성
   - 실습 환경 구축 가이드 마련
   - 학습 기록 템플릿 제작

3. 교육 운영 및 실행
   - 1주차: Python 파일 처리와 CLI 인자 처리
   - 2주차: 예외 처리와 로그 작성
   - 3주차: pytest 기본 구조와 fixture
   - 4주차: 작은 자동화 도구에 테스트 적용

4. 교육 결과 정리 및 회고

이번 주 우선순위:
- 교육 목표 및 완료 기준 구체화
- 커리큘럼 초안 설계
- 실습 환경 준비 계획 수립
- 학습 기록 템플릿 제작

리스크:
- 참여자 기술 수준 편차
- 실습 환경 구축 문제
- 교육 내용 난이도 조절
- 시간 관리 실패

관련 노트:
- 역량개발\교육\교육_수강_계획.md
- 역량개발\에이전트\obsidian_agent_테스트계획.md
- study_group_plan.md
```

## 3. Planning 결과 저장 기능

현재 저장 기능은 독립적인 Action Mode는 아니다.

```text
Planning Mode에서 Gemini가 markdown 응답 생성
-> Python agent가 해당 응답을 파일로 저장
```

### 예시 1

입력:

```powershell
python agent.py plan "설정 검증 명령 추가 계획을 노트로 남기고 싶어" --write --limit 3
```

흐름:

```text
Planning Mode 실행
-> Gemini가 설정 검증 명령 추가 계획 생성
-> sample_vault/Agent Notes 폴더에 markdown 저장
```

실제 결과 요약:

```text
목표 해석:
설정 검증 명령 추가 계획을 Obsidian 노트로 남기려는 목표입니다.
이는 자동화 도구의 초기 설정 경험 개선의 일부입니다.

WBS:
1. 설정 검증 명령의 필요성 및 범위 정의
2. 설정 검증 명령 설계 및 구현
3. 테스트 및 검증
4. 문서화 및 통합

이번 주 우선순위:
- 설정 검증 명령의 필요성 및 범위 정의
- 설정 검증 명령 코드 구현

관련 노트:
- 역량개발\회의록\프로젝트_회의록_2026-05-28.md
- 역량개발\프로젝트\프로젝트_일일보고_2026-05-29.md
- customer_feedback.md

생성된 노트:
sample_vault\Agent Notes\2026-05-29_execution_plan_2.md
```

### 예시 2

입력:

```powershell
python agent.py plan "교육 학습 기록 템플릿 개선 계획을 노트로 만들고 싶어" --write --limit 3
```

흐름:

```text
Planning Mode 실행
-> 교육 학습 기록 템플릿과 교육 수강 계획 검색
-> Gemini가 개선 계획 생성
-> sample_vault/Agent Notes 폴더에 markdown 저장
```

실제 결과 요약:

```text
목표 해석:
교육 학습 기록 템플릿을 개선하기 위한 계획을 노트로 작성하려는 목표입니다.

WBS:
1. 기존 템플릿 분석 및 문제점 도출
2. 개선 목표 설정
3. 개선된 템플릿 초안 설계
4. 템플릿 예시 작성 및 검증
5. 최종 템플릿 노트 작성

이번 주 우선순위:
- 기존 템플릿 분석
- 개선 목표 설정
- 개선된 템플릿 초안 설계

리스크:
- 템플릿 과잉 설계
- 실질적인 개선 부족
- 시간 부족

오늘 시작할 작업:
교육 학습 기록 템플릿 노트를 열어 현재 내용을 검토하고, 불편한 점을 메모합니다.

관련 노트:
- 역량개발\교육\교육_학습기록_템플릿.md
- 역량개발\교육\교육_수강_계획.md

생성된 노트:
sample_vault\Agent Notes\2026-05-29_execution_plan.md
```

## 현재 한계 및 개선 방향

### 한계

노트 검색이 키워드 기반이므로, 유사어/의미 기반 검색은 아직 제한적이다.
현재 agent가 활용하는 재료는 기본적으로 Obsidian vault 안의 markdown 파일이다.
구체적으로는 각 노트의 텍스트, 파일 경로, 위치한 폴더, 폴더 간 계층 구조 정도를 사용한다.
아직 노트의 의미적 관계나 작업 상태를 깊게 해석하는 별도 인덱스가 없다.
이 구조에서는 질문과 직접적으로 겹치는 단어가 있는 파일을 우선적으로 뽑아내는 경향이 있다.
예를 들어 같은 의미를 다른 표현으로 적어둔 노트, 제목에는 없지만 본문 맥락상 중요한 노트, 여러 노트에 흩어진 정보를 조합해야 하는 질문에는 검색 품질이 상대적을 낮을 수 있다.

### 개선 방향(안)

- 노트별 메타데이터 활용
  - 태그, 폴더, 최근 수정일, 파일명 패턴, 체크박스 task 여부 등을 검색 점수에 반영
  - `역량개발/교육`, `역량개발/회의록`처럼 폴더 구조 자체를 힌트로 사용

- 노트 내 블록 단위 검색
  - 노트 전체가 아니라 문단, heading section, task block 단위로 쪼개서 검색
  - 관련 노트를 찾는 것에서 한 단계 더 나아가, 관련 문단을 더 정확히 찾도록 함

- 프롬프트 고도화
  - Gemini에게 단순 답변 생성뿐 아니라, 근거 부족 여부 판단, 추가 검색 키워드 제안, 관련 노트 재분류 등의 역할 부여
  - Q&A Mode와 Planning Mode별로 더 명확한 출력 형식과 판단 기준을 부여

- skill 또는 MCP 연동
  - 반복되는 vault 분석 방법을 codex skill로 생성하여 분리
  - MCP를 붙이면 파일 검색, 태그 분석, task 파싱, 일정 정보 조회 같은 기능을 더 agentic하게 구성

- 나머지 mode 구현
  - Priority Mode, Focus Mode, Bottleneck Detector Mode, Overdue Task Rescheduler Mode를 구현
  - 각 mode가 서로 독립 실행되는 것에서 끝나지 않고, Q&A -> Planning -> Focus -> Action처럼 유기적으로 이어지도록 
  
- multi-agent 구조 실험
  - 각 mode를 하위 agent처럼 두고, 사용자의 입력을 먼저 해석하는 Routing Agent를 둘 수 있다.
  - Routing Agent가 "이 요청은 Q&A로 충분한지", "Planning까지 이어져야 하는지", "Action으로 노트를 생성해야 하는지"를 판단하는 구조를 실험해볼 수 있다.

- UI 실험
  - 현재는 UI는 CLI 기반이다.
  - Streamlit 같은 간단한 프론트엔드를 붙이면 입력창, 결과 영역, 관련 노트 목록, 생성된 파일 링크를 한 화면에서 보여줄 수 있다.
