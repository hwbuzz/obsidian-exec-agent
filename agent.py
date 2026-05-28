from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


MARKDOWN_EXTENSIONS = {".md", ".markdown"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "what",
    "when",
    "where",
    "how",
    "why",
    "내",
    "내가",
    "뭐",
    "무엇",
    "어떤",
    "관련",
    "해서",
    "하고",
    "있는",
    "있어",
    "정리",
    "보여줘",
    "알려줘",
    "계획",
    "만들어줘",
}


@dataclass(frozen=True)
class Note:
    path: Path
    title: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    note: Note
    score: int
    snippets: list[str]


def load_notes(vault: Path) -> list[Note]:
    if not vault.exists():
        raise FileNotFoundError(f"Vault path does not exist: {vault}")

    notes: list[Note] = []
    for path in sorted(vault.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MARKDOWN_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp949", errors="ignore")
        title = extract_title(path, text)
        notes.append(Note(path=path, title=title, text=text))
    return notes


def extract_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9가-힣_#/-]+", text.lower())
    return [token for token in tokens if len(token) >= 2 and token not in STOPWORDS]


def search_notes(notes: Iterable[Note], query: str, limit: int = 5) -> list[SearchResult]:
    keywords = tokenize(query)
    if not keywords:
        return []

    results: list[SearchResult] = []
    for note in notes:
        haystack = f"{note.title}\n{note.text}".lower()
        score = 0
        for keyword in keywords:
            title_hits = note.title.lower().count(keyword)
            body_hits = haystack.count(keyword)
            score += title_hits * 5 + body_hits
        if score <= 0:
            continue
        results.append(SearchResult(note=note, score=score, snippets=make_snippets(note.text, keywords)))

    return sorted(results, key=lambda item: (-item.score, str(item.note.path)))[:limit]


def make_snippets(text: str, keywords: list[str], max_snippets: int = 3) -> list[str]:
    snippets: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        lower = clean.lower()
        if any(keyword in lower for keyword in keywords):
            snippets.append(clean[:180])
        if len(snippets) >= max_snippets:
            break
    return snippets


def answer_question(vault: Path, query: str, limit: int) -> str:
    notes = load_notes(vault)
    results = search_notes(notes, query, limit=limit)
    if not results:
        return (
            "관련 노트를 찾지 못했습니다.\n\n"
            f"- 검색한 vault: {vault}\n"
            "- 팁: 질문에 프로젝트명, 키워드, 사람 이름, 파일명 일부를 넣어보세요."
        )

    lines = [
        "## 답변 초안",
        "아래 노트들이 질문과 가장 관련 있어 보입니다. 아직은 LLM 요약이 아니라 키워드 기반 MVP라서, 관련 근거를 먼저 모아 보여줍니다.",
        "",
        "## 관련 노트",
    ]
    for idx, result in enumerate(results, start=1):
        rel = result.note.path.relative_to(vault)
        lines.append(f"{idx}. {result.note.title} ({rel}) - score {result.score}")
        for snippet in result.snippets:
            lines.append(f"   - {snippet}")
    lines.extend(
        [
            "",
            "## 다음 액션 후보",
            "- 관련 노트 중 상위 1-2개를 열어 현재 결론/미완료 항목을 확인하세요.",
            "- 더 구체적인 질문으로 다시 실행하면 검색 범위가 좁아집니다.",
        ]
    )
    return "\n".join(lines)


def create_plan(goal: str) -> str:
    deadline = extract_deadline(goal)
    inferred_steps = infer_wbs(goal)
    lines = [
        "## 실행 계획 초안",
        f"- 목표: {goal}",
    ]
    if deadline:
        lines.append(f"- 감지된 마감 힌트: {deadline}")
    lines.extend(["", "## WBS"])
    for idx, step in enumerate(inferred_steps, start=1):
        lines.append(f"{idx}. {step}")
    lines.extend(
        [
            "",
            "## 이번 주 우선순위",
            "1. 산출물의 완료 기준을 한 문장으로 확정",
            "2. 가장 불확실한 선행 조건 하나를 먼저 제거",
            "3. 다음 실행 결과를 Obsidian 노트로 남기기",
            "",
            "## 리스크",
            "- 목표 범위가 넓으면 첫 주에 조사만 하다가 끝날 수 있습니다.",
            "- 마감일이 있다면 초안/검토/수정 시간을 분리해야 합니다.",
            "",
            "## 추천",
            "- 오늘은 60-90분짜리 첫 작업 하나만 정해서 시작하세요.",
        ]
    )
    return "\n".join(lines)


def extract_deadline(goal: str) -> str | None:
    patterns = [
        r"\d{1,2}월\s*\d{1,2}일",
        r"\d{1,2}월\s*말",
        r"\d{1,2}주\s*안",
        r"이번\s*주",
        r"이번\s*달",
        r"오늘",
        r"내일",
    ]
    for pattern in patterns:
        match = re.search(pattern, goal)
        if match:
            return match.group(0)
    return None


def infer_wbs(goal: str) -> list[str]:
    lower = goal.lower()
    if any(keyword in lower for keyword in ["논문", "paper", "thesis"]):
        return [
            "현재 주제와 연구 질문 정리",
            "관련 노트와 참고문헌 재검토",
            "데이터셋/실험 범위 확정",
            "baseline 또는 비교 기준 구현",
            "실험 결과 정리",
            "초안 작성",
            "피드백 반영 및 최종 수정",
        ]
    if any(keyword in lower for keyword in ["agent", "앱", "서비스", "프로젝트", "plugin", "플러그인"]):
        return [
            "핵심 사용자 흐름 정의",
            "MVP 기능 범위 확정",
            "입력/출력 데이터 구조 설계",
            "작게 동작하는 첫 버전 구현",
            "실제 예시 데이터로 테스트",
            "사용법 문서화",
            "다음 개선 목록 정리",
        ]
    if any(keyword in lower for keyword in ["공부", "학습", "강의", "시험"]):
        return [
            "학습 범위 목록화",
            "이미 아는 것과 모르는 것 분리",
            "핵심 개념 1차 정리",
            "예제/문제 풀이",
            "오답 또는 막힌 지점 정리",
            "최종 요약 노트 작성",
        ]
    return [
        "목표의 완료 기준 정의",
        "필요한 자료와 현재 상태 확인",
        "작업을 30-90분 단위로 분해",
        "가장 중요한 선행 작업 선택",
        "첫 산출물 만들기",
        "검토 후 다음 작업 재계획",
    ]


def write_note(vault: Path, title: str, content: str, folder: str = "Agent Notes") -> Path:
    target_dir = vault / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title).strip() or "agent_note"
    path = target_dir / f"{date.today().isoformat()}_{safe_title}.md"
    path.write_text(content + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Obsidian Execution Agent MVP")
    parser.add_argument("--vault", type=Path, default=Path.cwd(), help="Obsidian vault path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="Mode 1: vault 기반 Q&A 검색")
    ask.add_argument("query", help="질문")
    ask.add_argument("--limit", type=int, default=5, help="표시할 관련 노트 수")

    plan = subparsers.add_parser("plan", help="Mode 2: 목표를 WBS로 변환")
    plan.add_argument("goal", help="계획으로 바꿀 목표")
    plan.add_argument("--write", action="store_true", help="계획 결과를 markdown 노트로 저장")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    vault = args.vault.resolve()

    if args.command == "ask":
        print(answer_question(vault, args.query, args.limit))
        return

    if args.command == "plan":
        content = create_plan(args.goal)
        print(content)
        if args.write:
            path = write_note(vault, "execution_plan", content)
            print(f"\n생성된 노트: {path}")
        return


if __name__ == "__main__":
    main()
