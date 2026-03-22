# Basic Pipeline

## 과제1

- 어린이 동화책 만들기의 기초를 구축하세요!
- 함께 작동하는 두 개의 에이전트를 만드세요:

## 요구사항

- Google ADK를 사용하여 두 개의 에이전트를 만드세요.
  - Story Writer Agent: 테마를 전달 받아 5페이지 분량의 어린이 동화를 구조화된 데이터(페이지 텍스트 + 시각 설명) 형태로 작성합니다.
  - Illustrator Agent: State에서 데이터를 읽어 각 페이지의 이미지를 생성합니다.
- Agent State를 사용하여 두 에이전트가 서로 스토리 데이터를 공유하도록 구현하세요.
- ADK Web UI (adk web)로 테스트하세요.

## 예시 출력

```
Page 1:
Text: "옛날 옛적에, 베니라는 작은 토끼가 살았습니다."
Visual: "버섯 집 앞에 서 있는 작은 흰 토끼"
Image: [생성된 이미지가 Artifact로 저장됨]

Page 2:
Text: "베니는 탐험을 좋아했는데, 오늘은 하늘이 보라색이었어요!"
Visual: "보라색 하늘을 올려다보는 토끼"
Image: [생성된 이미지가 Artifact로 저장됨]
...
```

# Weekend Mission: Complete Story Book Maker

## Workflow Agent를 활용하여 어린이 동화책 만들기를 완성하세요

- 파이프라인에 다음 기능을 추가하세요:
  - SequentialAgent - Writer → Illustrator 흐름을 관리
  - ParallelAgent - 5개의 삽화를 동시에 생성
  - Callbacks - 진행 상황 표시 ("스토리 작성 중...", "이미지 1/5 생성 중...")

## 전체 파이프라인

```text
[사용자 입력: "용감한 아기 고양이 이야기"]
                    ↓
           [Sequential Agent]
                    ↓
           [Story Writer Agent]
            - 5페이지짜리 동화 작성
            - Agent State에 저장
                    ↓
           [Parallel Agent]
            - 5개의 이미지를 동시에 생성
            - Artifacts로 저장
                    ↓
    [최종 출력: 완성된 동화책]
    - 제목
    - 텍스트가 포함된 5페이지
    - 각 페이지에 어울리는 5개의 삽화
```
