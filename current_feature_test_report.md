# Obsidian Execution Agent 현재 구현 기능 테스트 리포트

작성일: 2026-05-28

## 1. 목적

이 문서는 현재까지 개발된 Obsidian Execution Agent MVP의 기능을 팀에 공유하기 위한 테스트 리포트다.

현재 구현은 설계 문서의 7개 모드 전체가 아니라, 아래 기능을 중심으로 한다.

- Q&A Mode
- Planning Mode
- Planning 결과 markdown 저장 기능

논문 관련 예시는 제외했다.

## 2. 현재 연결 상태

현재 agent는 로컬 Obsidian vault와 Gemini API를 사용한다.

```text
Vault: G:\내 드라이브\Obsidian
Model: gemini-2.5-flash
Fallback Models:
- gemini-2.5-flash-lite
- gemini-flash-lite-latest
```

API key는 repo 루트의 `.env` 파일에서 읽는다.

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

## 3. 전체 코드 흐름

공통 실행 흐름:

```text
사용자 CLI 입력
-> main()
-> .env 로딩
-> .agent_config.json 설정 로딩
-> vault 경로 결정
-> 명령어별 기능 실행
```

Q&A Mode 흐름:

```text
ask 입력
-> vault의 markdown 파일 로딩
-> 질문 키워드 추출
-> 관련 노트 검색 및 점수화
-> 상위 노트 snippet/excerpt 구성
-> Gemini API 호출
-> 근거 기반 답변 출력
```

Planning Mode 흐름:

```text
plan 입력
-> 목표 문장에서 마감 힌트 추출
-> 기본 WBS 후보 생성
-> 관련 vault 노트 검색
-> Gemini API 호출
-> 목표 해석/WBS/우선순위/리스크/시작 작업 출력
```

Planning 결과 저장 흐름:

```text
plan --write 입력
-> Planning Mode 실행
-> Gemini 응답 생성
-> Agent Notes 폴더 생성
-> markdown 파일 저장
-> 생성된 파일 경로 출력
```

## 4. Q&A Mode

### Gemini의 역할

Q&A Mode에서 Gemini는 검색된 vault 근거를 바탕으로 최종 답변을 생성한다.

agent 자체가 하는 일:

- markdown 파일 읽기
- 질문 키워드 추출
- 관련 노트 검색
- snippet/excerpt 생성

Gemini가 하는 일:

- 검색된 근거 해석
- 사용자 질문에 맞는 한국어 답변 생성
- 관련 노트와 다음 액션 정리

### 예시 1

입력:

```powershell
python agent.py ask "Obsidian Execution Agent의 MVP 범위는 뭐야?" --limit 2
```

실행 흐름:

```text
질문 키워드 추출
-> vault에서 관련 설계 노트 검색
-> 상위 2개 노트의 근거 구성
-> Gemini 호출
-> MVP 범위 설명 생성
```

실제 응답 요약:

```markdown
Obsidian Execution Agent의 MVP 범위는 다음과 같습니다.

핵심 목표:
단순한 Q&A를 넘어 계획 수립과 실행까지 연결하는 개인 실행 지원 agent를 만드는 것입니다.

주요 기능 흐름:
1. 정보 이해: vault 기반 Q&A, 관련 노트 검색 및 요약
2. 판단 및 계획: WBS 생성, 우선순위 선정, 실행 작업 추천, 미뤄진 일 재정리
3. 실행 연결: 결과를 markdown 노트로 생성

기능 요약:
- Q&A: vault 기반 정보 조회
- Planning: 목표 -> 실행 계획
- Priority: 지금 해야 할 일
- Focus: 지금 당장 할 일
- Overdue: 미뤄진 일 정리
- Action: 노트 생성

관련 노트:
- 자기개발\학습활동\obsidian_execution_agent_설계_v0.1.md
```

### 예시 2

입력:

```powershell
python agent.py ask "Action Mode는 어떤 역할을 해?" --limit 2
```

실행 흐름:

