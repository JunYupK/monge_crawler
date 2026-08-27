# 작업 전에 스킬부터 확인한다

작업을 시작하기 전에 `.claude/skills/` 의 스킬 목록을 먼저 확인하고,
해당하는 스킬이 있으면 그 절차를 따른다. 사용자에게 질문을 되묻기 전에도
먼저 확인한다.

이 저장소는 [obra/superpowers](https://github.com/obra/superpowers) 스킬을
`.claude/skills/` 에 벤더링해 두었다. 업스트림에 있던 `SessionStart` 훅은
벤더링하면 빠지므로, 매 세션 "답하기 전에 스킬부터 찾아라" 를 강제하던
그 훅의 자리를 이 절이 대신 메운다.

## 스킬 이름에 `superpowers:` 접두사가 없다

벤더링된 스킬은 플러그인이 아니라 프로젝트 스킬이므로 이름에
`superpowers:` 접두사가 **붙지 않는다**. 다른 문서나 스킬 본문에
`superpowers:executing-plans` 처럼 적혀 있어도, 이 저장소에서 실제로
호출할 이름은 `executing-plans` 다. 접두사를 떼고 사용한다.

벤더링 출처와 갱신 절차는 `.claude/README.md` 를 참고한다.
