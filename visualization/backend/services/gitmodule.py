import pygit2
import logging
import json
from typing import List, Dict
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_repo(path: str) -> pygit2.Repository:
    return pygit2.Repository(path)

def is_service_commit(commit: pygit2.Commit) -> bool:
    service_keywords = ['merge', 'fixup', 'squash']
    message = commit.message.lower()
    return any(keyword in message for keyword in service_keywords)

def get_commit_ids_for_lines(
    repo: pygit2.Repository,
    file_path: str,
    start: int,
    end: int
) -> List[str]:
    """
    Возвращает уникальные SHA-коммиты, затронувшие строки [start..end].
    Фильтрует «сервисные» коммиты.
    """
    try:
        blame = repo.blame(
            file_path,
            min_line=start,
            max_line=end,
            flags=(
                pygit2.GIT_BLAME_TRACK_COPIES_SAME_FILE
                | pygit2.GIT_BLAME_TRACK_COPIES_SAME_COMMIT_MOVES
            )
        )
    except KeyError:
        logger.warning(f"File {file_path} is not committed yet")
        return []
    commits = []
    for hunk in blame:
        commit = repo[hunk.orig_commit_id]
        if not is_service_commit(commit):
            commits.append(str(hunk.orig_commit_id))

    unique = list(set(commits))
    logger.info(f"Found {len(unique)} unique commits for lines {start}-{end} in {file_path}")
    return unique

def fetch_commit(
    repo: pygit2.Repository,
    commit_hash: str,
    context_lines: int = 3,
    max_hunks: int = 5
) -> Dict:
    commit = repo.get(commit_hash)
    message = commit.message.strip().splitlines()[0]

    files = []
    hunks = []
    if commit.parents:
        parent = commit.parents[0]
        diff = parent.tree.diff_to_tree(
            commit.tree,
            context_lines=context_lines,
            interhunk_lines=1
        )
        for i, patch in enumerate(diff):
            if i >= max_hunks:
                break

            # путь файла
            path = patch.delta.new_file.path or patch.delta.old_file.path
            files.append(path)

            # вытаскиваем первые строки из patch.text
            text = patch.text or ""
            snippet = "\n".join(text.splitlines()[:context_lines*2 + 5])
            hunks.append(snippet)
    else:
        # initial commit
        for entry in commit.tree:
            files.append(entry.name)

    return {
        "message": message,
        "files": files,
        "diff_hunks": hunks
    }


def get_information_for_commits(
    repo: pygit2.Repository,
    commits: List[str]
) -> List[Dict]:
    """
    Для списка SHA возвращает список объектов с метаданными.
    """
    info = []
    for sha in commits:
        meta = fetch_commit(repo, sha)
        info.append(meta)
    return info

def compute_coupling(
    commits_meta: List[Dict],
    target_file: str,
    top_n: int = 10
) -> List[Dict]:
    """
    Считает частоту совместных правок.
    """
    counter = Counter()

    for commit in commits_meta:
        for f in commit["files"]:
            if f != target_file:
                counter[f] += 1

    result = []
    for f, count in counter.most_common(top_n):
        result.append({
            "file": f,
            "count": count,
        })
    return result

def build_llm_prompt(
    target: dict,
    commits_meta: list[dict],
    coupling: list[dict],
    *,
    max_commits: int = 3,
    max_coupled: int = 10,
    max_recommendations: int = 5,
) -> str:
    """
    Формирует минималистичный и строго структурированный prompt.
    """

    # --- 1. Функция ---
    header = (
        "### Функция\n"
        f"{target['file']} (строки {target['start']}–{target['end']})"
    )

    # --- 2. Coupling ---
    coupled_lines = [
        f"{i}. {item['file']} — {item['count']} раз"
        for i, item in enumerate(coupling[:max_coupled], 1)
    ]
    coupling_block = (
        "### Часто сопутствующие файлы\n" +
        ("\n".join(coupled_lines) if coupled_lines else "_нет данных_")
    )

    # --- 3. Коммиты ---
    commits_block_lines = []
    for meta in commits_meta[:max_commits]:
        date = meta.get("date", "")[:10]
        sha = meta.get("sha", "")[:7]
        msg = meta["message"][:120]
        commits_block_lines.append(f"- {date} {sha}: {msg}")
    commits_block = (
        "### Последние коммиты по функции\n" +
        ("\n".join(commits_block_lines) if commits_block_lines else "_нет коммитов_")
    )

    # --- 4. Формат ответа ---
    answer_format = (
        "### Формат ответа\n"
        "- Выведи **не более 5 файлов**.\n"
        "- Только маркированный список.\n"
        "- Каждая строка: `<путь>` — 1 краткое пояснение (не более 1 предложения).\n"
        "- **Не пиши вступление, выводы и обобщения.**\n"
        "- **Избегай общих фраз** типа «может быть полезен», «возможно связан».\n\n"
        "Пример:\n"
        "- `tests/test_parse.c` — проверяет поведение функции при некорректных строках.\n"
        "- `utils/memory.c` — содержит аналогичный аллокатор, который часто меняется вместе.\n"
    )

    # --- 5. System-инструкция ---
    system_msg = (
        "Ты — старший инженер проекта н "
        "На основе исторических данных и списка совместно меняющихся файлов "
        "выбери максимум 5 файлов, которые следует проверить при изменении функции. "
        "Отвечай кратко, точно и строго в заданном формате."
    )

    # --- 6. Склейка ---
    prompt = (
        f"System:\n{system_msg}\n\n"
        f"User:\n{header}\n\n{coupling_block}\n\n{commits_block}\n\n{answer_format}"
    )

    return prompt 