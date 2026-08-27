# .claude/ — 벤더링된 스킬

이 디렉터리에는 저장소에 고정(vendoring)된 Claude 스킬이 들어 있다.
매 세션 새 컨테이너로 뜨는 원격 환경에서도 스킬이 항상 로드되도록,
스킬 폴더를 `.claude/skills/` 바로 아래에 **평평하게(flat)** 둔다.

## 왜 이 방식인가

다음 두 방식은 이 저장소에서 실측으로 동작하지 않아 쓰지 않는다.

- `.claude/settings.json` 의 `extraKnownMarketplaces` / `enabledPlugins`:
  이건 선언일 뿐 설치가 아니다. 실제 설치 기록은 사용자 레벨
  `~/.claude/plugins/installed_plugins.json` 에 프로젝트 경로별로 남고
  저장소를 따라가지 않는다. 새 세션에서 스킬이 하나도 뜨지 않는다.
- `.claude/skills/superpowers/.claude-plugin/plugin.json` 으로
  프로젝트 스코프 플러그인을 만드는 방식: 워크스페이스 신뢰(trust)를
  수락하기 전까지 억제되므로, 매번 새 컨테이너로 뜨는 세션에서는
  역시 하나도 뜨지 않는다.

유일하게 동작하는 형태는 스킬 폴더를 `.claude/skills/` 바로 아래에
평평하게 두는 것이다.

## 스킬 이름에 접두사가 없다

벤더링된 스킬은 폴더 이름 그대로가 스킬 이름이다. `superpowers:` 같은
플러그인 접두사가 **붙지 않는다**. 문서에서 `superpowers:executing-plans`
라고 적혀 있어도 이 저장소에서의 실제 이름은 `executing-plans` 다.

## 벤더링 출처

- 업스트림: [obra/superpowers](https://github.com/obra/superpowers)
- 버전: **v6.3.0**
- 커밋: **b36e0829c6d0140e93cfef2ca599b1b07d4a7797**
- 라이선스: MIT (`.claude/SUPERPOWERS-LICENSE`, Copyright (c) 2025 Jesse Vincent)

`skills/` 를 그대로 `.claude/skills/` 로 복사했으며 파일 내용은 수정하지 않았다.

## 업스트림 갱신 절차 (수동)

자동 갱신은 없다. 새 버전을 반영하려면 수동으로 다음을 수행한다.

```sh
# 1. 원하는 릴리스/커밋 체크아웃
git clone https://github.com/obra/superpowers.git /tmp/superpowers
cd /tmp/superpowers
git checkout <새 커밋 해시>

# 2. 기존 스킬을 통째로 교체 (내용 수정 없이 복사)
rm -rf <이 저장소>/.claude/skills
mkdir -p <이 저장소>/.claude/skills
cp -R skills/. <이 저장소>/.claude/skills/
cp LICENSE <이 저장소>/.claude/SUPERPOWERS-LICENSE

# 3. 이 README 의 버전/커밋 해시를 갱신하고 커밋
```

업스트림의 `SessionStart` 훅은 벤더링 시 함께 오지 않는다. 그 훅이 매 세션
`using-superpowers` 를 주입해 "답하기 전에 스킬부터 찾아라" 를 강제하던
역할은 저장소 최상단 `CLAUDE.md` 의 첫 절이 대신한다.