```text
질문에서 Action Mode 키워드 추출
-> vault에서 Action Mode 관련 노트 검색
-> 관련 excerpt를 Gemini에 전달
-> Action Mode 역할 설명 생성
```

실제 응답 요약:

```markdown
Action Mode는 결과를 markdown 노트로 생성하는 역할을 합니다.

예를 들어 다음과 같은 형식으로 결과를 기록할 수 있습니다.
- 실행 계획 노트
- 우선순위 노트

관련 노트:
- 자기개발\학습활동\obsidian_execution_agent_설계_v0.1.md

다음 액션:
- Action Mode의 구체적인 사용 시나리오를 더 확인할 수 있습니다.
- 현재 진행 중인 작업에 대한 실행 계획 노트를 생성해볼 수 있습니다.
```

## 5. Planning Mode

### Gemini의 역할

Planning Mode에서 Gemini는 목표를 실제 실행 계획으로 재구성한다.

agent 자체가 하는 일:

- 목표 문장에서 마감 힌트 추출
- 목표 유형에 따른 기본 WBS 후보 생성
- 관련 vault 노트 검색
- Gemini prompt 구성

Gemini가 하는 일:

- 목표 해석
- WBS 재구성
- 이번 주 우선순위 제안
- 리스크 정리
- 오늘 시작할 작업 제안
- 관련 노트 정리

### 예시 1

입력:

```powershell
python agent.py plan "오늘 2시간 안에 Focus Mode를 CLI에 추가하고 싶어" --limit 2
```

실행 흐름:

```text
목표 분석
-> "오늘" 마감 힌트 감지
-> agent/project 유형 WBS 후보 생성
-> vault에서 Focus Mode 관련 노트 검색
-> Gemini 호출
-> 2시간짜리 구현 계획 생성
```

실제 응답 요약:

```markdown
## 목표 해석

Obsidian vault 기반 개인 실행 지원 Agent에 Focus Mode 기능을 CLI로 추가하려는 목표입니다.
Focus Mode는 확보된 시간 기준으로 실행할 작업을 추천하는 기능입니다.

## WBS

- Focus Mode 입력 형식 정의
- 사용자가 입력한 확보 시간 파싱
- 관련 task/우선순위 후보를 가져올 방식 결정
- CLI 명령 추가
- 예시 입력으로 동작 검증

## 리스크

- 2시간 안에 task 추출과 추천 로직을 모두 정교하게 만들기는 어려울 수 있습니다.
- 우선은 간단한 규칙 기반 추천으로 시작하는 것이 적절합니다.
```

### 예시 2

입력:

```powershell
python agent.py plan "이번 주 안에 README와 사용법을 팀원이 따라할 수 있게 정리하고 싶어" --limit 2
```

실행 흐름:

```text
목표 분석
-> "이번 주" 마감 힌트 감지
-> 문서화 목표에 맞는 WBS 후보 생성
-> README/설계 노트 관련 근거 검색
-> Gemini 호출
-> 팀 공유용 문서화 계획 생성
```

실제 응답 요약:

```markdown
## 목표 해석

이번 주 안에 README와 사용법 문서를 팀원이 쉽게 따라할 수 있도록 정리하는 목표입니다.
핵심은 설치부터 기능 사용까지 막힘없이 따라할 수 있는 가이드를 제공하는 것입니다.

## WBS

1. 목표 명확화 및 범위 설정
   - "팀원이 따라할 수 있다"의 구체적인 기준 정의
   - README와 사용법 문서에 포함할 핵심 내용 목록화

2. 자료 수집 및 구조화
   - 기존 README, 사용 기록, 팀원 질문 수집
   - 시작하기, 기본 사용법, 문제 해결 섹션 구성

3. 초안 작성
   - 초기 설정
   - 기본 명령 사용법
   - 주요 워크플로우

4. 내부 검토 및 피드백 요청

5. 피드백 반영 및 최종 정리

6. 배포 및 공유
```

## 6. Planning 결과 저장 기능

### Gemini의 역할

현재 저장 기능은 독립적인 Action Mode는 아니다.

