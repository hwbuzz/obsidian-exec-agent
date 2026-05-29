from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


MARKDOWN_EXTENSIONS = {".md", ".markdown"}
CONFIG_FILE = ".agent_config.json"
ENV_FILE = ".env"
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-flash-lite-latest"]
MAX_OUTPUT_TOKENS = 2048
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


@dataclass(frozen=True)
class AppConfig:
    vault: Path | None = None
    model: str = DEFAULT_MODEL


class AgentError(RuntimeError):
    pass


def load_dotenv(path: Path = Path(ENV_FILE)) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_config(path: Path = Path(CONFIG_FILE)) -> AppConfig:
    if not path.exists():
        return AppConfig()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    vault = Path(data["vault"]).expanduser() if data.get("vault") else None
    model = data.get("model") or DEFAULT_MODEL
    return AppConfig(vault=vault, model=model)


def save_config(config: AppConfig, path: Path = Path(CONFIG_FILE)) -> None:
    data = {
        "vault": str(config.vault) if config.vault else None,
        "model": config.model,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_vault(cli_vault: Path | None, config: AppConfig) -> Path:
    vault = cli_vault or config.vault or Path.cwd()
    return vault.expanduser().resolve()


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


def call_gemini(prompt: str, model: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise AgentError(
            "GEMINI_API_KEY가 설정되어 있지 않습니다. .env 파일에 GEMINI_API_KEY=... 형태로 추가하세요."
        )

    attempted: list[str] = []
    errors: list[str] = []
    for candidate_model in [model, *[item for item in FALLBACK_MODELS if item != model]]:
        attempted.append(candidate_model)
        try:
            return call_gemini_once(prompt, candidate_model, api_key)
        except AgentError as exc:
            message = str(exc)
            errors.append(f"[{candidate_model}] {message}")
            if "HTTP 400" in message or "HTTP 401" in message or "HTTP 403" in message:
                break
            if "HTTP 503" in message:
                time.sleep(2)
                try:
                    return call_gemini_once(prompt, candidate_model, api_key)
                except AgentError as retry_exc:
                    errors.append(f"[{candidate_model} retry] {retry_exc}")
            continue

    raise AgentError(
        "Gemini API 호출에 실패했습니다.\n"
        f"시도한 모델: {', '.join(attempted)}\n"
        + "\n".join(errors)
    )


def call_gemini_once(prompt: str, model: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AgentError(f"Gemini API 호출 실패: HTTP {exc.code}\n{body}") from exc
    except urllib.error.URLError as exc:
        raise AgentError(f"Gemini API 네트워크 오류: {exc.reason}") from exc

    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as exc:
        raise AgentError(f"Gemini API 응답에서 텍스트를 찾지 못했습니다:\n{json.dumps(data, ensure_ascii=False)}") from exc
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise AgentError("Gemini API가 빈 응답을 반환했습니다.")
    return text


def build_context(vault: Path, results: list[SearchResult], query: str = "", max_chars_per_note: int = 1600) -> str:
    if not results:
        return "관련 노트를 찾지 못했습니다."
    blocks: list[str] = []
    keywords = tokenize(query)
    for result in results:
        rel = result.note.path.relative_to(vault)
        snippets = "\n".join(f"- {snippet}" for snippet in result.snippets) or "- 관련 snippet 없음"
        excerpt = make_excerpt(result.note.text, keywords, max_chars=max_chars_per_note)
        blocks.append(
            f"노트: {rel}\n"
            f"제목: {result.note.title}\n"
            f"검색 점수: {result.score}\n"
            f"검색 근거:\n{snippets}\n\n"
            f"본문 excerpt:\n{excerpt}"
        )
    return "\n\n---\n\n".join(blocks)


def make_excerpt(text: str, keywords: list[str], max_chars: int = 3500) -> str:
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean
    lower = clean.lower()
    hit_positions = [lower.find(keyword) for keyword in keywords if lower.find(keyword) >= 0]
    if not hit_positions:
        return clean[:max_chars].rstrip() + "\n..."
    center = min(hit_positions)
    start = max(0, center - max_chars // 3)
    end = min(len(clean), start + max_chars)
    excerpt = clean[start:end].strip()
    prefix = "...\n" if start > 0 else ""
    suffix = "\n..." if end < len(clean) else ""
    return prefix + excerpt + suffix


def answer_question(vault: Path, query: str, limit: int, model: str) -> str:
    notes = load_notes(vault)
    results = search_notes(notes, query, limit=limit)
    context = build_context(vault, results, query=query)
    prompt = f"""너는 Obsidian vault를 읽고 사용자의 다음 행동을 돕는 개인 실행 agent다.

사용자 질문:
{query}

검색된 vault 근거:
{context}

요구사항:
- 반드시 위 근거를 바탕으로 답하라.
- 근거가 부족하면 부족하다고 말하고, 추가로 확인할 노트/질문을 제안하라.
- 답변은 한국어 markdown으로 작성하라.
- 마지막에 "관련 노트"와 "다음 액션" 섹션을 포함하라.
"""
    return call_gemini(prompt, model)


def create_plan(goal: str, vault: Path, model: str, limit: int) -> str:
    deadline = extract_deadline(goal)
    inferred_steps = infer_wbs(goal)
    notes = load_notes(vault)
    results = search_notes(notes, goal, limit=limit)
    context = build_context(vault, results, query=goal)
    template = "\n".join(f"{idx}. {step}" for idx, step in enumerate(inferred_steps, start=1))
    prompt = f"""너는 Obsidian vault를 읽고 목표를 실행 계획으로 바꾸는 Planning Assistant다.

사용자 목표:
{goal}

감지된 마감 힌트:
{deadline or "없음"}

초기 WBS 후보:
{template}

관련 vault 근거:
{context}

요구사항:
- 반드시 LLM이 직접 계획을 재구성하라. 초기 WBS 후보를 그대로 복사하지 말고 목표와 vault 근거에 맞게 조정하라.
- 답변은 한국어 markdown으로 작성하라.
- 섹션은 "목표 해석", "WBS", "이번 주 우선순위", "리스크", "오늘 시작할 작업", "관련 노트"를 포함하라.
- WBS는 실행 가능한 작업 단위로 작성하라.
"""
    return call_gemini(prompt, model)


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
    base = target_dir / f"{date.today().isoformat()}_{safe_title}.md"
    path = base
    counter = 2
    while path.exists():
        path = target_dir / f"{date.today().isoformat()}_{safe_title}_{counter}.md"
        counter += 1
    path.write_text(content + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Obsidian Execution Agent MVP")
    parser.add_argument("--vault", type=Path, default=None, help="Obsidian vault path")
    parser.add_argument("--model", default=None, help=f"Gemini model name. Default: {DEFAULT_MODEL}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config = subparsers.add_parser("config", help="초기 설정 확인/변경")
    config.add_argument("--vault", type=Path, help="기본 Obsidian vault 경로 저장")
    config.add_argument("--model", help="기본 Gemini model 저장")
    config.add_argument("--show", action="store_true", help="현재 설정 출력")

    ask = subparsers.add_parser("ask", help="Mode 1: vault 기반 Q&A 검색")
    ask.add_argument("query", help="질문")
    ask.add_argument("--limit", type=int, default=5, help="표시할 관련 노트 수")

    plan = subparsers.add_parser("plan", help="Mode 2: 목표를 WBS로 변환")
    plan.add_argument("goal", help="계획으로 바꿀 목표")
    plan.add_argument("--write", action="store_true", help="계획 결과를 markdown 노트로 저장")
    plan.add_argument("--limit", type=int, default=5, help="계획에 참고할 관련 노트 수")

    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    model = args.model or config.model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL

    if args.command == "config":
        updated = AppConfig(vault=config.vault, model=config.model)
        if args.vault:
            updated = AppConfig(vault=args.vault.expanduser().resolve(), model=updated.model)
        if args.model:
            updated = AppConfig(vault=updated.vault, model=args.model)
        if args.vault or args.model:
            save_config(updated)
            config = updated
            print(f"설정 저장 완료: {Path(CONFIG_FILE).resolve()}")
        if args.show or not (args.vault or args.model):
            print(f"vault: {config.vault or '(미설정 - 현재 폴더 사용)'}")
            print(f"model: {config.model}")
            print(f"env: {Path(ENV_FILE).resolve()}")
        return

    vault = resolve_vault(args.vault, config)

    try:
        if args.command == "ask":
            print(answer_question(vault, args.query, args.limit, model))
            return

        if args.command == "plan":
            content = create_plan(args.goal, vault, model, args.limit)
            print(content)
            if args.write:
                path = write_note(vault, "execution_plan", content)
                print(f"\n생성된 노트: {path}")
            return
    except (AgentError, FileNotFoundError) as exc:
        parser.exit(status=1, message=f"오류: {exc}\n")


if __name__ == "__main__":
    main()
