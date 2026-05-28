# Obsidian Execution Agent MVP

Obsidian vault를 읽어서 실행을 돕는 toy agent입니다. 현재는 설계안의 7개 모드 중 아래 2개 모드만 구현되어 있습니다.

- Mode 1: Q&A Mode
- Mode 2: Planning Mode

## 사용법

현재 폴더를 vault처럼 사용하려면:

```powershell
python agent.py ask "논문 방향 뭐였지?"
python agent.py plan "논문 초안을 5월 말까지 쓰고 싶어"
```

다른 Obsidian vault를 대상으로 실행하려면:

```powershell
python agent.py --vault "C:\path\to\vault" ask "BERT4Rec 관련해서 내가 정리한 내용 보여줘"
python agent.py --vault "C:\path\to\vault" plan "codex toy agent를 2주 안에 만들고 싶어"
```

계획 결과를 vault 안에 markdown 노트로 저장하려면:

```powershell
python agent.py --vault "C:\path\to\vault" plan "pytest 공부를 이번 달 안에 끝내고 싶어" --write
```

저장 위치:

```text
Agent Notes/YYYY-MM-DD_execution_plan.md
```

## 현재 구현 범위

### Q&A Mode

- vault 아래의 `.md`, `.markdown` 파일을 재귀적으로 읽습니다.
- 질문에서 키워드를 뽑고 관련 노트를 점수화합니다.
- 관련 노트와 근거 snippet을 출력합니다.

### Planning Mode

- 목표 문장에서 마감 힌트를 간단히 감지합니다.
- 논문, agent/project, 공부 목표에 대해 기본 WBS를 생성합니다.
- `--write` 옵션으로 계획 노트를 생성합니다.

## 다음 후보

- Focus Mode: 확보 시간 기준으로 오늘 할 일 추천
- Overdue Mode: `- [ ] task 📅 YYYY-MM-DD` 형태의 지난 task 탐지
- Action Mode 확장: focus/overdue 결과도 markdown으로 저장
