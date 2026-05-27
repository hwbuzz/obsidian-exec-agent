
# Obsidian Execution Agent (Toy Project 제안)

## 1. Agent 개요

이 agent는 Obsidian vault를 기반으로  
단순한 Q&A를 넘어서 **계획 수립과 실행까지 연결하는 개인 실행 지원 agent**이다.

핵심은 다음 3가지 흐름을 자동으로 연결하는 것이다:

정보 이해 → 계획 수립 → 실행 연결

즉, “답변하는 챗봇”이 아니라  
**“다음 행동을 만들어주는 agent”**를 목표로 한다.

---

## 2. 전체 기능 구조

Agent는 크게 3단계로 구성된다.

### 1) Understand (상태 파악)
- vault 기반 Q&A
- 관련 노트 검색 및 요약

👉 내가 지금 무엇을 하고 있는지 이해

---

### 2) Plan (판단 및 계획)
- Planning: 목표 → WBS 생성
- Priority: 지금 해야 할 일 선정
- Focus: 지금 당장 할 작업 추천
- Overdue: 미뤄진 일 재정리

👉 그래서 지금 무엇을 해야 하는지 결정

---

### 3) Execute (실행 연결)
- markdown 노트 생성

👉 결과를 실제 작업 자산으로 남김

---

## 3. 기능 요약 (한눈에 보기)

| 기능 | 역할 |
|------|------|
| Q&A | vault 기반 정보 조회 |
| Planning | 목표 → 실행 계획 |
| Priority | 지금 해야 할 일 |
| Focus | 지금 당장 할 일 |
| Overdue | 미뤄진 일 정리 |
| Action | 노트 생성 |

---

## 4. 기능별 상세 설명

### 4.1 Q&A Mode
- 질문을 기반으로 관련 노트를 검색하고 요약
- 단순 검색이 아니라 “맥락”을 함께 제공

예시:
내 논문 방향 뭐였지?  
→ BERT4Rec 기반 + 시간 정보 통합  
→ 관련 노트: 논문.md, 미팅.md  

---

### 4.2 Planning Mode
- 목표와 마감일을 기반으로 WBS 생성

예시:
논문 5월까지 끝내고 싶어  

→ WBS  
1. 데이터셋 선정  
2. baseline 구현  
3. 실험  
4. 작성  

---

### 4.3 Priority Mode
- 현재 상황에서 가장 중요한 작업 선정

기준:
- 중요도
- 긴급도
- dependency

---

### 4.4 Focus Mode
- 지금 확보된 시간 기준으로 실행 task 추천

예시:
오늘 2시간 뭐할까?  

→ dataset 비교 (90분)  
→ 목표: 하나 선택  

---

### 4.5 Overdue Mode
- 마감일이 지난 task를 찾아 재배치 제안

특징:
- 단순 날짜 변경이 아니라
- 전체 맥락 기반 재조정

---

### 4.6 Action Mode
- 결과를 markdown 노트로 생성

예시:
- 논문_실행계획.md  
- 이번주_우선순위.md  

---

## 5. Agent 실행 흐름

### 기본 흐름

User Input  
↓  
Intent 판단  
↓  
(Understand → Plan → Execute 중 선택)  
↓  
결과 출력 (+ 노트 생성)  

---

### 실제 동작 예시

입력: "논문 해야 하는데 뭐부터 하지?"  

1. Q&A → 현재 논문 상태 확인  
2. Priority → dataset 선정이 가장 중요  
3. Focus → 오늘 dataset 비교 추천  
4. Action → focus 노트 생성  

---

## 6. MVP 범위

초기 구현은 아래 기능만 포함한다:

- Q&A (간단 검색)
- Planning (WBS 생성)
- Priority / Focus
- Overdue (조회 + 제안)
- Action (노트 생성)

제외 기능:

- 자동 병목 분석
- 일정 충돌 계산
- 파일 수정

---

## 7. 기대 효과

- vault를 단순 저장소가 아니라 **실행 시스템으로 전환**
- “뭐 해야 하지?” 고민 감소
- 미뤄진 일 관리 자동화
- 계획 → 실행 연결 강화

---

## 8. 한 줄 정의

**Obsidian Execution Agent =  
지식, 계획, 할 일을 연결하여 실행을 만들어주는 개인 agent**