현재 동작:

```text
Planning Mode에서 Gemini가 markdown 응답 생성
-> agent가 해당 응답을 파일로 저장
```

즉, Gemini는 저장할 markdown 본문을 생성하고, 파일 생성은 로컬 Python 코드가 수행한다.

### 예시 1

입력:

```powershell
python agent.py --vault . plan "팀 공유용 데모 노트를 하나 만들고 싶어" --write --limit 2
```

실행 흐름:

```text
repo 폴더를 임시 vault로 지정
-> Planning Mode 실행
-> Gemini가 데모 노트 생성 계획 작성
-> Agent Notes 폴더에 markdown 저장
```

실제 응답 요약:

```markdown
## 팀 공유용 데모 노트 생성 계획

### 목표 해석

팀 공유용 데모 노트를 하나 만들고 싶다는 목표는,
Obsidian vault 내에서 마크다운 노트를 생성하여 팀원들에게 특정 정보, 기능 또는 작업 흐름을 시연하고 공유하는 것을 의미합니다.
```

생성 결과:

```text
Agent Notes\2026-05-28_execution_plan_2.md
```

### 예시 2

입력:

```powershell
python agent.py --vault . plan "CLI 사용법 점검 노트를 만들고 싶어" --write --limit 2
```

실행 흐름:

```text
repo 폴더를 임시 vault로 지정
-> Planning Mode 실행
-> Gemini가 CLI 사용법 점검 노트 계획 작성
-> Agent Notes 폴더에 markdown 저장
```

실제 응답 요약:

```markdown
## 목표 해석

CLI 사용법 점검 노트를 만들고 싶다는 목표는,
Obsidian Execution Agent의 명령줄 인터페이스 사용법을 정리하고,
각 명령의 작동 여부를 점검하며,
사용자가 쉽게 따라 할 수 있도록 가이드하는 노트를 작성하는 것으로 해석됩니다.

## WBS

1. 노트의 목표 및 범위 정의
2. Obsidian Execution Agent CLI 기능 목록 파악
3. 각 기능별 상세 사용법 및 예시 수집
4. 노트 초안 작성
```

생성 결과:

```text
Agent Notes\2026-05-28_execution_plan_3.md
```

## 7. 현재 구현 범위와 한계

현재 구현 완료:

- Q&A Mode
- Planning Mode
- Planning 결과 저장 기능

부분 구현:

- Action Mode
  - 현재는 `plan --write`를 통한 저장만 가능
  - 독립적인 `action` 명령은 아직 없음
  - 기존 노트 수정 기능도 아직 없음

미구현:

- Priority Optimization Mode
- Bottleneck Detector Mode
- Focus Session Mode
- Overdue Task Rescheduler Mode

## 8. 테스트 중 확인한 개선 사항

### 8.1 Gemini 호출 안정화

테스트 중 `gemini-2.5-flash`가 일시적으로 `HTTP 503`을 반환하는 경우가 있었다.

대응:

- fallback 모델 추가
- `HTTP 503` 발생 시 짧은 재시도
- 출력 토큰 제한 설정
- vault excerpt 길이 축소

### 8.2 저장 파일명 중복 방지

`plan --write`를 같은 날짜에 여러 번 실행하면 기존 파일을 덮어쓸 수 있어, 파일명이 겹칠 경우 `_2`, `_3` suffix를 붙이도록 개선했다.

예시:

```text
2026-05-28_execution_plan.md
2026-05-28_execution_plan_2.md
2026-05-28_execution_plan_3.md
```

## 9. 요약

현재 Obsidian Execution Agent MVP는 실제 vault와 Gemini API를 연결해 다음을 수행할 수 있다.

```text
vault 검색
-> 관련 근거 구성
-> Gemini 호출
-> Q&A 또는 실행 계획 생성
-> 필요 시 markdown 파일 저장
```

아직 완성형 7-mode agent는 아니지만, vault 기반 LLM agent로 동작하는 최소 골격은 구현되어 있다.
